import unittest
from pathlib import Path


TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "template.yml"


class SchedulerTemplateTests(unittest.TestCase):
    def test_shared_data_lake_bucket_has_source_neutral_name(self):
        template = TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn("  DataLakeS3Bucket:", template)
        self.assertIn("  DataLakeS3BucketPolicy:", template)
        self.assertIn(
            'BucketName: !Sub "github-data-lake-${Environment}-${AWS::AccountId}"',
            template,
        )
        self.assertIn("  DataLakeS3BucketName:", template)
        self.assertNotIn("WebhookS3Bucket", template)
        self.assertNotIn("github-webhooks-parquet-${Environment}", template)

    def test_data_prefixes_use_zone_then_source_layout(self):
        template = TEMPLATE_PATH.read_text(encoding="utf-8")

        for prefix in (
            "bronze/webhooks/year=",
            "bronze/audit-logs/year=",
            "errors/webhooks/year=",
            "errors/audit-logs/year=",
            "s3://${DataLakeS3Bucket}/silver/webhooks/",
            "s3://${DataLakeS3Bucket}/quarantine/webhooks/",
            "${DataLakeS3Bucket.Arn}/quarantine/audit-logs/*",
        ):
            self.assertIn(prefix, template)

        for obsolete_prefix in (
            'Prefix: "webhooks/year=',
            'Prefix: "audit-logs/year=',
            "webhooks-errors/",
            "audit-logs-errors/",
            's3://${DataLakeS3Bucket}/silver/"',
        ):
            self.assertNotIn(obsolete_prefix, template)

    def test_webhook_bronze_database_name_includes_medallion_layer(self):
        template = TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn(
            'Name: !Sub "github_webhooks_bronze_${Environment}"',
            template,
        )
        self.assertNotIn('Name: !Sub "github_webhooks_${Environment}"', template)

    def test_execution_role_is_scoped_to_the_default_schedule_group(self):
        template = TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn(
            'aws:SourceArn: !Sub "arn:${AWS::Partition}:scheduler:${AWS::Region}:${AWS::AccountId}:schedule-group/default"',
            template,
        )
        self.assertNotIn(
            "arn:${AWS::Partition}:scheduler:${AWS::Region}:${AWS::AccountId}:schedule/default/",
            template,
        )

    def test_webhook_ingestion_records_the_request_epoch(self):
        template = TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn("- Name: received_at_epoch_ms", template)
        self.assertEqual(
            template.count("#set($receivedAtEpochMs = $context.requestTimeEpoch)"),
            2,
        )
        self.assertEqual(
            template.count("${!quote}received_at_epoch_ms${!quote}:${!receivedAtEpochMs}"),
            2,
        )
        self.assertIn("WebhookDeploymentV13", template)


if __name__ == "__main__":
    unittest.main()