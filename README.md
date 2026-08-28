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
  * Configured with a **direct service integration proxy** that pushes incoming events directly into Firehose pipelines via Velocity Mapping Templates (VTL).
  * Completely eliminates intermediate computing runtimes (like AWS Lambda functions) to minimize execution latency and eliminate invocation compute costs.

---

## 🚀 Deployment Instructions

### 1. Execute the Infrastructure Deployment
From the repository root, validate and build the template, then deploy it using the AWS SAM CLI. The guided deployment saves your selections for future `sam deploy` commands:

```bash
sam validate --lint
sam build
sam deploy --guided \
  --stack-name robandpdx-gh-webhook-parquet-pipeline \
  --parameter-overrides Environment=dev \
  --capabilities CAPABILITY_IAM
```

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

* Allow up to **5 minutes** for low-volume traffic to appear. The Firehose stream
  flushes after 300 seconds or 64 MiB, whichever comes first.
* Successful Parquet files are written below `webhooks/`. Records that reach
  Firehose but cannot be converted are written below `webhooks-errors/`, with
  details in the `FirehoseLogGroupName` CloudFormation output.
* The endpoint accepts both GitHub content types: `application/json` and
  `application/x-www-form-urlencoded`. Other content types receive HTTP 415.
* Firehose service errors are returned as non-2xx responses so GitHub marks the
  delivery as failed instead of displaying a false success.

### 4. Initialize Data Partition Catalog Refreshes
Once the pipeline has captured its first set of live incoming events and deposited Parquet blocks into the S3 bucket, synchronize the AWS Glue table structural directory map:
1. Open the **Amazon Athena Console**.
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
