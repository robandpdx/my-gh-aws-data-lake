# Sample Athena Queries

## GitHub Enterprise audit logs

The `raw_events` table reads GitHub's `.json.log.gz` objects directly. Athena
decompresses gzip automatically, and partition projection means no
`MSCK REPAIR TABLE` command is required. GitHub's S3 path components are UTC.

Always filter on `year`, `month`, `day`, and preferably `hour` and `minute` to
limit the S3 paths that Athena scans.

```sql
SELECT
  from_unixtime(event_timestamp / 1000.0) AS event_time,
  action,
  actor,
  org AS organization,
  coalesce(repository, repo) AS repository,
  operation_type,
  "$path" AS source_object
FROM github_audit_logs_bronze_dev.raw_events
WHERE year = '2026'
  AND month = '09'
  AND day = '03'
  AND hour = '04'
  AND minute BETWEEN '00' AND '59'
ORDER BY event_timestamp DESC
LIMIT 100;
```

GitHub audit-log delivery is at least once. Deduplicate by `document_id` before
using raw data for counts:

```sql
WITH ranked_events AS (
  SELECT
    document_id,
    action,
    actor,
    org,
    event_timestamp,
    row_number() OVER (
      PARTITION BY document_id
      ORDER BY event_timestamp DESC, "$path" DESC
    ) AS occurrence
  FROM github_audit_logs_bronze_dev.raw_events
  WHERE year = '2026'
    AND month = '09'
    AND day = '03'
)
SELECT
  action,
  count(*) AS event_count,
  count(DISTINCT actor) AS distinct_actors
FROM ranked_events
WHERE occurrence = 1
GROUP BY action
ORDER BY event_count DESC;
```

## Normalized audit bronze

The `bronze_events` table reads Snappy-compressed Parquet produced by the audit
normalizer. Its `year`, `month`, `day`, and `hour` partitions represent UTC
normalization time, not `event_timestamp`. Always prune these partitions even
when applying an event-time predicate.

### Inspect normalized events

```sql
SELECT
  event_timestamp,
  action,
  actor,
  organization,
  repository,
  operation_type,
  normalized_at,
  source_object_key
FROM github_audit_logs_bronze_dev.bronze_events
WHERE year = '2026'
  AND month = '09'
  AND day = '03'
  AND hour BETWEEN '04' AND '05'
ORDER BY event_timestamp DESC
LIMIT 100;
```

### Count activity by event hour and category

```sql
SELECT
  date_trunc('hour', event_timestamp) AS event_hour,
  action_category,
  count(*) AS event_count,
  count(DISTINCT actor_id) AS distinct_actors,
  count(DISTINCT repository_id) AS distinct_repositories
FROM github_audit_logs_bronze_dev.bronze_events
WHERE year = '2026'
  AND month = '09'
  AND day = '03'
  AND hour BETWEEN '00' AND '23'
GROUP BY 1, 2
ORDER BY event_hour DESC, event_count DESC;
```

### Measure normalization latency

```sql
SELECT
  action_category,
  count(*) AS event_count,
  avg(date_diff('second', event_timestamp, normalized_at)) AS avg_latency_seconds,
  approx_percentile(
    date_diff('second', event_timestamp, normalized_at),
    0.95
  ) AS p95_latency_seconds,
  max(date_diff('second', event_timestamp, normalized_at)) AS max_latency_seconds
FROM github_audit_logs_bronze_dev.bronze_events
WHERE year = '2026'
  AND month = '09'
  AND day = '03'
  AND hour BETWEEN '00' AND '23'
GROUP BY action_category
ORDER BY p95_latency_seconds DESC;
```

### Find duplicate deliveries

Duplicate bronze rows are expected under at-least-once delivery. Deduplicate on
`document_id` in curated layers.

```sql
SELECT
  document_id,
  count(*) AS occurrence_count,
  count(DISTINCT source_object_key) AS source_object_count,
  min(normalized_at) AS first_normalized_at,
  max(normalized_at) AS last_normalized_at
FROM github_audit_logs_bronze_dev.bronze_events
WHERE year = '2026'
  AND month = '09'
  AND day = '03'
  AND hour BETWEEN '00' AND '23'
GROUP BY document_id
HAVING count(*) > 1
ORDER BY occurrence_count DESC;
```

### Detect document ID integrity conflicts

A document ID associated with multiple payload hashes requires investigation
before silver-layer deduplication.

```sql
SELECT
  document_id,
  count(*) AS occurrence_count,
  count(DISTINCT payload_sha256) AS payload_versions
FROM github_audit_logs_bronze_dev.bronze_events
WHERE year = '2026'
  AND month = '09'
  AND day = '03'
  AND hour BETWEEN '00' AND '23'
GROUP BY document_id
HAVING count(DISTINCT payload_sha256) > 1
ORDER BY payload_versions DESC, occurrence_count DESC;
```

### Summarize audit API request outcomes

This query intentionally excludes sensitive `source_ip` and `raw_payload`
values.

```sql
SELECT
  request_method,
  route,
  status_code,
  count(*) AS request_count,
  count(DISTINCT actor_id) AS distinct_actors
FROM github_audit_logs_bronze_dev.bronze_events
WHERE year = '2026'
  AND month = '09'
  AND day = '03'
  AND hour BETWEEN '00' AND '23'
  AND action = 'api.request'
GROUP BY 1, 2, 3
ORDER BY request_count DESC;
```

### Reconcile records by source object

```sql
SELECT
  source_object_key,
  source_object_version,
  count(*) AS normalized_record_count,
  min(source_record_index) AS first_record_index,
  max(source_record_index) AS last_record_index,
  min(normalized_at) AS normalized_at
FROM github_audit_logs_bronze_dev.bronze_events
WHERE year = '2026'
  AND month = '09'
  AND day = '03'
  AND hour BETWEEN '00' AND '23'
GROUP BY source_object_key, source_object_version
ORDER BY normalized_at DESC;
```

