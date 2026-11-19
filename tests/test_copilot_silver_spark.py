import json
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch

from copilot_silver import job
from webhook_silver import job as webhook_job

try:
    from pyspark.sql import SparkSession, functions
except ModuleNotFoundError as error:
    if error.name != "pyspark":
        raise
    SparkSession = None


@unittest.skipIf(SparkSession is None, "requires Spark and the Iceberg runtime jar")
class CopilotCustomizationSparkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix="copilot-customizations-")
        cls.addClassCleanup(cls.directory.cleanup)
        cls.warehouse = Path(cls.directory.name) / "warehouse"
        cls.spark = (
            SparkSession.builder.master("local[2]")
            .appName("copilot-customizations-test")
            .config(
                "spark.sql.extensions",
                "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions",
            )
            .config("spark.sql.catalog.glue_catalog", "org.apache.iceberg.spark.SparkCatalog")
            .config("spark.sql.catalog.glue_catalog.type", "hadoop")
            .config("spark.sql.catalog.glue_catalog.warehouse", f"file:{cls.warehouse}")
            .config("spark.sql.session.timeZone", "UTC")
            .config("spark.sql.shuffle.partitions", "2")
            .getOrCreate()
        )
        cls.addClassCleanup(cls.spark.stop)
        cls.spark.sparkContext.setLogLevel("ERROR")
        cls.spark.sql("CREATE DATABASE glue_catalog.customizations_test")

    def test_customization_extraction_migration_and_replay(self):
        names = ("skill", "custom_agent", "mcp", "slash_cmd", "plugin")
        populated = {}
        for name in names:
            populated[f"totals_by_{name}"] = [
                {name: f"internal-{name}-{index}", "interaction_count": index + 1}
                for index in range(24)
            ] + [{name: "other", "interaction_count": 50}]
            populated[f"distinct_{name}_use_count"] = 40
        cases = (
            {},
            {key: None for key in populated},
            {
                key: [] if key.startswith("totals_by_") else 0
                for key in populated
            },
            populated,
        )
        for report_type, table_name, builder in (
            ("enterprise", "enterprise_usage_daily", job._enterprise_frame),
            ("users", "user_usage_daily", job._user_frame),
        ):
            with self.subTest(table=table_name):
                rows = [
                    (
                        report_type, date(2026, 10, 20 + index), date(2026, 10, 26),
                        datetime(2026, 10, 26, 8, 30), "s3://example/report.ndjson",
                        "test-run", datetime(2026, 10, 26, 10, 30),
                        json.dumps({"enterprise_id": "1", "user_id": 42, **payload}),
                    )
                    for index, payload in enumerate(cases)
                ]
                source = self.spark.createDataFrame(
                    rows,
                    "_report_type string, _report_day date, _collection_date date, "
                    "_collected_at timestamp, _bronze_object_path string, "
                    "_processing_run_id string, _normalized_at timestamp, raw_payload string",
                )
                frame = builder(source, functions)
                self.assertEqual(
                    set(frame.columns),
                    {name for name, _ in job.TABLE_DEFINITIONS[table_name]["columns"]},
                )
                new_columns = {f"totals_by_{name}_json" for name in names}
                if report_type == "users":
                    new_columns.update(f"distinct_{name}_use_count" for name in names)
                target = job.qualified_table("customizations_test", table_name)
                location = (self.warehouse / "customizations_test" / table_name).as_uri()
                legacy_definition = {
                    **job.TABLE_DEFINITIONS[table_name],
                    "columns": tuple(
                        (name, kind)
                        for name, kind in job.TABLE_DEFINITIONS[table_name]["columns"]
                        if name not in new_columns
                    ),
                }
                with patch.object(job, "_validate_s3_path"), patch.dict(
                    job.TABLE_DEFINITIONS, {table_name: legacy_definition}
                ):
                    self.spark.sql(
                        job.create_table_sql("customizations_test", table_name, location)
                    )
                frame.drop(*new_columns).writeTo(target).append()
                with patch.object(job, "_validate_s3_path"):
                    job.ensure_table(self.spark, "customizations_test", table_name, location)
                    job.ensure_table(self.spark, "customizations_test", table_name, location)
                self.assertEqual(self.spark.table(target).count(), 4)
                for column in new_columns:
                    self.assertEqual(
                        self.spark.table(target).where(functions.col(column).isNotNull()).count(),
                        0,
                    )
                for _ in range(2):
                    job._merge_frame(frame, self.spark, "customizations_test", table_name)
                actual = self.spark.table(target).orderBy("report_day").collect()
                self.assertEqual(len(actual), 4)
                for name in names:
                    column = f"totals_by_{name}_json"
                    self.assertIsNone(actual[0][column])
                    self.assertIsNone(actual[1][column])
                    self.assertEqual(json.loads(actual[2][column]), [])
                    self.assertEqual(
                        json.loads(actual[3][column]), populated[f"totals_by_{name}"]
                    )
                    if report_type == "users":
                        counter = f"distinct_{name}_use_count"
                        self.assertEqual(
                            [row[counter] for row in actual], [None, None, 0, 40]
                        )
                        self.assertEqual(dict(frame.dtypes)[counter], "bigint")

    def test_reporting_fields_migrate_and_preserve_missing_empty_and_populated_values(self):
        self.spark.sql("CREATE DATABASE IF NOT EXISTS glue_catalog.coverage_test")
        requirements = {"met": ["vscode"], "unmet": [], "unknown": ["future-ide"]}
        review_times = [{
            "authored_by": "human", "reviewed_by": "human", "total_merged": 2,
            "median_minutes_ready_to_first_review": 12.5,
            "p90_minutes_ready_to_first_review": 20.25,
            "median_minutes_first_to_final_review": 0,
            "p90_minutes_first_to_final_review": 0,
            "median_minutes_final_review_to_merge": 3.5,
            "p90_minutes_final_review_to_merge": 4.75,
        }]
        outcomes = {
            "total_comments_evaluated": 10,
            "total_comments_addressed": 7,
            "total_merged_no_human_change_request_after_review": 2,
            "review_comments_by_customization": [
                {"customization": "skill", "total_comments_evaluated": 3,
                 "total_comments_addressed": 2},
            ],
            "future_breakdown": [{"category": "new", "count": 1}],
        }
        cases = (
            ("enterprise", "enterprise_usage_daily", job._enterprise_frame, {
                "missing_client_telemetry_user_count": 3,
                "below_usage_metrics_minimum_user_count": 2,
                "daily_active_vscode_agent_users": 4,
                "weekly_active_vscode_agent_users": 5,
                "monthly_active_vscode_agent_users": 6,
                "totals_by_vscode_agent": {"session_count": 7, "total_user_messages": 9},
            }, {
                "missing_client_telemetry_user_count": 3,
                "below_usage_metrics_minimum_user_count": 2,
                "daily_active_vscode_agent_users": 4,
                "weekly_active_vscode_agent_users": 5,
                "monthly_active_vscode_agent_users": 6,
                "vscode_agent_session_count": 7,
                "vscode_agent_total_user_messages": 9,
            }),
            ("users", "user_usage_daily", job._user_frame, {
                "client_telemetry_present": False,
                "usage_metrics_requirements": requirements,
                "used_vscode_agent": True,
                "totals_by_vscode_agent": {"session_count": 7, "total_user_messages": 9},
            }, {
                "client_telemetry_present": False,
                "usage_metrics_requirements_json": requirements,
                "used_vscode_agent": True,
                "vscode_agent_session_count": 7,
                "vscode_agent_total_user_messages": 9,
            }),
            ("repositories", "repository_usage_daily", job._repository_frame, {
                "pull_request_review_times": review_times,
                "copilot_code_review": outcomes,
            }, {
                "pull_request_review_times_json": review_times,
                "copilot_code_review_json": outcomes,
                "copilot_review_comments_evaluated": 10,
                "copilot_review_comments_addressed": 7,
                "copilot_review_merged_no_human_change_request": 2,
            }),
        )
        for report_type, table_name, builder, payload, expected in cases:
            with self.subTest(table=table_name):
                def empty_value(value):
                    if isinstance(value, dict):
                        return {key: empty_value(item) for key, item in value.items()}
                    if isinstance(value, list):
                        return []
                    if isinstance(value, bool):
                        return False
                    return 0

                payloads = ({}, dict.fromkeys(payload), empty_value(payload), payload)
                source = self.spark.createDataFrame([
                    (
                        report_type, date(2026, 11, 6 + index), date(2026, 11, 14),
                        datetime(2026, 11, 14, 8, 30), "s3://example/report.ndjson",
                        "coverage-run", datetime(2026, 11, 14, 10, 30),
                        json.dumps({"enterprise_id": "1", "user_id": 42, "repo_id": 7,
                                    "repo_owner_name": "org", "repo_name": "repo", **item}),
                    )
                    for index, item in enumerate(payloads)
                ], "_report_type string, _report_day date, _collection_date date, "
                   "_collected_at timestamp, _bronze_object_path string, "
                   "_processing_run_id string, _normalized_at timestamp, raw_payload string")
                frame = builder(source, functions)
                self.assertEqual(
                    set(frame.columns),
                    {name for name, _ in job.TABLE_DEFINITIONS[table_name]["columns"]},
                )
                target = job.qualified_table("coverage_test", table_name)
                location = (self.warehouse / "coverage_test" / table_name).as_uri()
                legacy = {
                    **job.TABLE_DEFINITIONS[table_name],
                    "columns": tuple(
                        (name, kind)
                        for name, kind in job.TABLE_DEFINITIONS[table_name]["columns"]
                        if name not in expected
                    ),
                }
                with patch.object(job, "_validate_s3_path"), patch.dict(
                    job.TABLE_DEFINITIONS, {table_name: legacy}
                ):
                    self.spark.sql(job.create_table_sql("coverage_test", table_name, location))
                frame.drop(*expected).writeTo(target).append()
                with patch.object(job, "_validate_s3_path"):
                    job.ensure_table(self.spark, "coverage_test", table_name, location)
                    job.ensure_table(self.spark, "coverage_test", table_name, location)
                for _ in range(2):
                    job._merge_frame(frame, self.spark, "coverage_test", table_name)
                older = source.withColumn(
                    "_collection_date", functions.lit(date(2026, 11, 13))
                ).withColumn("raw_payload", functions.lit(
                    '{"enterprise_id":"1","user_id":42,"repo_id":7}'
                ))
                job._merge_frame(builder(older, functions), self.spark, "coverage_test", table_name)
                actual = self.spark.table(target).orderBy("report_day").collect()
                self.assertEqual(len(actual), 4)
                for column, value in expected.items():
                    self.assertIsNone(actual[0][column])
                    self.assertIsNone(actual[1][column])
                    if column.endswith("_json"):
                        self.assertEqual(json.loads(actual[2][column]), empty_value(value))
                        self.assertEqual(json.loads(actual[3][column]), value)
                    else:
                        self.assertEqual(actual[2][column], empty_value(value))
                        self.assertEqual(actual[3][column], value)

    def test_webhook_relationships_fields_and_dependency_versions(self):
        rows = [
            ("same-repo", "issue_relates_to",
             {"action": "relates_to_added", "issue_id": 10, "related_issue_id": 11}),
            ("cross-repo", "issue_relates_to",
             {"action": "relates_to_removed", "issue_id": 10}),
            ("field", "issues", {
                "action": "field_added", "issue": {"id": 10},
                "issue_field": {"id": 1, "name": "Effort", "data_type": "number"},
                "issue_field_value": {"value": 0}, "changes": {"from": 2},
            }),
            ("version", "dependabot_alert", {
                "action": "created",
                "alert": {"number": 2, "dependency": {"version_requirement": "^1.2.3"}},
            }),
            ("withdrawn", "dependabot_alert",
             {"action": "withdrawn", "alert": {"number": 2}}),
        ]
        source = self.spark.createDataFrame([
            (key, event_type, json.dumps(payload), 1794000000000)
            for key, event_type, payload in rows
        ], "id string, event_type string, raw_payload string, received_at_epoch_ms long")
        prepared = webhook_job._prepare_source(
            source, "coverage", "s3://example/bronze/webhooks/", functions
        )
        self.assertEqual(prepared.where(functions.col("reason").isNotNull()).count(), 0)
        issues = {
            row.delivery_id: row
            for row in webhook_job._family_frame(prepared, "issues", functions).collect()
        }
        self.assertEqual(issues["same-repo"].issue_id, 10)
        self.assertEqual(issues["same-repo"].related_issue_id, 11)
        self.assertIsNone(issues["cross-repo"].related_issue_id)
        self.assertEqual(json.loads(issues["field"].issue_field_value_json), {"value": 0})
        self.assertEqual(json.loads(issues["field"].changes_json), {"from": 2})
        alerts = {
            row.delivery_id: row
            for row in webhook_job._family_frame(prepared, "security_alerts", functions).collect()
        }
        self.assertEqual(alerts["version"].dependency_version_requirement, "^1.2.3")
        self.assertIsNone(alerts["withdrawn"].dependency_version_requirement)
        self.assertEqual(alerts["withdrawn"].action, "withdrawn")


if __name__ == "__main__":
    unittest.main()
