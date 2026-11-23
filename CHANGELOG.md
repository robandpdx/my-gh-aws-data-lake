# Changelog

Stack changes, compatibility notes, and migration instructions belong here.
The [README](./README.md) describes the current stack, setup, and operation.
Link each GitHub-driven change to the relevant GitHub changelog article when
available; upstream announcement dates are not stack deployment dates.

## Unreleased

### GHE.com audit-log streaming with OIDC

- Add the optional `GitHubEnterpriseCloudSubdomain` deployment parameter for
  GitHub Enterprise Cloud with data residency. When nonempty, it selects the
  exact lowercase `https://<subdomain>.ghe.com` audit-log OIDC subject. The empty
  default preserves the case-sensitive github.com enterprise-slug subject.
  The provider URL, `sts.amazonaws.com` audience, and bucket-scoped
  `s3:PutObject` permission are unchanged.
- Source: [S3 audit-log streaming with OpenID Connect expands to GHE.com](https://github.blog/changelog/2026-11-19-s3-audit-log-streaming-with-openid-connect-expands-to-ghe-com/)
  (GitHub announcement: November 19, 2026).
  See GitHub's [S3 OIDC setup documentation](https://docs.github.com/enterprise-cloud@latest/admin/monitoring-activity-in-your-enterprise/reviewing-audit-logs-for-your-enterprise/streaming-the-audit-log-for-your-enterprise#setting-up-streaming-to-s3-with-openid-connect).
- Upgrade: validate, build, and redeploy the existing stack while preserving
  its current parameters. For GHE.com, supply only the lowercase hostname label
  as `GitHubEnterpriseCloudSubdomain` and retain `GitHubEnterpriseSlug`. For
  github.com, leave the new parameter empty; no stream reconfiguration is
  required. This parameter does not change optional collectors' API endpoints.
- A GHE.com enterprise owner must configure the S3 stream with the existing
  bucket, Region, and writer-role outputs, then run **Check endpoint** and save.
  Review the destination's data residency/compliance requirements first.
  When migrating an access-key stream, revoke its old AWS credentials after
  verifying OIDC delivery. If the subdomain changes or the enterprise is deleted,
  remove old subjects from any other IAM trust policies; updating this stack
  replaces only this writer role's subject.
- No new dataset, payload fields, GitHub API permission, or secret is required.
  Raw/bronze processing and replay formats are unchanged; no data migration or
  backfill is required. Enabling a stream does not recover pre-stream history.

### Organization webhook installer integration

- Maintain `organization-webhooks.json` for
  [github-org-app-installer](https://github.com/robandpdx/github-org-app-installer),
  with the nine documented issue, pull-request, relationship, and security-alert
  events, JSON delivery, TLS verification, and a `__WEBHOOK_URL__` placeholder.
- Document runtime URL substitution, bulk reconciliation, ongoing organization
  setup, and the installer's full-payload signing-secret behavior. No local
  installer wrapper or CSV configuration is required.
- Require the weekly agent to maintain the JSON definitions alongside ingestion
  changes while preserving placeholders and avoiding credentials or live
  webhook mutations. Operators must apply reviewed changes through the
  installer; no stack deployment or data migration is needed for this change.
- This is stack configuration tooling, not a new GitHub data feature; there
  is no corresponding GitHub changelog article.

### Documentation organization

- Separate change history and migration guidance from the stack README.
- Require weekly data-coverage proposals to update this changelog with source
  links and upgrade/backfill requirements, while keeping the README focused on
  the current stack.

## Recorded stack changes

The entries below were moved from existing documentation. Original stack
release/deployment dates were not recorded, so none are inferred from the
upstream article dates.

### Additional silver coverage from the September-November 2026 review

#### Changes and GitHub sources

The existing daily Copilot collectors already archive these source fields.
The silver job additionally promotes:

- Dedicated VS Code Agents-window active users, sessions, user-message totals,
  and per-user `used_vscode_agent`, independently of editor-window agent mode.
  Source: [September 18 usage metrics announcement](https://github.blog/changelog/2026-09-18-github-copilot-weekly-releases-september-14).
- Daily missing-client-telemetry and below-minimum-version counts, per-user
  `client_telemetry_present`, and the complete `usage_metrics_requirements`
  object as JSON.
  Source: [Telemetry and version gaps](https://github.blog/changelog/2026-11-05-usage-metrics-api-flags-telemetry-and-version-gaps).
- Repository `pull_request_review_times_json`, preserving each author/reviewer
  cohort's median and p90 timings rather than averaging percentiles.
  Source: [Pull request review stages](https://github.blog/changelog/2026-09-25-usage-metrics-api-adds-pull-request-review-stages).
- Repository `copilot_code_review_json`, preserving all breakdowns and future
  nested fields, plus typed evaluated/addressed comment counts and the number
  of merged PRs without a later human change request.
  Sources: [Code review details and addressed rate](https://github.blog/changelog/2026-11-05-usage-metrics-api-adds-code-review-details-and-addressed-rate)
  and [Repository insights](https://github.blog/changelog/2026-11-17-track-copilot-code-review-outcomes-in-repository-insights).

The webhook silver job promotes `issue_relates_to` deliveries into `issues`,
including nullable `related_issue_id`, and preserves issue field definitions,
values, and changes as JSON. Sources: [Issue relationships](https://github.blog/changelog/2026-09-25-personal-saved-views-for-repository-issues-and-more)
and [Personal-account issue types and fields](https://github.blog/changelog/2026-11-11-issue-types-and-fields-are-available-for-personal-accounts).
Subscribe your organization or GitHub App webhook to `issue_relates_to` as well
as `issues`; enterprise global webhooks cannot emit this event. Cross-repository
deliveries intentionally omit the other issue's identity; a null is not a
collection error.

The security-alert table exposes Dependabot's `dependency_version_requirement`.
Source: [Dependency versions in Dependabot alerts](https://github.blog/changelog/2026-10-20-dependabot-alerts-rest-api-now-includes-dependency-versions).
Regression coverage also checks [withdrawn alerts](https://github.blog/changelog/2026-10-13-improved-detection-for-withdrawn-dependabot-alerts):
they can contain only identifiers, so missing state/version fields remain null
rather than rejecting the delivery.

#### Migration and backfill

Both Glue jobs add missing Iceberg columns on startup without dropping existing
columns or rows. A normal SAM build/deployment republishes the scripts through
the versioned script publisher; no infrastructure permissions or schedules
change. Use the [existing-stack deployment procedure](#deploying-client-level-usage-support-to-an-existing-stack)
below for Copilot and the [webhook job instructions](./README.md#7-operate-the-webhook-silver-layer)
for webhook processing.

New columns on existing rows remain null until the corresponding bronze dates
are replayed with bookmarks disabled. Webhook dates use arrival-date partitions;
Copilot dates use report-day partitions. Follow each job's date-window limit.
No new source, credentials, preview, or sensitive-content capture is enabled
automatically.

Missing or null source fields remain SQL null; measured false/zero values and
empty arrays stay distinct. Review-stage data starts with qualifying PRs ready
for review on or after September 21, 2026; replay cannot manufacture earlier
data. [Telemetry gaps caused by affected IDE versions](https://github.blog/changelog/2026-10-06-update-your-ide-to-restore-agent-activity-in-copilot-usage-metrics)
cannot be recovered either. Review outcomes count on the merge day and are not
the same as suggestion-apply counts. Do not sum overlapping telemetry-health
counts, average daily medians, or interpret absent telemetry as employee
inactivity.

See the [Athena examples](./sample-athena-queries.md#copilot-telemetry-health),
[validation instructions](./README.md#validation), and
[historical coverage review and follow-up collection plans](./github-enterprise-data-collection-guide.md#changelog-coverage-review-september-18-november-18-2026).

### Client-level usage support

The [October 23, 2026 API addition](https://github.blog/changelog/2026-10-23-usage-metrics-api-adds-usage-from-tools-like-opencode/)
is additive. Existing enterprise/user daily collection already archives
`totals_by_client`; no new endpoint, GitHub permission, secret, or collection
setting is needed. Organization-specific and 28-day collection are not required
for this stack's existing enterprise-wide scope.

#### Deploying client-level usage support to an existing stack

1. Use the AWS account, profile, Region, and SAM configuration for the existing
   deployment. Keep `EnableCopilotCollection=true` and the current secret ARN
   and other parameter values. Do not replace saved parameters with the
   [minimal first-deployment example](./README.md#1-execute-the-infrastructure-deployment).

   ```bash
   PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_copilot_*.py' -v
   sam validate --lint
   sam build --use-container
   sam deploy --config-env default --confirm-changeset
   ```

   Substitute your configuration environment if it is not `default`, and
   review the changeset before approving. Wait for `UPDATE_COMPLETE`. SAM
   packages the silver script with the Glue script publisher; the changed
   publisher version makes the custom resource upload the new script
   automatically. No manual S3 upload is needed.

2. Run the upgraded silver job, or wait for the next scheduled run. At startup
   it creates missing tables and adds missing declared columns to existing
   Iceberg tables before any merge, including when no new bronze rows are
   available. This migration is repeatable and does not drop columns, change
   existing column types, or rewrite historical rows. The existing Glue role
   already has catalog-update permission. Do not edit Glue column metadata
   manually or run `MSCK REPAIR TABLE`.

   ```bash
   export STACK_NAME="your-existing-stack-name"
   export COPILOT_SILVER_JOB="$(aws cloudformation describe-stacks \
     --stack-name "$STACK_NAME" \
     --query 'Stacks[0].Outputs[?OutputKey==`CopilotSilverGlueJobName`].OutputValue | [0]' \
     --output text)"

   aws glue start-job-run --job-name "$COPILOT_SILVER_JOB"
   ```

   Save the returned `JobRunId` and check its state:

   ```bash
   aws glue get-job-run \
     --job-name "$COPILOT_SILVER_JOB" \
     --run-id <JOB_RUN_ID> \
     --query 'JobRun.{State:JobRunState,Error:ErrorMessage}'
   ```

   Wait for `SUCCEEDED` before starting another run. The job allows only one
   concurrent run; avoid the daily 10:30 UTC schedule (or your configured time)
   during manual backfills. Inspect Glue logs on failure rather than assuming
   a schema update completed.

3. To populate the new column for previously processed dates, replay retained
   bronze through silver with bookmarks disabled. This does not reset or
   advance the scheduled job's bookmarks. For example, after bronze for these
   report days is present:

   ```bash
   aws glue start-job-run \
     --job-name "$COPILOT_SILVER_JOB" \
     --arguments '{
       "--job-bookmark-option":"job-bookmark-disable",
       "--start_date":"2026-10-23",
       "--end_date":"2026-10-25"
     }'
   ```

   Choose dates actually available in bronze. Normal collection requests usage
   from UTC today minus 10 days through today minus 4 days, so on October 26 the
   normal run only requests through October 22. Newer report days will arrive
   later; their absence is not a deployment failure. Replaying old bronze
   cannot invent a missing source field. Only re-download reports using the
   [coordinator backfill](./README.md#8-operate-copilot-billing-and-usage-collection)
   if GitHub has made enriched reports available; the announcement does not
   promise historical backfill. Wait for all collection tasks to finish
   successfully before replaying silver.

4. In the stack's Athena workgroup, use the matching silver database name
   (replace `dev` below if needed) to verify both table schemas:

   ```sql
   SELECT table_name, column_name, data_type
   FROM information_schema.columns
   WHERE table_schema = 'github_copilot_silver_dev'
     AND table_name IN ('enterprise_usage_daily', 'user_usage_daily')
     AND column_name = 'totals_by_client_json';
   ```

   Expect two rows with type `varchar`. Then check the chosen replay range:

   ```sql
   SELECT
     report_day,
     totals_by_client_json IS NOT NULL AS client_field_available,
     json_array_length(totals_by_client_json) AS client_count
   FROM github_copilot_silver_dev.enterprise_usage_daily
   WHERE report_day BETWEEN DATE '2026-10-23' AND DATE '2026-10-25'
   ORDER BY report_day;
   ```

   A null value means absent/null source data or an unreprocessed row, not zero
   usage; `[]` means the source reported no client usage. Client/model and
   restricted per-user queries are in
   [sample-athena-queries.md](./sample-athena-queries.md#daily-model-traffic-by-client).
   Counts represent successful model calls, not prompts, and overlap with
   existing surface breakdowns. Client names are best-effort identifiers.

### Named customization usage support

The [October 22, 2026 API update](https://github.blog/changelog/2026-10-22-custom-skills-agents-and-mcp-servers-in-usage-metrics-api/)
reports configured names for skills, custom agents, MCP servers, slash commands,
and plugins. Existing raw/bronze collection already preserves these arrays
without limiting their size. No new endpoint, secret, or permission is needed.

Use the same build/deploy, silver-job startup, and bounded replay steps in
[the client-level deployment instructions](#deploying-client-level-usage-support-to-an-existing-stack).
The automatic migration adds all five JSON columns to each usage table and
the five distinct-use counters to the user table, including when upgrading
directly from a deployment without client-level support. No manual DDL or S3
upload is needed. To verify the new columns in Athena:

```sql
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'github_copilot_silver_dev'
  AND table_name IN ('enterprise_usage_daily', 'user_usage_daily')
  AND column_name IN (
    'totals_by_skill_json', 'totals_by_custom_agent_json', 'totals_by_mcp_json',
    'totals_by_slash_cmd_json', 'totals_by_plugin_json',
    'distinct_skill_use_count', 'distinct_custom_agent_use_count',
    'distinct_mcp_use_count', 'distinct_slash_cmd_use_count', 'distinct_plugin_use_count'
  )
ORDER BY table_name, column_name;
```

Expect 15 rows: five `varchar` breakdowns on each table and five `bigint`
counters only on `user_usage_daily`. Use the environment's database name.
Replay dates already present in bronze to populate previously processed rows.
Names appear only for report days processed by GitHub after this release;
earlier reports retain `other`/`custom`, and replay does not reconstruct names.

See the [current customization requirements and interpretation guidance](./README.md#8-operate-copilot-billing-and-usage-collection),
[customization queries](./sample-athena-queries.md#named-skills-custom-agents-mcp-servers-slash-commands-and-plugins),
and [Spark/Iceberg validation instructions](./README.md#validation).

### Legacy webhook compatibility

Webhook history can predate the API Gateway mapping that captures `raw_payload`,
`id`, `event_type`, and precise receipt timestamps. Those fields are populated
only for records received after deploying the corresponding mapping; replay
cannot reconstruct missing source data.

Bronze history without receiver-side signature validation or a precise receiver
timestamp is marked `legacy_unverified`. Bounded backfills derive `received_at`
from the Firehose UTC day prefix with `received_at_precision = 'day'`; midnight
is a partition marker, not the actual receipt time. Records with API Gateway's
`received_at_epoch_ms` use millisecond precision. Receiver hardening can supply
`signature_valid` and `trust_state` without changing the silver schema.

No related GitHub changelog article was recorded for these stack-specific
receiver changes.
