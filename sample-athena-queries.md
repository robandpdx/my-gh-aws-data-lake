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

