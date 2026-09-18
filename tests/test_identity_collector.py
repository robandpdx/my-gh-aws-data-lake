import json
import unittest
from unittest.mock import patch

from identity_collector import app


class FakeSecretsManager:
    def get_secret_value(self, **request):
        return {"SecretString": json.dumps({"token": "enterprise-token"})}


class FakeS3:
    def __init__(self):
        self.objects = {}

    def put_object(self, **request):
        self.objects[request["Key"]] = request["Body"]


class FakeCloudWatch:
    def __init__(self):
        self.requests = []

    def put_metric_data(self, **request):
        self.requests.append(request)


class IdentityCollectorTests(unittest.TestCase):
    def setUp(self):
        app._clients.clear()
        self.s3 = FakeS3()
        app._clients["s3"] = self.s3
        self.environment = {
            "DATA_LAKE_BUCKET": "data-lake",
            "ENVIRONMENT": "test",
            "GITHUB_ENTERPRISE_SLUG": "example-enterprise",
        }

    def test_collects_complete_user_and_license_snapshots(self):
        first_page = {
            "total_seats_consumed": 101,
            "total_seats_purchased": 120,
            "users": [
                {
                    "github_com_login": f"user-{index}",
                    "github_com_name": f"User {index}",
                    "github_com_user": True,
                    "enterprise_server_user": False,
                    "visual_studio_subscription_user": False,
                    "license_type": "enterprise",
                    "github_com_member_roles": ["org member"],
                    "github_com_enterprise_roles": [],
                    "github_com_verified_domain_emails": [
                        f"user-{index}@example.com"
                    ],
                }
                for index in range(100)
            ],
        }
        second_page = {
            "total_seats_consumed": 101,
            "total_seats_purchased": 120,
            "users": [
                {
                    "github_com_login": "last-user",
                    "github_com_user": True,
                    "license_type": "enterprise",
                }
            ],
        }
        responses = [
            (200, {}, json.dumps(first_page).encode("utf-8")),
            (200, {}, json.dumps(second_page).encode("utf-8")),
        ]

        with patch.dict(app.os.environ, self.environment, clear=True), patch.object(
            app, "_request_json", side_effect=responses
        ) as request_json:
            summary = app.collect_snapshot(
                "token", "2026-09-17", "2026-09-17T08:00:00+00:00"
            )

        self.assertEqual(summary["user_count"], 101)
        self.assertEqual(summary["page_count"], 2)
        self.assertEqual(request_json.call_count, 2)
        users_key = (
            "bronze/identity/users/year=2026/month=09/day=17/snapshot.ndjson"
        )
        licenses_key = (
            "bronze/identity/licenses/year=2026/month=09/day=17/snapshot.ndjson"
        )
        users = [json.loads(line) for line in self.s3.objects[users_key].splitlines()]
        licenses = [
            json.loads(line) for line in self.s3.objects[licenses_key].splitlines()
        ]
        self.assertEqual(len(users), 101)
        self.assertEqual(len(licenses), 101)
        self.assertEqual(users[-1]["github_login"], "last-user")
        self.assertEqual(licenses[0]["license_type"], "enterprise")
        self.assertNotIn("github_com_verified_domain_emails", users[0])
        self.assertIn(
            "raw/identity/consumed-licenses/snapshot_date=2026-09-17/manifest.json",
            self.s3.objects,
        )

    def test_does_not_publish_partial_snapshot(self):
        first_page = {
            "total_seats_consumed": 100,
            "users": [{"github_com_login": str(index)} for index in range(100)],
        }
        with patch.dict(app.os.environ, self.environment, clear=True), patch.object(
            app,
            "_request_json",
            side_effect=[
                (200, {}, json.dumps(first_page).encode("utf-8")),
                RuntimeError("page failed"),
            ],
        ), self.assertRaisesRegex(RuntimeError, "page failed"):
            app.collect_snapshot("token", "2026-09-17")

        self.assertEqual(self.s3.objects, {})

    def test_lambda_reads_dedicated_token_and_emits_metrics(self):
        app._clients["secretsmanager"] = FakeSecretsManager()
        app._clients["cloudwatch"] = FakeCloudWatch()
        environment = dict(
            self.environment,
            GITHUB_IDENTITY_SECRET_ARN="identity-secret-arn",
        )
        summary = {
            "snapshot_date": "2026-09-17",
            "user_count": 1,
            "page_count": 1,
            "total_seats_consumed": 1,
        }
        with patch.dict(app.os.environ, environment, clear=True), patch.object(
            app, "collect_snapshot", return_value=summary
        ) as collect_snapshot:
            result = app.lambda_handler({"snapshot_date": "2026-09-17"}, None)

        collect_snapshot.assert_called_once_with(
            "enterprise-token", snapshot_date="2026-09-17"
        )
        self.assertEqual(result, summary)
        self.assertEqual(len(app._clients["cloudwatch"].requests), 1)


if __name__ == "__main__":
    unittest.main()