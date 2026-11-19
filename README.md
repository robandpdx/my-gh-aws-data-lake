# GitHub Webhook and Audit Log Data Lake on AWS

This SAM application ingests GitHub webhooks, GitHub Enterprise Cloud audit
logs, and optional GitHub Copilot billing and usage reports. It retains
source-faithful raw data, produces queryable bronze datasets, materializes
webhook silver tables, and catalogs the analytical layers for Amazon Athena.

For change history, GitHub announcement links, and upgrade or migration
instructions, see [CHANGELOG.md](./CHANGELOG.md).

---

## Architecture Overview

```text
GitHub webhooks -> API Gateway -> Data Firehose -> S3 bronze/webhooks/ Parquet
                                                 -> scheduled Glue 5 Spark
                                                 -> Iceberg silver core and family tables

GitHub audit OIDC -> versioned raw S3 -> EventBridge -> encrypted SQS
                 -> Lambda normalizer
                 -> Data Firehose
                 -> S3 bronze/audit-logs/ Parquet
             failures -> DLQ or quarantine metadata

EventBridge Scheduler -> coordinator Lambda -> encrypted SQS -> collector Lambda
           -> GitHub App installation token -> GitHub REST APIs
           -> S3 raw/copilot/ source responses and NDJSON
           -> S3 bronze/copilot/ stable NDJSON envelopes
           -> scheduled Glue 5 Spark -> typed Copilot Iceberg silver tables
         failures -> DLQ

S3 bronze and silver data -> AWS Glue Data Catalog -> Amazon Athena
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
    `actions_workflow_jobs`, `push_events`, `pull_requests`, `issues`,
    `security_alerts`, and `organization_activity` tables in
    `github_webhooks_silver_<environment>`.
  * Reads the bronze S3 prefix directly because Firehose does not register
    Glue partitions, then uses `delivery_id` Iceberg merges for replay-safe
    materialization.
  * Exposes issue relationships and field changes in `issues`, and Dependabot
    dependency version requirements in `security_alerts`. Sparse withdrawn-alert
    payloads and cross-repository relationships retain nullable fields.
  * Quarantines malformed deliveries and conflicting payload hashes in the
    `quarantined_events` Iceberg table under `quarantine/webhooks/`.
  * Publishes per-run row counts to `GitHubDataLake/WebhookSilver`, sends failed
    Glue state changes to the alarm topic, and alarms on quarantine rows or
    scheduler dead letters.

* **Amazon Data Firehose Delivery Stream**
  * Acts as the real-time buffer engine, minimizing data pipeline latency.
  * Utilizes built-in inline record format serialization to convert raw incoming streaming JSON objects into high-performance, columnar **Apache Parquet** format.
  * Employs time-based and size-based delivery window thresholds to cluster files logically.
  * Organizes streaming writes natively using standard Hive partitioning patterns: `bronze/webhooks/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/`.

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
    `bronze/audit-logs/year=YYYY/month=MM/day=DD/hour=HH/`.

* **Copilot billing and usage bronze collection**
  * Is disabled by default and uses an enterprise-installed GitHub App instead
    of a long-lived personal access token.
  * Runs daily at 08:30 UTC, re-fetching billing dates `T-1` through `T-7` and
    finalized usage dates `T-4` through `T-10` for late-data reconciliation.
  * Fans out 42 deterministic report tasks through an encrypted SQS queue and
    isolates repeatedly failing tasks in a 14-day dead-letter queue.
  * Archives exact billing JSON and downloaded usage NDJSON under
    `raw/copilot/`; signed download URLs are consumed immediately and are not
    persisted.
  * Writes schema-tolerant envelopes under `bronze/copilot/` and exposes
    partition-projected `billing_usage` and `usage_reports` Glue tables.

* **Copilot billing and usage silver layer**
  * Runs a Glue 5.0 Spark job daily at 10:30 UTC, after the 08:30 UTC collector,
    with independent bookmarks for billing and usage bronze inputs.
  * Creates Iceberg v2 `billing_usage_daily`, `enterprise_usage_daily`,
    `user_usage_daily`, `repository_usage_daily`, and
    `user_team_memberships_daily` tables in
    `github_copilot_silver_<environment>`.
  * Selects the newest reconciliation snapshot per natural key and conditionally
    merges it so an older collection cannot replace a newer one.
  * Promotes stable scalar metrics and preserves evolving feature, IDE,
    language, model, agent, and adoption-phase breakdowns as JSON columns.
  * Includes dedicated VS Code Agents-window activity, telemetry-health
    indicators, human PR review-stage timings, and Copilot review outcomes.
  * Routes malformed or keyless records to `quarantined_records` under
    `quarantine/copilot/` and publishes run counts to
    `GitHubDataLake/CopilotSilver`.

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
  --stack-name <STACK_NAME> \
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

Copilot collection remains disabled unless `EnableCopilotCollection=true` and
`CopilotGitHubAppSecretArn` names an existing Secrets Manager secret. See
section 8 before enabling it.

### 2. Capture the Webhook Ingestion Endpoint
Once the deployment status shows `CREATE_COMPLETE`:
1. Navigate to the **Outputs** tab of your deployed CloudFormation stack.
2. Locate and copy the value corresponding to the **`WebhookEndpoint`** key.

### 3. Configure the GitHub Webhook Settings
GitHub enterprise global webhooks only expose events whose documented
availability includes `business`. They can populate the Actions and
organization-activity silver tables, but they cannot emit `issues`,
`issue_comment`, `pull_request`, pull-request review, or repository security
alert events. Selecting **Send me everything** does not add event types that
are unavailable to global webhooks.

To populate the `issues`, `pull_requests`, and `security_alerts` silver tables,
create an organization webhook in each organization you want to ingest, or use
a GitHub App installed in those organizations:

1. Open the organization's **Settings** page.
2. Select **Webhooks** from the left navigation tree, then click **Add webhook**.
3. **Payload URL:** Paste the `WebhookEndpoint` URL retrieved from your CloudFormation Outputs step.
4. **Content type:** Change the dropdown selection to `application/json`.
5. **Secret:** Input a complex string password to cryptographically sign all inbound webhook payloads.
6. **Trigger Events:** Select the events needed by the silver tables. At minimum,
   enable **Issues**, **Issue comments**, **Pull requests**, **Pull request
   reviews**, and **Pull request review comments**. Enable the code scanning,
   Dependabot, and secret scanning alert events when collecting security data.
   Also subscribe to `issue_relates_to` for issue relationship activity.
7. Click **Add webhook** to activate real-time stream ingestion.

Use an enterprise global webhook separately when collecting enterprise-wide
`workflow_job`, `workflow_run`, repository, and organization activity.

### Troubleshooting: GitHub Shows Success but S3 Is Empty

* A GitHub delivery status of **200** means API Gateway successfully submitted
  the record to Firehose. Parquet conversion and S3 delivery occur
  asynchronously after that response.
* Allow up to **5 minutes** for low-volume traffic to appear. The Firehose stream
  flushes after 300 seconds or 64 MiB, whichever comes first.
* Successful Parquet files are written below `bronze/webhooks/`. Records that
  reach Firehose but cannot be converted are written below `errors/webhooks/`, with
  details in the `FirehoseLogGroupName` CloudFormation output.
* The endpoint accepts both GitHub content types: `application/json` and
  `application/x-www-form-urlencoded`. Other content types receive HTTP 415.
* Synchronous Firehose API errors are returned as non-2xx responses. Later
  format-conversion failures cannot change GitHub's original 200 response and
  must be diagnosed under `errors/webhooks/`.

### 4. Initialize Data Partition Catalog Refreshes
Once the pipeline has captured its first set of live incoming events and deposited Parquet blocks into the S3 bucket, synchronize the AWS Glue table structural directory map:
1. Open the **Amazon Athena Console** and select the workgroup shown by the
  `AthenaWorkGroupName` CloudFormation output. The workgroup automatically
  stores encrypted query results at the `AthenaQueryResultsLocation` output,
  so no manual query result location is required.
2. Use the database shown by the `WebhookBronzeGlueDatabaseName` CloudFormation
  output, then repair the table partitions (the configured `dev` deployment
  uses `github_webhooks_bronze_dev`):
```sql
MSCK REPAIR TABLE github_webhooks_bronze_dev.events;
```
3. Query your data lake directly using standard SQL operations:
```sql
SELECT event_type, action, repository.name, sender.login
FROM github_webhooks_bronze_dev.events
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

