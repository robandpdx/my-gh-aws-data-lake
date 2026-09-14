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

    def test_copilot_collection_is_opt_in_and_uses_github_app_secret(self):
        template = TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn("  EnableCopilotCollection:", template)
        self.assertIn("  CopilotGitHubAppSecretArn:", template)
        self.assertIn("Condition: ShouldEnableCopilotCollection", template)
        self.assertIn("Action: secretsmanager:GetSecretValue", template)
        self.assertIn("Resource: !Ref CopilotGitHubAppSecretArn", template)
        self.assertNotIn("private_key:", template)

    def test_copilot_collection_uses_daily_queue_fanout(self):
        template = TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn("Default: cron(30 8 * * ? *)", template)
        self.assertIn("  CopilotCollectionQueue:", template)
        self.assertIn("  CopilotCollectionDeadLetterQueue:", template)
        self.assertIn("BatchSize: 1", template)
        self.assertIn("MaximumConcurrency: !Ref CopilotCollectorReservedConcurrency", template)

    def test_copilot_bronze_tables_use_partition_projection(self):
        template = TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn('Name: !Sub "github_copilot_bronze_${Environment}"', template)
        self.assertIn("Name: billing_usage", template)
        self.assertIn("Name: usage_reports", template)
        self.assertIn("bronze/copilot/billing/year=${!year}", template)
        self.assertIn("bronze/copilot/usage/year=${!year}", template)
        self.assertIn("projection.year.range: '2024,2040'", template)
        self.assertGreaterEqual(template.count("projection.enabled: 'true'"), 4)


if __name__ == "__main__":
    unittest.main()