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

### Create the Copilot usage metadata view

Copilot usage records share the audit stream but are not ordinary audit
actions. Requests contain a JSON-encoded `body`; responses can contain a
server-sent event stream. The restricted view below extracts only operational
metadata and source-reported token counters. It never exposes request or
response content, headers, prompts, tool arguments, or generated text.

The token fields are preview data whose semantics can vary by endpoint and
model. The view takes the last value reported in an SSE response rather than
summing cumulative counters.

```sql
CREATE OR REPLACE VIEW
  github_audit_logs_bronze_dev.copilot_usage_records_metadata AS
WITH copilot_records AS (
  SELECT
    document_id,
    event_id,
    github_request_id,
    event_timestamp,
    copilot_record_type,
    user_id,
    enterprise_id,
    endpoint,
    truncated,
    payload_sha256,
    source_object_key,
    source_record_index,
    schema_version,
    normalized_at,
    year,
    month,
    day,
    hour,
    json_extract_scalar(raw_payload, '$.body') AS body
  FROM github_audit_logs_bronze_dev.bronze_events
  WHERE record_family = 'copilot_usage'
)
SELECT
  document_id,
  event_id,
  github_request_id,
  event_timestamp,
  copilot_record_type,
  user_id,
  enterprise_id,
  endpoint,
  truncated,
  CASE
    WHEN copilot_record_type = 'request'
      THEN try(json_extract_scalar(body, '$.model'))
    WHEN copilot_record_type = 'response'
      THEN nullif(regexp_extract(body, '"model"\s*:\s*"([^"]+)"', 1), '')
  END AS model,
  CASE WHEN copilot_record_type = 'request' THEN
    try_cast(json_extract_scalar(body, '$.max_tokens') AS bigint)
  END AS requested_max_tokens,
  CASE WHEN copilot_record_type = 'request' THEN
    try(json_array_length(json_extract(body, '$.messages')))
  END AS request_message_count,
  CASE WHEN copilot_record_type = 'request' THEN
    try(json_array_length(json_extract(body, '$.tools')))
  END AS request_tool_count,
  CASE WHEN copilot_record_type = 'response' THEN
    try_cast(element_at(
      regexp_extract_all(body, '"input_tokens"\s*:\s*(\d+)', 1), -1
    ) AS bigint)
  END AS input_tokens,
  CASE WHEN copilot_record_type = 'response' THEN
    try_cast(element_at(
      regexp_extract_all(body, '"output_tokens"\s*:\s*(\d+)', 1), -1
    ) AS bigint)
  END AS output_tokens,
  CASE WHEN copilot_record_type = 'response' THEN
    try_cast(element_at(
      regexp_extract_all(
        body,
        '"cache_creation_input_tokens"\s*:\s*(\d+)',
        1
      ),
      -1
    ) AS bigint)
  END AS cache_creation_input_tokens,
  CASE WHEN copilot_record_type = 'response' THEN
    try_cast(element_at(
      regexp_extract_all(body, '"cache_read_input_tokens"\s*:\s*(\d+)', 1),
      -1
    ) AS bigint)
  END AS cache_read_input_tokens,
  CASE WHEN copilot_record_type = 'response' THEN
    try_cast(element_at(
      regexp_extract_all(body, '"thinking_tokens"\s*:\s*(\d+)', 1), -1
    ) AS bigint)
  END AS thinking_tokens,
  copilot_record_type = 'response'
    AND NOT truncated
    AND regexp_like(body, '(?m)^event: message_stop\r?$') AS usage_complete,
  1 AS body_parser_version,
  payload_sha256,
  source_object_key,
  source_record_index,
  schema_version,
  normalized_at,
  year,
  month,
  day,
  hour
FROM copilot_records;
```

Treat this view as a convenience projection, not an access-control boundary.
Use Lake Formation and S3/IAM policy to prevent its consumers from reading the
underlying `raw_payload` column or bronze objects directly.

### Inspect Copilot request and response metadata

`event_id` identifies one streamed record. `github_request_id` correlates the
request and response and must not be used as the deduplication key.

```sql
SELECT
  event_timestamp,
  event_id,
  github_request_id,
  copilot_record_type,
  endpoint,
  model,
  request_message_count,
  request_tool_count,
  input_tokens,
  output_tokens,
  cache_creation_input_tokens,
  cache_read_input_tokens,
  thinking_tokens,
  truncated,
  usage_complete
FROM github_audit_logs_bronze_dev.copilot_usage_records_metadata
WHERE year = '2026'
  AND month = '09'
  AND day = '03'
  AND hour BETWEEN '00' AND '23'
ORDER BY github_request_id, event_timestamp;
```

### Summarize complete Copilot responses

Exclude truncated or incomplete responses from token totals. Deduplicate only
after applying physical partition filters so Athena can prune S3. Use the
future Iceberg silver table when canonical deduplication must span all ingest
partitions.

```sql
WITH selected_responses AS (
  SELECT *
  FROM github_audit_logs_bronze_dev.copilot_usage_records_metadata
  WHERE year = '2026'
    AND month = '09'
    AND day = '03'
    AND hour BETWEEN '00' AND '23'
    AND copilot_record_type = 'response'
),
event_stats AS (
  SELECT
    event_id,
    count(*) AS delivery_count,
    count(DISTINCT payload_sha256) AS payload_versions
  FROM selected_responses
  GROUP BY event_id
),
ranked_responses AS (
  SELECT
    response.*,
    row_number() OVER (
      PARTITION BY event_id
      ORDER BY normalized_at DESC, source_object_key DESC, source_record_index DESC
    ) AS occurrence
  FROM selected_responses AS response
)
SELECT
  date_trunc('hour', response.event_timestamp) AS event_hour,
  response.endpoint,
  response.model,
  count(*) AS response_count,
  count(DISTINCT response.user_id) AS distinct_users,
  sum(response.input_tokens) AS input_tokens,
  sum(response.output_tokens) AS output_tokens,
  sum(response.cache_creation_input_tokens) AS cache_creation_input_tokens,
  sum(response.cache_read_input_tokens) AS cache_read_input_tokens,
  sum(response.thinking_tokens) AS thinking_tokens,
  sum(statistics.delivery_count - 1) AS duplicate_deliveries,
  count_if(statistics.payload_versions > 1) AS integrity_conflicts
FROM ranked_responses AS response
JOIN event_stats AS statistics USING (event_id)
WHERE response.occurrence = 1
  AND response.usage_complete
GROUP BY 1, 2, 3
ORDER BY event_hour DESC, response_count DESC;
```

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

