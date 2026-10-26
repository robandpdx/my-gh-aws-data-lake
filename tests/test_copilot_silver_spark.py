import json
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch

from copilot_silver import job

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


if __name__ == "__main__":
    unittest.main()