Use the replay job to reprocess retained raw objects.
The prefix follows the raw bucket's UTC `YYYY/MM/DD/HH/mm/` layout:

```bash
export REPLAY_FUNCTION="$(aws cloudformation describe-stacks \
  --stack-name <STACK_NAME> \
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
sam build --use-container
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
  --stack-name <STACK_NAME> \
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

Webhook bronze records include API Gateway's `received_at_epoch_ms`, which
silver stores with millisecond precision. `signature_valid` and `trust_state`
describe available receiver trust metadata; a missing signature result does
not imply a verified delivery.

Quarantine is append-only operational history. A record remains visible after
a corrected replay successfully materializes it in `events`; use
`processing_run_id` and the latest successful job run when distinguishing an
active data-quality problem from a resolved historical failure.

Use the `WebhookSilverGlueDatabaseName`, `WebhookSilverWarehouseLocation`,
`WebhookSilverQuarantineLocation`, and
`WebhookSilverScheduleDeadLetterQueueUrl` outputs for querying and operations.
See [sample-athena-queries.md](./sample-athena-queries.md) for reconciliation
and family-table examples.

### Import the Grafana usage dashboards

Import each JSON file using
**Dashboards > New > Import > Upload dashboard JSON file**. Each dashboard
prompts for its one Amazon Athena datasource:

| Dashboard | Charts | Existing datasource | Database queried |
| --- | --- | --- | --- |
| [Copilot adoption and usage](./dashboards/github-copilot.json) | 10 | `athena-copilot-datasource` | `github_copilot_silver_dev` |
| [PRs and code activity](./dashboards/github-pr-code.json) | 5 | `athena-github-datasource` | `github_webhooks_silver_dev` |
| [Actions usage and reliability](./dashboards/github-actions.json) | 5 | `athena-github-datasource` | `github_webhooks_silver_dev` |
| [Audit activity and freshness](./dashboards/github-audit.json) | 4 | `athena-auditlogs-datasource` | `github_audit_logs_bronze_dev` |

Import inputs are labeled with those datasource names. Grafana resolves their
actual UIDs at import; the JSON does not assume a datasource name is its UID.
Each datasource uses its configured region, catalog, and workgroup. The SQL
uses fully qualified `dev` database names; change those names in the JSON for
another environment. Keep the supplied dashboard UIDs so navigation links work
after all four dashboards are imported. Links preserve the selected time range.
If Grafana is hosted under a URL subpath, prefix each link URL with that subpath.

The four dashboards contain 24 time-series charts in total; opening one only
executes its own queries, rather than loading every section.
All panels follow the global time picker, default to the last 90 days in UTC,
and display observed data without replacing missing values with zero. Lines
may connect sparse observations; points mark recorded dates. Auto-refresh is
off because refreshing panels executes Athena queries and incurs scan costs.
Copilot reports may lag, and webhook silver updates hourly.

PR creation-cohort averages select each PR's latest observed non-null snapshot;
historical averages can change as new webhooks arrive, even after the displayed
range. Actions charts deduplicate completed workflow attempts or job IDs;
execution minutes are wall-clock time, not billed minutes. Audit charts prune
normalization-time partitions and deduplicate by `document_id` within the
selected range, then plot by normalization day rather than original event day.
Replayed audit events can therefore shift to a later day.

Only enterprise-level Copilot aggregates and aggregated webhook/audit metrics
are displayed. The queries do not return user names, IPs, or raw payloads.
Copilot surfaces and customization categories can overlap; do not add them
together or infer productivity or causation from correlated activity.
Permissions still apply to the underlying data: use restricted Athena roles
and Grafana access controls rather than treating a dashboard as a security
boundary.

### 8. Operate Copilot Billing and Usage Collection

Before enabling collection:

1. Set the enterprise **Copilot usage metrics** policy to **Enabled
   everywhere**.
2. Create a GitHub App owned by the enterprise with read access to the
   **Enterprise billing** and **Enterprise Copilot metrics** permissions. No
   repository permission is required by these report endpoints.
3. Install the App on the enterprise and record its App ID and enterprise
   installation ID. GitHub documents installation access tokens for every
   endpoint used by this collector.
4. In AWS Secrets Manager, create one JSON secret with the fields below. Enter
   the actual values only in Secrets Manager, never in this repository,
   CloudFormation parameters, or shell history.

```json
{
  "app_id": "GITHUB_APP_ID",
  "installation_id": "ENTERPRISE_INSTALLATION_ID",
  "private_key": "GITHUB_APP_PRIVATE_KEY_PEM"
}
```

Create the secret in the same AWS Region as the stack. The default Secrets
Manager service key requires no additional permission. If the secret uses a
customer-managed KMS key, extend `CopilotCollectorRole` with `kms:Decrypt` for
that key and permit the role in the key policy. Rotate the private key by
updating the secret; no stack update is required.

Store `private_key` as the decoded multiline PEM, including its `BEGIN` and
`END` lines. Do not store a base64 encoding of the PEM.

Deploy with `sam deploy --guided`, set `EnableCopilotCollection` to `true`, and
provide the complete secret ARN for `CopilotGitHubAppSecretArn`. The template
rejects an enabled deployment that retains the disabled sentinel ARN. The
schedule defaults to `cron(30 8 * * ? *)` in UTC and can be changed with
`CopilotCollectionScheduleExpression`.

Every normal run creates 14 billing tasks for AI credit and premium request
reports and 28 usage tasks for enterprise, user, repository, and user-team
reports. Object keys include both `report_day` and `collection_date`, while a
retry of the same task overwrites the same key. This preserves late-arriving
versions without producing retry duplicates.

Query `github_copilot_bronze_dev.billing_usage` and
`github_copilot_bronze_dev.usage_reports` using the stack's Athena workgroup.
Both tables use partition projection, so they do not require `MSCK REPAIR
TABLE`. Always filter `year`, `month`, `day`, and `report_type`. Because recent
dates are collected repeatedly, select the greatest `collection_date` for each
`report_day` and `report_type` before aggregating. See
[sample-athena-queries.md](./sample-athena-queries.md).

The scheduled silver job runs at 10:30 UTC. Query these Iceberg tables in
`github_copilot_silver_dev` directly on `report_day`; hidden partitioning means
there are no Hive partition columns to repair:

- `billing_usage_daily`: one row per billing report, day, scope, product, SKU,
  model, unit type, and cost center.
- `enterprise_usage_daily`: one enterprise aggregate per day.
- `user_usage_daily`: one user per day, including adoption phase and activity.
- `repository_usage_daily`: one active repository per day with pull-request
  metrics.
- `user_team_memberships_daily`: one user-team membership per day. GitHub omits
  teams with fewer than five seated Copilot users, so this table can be empty.
- `quarantined_records`: validation failures with source lineage.

Nested dimensional breakdowns remain JSON in silver because GitHub evolves
those arrays independently. Stable top-level counters, identities, billing
amounts, CLI/App counters, adoption fields, and pull-request metrics are typed.
Both enterprise and user usage tables expose `totals_by_client_json`, including
client request/session counts, token usage, and nested model/selection-mode
breakdowns. The full report remains in `raw_payload`. Missing source fields
remain SQL null; an empty source array remains `[]`.
The same tables expose `totals_by_skill_json`, `totals_by_custom_agent_json`,
`totals_by_mcp_json`, `totals_by_slash_cmd_json`, and `totals_by_plugin_json`.
The user table also types `distinct_skill_use_count`,
`distinct_custom_agent_use_count`, `distinct_mcp_use_count`,
`distinct_slash_cmd_use_count`, and `distinct_plugin_use_count` as `bigint`.
Zero counts are preserved; absent/null counters are not replaced with zeros.

Dedicated VS Code Agents-window metrics are separate from editor-window agent
mode. Enterprise reports expose daily, weekly, and monthly active users; both
enterprise and user reports expose session and user-message totals. The user
table also exposes `used_vscode_agent`, nullable `client_telemetry_present`, and
the complete version assessment in `usage_metrics_requirements_json`.
Enterprise missing-telemetry and below-minimum-version counts can overlap;
do not sum them or treat missing telemetry as employee inactivity.

Repository reports preserve human review cohorts and median/p90 durations in
`pull_request_review_times_json`. `copilot_code_review_json` retains review
outcome breakdowns alongside typed evaluated/addressed comment counts and
merged PRs without a later human change request. Outcomes belong to the merge
day and differ from suggestion-apply counts. Do not average daily percentiles
or compute rates without a nonzero denominator.

Named customization arrays contain up to 25 entries, with remaining activity in
`other`; do not infer distinct-use counts from array length. These are client
telemetry trends, not exact accounting. Configured names are trimmed and limited
to 128 characters upstream; path-like names remain `other`/`custom`. Review data
access before exporting names, even from enterprise aggregate reports.
Prompt mode, the Copilot app, and ACP integrations require Copilot CLI
**1.0.97+**; SDK-based experiences require Copilot SDK **1.0.21+**. Built-in IDE
chat telemetry does not report names; IDE agent experiences need the supported
SDK. See [customization queries](./sample-athena-queries.md#named-skills-custom-agents-mcp-servers-slash-commands-and-plugins)
and [telemetry-health queries](./sample-athena-queries.md#copilot-telemetry-health).

Invoke the coordinator directly for a bounded backfill. Each source window is
limited to 31 days, so split longer billing history into multiple invocations:

```bash
export COPILOT_COORDINATOR="$(aws cloudformation describe-stacks \
  --stack-name <STACK_NAME> \
  --query 'Stacks[0].Outputs[?OutputKey==`CopilotCollectionCoordinatorFunctionName`].OutputValue | [0]' \
  --output text)"

