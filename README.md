# 🚀 GitHub Webhooks to AWS S3 Parquet Pipeline

This deployment guide outlines the infrastructure architecture and setup steps required to ingest global or organization-level GitHub webhooks, convert them to Apache Parquet format via Amazon Data Firehose, and query them seamlessly using Amazon Athena.

---

## 🏛️ Architecture Overview

```
[GitHub Enterprise/Org] 
       │ (JSON Webhook Payload over HTTPS)
       ▼
[Amazon API Gateway] 
       │ (Authenticates, validates, & routes directly)
       ▼
[Amazon Data Firehose] 
       │ (Buffers data & converts format using AWS Glue Schema)
       ▼
[Amazon S3 Bucket] (Partitioned Parquet files: year=YYYY/month=MM/day=DD/)
       │
       ▼
[Amazon Athena] (Query raw logs seamlessly using SQL)
```

---

## 📦 Infrastructure Component Breakdown

The pipeline leverages a completely serverless architecture to process high-throughput webhook streams efficiently without provisioning underlying servers:

* **Amazon S3 Bucket**
  * Serves as the centralized data lake repository for long-term audit logs.
  * Configured with default **SSE-S3 (AES-256) server-side encryption** to maintain strict enterprise data security compliance.

* **AWS Glue Catalog Database & Table**
  * Establishes the target relational structure for your data lake.
  * Outlines a foundational, strongly-typed schema for standard GitHub metadata properties (`id`, `event_type`, `action`, `repository`, `sender`).
  * Integrates an explicit, open-ended string column (`raw_payload`) to handle shifting polymorphic GitHub event fields gracefully, preventing schema validation dropouts.

* **Amazon Data Firehose Delivery Stream**
  * Acts as the real-time buffer engine, minimizing data pipeline latency.
  * Utilizes built-in inline record format serialization to convert raw incoming streaming JSON objects into high-performance, columnar **Apache Parquet** format.
  * Employs time-based and size-based delivery window thresholds to cluster files logically.
  * Organizes streaming writes natively using standard Hive partitioning patterns: `webhooks/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/`.

* **Amazon API Gateway Framework**
  * Exposes a public, high-availability HTTPS REST API endpoint required by GitHub webhooks.
  * Configured with a **direct service integration proxy** that uses Velocity Mapping Templates (VTL) to preserve the complete GitHub body in `raw_payload`, capture the delivery ID and event-type headers, and push the enriched record directly into Firehose.
  * Completely eliminates intermediate computing runtimes (like AWS Lambda functions) to minimize execution latency and eliminate invocation compute costs.

---

## 🚀 Deployment Instructions

### 1. Execute the Infrastructure Deployment
From the repository root, validate and build the template, then deploy it using the AWS SAM CLI. The guided deployment saves your selections for future `sam deploy` commands:

```bash
export GITHUB_ENTERPRISE_SLUG="your-case-sensitive-enterprise-slug"
# Keep false when the account already has this account-global OIDC provider.
export CREATE_GITHUB_AUDIT_LOG_OIDC_PROVIDER="false"

sam validate --lint
sam build
sam deploy --guided \
  --stack-name robandpdx-gh-webhook-parquet-pipeline \
  --parameter-overrides \
    Environment=dev \
    owner=robandpdx \
    GitHubEnterpriseSlug="$GITHUB_ENTERPRISE_SLUG" \
    CreateGitHubAuditLogOidcProvider="$CREATE_GITHUB_AUDIT_LOG_OIDC_PROVIDER" \
  --capabilities CAPABILITY_IAM
```

The stack also creates a private raw S3 landing bucket and an
enterprise-scoped OIDC writer role for GitHub audit-log streaming. It reuses
the account-global GitHub audit-log OIDC provider by default. Set
`CREATE_GITHUB_AUDIT_LOG_OIDC_PROVIDER=true` only if the provider does not
already exist. The guided deployment stores the parameter values for later
deployments.

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

### 6. Next Steps

See [aws_webhook_analytics_architecture.md](./aws_webhook_analytics_architecture.md)
for the broader webhook analytics architecture.
