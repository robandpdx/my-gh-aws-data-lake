import unittest
from argparse import Namespace
from unittest.mock import Mock, call

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

    def test_defines_client_breakdown_for_enterprise_and_user_usage(self):
        for table_name in ("enterprise_usage_daily", "user_usage_daily"):
            with self.subTest(table=table_name):
                columns = dict(job.TABLE_DEFINITIONS[table_name]["columns"])
                self.assertEqual(columns["totals_by_client_json"], "string")
                self.assertEqual(columns["raw_payload"], "string")
                statement = job.create_table_sql(
                    "github_copilot_silver_dev",
                    table_name,
                    f"s3://example/silver/copilot/{table_name}/",
                )
                self.assertIn("`totals_by_client_json` string", statement)
                self.assertIn(
                    "target.`totals_by_client_json` = source.`totals_by_client_json`",
                    job.merge_sql("github_copilot_silver_dev", table_name, "incoming"),
                )

    def test_extracts_client_breakdown_without_reinterpreting_nested_values(self):
        functions = Mock()
        client_expression = Mock()
        functions.get_json_object.side_effect = (
            lambda column, path: client_expression
            if path == "$.totals_by_client"
            else Mock()
        )

        expressions = job._breakdown_expressions(functions)

        functions.get_json_object.assert_any_call("raw_payload", "$.totals_by_client")
        client_expression.alias.assert_called_once_with("totals_by_client_json")
        self.assertIn(client_expression.alias.return_value, expressions)
        self.assertEqual(len(expressions), len(job.BREAKDOWN_COLUMNS))

    def test_adds_client_column_to_existing_tables_only_once(self):
        for table_name in ("enterprise_usage_daily", "user_usage_daily"):
            with self.subTest(table=table_name):
                spark = Mock()
                columns = [
                    name for name, _ in job.TABLE_DEFINITIONS[table_name]["columns"]
                ]
                spark.table.return_value.columns = [
                    name for name in columns if name != "totals_by_client_json"
                ]
                location = f"s3://example/silver/copilot/{table_name}/"
                create = job.create_table_sql(
                    "github_copilot_silver_dev", table_name, location
                )
                alter = (
                    f"ALTER TABLE {job.qualified_table('github_copilot_silver_dev', table_name)}"
                    " ADD COLUMNS (`totals_by_client_json` string)"
                )

                job.ensure_table(
                    spark, "github_copilot_silver_dev", table_name, location
                )
                spark.table.return_value.columns = columns
                job.ensure_table(
                    spark, "github_copilot_silver_dev", table_name, location
                )

                self.assertEqual(
                    spark.sql.call_args_list, [call(create), call(alter), call(create)]
                )
                spark.table.assert_called_with(
                    job.qualified_table("github_copilot_silver_dev", table_name)
                )

    def test_leaves_current_schemas_and_extra_columns_unchanged(self):
        for table_name, definition in job.TABLE_DEFINITIONS.items():
            with self.subTest(table=table_name):
                spark = Mock()
                spark.table.return_value.columns = [
                    name for name, _ in definition["columns"]
                ] + ["future_column"]
                location = f"s3://example/silver/copilot/{table_name}/"

                job.ensure_table(
                    spark, "github_copilot_silver_dev", table_name, location
                )

                spark.sql.assert_called_once_with(
                    job.create_table_sql(
                        "github_copilot_silver_dev", table_name, location
                    )
                )

    def test_customization_columns_and_existing_table_migration(self):
        breakdowns = {
            f"totals_by_{name}_json": f"$.totals_by_{name}"
            for name in ("skill", "custom_agent", "mcp", "slash_cmd", "plugin")
        }
        counters = {
            f"distinct_{name}_use_count"
            for name in ("skill", "custom_agent", "mcp", "slash_cmd", "plugin")
        }
        functions = Mock()
        job._breakdown_expressions(functions)
        for column, path in breakdowns.items():
            functions.get_json_object.assert_any_call("raw_payload", path)
        for table_name in ("enterprise_usage_daily", "user_usage_daily"):
            with self.subTest(table=table_name):
                columns = dict(job.TABLE_DEFINITIONS[table_name]["columns"])
                expected = {name: "string" for name in breakdowns}
                if table_name == "user_usage_daily":
                    expected.update({name: "bigint" for name in counters})
                else:
                    self.assertTrue(counters.isdisjoint(columns))
                for column, column_type in expected.items():
                    self.assertEqual(columns[column], column_type)
                    self.assertIn(
                        f"target.`{column}` = source.`{column}`",
                        job.merge_sql("silver_dev", table_name, "incoming"),
                    )
                spark = Mock()
                spark.table.return_value.columns = [
                    name for name in columns if name not in expected
                ]
                location = f"s3://example/silver/copilot/{table_name}/"
                job.ensure_table(spark, "silver_dev", table_name, location)
                additions = ", ".join(
                    f"`{name}` {column_type}"
                    for name, column_type in columns.items()
                    if name in expected
                )
                self.assertEqual(
                    spark.sql.call_args_list[-1],
                    call(
                        f"ALTER TABLE {job.qualified_table('silver_dev', table_name)}"
                        f" ADD COLUMNS ({additions})"
                    ),
                )
                spark.reset_mock()
                spark.table.return_value.columns = list(columns)
                job.ensure_table(spark, "silver_dev", table_name, location)
                spark.sql.assert_called_once()

    def test_propagates_schema_migration_failure(self):
        spark = Mock()
        table_name = "enterprise_usage_daily"
        spark.table.return_value.columns = [
            name
            for name, _ in job.TABLE_DEFINITIONS[table_name]["columns"]
            if name != "totals_by_client_json"
        ]
        spark.sql.side_effect = [None, RuntimeError("catalog update denied")]

        with self.assertRaisesRegex(RuntimeError, "catalog update denied"):
            job.ensure_table(
                spark,
                "github_copilot_silver_dev",
                table_name,
                "s3://example/silver/copilot/enterprise_usage_daily/",
            )

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