aws lambda invoke \
  --function-name "$COPILOT_COORDINATOR" \
  --cli-binary-format raw-in-base64-out \
  --payload '{
    "collection_date":"2026-09-14",
    "billing_start_date":"2026-09-01",
    "billing_end_date":"2026-09-13",
    "usage_start_date":"2026-09-01",
    "usage_end_date":"2026-09-10"
  }' \
  /tmp/copilot-collection.json
```

After the bronze backfill completes, run the same calendar range through the
silver job. Bounded runs require bookmarks to be disabled and do not advance
the scheduled job's incremental state:

```bash
export COPILOT_SILVER_JOB="$(aws cloudformation describe-stacks \
  --stack-name <STACK_NAME> \
  --query 'Stacks[0].Outputs[?OutputKey==`CopilotSilverGlueJobName`].OutputValue | [0]' \
  --output text)"

aws glue start-job-run \
  --job-name "$COPILOT_SILVER_JOB" \
  --arguments '{
    "--job-bookmark-option":"job-bookmark-disable",
    "--start_date":"2026-09-01",
    "--end_date":"2026-09-13"
  }'
```

Monitor the coordinator and collector function outputs, queue age, collector
errors, and `CopilotCollectionDeadLetterQueueUrl`. Logs are retained for 30
days and contain identifiers and counts, not tokens, private keys, signed URLs,
or report bodies. Restrict Athena access to `raw_payload` and user-level usage
records because they can contain identifiable employee activity.

Also monitor `CopilotSilverGlueJobName`,
`CopilotSilverScheduleDeadLetterQueueUrl`, and the shared alarm topic. Restrict
general analysts to aggregate and repository tables; user-level usage, team
membership, raw payload, and quarantine data require a narrower data-access
role.

At the default cadence, request, SQS, Lambda, and S3 charges are generally low;
report size and Athena bytes scanned are the main variable costs. Secrets
Manager adds one secret charge, and the two metrics across six report types
create 12 custom CloudWatch metric time series per environment. Review current
regional pricing and add S3 lifecycle rules only after choosing raw and bronze
retention requirements.

The daily Glue 5.0 job uses two G.1X workers. At small volumes, Glue's minimum
billed run duration is likely the dominant incremental silver cost; review job
duration after several runs before increasing workers or schedule frequency.

### 9. Operate Enterprise Identity and License Collection

Identity collection is separate from Copilot collection because the enterprise
licensing endpoint requires an enterprise administrator credential. Create a
dedicated fine-grained credential where supported, or a personal access token
(classic) with only `read:enterprise`, and store it in Secrets Manager as:

```json
{
  "token": "GITHUB_ENTERPRISE_READ_TOKEN"
}
```

Enter the value directly in Secrets Manager or through another protected
secret-management workflow. Do not place it in this repository, a
CloudFormation parameter, or shell history. The secret must be in the stack's
AWS Region. If it uses a customer-managed KMS key, grant
`IdentityCollectorRole` `kms:Decrypt` and permit the role in the key policy.

Deploy with `EnableIdentityCollection` set to `true` and pass the complete
secret ARN as `GitHubIdentitySecretArn`. The schedule defaults to 09:00 UTC and
can be changed with `IdentityCollectionScheduleExpression`.

The consumed-licenses API returns only the enterprise's current state; it has
no date range or historical `as of` parameter. Consequently, the earliest
truthful automated baseline is the first successful collection. Trigger that
baseline immediately after deployment, then let the daily schedule accumulate
history:

```bash
export IDENTITY_COLLECTOR="$(aws cloudformation describe-stacks \
  --stack-name <STACK_NAME> \
  --query 'Stacks[0].Outputs[?OutputKey==`IdentityCollectorFunctionName`].OutputValue | [0]' \
  --output text)"