### Correlate audit and webhook repository activity

Join on immutable repository IDs rather than mutable repository names.

```sql
WITH audit_activity AS (
  SELECT
    repository_id,
    count(*) AS audit_event_count,
    count(DISTINCT actor_id) AS audit_actor_count
  FROM github_audit_logs_bronze_dev.bronze_events
  WHERE year = '2026'
    AND month = '09'
    AND day = '03'
    AND hour BETWEEN '00' AND '23'
    AND repository_id IS NOT NULL
  GROUP BY repository_id
),
webhook_activity AS (
  SELECT
    repository.id AS repository_id,
    max(repository.full_name) AS repository,
    count(*) AS webhook_event_count
  FROM github_webhooks_dev.events
  WHERE year = '2026'
    AND month = '09'
    AND day = '03'
    AND repository.id IS NOT NULL
  GROUP BY repository.id
)
SELECT
  coalesce(webhook.repository_id, audit.repository_id) AS repository_id,
  webhook.repository,
  coalesce(audit.audit_event_count, 0) AS audit_event_count,
  coalesce(audit.audit_actor_count, 0) AS audit_actor_count,
  coalesce(webhook.webhook_event_count, 0) AS webhook_event_count
FROM audit_activity AS audit
FULL OUTER JOIN webhook_activity AS webhook
  ON audit.repository_id = webhook.repository_id
ORDER BY audit_event_count DESC, webhook_event_count DESC;
```

## GitHub webhooks

The webhook table keeps common fields as typed columns and the complete
event-specific payload in `raw_payload`. Replace the UTC partition values in
each example with the period you want to analyze.

### Inspect webhook deliveries

```sql
SELECT
  id AS delivery_id,
  event_type,
  nullif(action, '') AS action,
  repository.full_name AS repository,
  sender.login AS sender
FROM github_webhooks_dev.events
WHERE year = '2026'
  AND month = '09'
  AND day = '03'
LIMIT 100;
```

### Count events by type and action

```sql
SELECT
  event_type,
  coalesce(nullif(action, ''), '(none)') AS action,
  count(*) AS delivery_count
FROM github_webhooks_dev.events
WHERE year = '2026'
  AND month = '09'
  AND day = '03'
GROUP BY 1, 2
ORDER BY delivery_count DESC;
```

### Find the most active repositories

```sql
SELECT
  repository.full_name AS repository,
  count(*) AS delivery_count,
  count(DISTINCT sender.login) AS distinct_senders,
  count_if(event_type = 'pull_request') AS pull_request_events,
  count_if(event_type = 'push') AS push_events
FROM github_webhooks_dev.events
WHERE year = '2026'
  AND month = '09'
  AND day = '03'
  AND repository.full_name IS NOT NULL
GROUP BY repository.full_name
ORDER BY delivery_count DESC
LIMIT 25;
```

### Inspect pull request lifecycle events

```sql
SELECT
  repository.full_name AS repository,
  try_cast(
    json_extract_scalar(raw_payload, '$.pull_request.number') AS bigint
  ) AS pull_request_number,
  action,
  sender.login AS sender,
  json_extract_scalar(raw_payload, '$.pull_request.title') AS title,
  from_iso8601_timestamp(
    json_extract_scalar(raw_payload, '$.pull_request.created_at')
  ) AS created_at,
  from_iso8601_timestamp(
    json_extract_scalar(raw_payload, '$.pull_request.closed_at')
  ) AS closed_at,
  try_cast(
    json_extract_scalar(raw_payload, '$.pull_request.merged') AS boolean
  ) AS merged,
  json_extract_scalar(raw_payload, '$.pull_request.html_url') AS url
FROM github_webhooks_dev.events
WHERE year = '2026'
  AND month = '09'
  AND day = '03'
  AND event_type = 'pull_request'
ORDER BY repository, pull_request_number
LIMIT 100;
```

### Summarize GitHub Actions workflow outcomes

```sql
SELECT
  repository.full_name AS repository,
  json_extract_scalar(raw_payload, '$.workflow_run.name') AS workflow,
  json_extract_scalar(raw_payload, '$.workflow_run.event') AS trigger_event,
  coalesce(
    json_extract_scalar(raw_payload, '$.workflow_run.conclusion'),
    '(in progress)'
  ) AS conclusion,
  count(*) AS run_events
FROM github_webhooks_dev.events
WHERE year = '2026'
  AND month = '09'
  AND day = '03'
  AND event_type = 'workflow_run'
GROUP BY 1, 2, 3, 4
ORDER BY run_events DESC;
```

### Measure commits delivered in push events

```sql
SELECT
  repository.full_name AS repository,
  sender.login AS sender,
  json_extract_scalar(raw_payload, '$.ref') AS git_ref,
  coalesce(
    json_array_length(json_extract(raw_payload, '$.commits')),
    0
  ) AS commit_count,
  json_extract_scalar(raw_payload, '$.compare') AS compare_url
FROM github_webhooks_dev.events
WHERE year = '2026'
  AND month = '09'
  AND day = '03'
  AND event_type = 'push'
ORDER BY commit_count DESC
LIMIT 100;
```

### Detect duplicate webhook deliveries

Webhook delivery IDs should be unique. This query identifies retries or
duplicate records before downstream aggregation.

```sql
SELECT
  id AS delivery_id,
  count(*) AS occurrence_count
FROM github_webhooks_dev.events
WHERE year = '2026'
  AND month = '09'
  AND day = '03'
GROUP BY id
HAVING count(*) > 1
ORDER BY occurrence_count DESC;
```

