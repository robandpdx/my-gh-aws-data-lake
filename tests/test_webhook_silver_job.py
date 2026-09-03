import unittest
from argparse import Namespace

from webhook_silver import job


class FakeS3:
    def __init__(self, populated_prefixes):
        self.populated_prefixes = set(populated_prefixes)
        self.requests = []

    def list_objects_v2(self, **request):
        self.requests.append(request)
        key_count = int(request["Prefix"] in self.populated_prefixes)
        return {"KeyCount": key_count}


class WebhookSilverJobTests(unittest.TestCase):
    def test_classifies_promoted_and_unmodeled_event_types(self):
        self.assertEqual(job.event_family("workflow_job"), "actions")
        self.assertEqual(job.event_family("pull_request"), "pull_requests")
        self.assertEqual(job.event_family("secret_scanning_alert"), "security_alerts")
        self.assertEqual(job.event_family("team"), "organization_activity")
        self.assertEqual(job.event_family("fork"), "other")

    def test_defines_every_planned_event_family_table(self):
        self.assertEqual(
            set(job.FAMILY_EVENT_TYPES),
            {
                "actions_workflow_runs",
                "actions_workflow_jobs",
                "pull_requests",
                "issues",
                "security_alerts",
                "organization_activity",
            },
        )
        self.assertTrue(set(job.FAMILY_EVENT_TYPES) < set(job.TABLE_DEFINITIONS))

    def test_selects_event_specific_timestamp_paths(self):
        self.assertEqual(
            job.event_timestamp_paths("workflow_job"),
            (
                "$.workflow_job.completed_at",
                "$.workflow_job.started_at",
                "$.workflow_job.created_at",
            ),
        )
        self.assertEqual(job.event_timestamp_paths("fork"), job.DEFAULT_TIMESTAMP_PATHS)

    def test_accepts_a_bounded_backfill_window(self):
        arguments = job.parse_job_arguments(
            self._required_arguments()
            + [
                "--start_date",
                "2026-08-01",
                "--end_date",
                "2026-08-31",
                "--job-bookmark-option",
                "job-bookmark-disable",
            ]
        )

        self.assertEqual(arguments.start_date, "2026-08-01")
        self.assertEqual(arguments.end_date, "2026-08-31")

    def test_rejects_an_incomplete_backfill_window(self):
        with self.assertRaises(SystemExit):
            job.parse_job_arguments(
                self._required_arguments() + ["--start_date", "2026-08-01"]
            )

    def test_rejects_a_reversed_backfill_window(self):
        with self.assertRaises(SystemExit):
            job.parse_job_arguments(
                self._required_arguments()
                + [
                    "--start_date",
                    "2026-09-01",
                    "--end_date",
                    "2026-08-01",
                    "--job-bookmark-option",
                    "job-bookmark-disable",
                ]
            )

    def test_rejects_a_bookmarked_calendar_backfill(self):
        with self.assertRaises(SystemExit):
            job.parse_job_arguments(
                self._required_arguments()
                + ["--start_date", "2026-08-01", "--end_date", "2026-08-31"]
            )

    def test_builds_one_bronze_path_per_backfill_day(self):
        arguments = Namespace(
            bronze_path="s3://example/webhooks/",
            start_date="2026-08-31",
            end_date="2026-09-01",
        )

        self.assertEqual(
            job.source_paths(arguments),
            [
                "s3://example/webhooks/year=2026/month=08/day=31/",
                "s3://example/webhooks/year=2026/month=09/day=01/",
            ],
        )

    def test_filters_empty_source_prefixes_before_starting_spark_read(self):
        paths = [
            "s3://example/webhooks/year=2026/month=08/day=31/",
            "s3://example/webhooks/year=2026/month=09/day=01/",
        ]
        s3 = FakeS3({"webhooks/year=2026/month=09/day=01/"})

        self.assertEqual(job.paths_with_objects(paths, s3), [paths[1]])
        self.assertEqual(s3.requests[0]["Bucket"], "example")
        self.assertEqual(s3.requests[0]["MaxKeys"], 1)

    def test_generates_iceberg_v2_ddl_with_a_dedicated_location(self):
        statement = job.create_table_sql(
            "github_webhooks_silver_dev",
            "pull_requests",
            "s3://example/silver/pull_requests/",
        )

        self.assertIn("USING iceberg", statement)
        self.assertIn("PARTITIONED BY (days(`received_at`))", statement)
        self.assertIn("'format-version'='2'", statement)
        self.assertIn("s3://example/silver/pull_requests/", statement)

    def test_generates_an_explicit_delivery_id_merge(self):
        statement = job.merge_sql(
            "github_webhooks_silver_dev",
            "issues",
            "incoming_issues",
            "delivery_id",
        )

        self.assertIn("ON target.`delivery_id` = source.`delivery_id`", statement)
        self.assertIn("WHEN MATCHED THEN UPDATE SET", statement)
        self.assertIn("WHEN NOT MATCHED THEN INSERT", statement)

    @staticmethod
    def _required_arguments():
        return [
            "--JOB_NAME",
            "test-job",
            "--environment",
            "dev",
            "--bronze_path",
            "s3://example/webhooks/",
            "--silver_database",
            "github_webhooks_silver_dev",
            "--warehouse_path",
            "s3://example/silver/",
            "--quarantine_path",
            "s3://example/quarantine/webhooks/",
        ]


if __name__ == "__main__":
    unittest.main()