aws lambda invoke \
  --function-name "$IDENTITY_COLLECTOR" \
  --cli-binary-format raw-in-base64-out \
  --payload '{}' \
  /tmp/identity-collection.json

jq . /tmp/identity-collection.json
```

The response should report `complete: true` and include `snapshot_date`,
`user_count`, and `page_count`. To retry or replace the partition for a date on
which the snapshot was actually collected, pass that same UTC date:

```bash
aws lambda invoke \
  --function-name "$IDENTITY_COLLECTOR" \
  --cli-binary-format raw-in-base64-out \
  --payload '{"snapshot_date":"2026-09-18"}' \
  /tmp/identity-collection.json
```

Do not invoke the collector with dates before the first collection in an
attempt to manufacture a backfill. `snapshot_date` controls the destination
partition only; every invocation still retrieves the current GitHub state and
records the real retrieval time in `collected_at`. For history predating this
pipeline, retain and reconcile any existing enterprise membership CSV exports,
license reports, or other dated administrative records separately. The current
collector does not import those formats, and a historical partition should be
published only when its source artifact proves the corresponding effective
date.

The collector retrieves every page from
`GET /enterprises/{enterprise}/consumed-licenses` before publishing anything.
A failed page therefore cannot create a partial daily snapshot. Raw responses
and a completion manifest are retained under `raw/identity/`; query these
projected bronze tables in `github_identity_bronze_dev`:

- `enterprise_users_daily`: license-associated users, roles, deployment
  presence, pending organization invitations, and 2FA status.
- `enterprise_licenses_daily`: license type and Cloud, Server, and Visual
  Studio license indicators per associated user.
- `enterprise_license_summary_daily`: purchased and consumed totals plus
  collection completeness counts.

The promoted tables intentionally omit email addresses, SAML NameIDs, and
verified-domain email arrays. Restrict raw identity objects and these tables to
authorized workforce and license administrators.

This API is the correct automated denominator for license analysis, but it is
not identical to GitHub's broader membership CSV. Periodically reconcile it
against the enterprise membership export when administrators, non-license
associations, or other access relationships must be audited. The API also does
not return a GitHub numeric user ID, so audit joins use login and can miss an
account whose login changed during the activity window.

Monitor `IdentityCollectorFunctionName`,
`IdentityCollectionDeadLetterQueueUrl`, the `GitHubDataLake/Identity` custom
metrics, and the shared alarm topic. See
[sample-athena-queries.md](./sample-athena-queries.md) for snapshot and inactive
user queries.

### 10. Weekly GitHub Data Coverage Review

The [weekly agentic workflow](./.github/workflows/weekly-github-data-coverage.md)
reviews GitHub's changelog for the preceding seven days, follows paginated feeds
and official documentation, and compares announcements with the actual ingestion
code. It checks existing data paths and newly available webhook, REST, GraphQL,
audit-log, report, and export data, including compatibility changes and
deprecations. Comprehensive GitHub data coverage is the goal, not a statement
that this stack already collects every available dataset.

It is scheduled for **Sunday at 20:00 UTC**, equivalent to **noon PST year-round**
(13:00 PDT during daylight saving time). GitHub Actions schedules are best-effort
and may start late. Manual runs use the same rolling seven-day window.

Each run can open at most one **draft pull request** containing validated code,
tests, schemas, and documentation, plus one issue for blocked or deferred work.
It checks existing proposals to avoid duplicates and reports no action when
coverage is already sufficient. Incomplete evidence is reported explicitly,
not treated as a successful review. New collectors remain opt-in, and all
changes require human review. The workflow never merges or deploys changes and
has no AWS credentials or access to live enterprise datasets.

To enable it:

1. Enable GitHub Actions in this repository. Under **Settings > Actions >
   General > Workflow permissions**, enable **Allow GitHub Actions to create
   and approve pull requests** (subject to organization policy). The agent has
   read-only GitHub permissions; separate gh-aw safe-output jobs publish proposals.
2. For this personal repository, create a fine-grained PAT owned by a user
   with an active Copilot license, grant the account permission **Copilot
   Requests: Read**, and save it as the Actions secret `COPILOT_GITHUB_TOKEN`.
   Enter it through the GitHub secrets UI or the interactive
   `gh aw secrets set COPILOT_GITHUB_TOKEN` prompt; never put it in a file or
   command argument. See [gh-aw authentication](https://github.github.com/gh-aw/reference/auth/).
3. Commit both the Markdown source and its generated
   [lock file](./.github/workflows/weekly-github-data-coverage.lock.yml) to the
   default branch, along with the compiler's
   [action pins](./.github/aw/actions-lock.json). The lock file is the executable
   GitHub Actions workflow.
4. Optionally select **Actions > Weekly GitHub data coverage > Run workflow**
   to verify setup without waiting until Sunday, or run:

   ```bash
   gh aw run weekly-github-data-coverage
   ```

After editing the workflow source, install the `github/gh-aw` GitHub CLI extension
if needed, then regenerate and validate the lock file and commit both files:

```bash
gh aw compile weekly-github-data-coverage --strict --validate --actionlint
```

Compilation validates the workflow but does not run the AI review. Review run
logs for missing evidence or test/tool failures. PRs created with the default
`GITHUB_TOKEN` do not automatically trigger other Actions workflows; maintainers
must run required checks before merging. See
[gh-aw CI triggering](https://github.github.com/gh-aw/reference/triggering-ci/)
if a separately scoped GitHub App token is needed later.

### 11. Next Steps

See [aws_webhook_analytics_architecture.md](./aws_webhook_analytics_architecture.md)
for the broader webhook analytics architecture.

## Validation

Run the focused silver-layer tests and SAM validation before deployment:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*silver*.py'
sam validate --lint
```

The optional [Spark/Iceberg integration tests](./tests/test_copilot_silver_spark.py)
require Spark 3.5 and the Iceberg Spark runtime. Standard unit-test runs skip
them when PySpark is absent. They exercise JSON extraction, missing/null/empty
values, typed counters, additive schemas, replay, issue relationships, and
sparse withdrawn Dependabot alerts.

```bash
PYTHONPATH=src spark-submit \
  --jars /path/to/iceberg-spark-runtime-3.5_2.12-1.7.1.jar \
  tests/test_copilot_silver_spark.py
```
