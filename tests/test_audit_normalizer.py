import gzip
import io
import json
import unittest

from audit_normalizer import app


class FakeS3:
    def __init__(self, content):
        self.content = content
        self.get_requests = []
        self.quarantine_objects = []

    def get_object(self, **request):
        self.get_requests.append(request)
        return {"Body": io.BytesIO(self.content)}

    def put_object(self, **request):
        self.quarantine_objects.append(request)


class FakeFirehose:
    def __init__(self, responses=None):
        self.calls = []
        self.responses = list(responses or [])

    def put_record_batch(self, **request):
        self.calls.append(request)
        if self.responses:
            return self.responses.pop(0)
        return {
            "FailedPutCount": 0,
            "RequestResponses": [{"RecordId": "accepted"} for _ in request["Records"]],
        }


def sqs_event(key="2026/09/03/04/45/event.json.log.gz", size=100):
    body = {
        "source": "aws.s3",
        "detail-type": "Object Created",
        "detail": {
            "bucket": {"name": "raw-audit-bucket"},
            "object": {"key": key, "size": size, "version-id": "version-1"},
        },
    }
    return {"Records": [{"messageId": "message-1", "body": json.dumps(body)}]}


class AuditNormalizerTests(unittest.TestCase):
    def setUp(self):
        app.SOURCE_BUCKET = "raw-audit-bucket"
        app.QUARANTINE_BUCKET = "data-lake-bucket"
        app.DESTINATION_STREAM_NAME = "audit-bronze"
        app.FIREHOSE_MAX_ATTEMPTS = 3
        app._clients.clear()

    def test_normalizes_a_github_audit_event(self):
        source_event = {
            "@timestamp": 1788400000123,
            "_document_id": "document-1",
            "action": "repo.create",
            "actor": "octocat",
            "actor_id": "42",
            "org": "example-org",
            "org_id": 7,
            "repo": "example-org/example-repo",
            "repo_id": 99,
            "actor_ip": "192.0.2.10",
        }
        app._clients["s3"] = FakeS3(gzip.compress(json.dumps(source_event).encode("utf-8")))
        firehose = FakeFirehose()
        app._clients["firehose"] = firehose

        result = app.lambda_handler(sqs_event(), None)

        self.assertEqual(result, {"batchItemFailures": []})
        normalized = json.loads(firehose.calls[0]["Records"][0]["Data"])
        self.assertEqual(normalized["document_id"], "document-1")
        self.assertEqual(normalized["action_category"], "repo")
        self.assertEqual(normalized["action_name"], "create")
        self.assertEqual(normalized["organization"], "example-org")
        self.assertEqual(normalized["repository_id"], 99)
        self.assertEqual(normalized["source_ip"], "192.0.2.10")
        self.assertEqual(normalized["source_object_version"], "version-1")
        self.assertEqual(normalized["record_family"], "audit")
        self.assertIsNone(normalized["copilot_record_type"])
        self.assertRegex(normalized["event_timestamp"], r"^2026-09-03T")

    def test_uses_payload_hash_when_source_ids_are_absent(self):
        source_event = {"@timestamp": 1788400000123, "action": "repo.create"}
        app._clients["s3"] = FakeS3(gzip.compress(json.dumps(source_event).encode("utf-8")))
        firehose = FakeFirehose()
        app._clients["firehose"] = firehose

        result = app.lambda_handler(sqs_event(), None)

        self.assertEqual(result, {"batchItemFailures": []})
        normalized = json.loads(firehose.calls[0]["Records"][0]["Data"])
        self.assertEqual(normalized["document_id"], normalized["payload_sha256"])

    def test_normalizes_copilot_usage_record_envelopes(self):
        source_events = [
            {
                "@timestamp": 1788400000123,
                "event_id": "copilot-request-1",
                "github_request_id": "github-request-1",
                "type": "request",
                "user_id": 42,
                "enterprise_id": 7,
                "endpoint": "/v1/messages",
                "body": json.dumps({"model": "test-model", "messages": []}),
                "headers": {"Authorization": "[REDACTED]"},
                "truncated": True,
            },
            {
                "@timestamp": 1788400000124,
                "event_id": "copilot-response-1",
                "github_request_id": "github-request-1",
                "type": "response",
                "user_id": 42,
                "enterprise_id": 7,
                "endpoint": "/v1/messages",
                "body": "event: message_stop\ndata: {}\n",
            },
        ]
        app._clients["s3"] = FakeS3(gzip.compress(json.dumps(source_events).encode("utf-8")))
        firehose = FakeFirehose()
        app._clients["firehose"] = firehose

        result = app.lambda_handler(sqs_event(), None)

        self.assertEqual(result, {"batchItemFailures": []})
        request = json.loads(firehose.calls[0]["Records"][0]["Data"])
        response = json.loads(firehose.calls[0]["Records"][1]["Data"])
        self.assertEqual(request["document_id"], "copilot-request-1")
        self.assertEqual(request["record_family"], "copilot_usage")
        self.assertEqual(request["copilot_record_type"], "request")
        self.assertEqual(request["event_id"], "copilot-request-1")
        self.assertEqual(request["github_request_id"], "github-request-1")
        self.assertEqual(request["enterprise_id"], 7)
        self.assertEqual(request["endpoint"], "/v1/messages")
        self.assertTrue(request["truncated"])
        self.assertEqual(response["document_id"], "copilot-response-1")
        self.assertEqual(response["copilot_record_type"], "response")
        self.assertFalse(response["truncated"])

    def test_quarantines_malformed_json_without_retrying_the_message(self):
        s3 = FakeS3(gzip.compress(b"not-json"))
        app._clients["s3"] = s3
        app._clients["firehose"] = FakeFirehose()

        result = app.lambda_handler(sqs_event(), None)

        self.assertEqual(result, {"batchItemFailures": []})
        self.assertEqual(len(s3.quarantine_objects), 1)
        quarantine = json.loads(s3.quarantine_objects[0]["Body"])
        self.assertEqual(quarantine["reason"], "invalid_gzip_or_json")
        self.assertNotIn("raw_payload", quarantine)

    def test_quarantines_invalid_gzip_without_retrying_the_message(self):
        s3 = FakeS3(b"not-gzip")
        app._clients["s3"] = s3
        app._clients["firehose"] = FakeFirehose()

        result = app.lambda_handler(sqs_event(), None)

        self.assertEqual(result, {"batchItemFailures": []})
        quarantine = json.loads(s3.quarantine_objects[0]["Body"])
        self.assertEqual(quarantine["reason"], "invalid_gzip_or_json")

    def test_normalizes_consecutive_json_values(self):
        source_events = [
            {"@timestamp": 1788400000123, "_document_id": "one", "action": "repo.create"},
            {"@timestamp": 1788400000124, "_document_id": "two", "action": "repo.destroy"},
        ]
        encoded = "".join(json.dumps(source_event) for source_event in source_events)
        app._clients["s3"] = FakeS3(gzip.compress(encoded.encode("utf-8")))
        firehose = FakeFirehose()
        app._clients["firehose"] = firehose

        result = app.lambda_handler(sqs_event(), None)

        self.assertEqual(result, {"batchItemFailures": []})
        normalized = [json.loads(record["Data"]) for record in firehose.calls[0]["Records"]]
        self.assertEqual([record["document_id"] for record in normalized], ["one", "two"])

    def test_quarantines_an_invalid_record_and_processes_valid_siblings(self):
        source_events = [
            {"@timestamp": 1788400000123, "_document_id": "valid", "action": "repo.create"},
            {"_document_id": "invalid", "action": "repo.destroy"},
        ]
        s3 = FakeS3(gzip.compress(json.dumps(source_events).encode("utf-8")))
        firehose = FakeFirehose()
        app._clients.update({"s3": s3, "firehose": firehose})

        result = app.lambda_handler(sqs_event(), None)

        self.assertEqual(result, {"batchItemFailures": []})
        self.assertEqual(len(firehose.calls[0]["Records"]), 1)
        quarantine = json.loads(s3.quarantine_objects[0]["Body"])
        self.assertEqual(quarantine["reason"], "missing_event_timestamp")
        self.assertEqual(quarantine["source_record_index"], 1)

    def test_retries_only_failed_firehose_records(self):
        source_events = [
            {"@timestamp": 1788400000123, "_document_id": "one", "action": "repo.create"},
            {"@timestamp": 1788400000124, "_document_id": "two", "action": "repo.destroy"},
        ]
        app._clients["s3"] = FakeS3(gzip.compress(json.dumps(source_events).encode("utf-8")))
        firehose = FakeFirehose(
            responses=[
                {
                    "FailedPutCount": 1,
                    "RequestResponses": [
                        {"RecordId": "accepted"},
                        {"ErrorCode": "ServiceUnavailableException"},
                    ],
                },
                {"FailedPutCount": 0, "RequestResponses": [{"RecordId": "accepted"}]},
            ]
        )
        app._clients["firehose"] = firehose

        result = app.lambda_handler(sqs_event(), None)

        self.assertEqual(result, {"batchItemFailures": []})
        self.assertEqual(len(firehose.calls[0]["Records"]), 2)
        self.assertEqual(len(firehose.calls[1]["Records"]), 1)
        retried = json.loads(firehose.calls[1]["Records"][0]["Data"])
        self.assertEqual(retried["document_id"], "two")

    def test_reports_an_invalid_queue_message_as_a_batch_failure(self):
        app._clients["s3"] = FakeS3(b"")
        app._clients["firehose"] = FakeFirehose()
        event = {"Records": [{"messageId": "bad-message", "body": "{}"}]}

        result = app.lambda_handler(event, None)

        self.assertEqual(result, {"batchItemFailures": [{"itemIdentifier": "bad-message"}]})


if __name__ == "__main__":
    unittest.main()