import json
import unittest

from audit_replay import app


class FakeS3:
    def __init__(self, response):
        self.response = response
        self.requests = []

    def list_objects_v2(self, **request):
        self.requests.append(request)
        return self.response


class FakeSqs:
    def __init__(self, failures=None):
        self.requests = []
        self.failures = failures or []

    def send_message_batch(self, **request):
        self.requests.append(request)
        return {"Successful": [], "Failed": self.failures}


class AuditReplayTests(unittest.TestCase):
    def setUp(self):
        app.SOURCE_BUCKET = "raw-audit-bucket"
        app.DESTINATION_QUEUE_URL = "https://sqs.example.test/queue"
        app._clients.clear()

    def test_lists_and_enqueues_only_audit_gzip_objects(self):
        s3 = FakeS3(
            {
                "IsTruncated": False,
                "Contents": [
                    {"Key": "_check", "Size": 1},
                    {"Key": "2026/09/03/event.json.log.gz", "Size": 100},
                ],
            }
        )
        sqs = FakeSqs()
        app._clients.update({"s3": s3, "sqs": sqs})

        result = app.lambda_handler({"prefix": "2026/09/03/"}, None)

        self.assertEqual(result, {"objects_enqueued": 1, "continuation_token": None})
        message = json.loads(sqs.requests[0]["Entries"][0]["MessageBody"])
        self.assertEqual(message["detail"]["bucket"]["name"], "raw-audit-bucket")
        self.assertEqual(message["detail"]["object"]["size"], 100)

    def test_enqueues_an_explicit_object_version(self):
        sqs = FakeSqs()
        app._clients["sqs"] = sqs
        event = {
            "objects": [
                {
                    "key": "2026/09/03/event.json.log.gz",
                    "size": 100,
                    "version_id": "version-1",
                }
            ]
        }

        result = app.lambda_handler(event, None)

        self.assertEqual(result["objects_enqueued"], 1)
        message = json.loads(sqs.requests[0]["Entries"][0]["MessageBody"])
        self.assertEqual(message["detail"]["object"]["version-id"], "version-1")

    def test_raises_when_sqs_rejects_a_replay_message(self):
        app._clients["sqs"] = FakeSqs(failures=[{"Id": "0", "Code": "InternalError"}])
        event = {"objects": [{"key": "2026/09/03/event.json.log.gz"}]}

        with self.assertRaisesRegex(RuntimeError, "SQS rejected"):
            app.lambda_handler(event, None)


if __name__ == "__main__":
    unittest.main()