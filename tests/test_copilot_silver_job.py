import unittest
from argparse import Namespace

from copilot_silver import job


class FakeS3:
    def __init__(self, populated_prefixes):
        self.populated_prefixes = set(populated_prefixes)

    def list_objects_v2(self, **request):
        return {"KeyCount": int(request["Prefix"] in self.populated_prefixes)}


class CopilotSilverJobTests(unittest.TestCase):
    def test_defines_typed_tables_for_each_stable_grain(self):
        self.assertEqual(
            set(job.TABLE_DEFINITIONS),
            {
                "billing_usage_daily",
                "enterprise_usage_daily",
                "user_usage_daily",
                "repository_usage_daily",
                "user_team_memberships_daily",
                "quarantined_records",
            },
        )
        billing_columns = dict(
            job.TABLE_DEFINITIONS["billing_usage_daily"]["columns"]
        )
        self.assertEqual(billing_columns["net_amount"], "decimal(38,12)")
        self.assertEqual(billing_columns["report_day"], "date")
        self.assertEqual(
            job.TABLE_DEFINITIONS["user_usage_daily"]["key"], "user_usage_key"
        )

    def test_accepts_a_bounded_backfill_with_bookmarks_disabled(self):
        arguments = job.parse_job_arguments(
            self._required_arguments()
            + [
                "--start_date",
                "2026-09-01",
                "--end_date",
                "2026-09-10",
                "--job-bookmark-option",
                "job-bookmark-disable",
            ]
        )

        self.assertEqual(arguments.start_date, "2026-09-01")
        self.assertEqual(arguments.end_date, "2026-09-10")

    def test_rejects_a_bookmarked_calendar_backfill(self):
        with self.assertRaises(SystemExit):
            job.parse_job_arguments(
                self._required_arguments()
                + ["--start_date", "2026-09-01", "--end_date", "2026-09-10"]
            )

    def test_builds_one_source_path_per_report_day(self):
        self.assertEqual(
            job.source_paths(
                "s3://example/bronze/copilot/usage/",
                "2026-09-09",
                "2026-09-10",
            ),
            [
                "s3://example/bronze/copilot/usage/year=2026/month=09/day=09/",
                "s3://example/bronze/copilot/usage/year=2026/month=09/day=10/",
            ],
        )

    def test_filters_source_paths_without_objects(self):
        paths = [
            "s3://example/bronze/copilot/usage/year=2026/month=09/day=09/",
            "s3://example/bronze/copilot/usage/year=2026/month=09/day=10/",
        ]
        s3 = FakeS3(
            {"bronze/copilot/usage/year=2026/month=09/day=10/"}
        )

        self.assertEqual(job.paths_with_objects(paths, s3), [paths[1]])

    def test_generates_iceberg_v2_ddl_partitioned_by_report_day(self):
        statement = job.create_table_sql(
            "github_copilot_silver_dev",
            "user_usage_daily",
            "s3://example/silver/copilot/user_usage_daily/",
        )

        self.assertIn("USING iceberg", statement)
        self.assertIn("PARTITIONED BY (days(`report_day`))", statement)
        self.assertIn("'format-version'='2'", statement)

    def test_merge_prevents_an_older_snapshot_from_replacing_a_newer_one(self):
        statement = job.merge_sql(
            "github_copilot_silver_dev",
            "billing_usage_daily",
            "incoming_billing",
        )

        self.assertIn(
            "target.`billing_usage_key` = source.`billing_usage_key`", statement
        )
        self.assertIn(
            "source.`collection_date` > target.`collection_date`", statement
        )
        self.assertIn("source.`collected_at` >= target.`collected_at`", statement)

    def test_uses_a_separate_quarantine_location(self):
        arguments = Namespace(
            warehouse_path="s3://example/silver/copilot/",
            quarantine_path="s3://example/quarantine/copilot/",
        )

        self.assertEqual(
            job.table_location(arguments, "quarantined_records"),
            "s3://example/quarantine/copilot/",
        )

    @staticmethod
    def _required_arguments():
        return [
            "--JOB_NAME",
            "test-job",
            "--environment",
            "dev",
            "--billing_bronze_path",
            "s3://example/bronze/copilot/billing/",
            "--usage_bronze_path",
            "s3://example/bronze/copilot/usage/",
            "--silver_database",
            "github_copilot_silver_dev",
            "--warehouse_path",
            "s3://example/silver/copilot/",
            "--quarantine_path",
            "s3://example/quarantine/copilot/",
        ]


if __name__ == "__main__":
    unittest.main()