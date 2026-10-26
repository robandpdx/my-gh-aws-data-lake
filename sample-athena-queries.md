# Sample Athena Queries

## GitHub Copilot silver

The `github_copilot_silver_dev` tables are Apache Iceberg v2 tables with hidden
day partitioning on typed `report_day`. Filter directly on that date column.

### Daily billed Copilot consumption

```sql
SELECT
  report_day,
  report_type,
  organization_login,
  product,
  sku,
  model,
  sum(net_quantity) AS net_quantity,
  sum(net_amount) AS net_amount
FROM github_copilot_silver_dev.billing_usage_daily
WHERE report_day BETWEEN DATE '2026-09-01' AND DATE '2026-09-30'
GROUP BY 1, 2, 3, 4, 5, 6
ORDER BY report_day DESC, net_amount DESC;
```

### Enterprise adoption and code activity

```sql
SELECT
  report_day,
  daily_active_users,
  weekly_active_users,
  monthly_active_users,
  user_initiated_interaction_count,
  code_generation_activity_count,
  code_acceptance_activity_count,
  loc_added_sum,
  loc_deleted_sum,
  daily_active_cli_users,
  daily_active_copilot_app_users
FROM github_copilot_silver_dev.enterprise_usage_daily
WHERE report_day >= current_date - INTERVAL '30' DAY
ORDER BY report_day;
```

### Users by AI adoption phase

User-level activity is identifiable employee data; apply a restricted Athena
role and aggregate before publishing it to broad dashboards.

```sql
SELECT
  report_day,
  ai_adoption_phase_number,
  ai_adoption_phase,
  count(*) AS users,
  sum(ai_credits_used) AS ai_credits_used,
  sum(user_initiated_interaction_count) AS interactions,
  sum(code_acceptance_activity_count) AS acceptances
FROM github_copilot_silver_dev.user_usage_daily
WHERE report_day >= current_date - INTERVAL '30' DAY
GROUP BY 1, 2, 3
ORDER BY report_day, ai_adoption_phase_number;
```

### Daily model traffic by client

