# GitHub Webhook and Audit Log Data Lake on AWS

This SAM application ingests GitHub webhooks and GitHub Enterprise Cloud audit
logs, retains the original audit gzip objects, converts both sources to Apache
Parquet, and catalogs them for Amazon Athena.

---

## Architecture Overview

```text
GitHub webhooks -> API Gateway -> Data Firehose -> S3 webhooks/ Parquet
                                                 -> scheduled Glue 5 Spark
                                                 -> Iceberg silver core and family tables

GitHub audit OIDC -> versioned raw S3 -> EventBridge -> encrypted SQS
                 -> Lambda normalizer
                 -> Data Firehose
                 -> S3 audit-logs/ Parquet
             failures -> DLQ or quarantine metadata

S3 Parquet -> AWS Glue Data Catalog -> Amazon Athena
```

---

## Infrastructure Component Breakdown

The pipeline leverages a completely serverless architecture to process high-throughput webhook streams efficiently without provisioning underlying servers:

* **Amazon S3 Bucket**
  * Serves as the centralized data lake repository for long-term audit logs.
  * Configured with default **SSE-S3 (AES-256) server-side encryption** to maintain strict enterprise data security compliance.

* **AWS Glue Catalog databases and tables**
  * Establishes the target relational structure for your data lake.
  * Outlines a foundational, strongly-typed schema for standard GitHub metadata properties (`id`, `event_type`, `action`, `repository`, `sender`).
  * Integrates an explicit, open-ended string column (`raw_payload`) to handle shifting polymorphic GitHub event fields gracefully, preventing schema validation dropouts.

* **Webhook silver layer**
  * Runs an hourly AWS Glue 5.0 Spark job with Glue job bookmarks and one
    concurrent run.
  * Creates Apache Iceberg v2 `events`, `actions_workflow_runs`,
    `actions_workflow_jobs`, `pull_requests`, `issues`, `security_alerts`, and
    `organization_activity` tables in `github_webhooks_silver_<environment>`.
  * Reads the bronze S3 prefix directly because Firehose does not register
    Glue partitions, then uses `delivery_id` Iceberg merges for replay-safe
    materialization.
  * Quarantines malformed deliveries and conflicting payload hashes in the
    `quarantined_events` Iceberg table under `quarantine/webhooks/`.
  * Publishes per-run row counts to `GitHubDataLake/WebhookSilver`, sends failed
    Glue state changes to the alarm topic, and alarms on quarantine rows or
    scheduler dead letters.

* **Amazon Data Firehose Delivery Stream**
  * Acts as the real-time buffer engine, minimizing data pipeline latency.
  * Utilizes built-in inline record format serialization to convert raw incoming streaming JSON objects into high-performance, columnar **Apache Parquet** format.
  * Employs time-based and size-based delivery window thresholds to cluster files logically.
  * Organizes streaming writes natively using standard Hive partitioning patterns: `webhooks/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/`.

* **Amazon API Gateway Framework**
  * Exposes a public, high-availability HTTPS REST API endpoint required by GitHub webhooks.
  * Configured with a **direct service integration proxy** that uses Velocity Mapping Templates (VTL) to preserve the complete GitHub body in `raw_payload`, capture the delivery ID and event-type headers, and push the enriched record directly into Firehose.
  * Completely eliminates intermediate computing runtimes (like AWS Lambda functions) to minimize execution latency and eliminate invocation compute costs.

* **Audit-log raw landing zone**
  * Accepts GitHub's enterprise audit stream through an enterprise-scoped OIDC
    role with only `s3:PutObject` access.
  * Retains private, encrypted, versioned `.json.log.gz` objects as the replay
    source of truth.
  * Exposes `raw_events` through partition projection for direct investigation.

