import gzip
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from copilot_collector import app


class FakeSecretsManager:
    def __init__(self, secret):
        self.secret = secret

    def get_secret_value(self, **request):
        return {"SecretString": json.dumps(self.secret)}


class FakeS3:
    def __init__(self):
        self.objects = {}

    def put_object(self, **request):
        self.objects[request["Key"]] = request["Body"]

    def upload_file(self, filename, bucket, key, ExtraArgs=None):
        self.objects[key] = Path(filename).read_bytes()


class FakeCloudWatch:
    def __init__(self):
        self.requests = []

    def put_metric_data(self, **request):
        self.requests.append(request)


class CopilotCollectorTests(unittest.TestCase):
    def setUp(self):
        app._clients.clear()
        self.s3 = FakeS3()
        app._clients["s3"] = self.s3
        app._clients["cloudwatch"] = FakeCloudWatch()
        self.environment = {
            "DATA_LAKE_BUCKET": "data-lake",
            "ENVIRONMENT": "test",
            "GITHUB_ENTERPRISE_SLUG": "example-enterprise",
        }

    def test_loads_required_github_app_credentials(self):
        credentials = app._secret_credentials(
            "secret-arn",
            FakeSecretsManager(
                {
                    "app_id": "123",
                    "installation_id": "456",
                    "private_key": "private-key",
                }
            ),
        )

        self.assertEqual(credentials["installation_id"], "456")

    def test_rejects_incomplete_github_app_credentials(self):
        with self.assertRaises(ValueError):
            app._secret_credentials(
                "secret-arn",
                FakeSecretsManager({"app_id": "123"}),
            )

    def test_collects_billing_usage_as_raw_and_bronze(self):
        task = {
            "source": "billing",
            "report_type": "ai_credit",
            "report_day": "2026-09-10",
            "collection_date": "2026-09-14",
        }
        response = {
            "organization": "example-org",
            "usageItems": [
                {
                    "product": "Copilot",
                    "sku": "Copilot Premium Request",
                    "model": "example-model",
                    "unitType": "requests",
                    "pricePerUnit": 0.04,
                    "grossQuantity": 2,
                    "grossAmount": 0.08,
                    "discountQuantity": 1,
                    "discountAmount": 0.04,
                    "netQuantity": 1,
                    "netAmount": 0.04,
                }
            ],
        }
        with patch.dict(app.os.environ, self.environment, clear=True), patch.object(
            app,
            "_github_request",
            return_value=(200, {}, json.dumps(response).encode("utf-8")),
        ) as github_request:
            count = app.collect_task(task, "installation-token", "2026-09-14T08:30:00Z")

        self.assertEqual(count, 1)
        github_request.assert_called_once_with(
            "/enterprises/example-enterprise/settings/billing/ai_credit/usage?year=2026&month=9&day=10",
            "installation-token",
        )
        raw_key = (
            "raw/copilot/billing/report_type=ai_credit/report_day=2026-09-10/"
            "collection_date=2026-09-14/response.json"
        )
        bronze_key = (
            "bronze/copilot/billing/year=2026/month=09/day=10/"
            "report_type=ai_credit/collection-2026-09-14.ndjson"
        )
        self.assertIn(raw_key, self.s3.objects)
        record = json.loads(self.s3.objects[bronze_key])
        self.assertEqual(record["organization_login"], "example-org")
        self.assertEqual(record["net_amount"], 0.04)
        self.assertIn("raw_payload", record)
        metric_dimensions = app._clients["cloudwatch"].requests[0]["MetricData"][0][
            "Dimensions"
        ]
        self.assertIn(
            {"Name": "Environment", "Value": "test"}, metric_dimensions
        )

    def test_collects_signed_usage_report_without_archiving_url(self):
        task = {
            "source": "usage",
            "report_type": "users",
            "report_day": "2026-09-10",
            "collection_date": "2026-09-14",
        }
        response = {
            "download_links": ["https://download.example/signed?secret=value"],
            "report_day": "2026-09-10",
        }

        def download_report(url, path):
            path.write_text(
                json.dumps({"user_id": 42, "login": "octocat"}) + "\n",
                encoding="utf-8",
            )

        with patch.dict(app.os.environ, self.environment, clear=True), patch.object(
            app,
            "_github_request",
            return_value=(200, {}, json.dumps(response).encode("utf-8")),
        ) as github_request, patch.object(
            app, "_download_to_path", side_effect=download_report
        ):
            count = app.collect_task(task, "installation-token", "2026-09-14T08:30:00Z")

        self.assertEqual(count, 1)
        github_request.assert_called_once_with(
            "/enterprises/example-enterprise/copilot/metrics/reports/users-1-day?day=2026-09-10",
            "installation-token",
        )
        manifest_key = (
            "raw/copilot/usage/report_type=users/report_day=2026-09-10/"
            "collection_date=2026-09-14/manifest.json"
        )
        manifest = self.s3.objects[manifest_key].decode("utf-8")
        self.assertNotIn("download.example", manifest)
        bronze_key = (
            "bronze/copilot/usage/year=2026/month=09/day=10/"
            "report_type=users/collection-2026-09-14.ndjson"
        )
        record = json.loads(self.s3.objects[bronze_key])
        self.assertEqual(record["user_id"], 42)
        self.assertEqual(record["user_login"], "octocat")

    def test_treats_empty_json_string_usage_response_as_no_data(self):
        task = {
            "source": "usage",
            "report_type": "users",
            "report_day": "2026-09-01",
            "collection_date": "2026-09-14",
        }
        with patch.dict(app.os.environ, self.environment, clear=True), patch.object(
            app,
            "_github_request",
            return_value=(200, {}, b'""'),
        ):
            count = app.collect_task(task, "installation-token", "2026-09-14T08:30:00Z")

        self.assertEqual(count, 0)
        manifest_key = (
            "raw/copilot/usage/report_type=users/report_day=2026-09-01/"
            "collection_date=2026-09-14/manifest.json"
        )
        manifest = json.loads(self.s3.objects[manifest_key])
        self.assertTrue(manifest["no_data"])
        bronze_key = (
            "bronze/copilot/usage/year=2026/month=09/day=01/"
            "report_type=users/collection-2026-09-14.ndjson"
        )
        self.assertEqual(self.s3.objects[bronze_key], b"")

    def test_preserves_client_breakdowns_in_raw_and_bronze_usage_reports(self):
        clients = [
            {
                "client": "opencode",
                "request_count": 12,
                "session_count": 3,
                "token_usage": {
                    "prompt_tokens_sum": 1000,
                    "output_tokens_sum": 200,
                    "avg_tokens_per_request": 100.0,
                },
                "totals_by_model": [
                    {
                        "model": "example-model",
                        "model_selection_mode": mode,
                        "request_count": 2,
                        "token_usage": {
                            "prompt_tokens_sum": 100,
                            "output_tokens_sum": 20,
                            "avg_tokens_per_request": 60.0,
                        },
                    }
                    for mode in (
                        "user_selected", "auto", "product_selected", "other", "unknown",
                        "future_mode",
                    )
                ],
                "future_field": {"preserved": True},
            },
            {"client": "other", "request_count": 0, "totals_by_model": []},
            {"client": "future_client", "request_count": 1},
        ]
        for report_type in ("enterprise", "users"):
            for breakdown in ({}, {"totals_by_client": []}, {"totals_by_client": clients}):
                with self.subTest(report_type=report_type, breakdown=breakdown):
                    task = {
                        "source": "usage",
                        "report_type": report_type,
                        "report_day": "2026-10-23",
                        "collection_date": "2026-10-26",
                    }
                    payload = {"enterprise_id": "1", "user_id": 42, **breakdown}
                    report = (json.dumps(payload) + "\n").encode("utf-8")
                    response = {"download_links": ["https://download.example/report"]}

                    def download_report(url, path):
                        path.write_bytes(report)

                    with patch.dict(
                        app.os.environ, self.environment, clear=True
                    ), patch.object(
                        app,
                        "_github_request",
                        return_value=(200, {}, json.dumps(response).encode("utf-8")),
                    ), patch.object(
                        app, "_download_to_path", side_effect=download_report
                    ):
                        count = app.collect_task(
                            task, "installation-token", "2026-10-26T08:30:00Z"
                        )

                    self.assertEqual(count, 1)
                    raw_key = (
                        f"raw/copilot/usage/report_type={report_type}/report_day=2026-10-23/"
                        "collection_date=2026-10-26/part-000.ndjson"
                    )
                    self.assertEqual(self.s3.objects[raw_key], report)
                    bronze_key = (
                        "bronze/copilot/usage/year=2026/month=10/day=23/"
                        f"report_type={report_type}/collection-2026-10-26.ndjson"
                    )
                    record = json.loads(self.s3.objects[bronze_key])
                    self.assertEqual(json.loads(record["raw_payload"]), payload)

    def test_rejects_invalid_usage_response_shape(self):
        task = {
            "source": "usage",
            "report_type": "users",
            "report_day": "2026-09-01",
            "collection_date": "2026-09-14",
        }
        with patch.dict(app.os.environ, self.environment, clear=True), patch.object(
            app,
            "_github_request",
            return_value=(200, {}, b'[]'),
        ), self.assertRaisesRegex(ValueError, "must be a JSON object"):
            app.collect_task(task, "installation-token", "2026-09-14T08:30:00Z")

    def test_preserves_named_customizations_and_long_tail_without_a_client_limit(self):
        payload = {"enterprise_id": "1", "user_id": 42}
        for name in ("skill", "custom_agent", "mcp", "slash_cmd", "plugin"):
            payload[f"totals_by_{name}"] = [
                {name: f"internal-{name}-{index}", "interaction_count": index + 1}
                for index in range(24)
            ] + [{name: "other", "interaction_count": 50}]
            payload[f"distinct_{name}_use_count"] = 40
        for report_type in ("enterprise", "users"):
            with self.subTest(report_type=report_type), patch.dict(
                app.os.environ, self.environment, clear=True
            ):
                task = {
                    "source": "usage",
                    "report_type": report_type,
                    "report_day": "2026-10-23",
                    "collection_date": "2026-10-26",
                }
                record = app._usage_record(task, payload, 0, "2026-10-26T08:30:00Z")
                self.assertEqual(json.loads(record["raw_payload"]), payload)

    def test_returns_only_failed_sqs_messages(self):
        secret = FakeSecretsManager(
            {
                "app_id": "123",
                "installation_id": "456",
                "private_key": "private-key",
            }
        )
        app._clients["secretsmanager"] = secret
        event = {
            "Records": [
                {"messageId": "good", "body": json.dumps({"source": "billing"})},
                {"messageId": "bad", "body": "not-json"},
            ]
        }
        environment = dict(self.environment, GITHUB_APP_SECRET_ARN="secret-arn")
        with patch.dict(app.os.environ, environment, clear=True), patch.object(
            app, "_installation_token", return_value="token"
        ), patch.object(app, "collect_task", return_value=1):
            result = app.lambda_handler(event, None)

        self.assertEqual(result, {"batchItemFailures": [{"itemIdentifier": "bad"}]})

    def test_reads_gzip_usage_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report"
            with gzip.open(path, "wt", encoding="utf-8") as stream:
                stream.write(json.dumps({"repository_id": 1}) + "\n")

            self.assertEqual(
                list(app._iter_report_records(path)),
                [{"repository_id": 1}],
            )

    def test_rejects_non_https_usage_report_url(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report"

            with self.assertRaises(ValueError):
                app._download_to_path("http://download.example/report", path)


if __name__ == "__main__":
    unittest.main()