`totals_by_client_json` is available in both `enterprise_usage_daily` and
`user_usage_daily`. It preserves the server-counted client breakdown introduced
in the [October 23, 2026 announcement](https://github.blog/changelog/2026-10-23-usage-metrics-api-adds-usage-from-tools-like-opencode/).
It includes clients such as `opencode`, `claude_code`, `codex`, `copilot_cli`,
and IDEs without requiring a fixed list of client names.

```sql
SELECT
  report_day,
  json_extract_scalar(client_usage, '$.client') AS client,
  cast(json_extract_scalar(client_usage, '$.request_count') AS bigint) AS request_count,
  cast(json_extract_scalar(client_usage, '$.session_count') AS bigint) AS session_count,
  cast(json_extract_scalar(client_usage, '$.token_usage.prompt_tokens_sum') AS bigint)
    AS prompt_tokens,
  cast(json_extract_scalar(client_usage, '$.token_usage.output_tokens_sum') AS bigint)
    AS output_tokens,
  cast(json_extract_scalar(client_usage, '$.token_usage.avg_tokens_per_request') AS double)
    AS avg_tokens_per_request
FROM github_copilot_silver_dev.enterprise_usage_daily
CROSS JOIN UNNEST(cast(json_parse(totals_by_client_json) AS array(json)))
  AS clients(client_usage)
WHERE report_day >= current_date - INTERVAL '30' DAY
ORDER BY report_day DESC, request_count DESC;
```

Requests count successful model calls, not prompts or user interactions. One
prompt can produce multiple requests. Do not add these counts to IDE, CLI, App,
or third-party-agent breakdowns: the surfaces can overlap, and third-party-agent
activity counts jobs/interactions rather than this model traffic. Client
identification is best-effort, not a verified identity. Daily session counts
are not a distinct-session count across a longer reporting period.

### Client traffic by model and selection mode

Keep `model_selection_mode` as a separate dimension. Values include
`user_selected`, `auto`, `product_selected`, `other`, and `unknown`; do not
discard unfamiliar future values. Code review reports model `unknown`, and
code review/cloud agent requests use `product_selected`. Missing nested values
remain SQL null rather than being silently replaced with zeros.

```sql
SELECT
  report_day,
  json_extract_scalar(client_usage, '$.client') AS client,
  json_extract_scalar(model_usage, '$.model') AS model,
  json_extract_scalar(model_usage, '$.model_selection_mode') AS model_selection_mode,
  cast(json_extract_scalar(model_usage, '$.request_count') AS bigint) AS request_count,
  cast(json_extract_scalar(model_usage, '$.token_usage.prompt_tokens_sum') AS bigint)
    AS prompt_tokens,
  cast(json_extract_scalar(model_usage, '$.token_usage.output_tokens_sum') AS bigint)
    AS output_tokens,
  cast(json_extract_scalar(model_usage, '$.token_usage.avg_tokens_per_request') AS double)
    AS avg_tokens_per_request
FROM github_copilot_silver_dev.enterprise_usage_daily
CROSS JOIN UNNEST(cast(json_parse(totals_by_client_json) AS array(json)))
  AS clients(client_usage)
CROSS JOIN UNNEST(cast(json_extract(client_usage, '$.totals_by_model') AS array(json)))
  AS models(model_usage)
WHERE report_day >= current_date - INTERVAL '30' DAY
ORDER BY report_day DESC, client, request_count DESC;
```

### Per-user OpenCode usage

Use the restricted user-level access role. Do not combine user rows with the
enterprise aggregate when summing usage.

```sql
SELECT
  report_day,
  user_id,
  user_login,
  cast(json_extract_scalar(client_usage, '$.request_count') AS bigint) AS request_count,
  cast(json_extract_scalar(client_usage, '$.session_count') AS bigint) AS session_count
FROM github_copilot_silver_dev.user_usage_daily
CROSS JOIN UNNEST(cast(json_parse(totals_by_client_json) AS array(json)))
  AS clients(client_usage)
WHERE report_day >= current_date - INTERVAL '30' DAY
  AND json_extract_scalar(client_usage, '$.client') = 'opencode'
ORDER BY report_day DESC, request_count DESC;
```

All three queries omit records with a null or empty client array. A null
`totals_by_client_json` means the source field was absent/null, or the silver row
has not been reprocessed since the column was added; `[]` means the source
reported no client usage. Neither should be used to infer a collection failure.
For records not yet reprocessed, query
`json_extract(raw_payload, '$.totals_by_client')` instead.

### Named skills, custom agents, MCP servers, slash commands, and plugins

Both enterprise and user usage tables expose these JSON arrays:

| Silver column | Entry name field |
| --- | --- |
| `totals_by_skill_json` | `skill` |
| `totals_by_custom_agent_json` | `custom_agent` |
| `totals_by_mcp_json` | `mcp` |
| `totals_by_slash_cmd_json` | `slash_cmd` |
| `totals_by_plugin_json` | `plugin` |

For example, list daily enterprise skill interactions:

```sql
SELECT
  report_day,
  json_extract_scalar(customization, '$.skill') AS skill,
  cast(json_extract_scalar(customization, '$.interaction_count') AS bigint)
    AS interaction_count
FROM github_copilot_silver_dev.enterprise_usage_daily
CROSS JOIN UNNEST(cast(json_parse(totals_by_skill_json) AS array(json)))
  AS customizations(customization)
WHERE report_day >= current_date - INTERVAL '30' DAY
ORDER BY report_day DESC, interaction_count DESC;
```

To query MCP servers, substitute `totals_by_mcp_json` and `$.mcp` (and rename
the output alias); use the table above for other categories. For per-user
analysis, use `user_usage_daily` and select `user_id`/`user_login` under a
restricted access role. Do not add user rows to enterprise aggregates.
Unnest one category at a time: unnesting multiple arrays together multiplies
rows and inflates counts.

The [October 22, 2026 announcement](https://github.blog/changelog/2026-10-22-custom-skills-agents-and-mcp-servers-in-usage-metrics-api/)
allows up to 25 entries per record, with remaining activity in a trailing
`other` bucket. Keep that bucket; the array is not an exhaustive inventory.
Configured names can disclose internal information, are trimmed/limited to
128 characters upstream, and path-like names remain `other`/`custom`.
These are telemetry-based interaction counts, not server-counted model
requests or billing totals. Do not sum categories as independent activity.

### Per-user customization breadth

The five distinct-use counters are typed `bigint` in `user_usage_daily`.
They describe distinct customizations used by that user on that day, not the
number of visible array entries, which is capped upstream. Summing them across
users or days does not give enterprise-wide distinct customization counts.

```sql
SELECT
  report_day,
  user_id,
  user_login,
  distinct_skill_use_count,
  distinct_custom_agent_use_count,
  distinct_mcp_use_count,
  distinct_slash_cmd_use_count,
  distinct_plugin_use_count
FROM github_copilot_silver_dev.user_usage_daily
WHERE report_day >= current_date - INTERVAL '30' DAY
ORDER BY report_day DESC, user_id;
```

Missing/null source fields stay SQL null, empty arrays stay `[]`, and explicit
zero counters stay zero. JSON arrays with missing/null values or `[]` produce
no rows when unnested. Earlier report days retain `other`/`custom`; replaying
silver cannot recover names absent from the original report.

### Repository pull-request activity

```sql
SELECT
  report_day,
  repository_full_name,
  pull_requests_created,
  pull_requests_created_by_copilot,
  pull_requests_reviewed,
  pull_requests_reviewed_by_copilot,
  pull_requests_merged,
  median_minutes_to_merge
FROM github_copilot_silver_dev.repository_usage_daily
WHERE report_day >= current_date - INTERVAL '30' DAY
ORDER BY report_day DESC, pull_requests_created DESC;
```

### Team-level daily usage

GitHub excludes teams with fewer than five seated Copilot users. A missing team
day therefore does not necessarily indicate collection failure.

```sql
SELECT
  membership.report_day,
  membership.organization_id,
  membership.team_slug,
  count(DISTINCT membership.user_id) AS active_users,
  sum(usage.ai_credits_used) AS ai_credits_used,
  sum(usage.user_initiated_interaction_count) AS interactions,
  sum(usage.code_acceptance_activity_count) AS acceptances
FROM github_copilot_silver_dev.user_team_memberships_daily AS membership
JOIN github_copilot_silver_dev.user_usage_daily AS usage
  ON membership.report_day = usage.report_day
 AND membership.enterprise_id = usage.enterprise_id
 AND membership.user_id = usage.user_id
WHERE membership.report_day >= current_date - INTERVAL '30' DAY
GROUP BY 1, 2, 3
ORDER BY membership.report_day DESC, active_users DESC;
```

### Inspect silver quarantine

```sql
SELECT report_day, source, report_type, reason, count(*) AS records
FROM github_copilot_silver_dev.quarantined_records
WHERE quarantined_at >= current_timestamp - INTERVAL '7' DAY
GROUP BY 1, 2, 3, 4
ORDER BY records DESC;
```

## GitHub Copilot bronze

Copilot partitions represent the GitHub report day. Recent report days have
multiple reconciliation snapshots, so select the latest `collection_date`
before aggregating. Partition projection means no `MSCK REPAIR TABLE` command
is required.

### Summarize latest Copilot billing snapshots

```sql
WITH scoped AS (
  SELECT *
  FROM github_copilot_bronze_dev.billing_usage
  WHERE year = '2026'
    AND month = '09'
    AND day BETWEEN '01' AND '30'
    AND report_type IN ('ai_credit', 'premium_request')
),
latest AS (
  SELECT report_day, report_type, max(collection_date) AS collection_date
  FROM scoped
  GROUP BY report_day, report_type
)
SELECT
  cast(scoped.report_day AS date) AS usage_day,
  scoped.report_type,
  scoped.organization_login,
  scoped.product,
  scoped.sku,
  scoped.model,
  sum(scoped.net_quantity) AS net_quantity,
  sum(scoped.net_amount) AS net_amount
FROM scoped
JOIN latest
  ON scoped.report_day = latest.report_day
 AND scoped.report_type = latest.report_type
 AND scoped.collection_date = latest.collection_date
GROUP BY 1, 2, 3, 4, 5, 6
ORDER BY usage_day DESC, net_amount DESC;
```

### Check latest Copilot usage report coverage

This query reports source row counts rather than interpreting the evolving
metric payload. Promote frequently used values from `raw_payload` only after
their production types and null behavior have been verified.

```sql
WITH scoped AS (
  SELECT *
  FROM github_copilot_bronze_dev.usage_reports
  WHERE year = '2026'
    AND month = '09'
    AND day BETWEEN '01' AND '30'
    AND report_type IN ('enterprise', 'users', 'repositories', 'user_teams')
),
latest AS (
  SELECT report_day, report_type, max(collection_date) AS collection_date
  FROM scoped
  GROUP BY report_day, report_type
)
SELECT
  cast(scoped.report_day AS date) AS report_day,
  scoped.report_type,
  latest.collection_date,
  count(*) AS source_rows,
  count(DISTINCT scoped.user_id) AS users,
  count(DISTINCT scoped.repository_id) AS repositories,
  count(DISTINCT scoped.team_id) AS teams
FROM scoped
JOIN latest
  ON scoped.report_day = latest.report_day
 AND scoped.report_type = latest.report_type
 AND scoped.collection_date = latest.collection_date
GROUP BY 1, 2, 3
ORDER BY report_day DESC, report_type;
```

## GitHub webhook silver

The `github_webhooks_silver_dev` tables are Apache Iceberg v2 tables. They use
hidden day partitioning on `received_at`, so filter directly on timestamp
columns rather than Hive partition strings.

### Reconcile canonical and quarantined deliveries

```sql
WITH canonical AS (
  SELECT count(*) AS canonical_rows
  FROM github_webhooks_silver_dev.events
  WHERE received_at >= TIMESTAMP '2026-09-01 00:00:00 UTC'
    AND received_at < TIMESTAMP '2026-09-02 00:00:00 UTC'
),
quarantine AS (
  SELECT reason, count(*) AS quarantined_rows
  FROM github_webhooks_silver_dev.quarantined_events
  WHERE quarantined_at >= TIMESTAMP '2026-09-01 00:00:00 UTC'
    AND quarantined_at < TIMESTAMP '2026-09-02 00:00:00 UTC'
  GROUP BY reason
)
SELECT canonical.canonical_rows, quarantine.reason, quarantine.quarantined_rows
FROM canonical
CROSS JOIN quarantine
ORDER BY quarantine.quarantined_rows DESC;
```

### Inspect workflow job lifecycle deliveries

One row represents one webhook delivery, not one unique job. Group by
`workflow_job_id` when computing job-level measures.

```sql
SELECT
  workflow_job_id,
  max_by(status, event_at) AS latest_status,
  max_by(conclusion, event_at) AS latest_conclusion,
  min(created_at) AS created_at,
  min(started_at) AS started_at,
  max(completed_at) AS completed_at,
  max(runner_labels) AS runner_labels,
  count(*) AS lifecycle_deliveries
FROM github_webhooks_silver_dev.actions_workflow_jobs
WHERE received_at >= current_timestamp - INTERVAL '7' DAY
GROUP BY workflow_job_id
ORDER BY completed_at DESC NULLS LAST;
```

### Summarize push activity

```sql
SELECT
  date_trunc('day', event_at) AS event_day,
  organization_login,
  repository_full_name,
  ref,
  count(*) AS push_deliveries,
  sum(commit_count) AS commits,
  sum(distinct_commit_count) AS distinct_commits,
  count_if(forced) AS force_pushes
FROM github_webhooks_silver_dev.push_events
WHERE received_at >= current_timestamp - INTERVAL '30' DAY
GROUP BY 1, 2, 3, 4
ORDER BY event_day DESC, commits DESC;
```

### Summarize pull request activity

```sql
SELECT
  date_trunc('day', event_at) AS event_day,
  organization_login,
  repository_full_name,
  count_if(action = 'opened') AS opened,
  count_if(action = 'closed' AND merged) AS merged,
  count_if(action = 'closed' AND NOT coalesce(merged, false)) AS closed_unmerged
FROM github_webhooks_silver_dev.pull_requests
WHERE received_at >= current_timestamp - INTERVAL '30' DAY
  AND event_type = 'pull_request'
GROUP BY 1, 2, 3
ORDER BY event_day DESC, opened DESC;
```

### Measure average pull request time to close

This measures the time from initial creation to first closure and groups by
pull request to avoid counting duplicate closure deliveries. Use
`max(closed_at)` instead of `min(closed_at)` to measure time to final closure
for pull requests that were reopened.

```sql
WITH closed_pull_requests AS (
  SELECT
    pull_request_id,
    min(created_at) AS opened_at,
    min(closed_at) AS closed_at
  FROM github_webhooks_silver_dev.pull_requests
  WHERE event_type = 'pull_request'
    AND action = 'closed'
    AND created_at IS NOT NULL
    AND closed_at IS NOT NULL
  GROUP BY pull_request_id
)
SELECT
  count(*) AS pull_requests_closed,
  round(
    avg(date_diff('second', opened_at, closed_at)) / 3600.0,
    2
  ) AS average_hours_open
FROM closed_pull_requests;
```

### Review security alert transitions

```sql
SELECT
  event_at,
  alert_kind,
  repository_full_name,
  alert_number,
  action,
  state,
  severity,
  resolution
FROM github_webhooks_silver_dev.security_alerts
WHERE received_at >= current_timestamp - INTERVAL '30' DAY
ORDER BY event_at DESC;
```

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

## Enterprise identity and licenses

The identity tables are daily snapshots from GitHub's enterprise
`consumed-licenses` endpoint. They include license-associated users rather than
every association in the broader membership CSV. Always select one complete
snapshot and prune its `year`, `month`, and `day` partitions.

### Review daily license utilization

```sql
SELECT
  cast(snapshot_date AS date) AS snapshot_date,
  total_seats_purchased,
  total_seats_consumed,
  total_seats_purchased - total_seats_consumed AS seats_available,
  user_count
FROM github_identity_bronze_dev.enterprise_license_summary_daily
WHERE year = '2026'
  AND month = '09'
  AND day BETWEEN '01' AND '30'
  AND complete
ORDER BY snapshot_date DESC;
```

### Find users inactive for 90 days excluding authentication

This example uses the 2026-09-17 roster snapshot and scans one year of audit
history. Change both ranges together. GitHub's consumed-license endpoint does
not return numeric user IDs, so this joins case-insensitive logins and can miss
users who changed their login during the audit window. A null activity time
means no qualifying event was observed in the selected history, not proof that
the user has never been active.

Review and extend the authentication action list against the actions present in
your enterprise before using this query for access-removal decisions.

```sql
WITH authentication_actions (action) AS (
  VALUES
    ('user.login'),
    ('user.failed_login'),
    ('user.two_factor_authentication_failed'),
    ('org.saml_sso_auth'),
    ('business.saml_sso_response')
),
roster AS (
  SELECT
    users.github_login,
    users.github_name,
    users.member_roles,
    users.enterprise_roles,
    licenses.license_type
  FROM github_identity_bronze_dev.enterprise_users_daily AS users
  JOIN github_identity_bronze_dev.enterprise_licenses_daily AS licenses
    ON users.snapshot_date = licenses.snapshot_date
   AND users.github_login = licenses.github_login
  WHERE users.year = '2026'
    AND users.month = '09'
    AND users.day = '17'
    AND licenses.year = '2026'
    AND licenses.month = '09'
    AND licenses.day = '17'
    AND users.github_login IS NOT NULL
),
ranked_events AS (
  SELECT
    document_id,
    actor,
    action,
    event_timestamp,
    row_number() OVER (
      PARTITION BY document_id
      ORDER BY normalized_at DESC, source_object_key DESC, source_record_index DESC
    ) AS occurrence
  FROM github_audit_logs_bronze_dev.bronze_events
  WHERE year BETWEEN '2025' AND '2026'
    AND event_timestamp >= TIMESTAMP '2025-09-17 00:00:00 UTC'
    AND event_timestamp < TIMESTAMP '2026-09-18 00:00:00 UTC'
    AND record_family = 'audit'
    AND actor IS NOT NULL
    AND NOT coalesce(actor_is_bot, false)
),
last_non_authentication_activity AS (
  SELECT
    lower(event.actor) AS actor_login,
    max(event.event_timestamp) AS last_active_at
  FROM ranked_events AS event
  LEFT JOIN authentication_actions AS authentication
    ON event.action = authentication.action
  WHERE event.occurrence = 1
    AND authentication.action IS NULL
  GROUP BY lower(event.actor)
)
SELECT
  roster.github_login,
  roster.github_name,
  roster.license_type,
  roster.member_roles,
  roster.enterprise_roles,
  activity.last_active_at,
  date_diff('day', activity.last_active_at, current_timestamp) AS inactive_days
FROM roster
LEFT JOIN last_non_authentication_activity AS activity
  ON lower(roster.github_login) = activity.actor_login
WHERE activity.last_active_at IS NULL
   OR activity.last_active_at < current_timestamp - INTERVAL '90' DAY
ORDER BY activity.last_active_at NULLS FIRST, roster.github_login;
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
  FROM github_webhooks_bronze_dev.events
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
FROM github_webhooks_bronze_dev.events
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
FROM github_webhooks_bronze_dev.events
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
FROM github_webhooks_bronze_dev.events
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
FROM github_webhooks_bronze_dev.events
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
FROM github_webhooks_bronze_dev.events
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
FROM github_webhooks_bronze_dev.events
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
FROM github_webhooks_bronze_dev.events
WHERE year = '2026'
  AND month = '09'
  AND day = '03'
GROUP BY id
HAVING count(*) > 1
ORDER BY occurrence_count DESC;
```