* **Audit-log bronze normalization**
  * Routes new audit gzip objects through EventBridge and an encrypted SQS
    queue with a 14-day dead-letter queue.
  * Processes up to five source objects per Lambda invocation with partial batch
    failure reporting, bounded gzip decompression, structured logs, X-Ray, and
    Embedded Metric Format counters.
  * Accepts both top-level JSON arrays and consecutive JSON values within a
    gzip object, as observed in the live audit stream.
  * Normalizes common identities and timestamps while preserving the complete
    source event in the restricted `raw_payload` column.
  * Identifies Copilot usage request/response records, uses `event_id` as their
    stable identity, and exposes only stable envelope metadata as typed bronze
    columns. Request and response content remains restricted to `raw_payload`.
  * Converts normalized JSON to Snappy-compressed Parquet under
    `audit-logs/year=YYYY/month=MM/day=DD/hour=HH/`.

* **Recovery and observability**
  * Provides a manually invoked replay Lambda for prefix-based backfills or
    explicit object-version replay.
  * Alarms on queue age, DLQ depth, Lambda errors/throttles, source failures,
    quarantine records, Firehose freshness, and Firehose delivery health.
  * Publishes alarms to an encrypted SNS topic and optionally creates an email
    subscription.

---

## Deployment Instructions

### 1. Execute the Infrastructure Deployment
From the repository root, validate and build the template, then deploy it using the AWS SAM CLI. The guided deployment saves your selections for future `sam deploy` commands:

```bash
export GITHUB_ENTERPRISE_SLUG="your-case-sensitive-enterprise-slug"
# Keep false when the account already has this account-global OIDC provider.
export CREATE_GITHUB_AUDIT_LOG_OIDC_PROVIDER="false"
# Optional; leave empty to create the alarm topic without an email subscriber.
export AUDIT_LOG_ALARM_EMAIL=""

sam validate --lint
sam build
sam deploy --guided \
  --stack-name robandpdx-gh-webhook-parquet-pipeline \
  --parameter-overrides \
    Environment=dev \
    owner=robandpdx \
    GitHubEnterpriseSlug="$GITHUB_ENTERPRISE_SLUG" \
    CreateGitHubAuditLogOidcProvider="$CREATE_GITHUB_AUDIT_LOG_OIDC_PROVIDER" \
    AuditLogAlarmEmail="$AUDIT_LOG_ALARM_EMAIL" \
    AuditLogNormalizerReservedConcurrency=2 \
    WebhookSilverScheduleExpression="rate(1 hour)" \
    WebhookSilverNumberOfWorkers=2 \
  --capabilities CAPABILITY_IAM
```

The stack also creates a private raw S3 landing bucket and an
enterprise-scoped OIDC writer role for GitHub audit-log streaming. It reuses
the account-global GitHub audit-log OIDC provider by default. Set
`CREATE_GITHUB_AUDIT_LOG_OIDC_PROVIDER=true` only if the provider does not
already exist. The guided deployment stores the parameter values for later
deployments. When an alarm email is supplied, confirm the Amazon SNS
subscription message before expecting notifications.

### 2. Capture the Webhook Ingestion Endpoint
Once the deployment status shows `CREATE_COMPLETE`:
1. Navigate to the **Outputs** tab of your deployed CloudFormation stack.
2. Locate and copy the value corresponding to the **`WebhookEndpoint`** key.

### 3. Configure the GitHub Webhook Settings
1. Open your **GitHub Enterprise Portal** or individual **Organization Profile Settings** page.
2. Select **Settings** -> **Webhooks** from the left navigation tree, then click **Add webhook**.
3. **Payload URL:** Paste the `WebhookEndpoint` URL retrieved from your CloudFormation Outputs step.
4. **Content type:** Change the dropdown selection to `application/json`.
5. **Secret:** Input a complex string password to cryptographically sign all inbound webhook payloads.
6. **Trigger Events:** Choose either "Send me everything" or select specific targeted operational event flags (such as `push`, `pull_request`, or `workflow_job`).
7. Click **Add webhook** to activate real-time stream ingestion.

### Troubleshooting: GitHub Shows Success but S3 Is Empty

* A GitHub delivery status of **200** means API Gateway successfully submitted
  the record to Firehose. Parquet conversion and S3 delivery occur
  asynchronously after that response.
* Allow up to **5 minutes** for low-volume traffic to appear. The Firehose stream
  flushes after 300 seconds or 64 MiB, whichever comes first.
* Successful Parquet files are written below `webhooks/`. Records that reach
  Firehose but cannot be converted are written below `webhooks-errors/`, with
  details in the `FirehoseLogGroupName` CloudFormation output.
* The endpoint accepts both GitHub content types: `application/json` and
  `application/x-www-form-urlencoded`. Other content types receive HTTP 415.
* Synchronous Firehose API errors are returned as non-2xx responses. Later
  format-conversion failures cannot change GitHub's original 200 response and
  must be diagnosed under `webhooks-errors/`.
* The `raw_payload`, `id`, and `event_type` fields are populated only for
  webhook records received after deploying the current API Gateway mapping.

### 4. Initialize Data Partition Catalog Refreshes
Once the pipeline has captured its first set of live incoming events and deposited Parquet blocks into the S3 bucket, synchronize the AWS Glue table structural directory map:
1. Open the **Amazon Athena Console** and select the workgroup shown by the
  `AthenaWorkGroupName` CloudFormation output. The workgroup automatically
  stores encrypted query results at the `AthenaQueryResultsLocation` output,
  so no manual query result location is required.
2. Use the database shown by the `GlueDatabaseName` CloudFormation output, then
  repair the table partitions (the configured `dev` deployment uses
  `github_webhooks_dev`):
```sql
MSCK REPAIR TABLE github_webhooks_dev.events;
```
3. Query your data lake directly using standard SQL operations:
```sql
SELECT event_type, action, repository.name, sender.login
FROM github_webhooks_dev.events
  WHERE year = '2026' AND month = '08' 
  LIMIT 10;
```

### 5. Stream Enterprise Audit Logs

Use the `AuditLogS3BucketName`, `AuditLogS3Region`, and
`AuditLogWriterRoleArn` stack outputs to configure an Amazon S3 audit-log stream
with OpenID Connect in the GitHub enterprise settings. The raw bucket is
versioned and retained if the stack is deleted. GitHub receives only
`s3:PutObject` permission for that bucket.

See [github_audit_log_analytics_plan.md](./github_audit_log_analytics_plan.md)
for setup, verification, normalization, Iceberg joins, Grafana serving,
security, observability, cost, and phased implementation details.

### 6. Operate the Audit Bronze Layer

New `.json.log.gz` objects are normalized automatically. Firehose buffers for
up to five minutes before writing Parquet. Bronze partitions use the UTC
**normalization time**, while `event_timestamp` records the original GitHub
event time. Partition projection means `MSCK REPAIR TABLE` is not required for
either audit table.

Query `github_audit_logs_bronze_dev.bronze_events` using the workgroup from the
`AthenaWorkGroupName` output. Always constrain `year`, `month`, `day`, and
preferably `hour`; see [sample-athena-queries.md](./sample-athena-queries.md).
Treat `source_ip` and `raw_payload` as sensitive fields and do not expose them
to general dashboard users. The sample queries define a metadata-only
`copilot_usage_records_metadata` view for Copilot usage analysis without
exposing headers, prompts, tool arguments, or generated content.

Use the replay job to backfill retained objects that arrived before deployment.
The prefix follows the raw bucket's UTC `YYYY/MM/DD/HH/mm/` layout:

```bash
export REPLAY_FUNCTION="$(aws cloudformation describe-stacks \
  --stack-name robandpdx-gh-webhook-parquet-pipeline \
  --query 'Stacks[0].Outputs[?OutputKey==`AuditLogReplayFunctionName`].OutputValue | [0]' \
  --output text)"

aws lambda invoke \
  --function-name "$REPLAY_FUNCTION" \
  --cli-binary-format raw-in-base64-out \
  --payload '{"prefix":"2026/09/03/","max_objects":1000}' \
  /tmp/audit-log-replay.json

jq . /tmp/audit-log-replay.json
```

If the response contains a `continuation_token`, invoke the function again with
that token. To replay an exact retained version instead:

```bash
aws lambda invoke \
  --function-name "$REPLAY_FUNCTION" \
  --cli-binary-format raw-in-base64-out \
  --payload '{"objects":[{"key":"2026/09/03/04/45/object.json.log.gz","version_id":"VERSION_ID"}]}' \
  /tmp/audit-log-replay.json
```

Monitor the `AuditLogIngestQueueUrl`, `AuditLogDeadLetterQueueUrl`,
`AuditLogNormalizerFunctionName`, `AuditLogFirehoseDeliveryStreamName`, and
`AuditLogAlarmTopicArn` stack outputs. Investigate quarantine metadata under
`quarantine/audit-logs/`; source event bodies remain in the retained raw bucket
and are not copied into quarantine logs.

Run the focused tests and SAM checks before deployment:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
sam validate --lint
sam build
```

At low audit volume, usage-based S3, SQS, Lambda, EventBridge, and Firehose
charges should remain modest. The customer-managed KMS key for encrypted alarm
notifications is the main fixed monthly resource charge ($1.00 per month, prorated hourly); CloudWatch custom
metrics, logs, alarms, and many small Parquet files can become material as
volume grows. Review current `us-west-2` pricing and compact curated layers
before broad dashboard use.

### 7. Operate the Webhook Silver Layer

The stack publishes the Glue script to `glue-scripts/webhook-silver.py` and
creates the Iceberg tables when the first job run starts. The hourly schedule
is a clean no-op when no bronze objects exist. To initialize or refresh the
tables immediately, start the job returned by the
`WebhookSilverGlueJobName` output:

```bash
export SILVER_JOB="$(aws cloudformation describe-stacks \
  --stack-name robandpdx-gh-webhook-parquet-pipeline \
  --query 'Stacks[0].Outputs[?OutputKey==`WebhookSilverGlueJobName`].OutputValue | [0]' \
  --output text)"

aws glue start-job-run --job-name "$SILVER_JOB"
```

Incremental runs keep the source path and transformation context stable so
Glue bookmarks can track newly written Parquet objects. Correctness does not
depend on the bookmark: every table is merged by `delivery_id`, and conflicting
payload hashes for one delivery ID are quarantined instead of overwritten.

For an explicit calendar backfill, disable the bookmark and supply both UTC
dates. The normal production bookmark is not advanced by this run:

```bash
aws glue start-job-run \
  --job-name "$SILVER_JOB" \
  --arguments '{
    "--job-bookmark-option":"job-bookmark-disable",
    "--start_date":"2026-08-01",
    "--end_date":"2026-08-31"
  }'
```

The existing bronze history predates receiver-side signature validation and a
precise receiver timestamp. Bounded backfills mark it `legacy_unverified` and
derive `received_at` from the Firehose UTC day prefix with
`received_at_precision = 'day'`; midnight is a partition marker, not the actual
receipt time. New webhook bronze records include API Gateway's
`received_at_epoch_ms`, which silver stores with millisecond precision. Future
receiver hardening can add `signature_valid` and `trust_state` without changing
the silver schema.

Quarantine is append-only operational history. A record remains visible after
a corrected replay successfully materializes it in `events`; use
`processing_run_id` and the latest successful job run when distinguishing an
active data-quality problem from a resolved historical failure.

Use the `WebhookSilverGlueDatabaseName`, `WebhookSilverWarehouseLocation`,
`WebhookSilverQuarantineLocation`, and
`WebhookSilverScheduleDeadLetterQueueUrl` outputs for querying and operations.
See [sample-athena-queries.md](./sample-athena-queries.md) for reconciliation
and family-table examples.

### 8. Next Steps

See [aws_webhook_analytics_architecture.md](./aws_webhook_analytics_architecture.md)
for the broader webhook analytics architecture.
