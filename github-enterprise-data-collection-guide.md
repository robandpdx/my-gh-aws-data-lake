# GitHub enterprise data collection guide

Source: [GitHub webhook events and payloads](https://docs.github.com/en/webhooks/webhook-events-and-payloads) (accessed September 11, 2026).

| Webhook event | Repository webhook | Organization webhook | GitHub App webhook | Enterprise webhook |
|---|:---:|:---:|:---:|:---:|
| [`branch_protection_configuration`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#branch_protection_configuration) | Yes | Yes | Yes | No |
| [`branch_protection_rule`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#branch_protection_rule) | Yes | Yes | Yes | No |
| [`check_run`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#check_run) | Yes | Yes | Yes | No |
| [`check_suite`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#check_suite) | Yes | Yes | Yes | No |
| [`code_scanning_alert`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#code_scanning_alert) | Yes | Yes | Yes | No |
| [`commit_comment`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#commit_comment) | Yes | Yes | Yes | No |
| [`create`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#create) | Yes | Yes | Yes | No |
| [`custom_property`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#custom_property) | No | Yes | Yes | Yes |
| [`custom_property_values`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#custom_property_values) | Yes | Yes | Yes | No |
| [`delete`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#delete) | Yes | Yes | Yes | No |
| [`dependabot_alert`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#dependabot_alert) | Yes | Yes | Yes | No |
| [`dismissal_request_code_scanning`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#dismissal_request_code_scanning) | Yes | Yes | Yes | No |
| [`dismissal_request_dependabot`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#dismissal_request_dependabot) | Yes | Yes | Yes | No |
| [`dismissal_request_secret_scanning`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#dismissal_request_secret_scanning) | Yes | Yes | Yes | No |
| [`deploy_key`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#deploy_key) | Yes | Yes | Yes | No |
| [`deployment`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#deployment) | Yes | Yes | Yes | No |
| [`deployment_protection_rule`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#deployment_protection_rule) | No | No | Yes | No |
| [`deployment_review`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#deployment_review) | No | No | Yes | No |
| [`deployment_status`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#deployment_status) | Yes | Yes | Yes | No |
| [`discussion`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#discussion) | Yes | Yes | Yes | No |
| [`discussion_comment`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#discussion_comment) | Yes | Yes | Yes | No |
| [`fork`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#fork) | Yes | Yes | Yes | Yes |
| [`github_app_authorization`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#github_app_authorization) | No | No | Yes | No |
| [`gollum`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#gollum) | Yes | Yes | Yes | No |
| [`installation`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#installation) | No | No | Yes | No |
| [`installation_repositories`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#installation_repositories) | No | No | Yes | No |
| [`installation_target`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#installation_target) | No | No | Yes | No |
| [`issue_comment`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#issue_comment) | Yes | Yes | Yes | No |
| [`issue_dependencies`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#issue_dependencies) | Yes | Yes | Yes | No |
| [`issues`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#issues) | Yes | Yes | Yes | No |
| [`label`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#label) | Yes | Yes | Yes | No |
| [`marketplace_purchase`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#marketplace_purchase) | No | No | No | No |
| [`member`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#member) | Yes | Yes | Yes | Yes |
| [`membership`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#membership) | No | Yes | Yes | Yes |
| [`merge_group`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#merge_group) | No | No | Yes | No |
| [`meta`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#meta) | Yes | Yes | Yes | Yes |
| [`milestone`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#milestone) | Yes | Yes | Yes | No |
| [`org_block`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#org_block) | No | Yes | Yes | Yes |
| [`organization`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#organization) | No | Yes | Yes | Yes |
| [`package`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#package) | Yes | Yes | No | No |
| [`page_build`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#page_build) | Yes | Yes | Yes | No |
| [`personal_access_token_request`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#personal_access_token_request) | No | Yes | Yes | No |
| [`ping`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#ping) | Yes | Yes | Yes | Yes |
| [`project`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#project) | Yes | Yes | Yes | No |
| [`project_card`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#project_card) | Yes | Yes | Yes | No |
| [`project_column`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#project_column) | Yes | Yes | Yes | No |
| [`projects_v2`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#projects_v2) | No | Yes | No | No |
| [`projects_v2_item`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#projects_v2_item) | No | Yes | No | No |
| [`projects_v2_status_update`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#projects_v2_status_update) | No | Yes | No | No |
| [`public`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#public) | Yes | Yes | Yes | No |
| [`pull_request`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#pull_request) | Yes | Yes | Yes | No |
| [`pull_request_review`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#pull_request_review) | Yes | Yes | Yes | No |
| [`pull_request_review_comment`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#pull_request_review_comment) | Yes | Yes | Yes | No |
| [`pull_request_review_thread`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#pull_request_review_thread) | Yes | Yes | Yes | No |
| [`push`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#push) | Yes | Yes | Yes | No |
| [`registry_package`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#registry_package) | Yes | Yes | Yes | No |
| [`release`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#release) | Yes | Yes | Yes | No |
| [`repository`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#repository) | Yes | Yes | Yes | Yes |
| [`repository_advisory`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#repository_advisory) | Yes | Yes | Yes | No |
| [`repository_dispatch`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#repository_dispatch) | No | No | Yes | No |
| [`repository_import`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#repository_import) | Yes | Yes | No | No |
| [`repository_ruleset`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#repository_ruleset) | Yes | Yes | Yes | No |
| [`repository_vulnerability_alert`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#repository_vulnerability_alert) | Yes | Yes | No | No |
| [`secret_scanning_alert`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#secret_scanning_alert) | Yes | Yes | Yes | No |
| [`secret_scanning_alert_location`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#secret_scanning_alert_location) | Yes | Yes | Yes | No |
| [`secret_scanning_scan`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#secret_scanning_scan) | Yes | Yes | Yes | No |
| [`security_advisory`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#security_advisory) | No | No | Yes | No |
| [`security_and_analysis`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#security_and_analysis) | Yes | Yes | Yes | No |
| [`sponsorship`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#sponsorship) | No | No | No | No |
| [`star`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#star) | Yes | Yes | Yes | No |
| [`status`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#status) | Yes | Yes | Yes | No |
| [`sub_issues`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#sub_issues) | Yes | Yes | Yes | No |
| [`team`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#team) | No | Yes | Yes | Yes |
| [`team_add`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#team_add) | Yes | Yes | Yes | No |
| [`watch`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#watch) | Yes | Yes | Yes | No |
| [`workflow_dispatch`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#workflow_dispatch) | No | No | Yes | No |
| [`workflow_job`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#workflow_job) | Yes | Yes | Yes | Yes |
| [`workflow_run`](https://docs.github.com/en/webhooks/webhook-events-and-payloads#workflow_run) | Yes | Yes | Yes | Yes |

> **Note:** GitHub labels enterprise webhook availability as `business` in the source documentation. The `marketplace_purchase` event is available only to GitHub Marketplace webhooks, and `sponsorship` is available only to sponsored-account webhooks, so both show "No" in the four requested webhook columns.

## Minimal setup without duplicate events

To capture the union of all events available to repository, organization, GitHub App, and enterprise webhooks, configure **two webhook registrations**. Both registrations can deliver to the same receiver URL, but the receiver should distinguish their deliveries by webhook ID or installation target.

| Webhook registration | Where to configure it | Events assigned | Purpose |
|---|---|---:|---|
| GitHub App webhook | In the GitHub App settings | 70 | Captures every event in the requested union that supports GitHub App webhooks. |
| Organization webhook | In each organization that must be monitored | 6 | Captures the events that support organization webhooks but not GitHub App webhooks. |

Repository and enterprise webhook registrations are not required for event-type coverage. Every event they support is already assigned to one of the two registrations above. This minimizes webhook types and prevents the same event type from being delivered through multiple registrations.

### GitHub App webhook subscriptions

Subscribe the GitHub App webhook to these 70 events:

| Event | Event | Event |
|---|---|---|
| `branch_protection_configuration` | `branch_protection_rule` | `check_run` |
| `check_suite` | `code_scanning_alert` | `commit_comment` |
| `create` | `custom_property` | `custom_property_values` |
| `delete` | `dependabot_alert` | `deploy_key` |
| `dismissal_request_code_scanning` | `dismissal_request_dependabot` | `dismissal_request_secret_scanning` |
| `deployment` | `deployment_protection_rule` | `deployment_review` |
| `deployment_status` | `discussion` | `discussion_comment` |
| `fork` | `github_app_authorization` | `gollum` |
| `installation` | `installation_repositories` | `installation_target` |
| `issue_comment` | `issue_dependencies` | `issues` |
| `label` | `member` | `membership` |
| `merge_group` | `meta` | `milestone` |
| `org_block` | `organization` | `page_build` |
| `personal_access_token_request` | `ping` | `project` |
| `project_card` | `project_column` | `public` |
| `pull_request` | `pull_request_review` | `pull_request_review_comment` |
| `pull_request_review_thread` | `push` | `registry_package` |
| `release` | `repository` | `repository_advisory` |
| `repository_dispatch` | `repository_ruleset` | `secret_scanning_alert` |
| `secret_scanning_alert_location` | `secret_scanning_scan` | `security_advisory` |
| `security_and_analysis` | `star` | `status` |
| `sub_issues` | `team` | `team_add` |
| `watch` | `workflow_dispatch` | `workflow_job` |
| `workflow_run` |  |  |

The GitHub App must be granted the permissions below and installed on every organization whose activity it should receive. Within each installation, grant access to all repositories that must be monitored; selecting only specific repositories limits repository-scoped deliveries to that selection.

#### Required GitHub App permissions

The following is the minimum permission set for receiving all actions of the GitHub App events assigned above. The event-to-permission requirements come from the permission statement in each event's linked GitHub documentation.

##### Repository permissions

| GitHub App repository permission | Required access | Events enabled |
|---|---|---|
| Actions | Read | `workflow_job`, `workflow_run` |
| Administration | Read | `branch_protection_configuration`, `branch_protection_rule`, repository-scoped `repository_ruleset`, `security_and_analysis` |
| Checks | **Write** | `check_run`, `check_suite` |
| Code scanning alerts | Read | `code_scanning_alert`, `dismissal_request_code_scanning` |
| Commit statuses | Read | `status` |
| Contents | Read | `commit_comment`, `create`, `delete`, `fork`, `gollum`, `push`, `release`, `repository_dispatch`, `workflow_dispatch` |
| Dependabot alerts | Read | `dependabot_alert`, `dismissal_request_dependabot` |
| Deployments | Read | `deploy_key`, `deployment`, `deployment_protection_rule`, `deployment_review`, `deployment_status` |
| Discussions | Read | `discussion`, `discussion_comment` |
| Issues | Read | `issue_comment`, `issue_dependencies`, `issues`, `sub_issues`; also satisfies `milestone` |
| Merge queues | Read | `merge_group` |
| Metadata | Read | `label`, `public`, `repository`, `star`, `watch` |
| Packages | Read | `registry_package` |
| Pages | Read | `page_build` |
| Projects | Read | Repository-scoped `project`, `project_card`, `project_column` |
| Pull requests | Read | `pull_request`, `pull_request_review`, `pull_request_review_comment`, `pull_request_review_thread`; can alternatively satisfy `milestone` |
| Repository security advisories | Read | `repository_advisory` |
| Secret scanning alerts | Read | `secret_scanning_alert`, `secret_scanning_alert_location`, `secret_scanning_scan`, `dismissal_request_secret_scanning` |

**Why Checks requires write access:** read access is sufficient to subscribe to `check_run` and `check_suite`, but it does not provide every documented action. GitHub requires **Checks: write** for the `check_run` actions `rerequested` and `requested_action`, and for the `check_suite` actions `requested` and `rerequested`. If those actions are not needed, reduce Checks to read access. Granting write access also gives the app authority to modify check runs and suites, so its private key and installation tokens must be protected accordingly.

The Metadata repository permission is read-only and is automatically included with every GitHub App installation. It is listed explicitly because the associated webhook documentation names it as the prerequisite.

The three dismissal-request events use the read permission for their underlying alert type; there is no separate GitHub App permission named "dismissal requests." These events report request lifecycle activity such as creation, cancellation, completion, or a submitted response, depending on the alert type. Modifying or responding to a request through the REST API may require write access and delegated alert dismissal to be enabled. Delegated alert dismissal for secret scanning is currently in public preview.

##### Organization permissions

| GitHub App organization permission | Required access | Events enabled |
|---|---|---|
| Administration | Read | `org_block`, organization-scoped `repository_ruleset` |
| Custom properties | Read | `custom_property`, `custom_property_values` |
| Members | Read | `member`, `membership`, `organization`, `team`, `team_add` |
| Personal access token requests | Read | `personal_access_token_request` |
| Projects | Read | Organization-scoped `project`, `project_card`, `project_column` |

Both repository and organization versions of **Administration** and **Projects** are required if the collector must capture those events at both scopes. The `milestone` event accepts either Issues: read or Pull requests: read; this setup already needs both permissions for other events.

##### App-level and permission-independent events

| Event | Permission behavior |
|---|---|
| `meta` | Requires the **Meta: read** app permission. This is an app-level permission rather than a repository or organization permission. |
| `github_app_authorization` | Every GitHub App receives this event by default and cannot unsubscribe. No repository or organization permission enables it. |
| `installation` | Every GitHub App receives this event by default and cannot manually subscribe to it. |
| `installation_repositories` | Every GitHub App receives this event by default and cannot manually subscribe to it. |
| `installation_target` | GitHub documents this as an app-only event and does not specify an additional repository or organization permission prerequisite. |
| `security_advisory` | GitHub documents this global advisory event as app-only and does not specify an additional repository or organization permission prerequisite. |
| `ping` | Sent when a webhook is created to confirm its configuration; it has no selectable permission prerequisite. |

Permission configuration controls whether the event can be selected and delivered, but it does not expand the installation's scope. A GitHub App installed on selected repositories will not receive repository events from unselected repositories. For enterprise-wide organization and repository coverage, install the app on every organization and grant each installation access to all repositories. GitHub currently states that an app installed on an enterprise cannot receive webhooks and must instead be installed on each organization.

When permissions or subscribed events are added after installation, organization owners may need to approve the updated installation permissions before deliveries that depend on them begin.

### Organization webhook subscriptions

Subscribe the organization webhook only to these six events:

| Event |
|---|
| `package` |
| `projects_v2` |
| `projects_v2_item` |
| `projects_v2_status_update` |
| `repository_import` |
| `repository_vulnerability_alert` |

An organization webhook applies to only one organization. Create this registration in each organization that must be monitored. Do not also subscribe repository or enterprise webhooks to these assigned events if the goal is to avoid event-type duplication.

### Events outside this setup

`marketplace_purchase` and `sponsorship` are not available to any of the four requested webhook types. Capturing them would require a GitHub Marketplace webhook and a sponsored-account webhook, respectively.

This plan avoids duplicate **event types** across registrations. GitHub may still send multiple deliveries for distinct actions or resources of the same event type; use the `X-GitHub-Delivery` header as the unique delivery identifier when implementing delivery-level deduplication.

## Additional enterprise data collection

The webhook setup above should be supplemented with audit log streaming and scheduled API collection for data that is not represented completely by webhook events. The recommendations below use UTC dates and assume that collected records are stored with their source, account scope, collection time, and natural identifiers.

| Data source | Collection method | Recommended frequency | Documented source window |
|---|---|---|---|
| Enterprise audit log | Continuous audit log stream | Continuous ingestion, with a daily health check | Starts when streaming is enabled; a paused stream buffers seven days |
| Billing usage APIs | Scheduled REST API requests | Daily; re-fetch the previous seven days | Summary, AI credit, and premium request endpoints expose up to 24 months |
| Copilot billing and seats APIs | Scheduled REST API snapshots | One complete snapshot daily | Current state only; no historical query window |
| Copilot usage metrics APIs | Scheduled REST API report downloads | Daily; collect finalized data beginning at `T-4` | Daily reports starting October 10, 2025, with up to one year of history |

### Audit log streaming

[Enterprise audit log streaming](https://docs.github.com/en/enterprise-cloud@latest/admin/monitoring-activity-in-your-enterprise/reviewing-audit-logs-for-your-enterprise/streaming-the-audit-log-for-your-enterprise) exports audit and Git events for all organizations in an enterprise to an external destination. It complements webhooks by recording administrative, identity, security, access, and Git activity that may not have a corresponding webhook event.

#### Available data

The stream includes:

- Enterprise and organization audit events, including changes to settings and access, organization membership, repository administration, app permissions, authentication, security controls, and policy changes. The complete taxonomy is in [Audit log events for an enterprise](https://docs.github.com/en/enterprise-cloud@latest/admin/monitoring-activity-in-your-enterprise/reviewing-audit-logs-for-your-enterprise/audit-log-events-for-your-enterprise).
- Git events across the enterprise, including operations such as clone, fetch, and push.
- Optional [Copilot agent session activity](https://docs.github.com/en/enterprise-cloud@latest/copilot/how-tos/administer-copilot/manage-for-enterprise/manage-agents/monitor-agentic-activity#tracking-agentic-activity-in-your-enterprise-through-the-audit-log), which is currently in public preview.
- Applicable event properties such as the action, actor, affected user, enterprise, organization, repository, timestamp, country, authentication method, SAML or SCIM identity, and optionally the source IP address.

The available destinations include Amazon S3, Azure Blob Storage, Azure Event Hubs, Datadog, Google Cloud Storage, Microsoft Purview for Copilot agent events, and Splunk. Object-storage destinations receive compressed JSON files using a `YYYY/MM/DD/HH/MM/<uuid>.json.log.gz` path.

#### Date window and delivery behavior

- Streaming is prospective: it exports activity from the time the stream is enabled and does not provide a historical backfill.
- GitHub uses **at-least-once delivery**, so duplicate records are possible.
- A paused stream retains a seven-day buffer. If it remains paused for more than seven days, it resumes from one week before the current time. After three weeks or more, no buffered data remains and the stream restarts at the current time.
- For comparison, the searchable [enterprise audit log](https://docs.github.com/en/enterprise-cloud@latest/admin/concepts/security-and-compliance/audit-log-for-an-enterprise) and Audit Log API retain ordinary audit events for 180 days and Git events for seven days. These query windows do not limit data already exported to your own storage.

#### Recommended collection frequency

Consume the stream continuously rather than treating it as a daily export. Run a daily stream-health and completeness check because GitHub performs a health check every 24 hours, and a broken configuration must be repaired within six days to prevent data loss.

Deduplicate using `_document_id` when it is present. Otherwise, generate a deterministic key from stable event fields such as timestamp, action, actor, organization, repository, and request or token identifiers. Partition storage by the event timestamp rather than arrival time. If an interruption occurs, use the Audit Log REST API immediately to recover the gap; Git events must be recovered within their seven-day API retention window.

### Billing APIs

The [billing usage REST APIs](https://docs.github.com/en/rest/billing/usage) expose metered product consumption and costs at user, organization, and enterprise billing scopes. Use the highest scope at which the cost is billed to avoid gaps and duplicate attribution. For example, usage billed through an enterprise should be collected from the enterprise endpoint rather than separately adding organization results.

#### Available data and endpoints

The endpoint families are:

| Report | Enterprise endpoint pattern | Data available |
|---|---|---|
| Billing usage | `GET /enterprises/{enterprise}/settings/billing/usage` | Daily summarized usage by product and SKU, including quantity, unit type, unit price, gross amount, discounts, net amount, organization, and repository where applicable |
| Billing usage summary | `GET /enterprises/{enterprise}/settings/billing/usage/summary` | Aggregated gross, discount, and net quantities and amounts, filterable by time period, product, SKU, repository, organization, and enterprise cost center where supported |
| AI credit usage | `GET /enterprises/{enterprise}/settings/billing/ai_credit/usage` | AI credit consumption and cost by product, SKU, model, user, organization, and other applicable scope dimensions |
| Premium request usage | `GET /enterprises/{enterprise}/settings/billing/premium_request/usage` | Premium request quantities and costs by product, SKU, model, user, and applicable billing scope |

Equivalent endpoints are available under `/organizations/{org}/settings/billing/...` and `/users/{username}/settings/billing/...`. User endpoints include only usage billed directly to the individual's personal account; they do not include licenses or usage billed through an organization or enterprise.

The AI credit and premium request reports include fields such as `product`, `sku`, `model`, `unitType`, `pricePerUnit`, `grossQuantity`, `discountQuantity`, `netQuantity`, `grossAmount`, `discountAmount`, and `netAmount`. These reports provide Copilot consumption cost data, but they are distinct from Copilot adoption and productivity metrics.

#### Date window

- The usage summary, AI credit usage, and premium request usage endpoints document access to the previous **24 months**.
- The APIs support calendar filters including `year`, `month`, and `day`. The usage summary defaults to the current year when no date is supplied.
- The consolidated `/usage` endpoint provides daily records and date filters, but its reference does not state a separate retention guarantee. Use the explicitly documented 24-month summary endpoints for historical recovery requirements.
- GitHub does not publish a general finalization or freshness SLA for all billing products.

#### Recommended daily collection

Run once daily after the previous UTC day has closed. Query the explicit `year`, `month`, and `day` for the target date, then re-fetch and upsert at least the previous seven calendar days because usage and billing adjustments can arrive after the initial collection and no general freshness SLA is documented.

Use a natural key containing the billing scope, date, product, SKU, organization, repository, cost center, user, and model fields that apply to the report. Replace matching rows rather than adding overlapping daily results, which would double-count usage. Retain the raw API response and periodically reconcile closed months against invoice totals.

Do not build new collectors on legacy product-specific Actions, Packages, shared-storage, or workflow-usage billing endpoints. GitHub has directed consumers to the consolidated billing usage endpoints.

### Copilot billing and seat APIs

Copilot cost consumption is available through the general billing AI credit and premium request APIs above. Copilot subscription configuration and assigned-seat state are exposed separately through the [Copilot user management REST APIs](https://docs.github.com/en/rest/copilot/copilot-user-management).

#### Available data and endpoints

| Endpoint | Data available |
|---|---|
| `GET /orgs/{org}/copilot/billing` | Current subscription plan, total seats, seats added during the current cycle, pending cancellations, pending invitations, active and inactive seats during the cycle, seat-management mode, and Copilot feature policies |
| `GET /orgs/{org}/copilot/billing/seats` | Every seat currently billed to the organization, including the assignee, assigning team, organization, assignment creation time, pending cancellation date, last Copilot activity time and editor, last authentication time, and plan type |

The seat-list endpoint is paginated, with 50 records by default and a maximum of 100 records per page. `last_activity_at` depends on IDE telemetry being enabled and may be null or incomplete even when the seat is assigned.

#### Date window

These endpoints return **current subscription and seat state**. They do not accept start or end dates and do not provide a historical seat ledger. Timestamps such as `created_at`, `pending_cancellation_date`, `last_activity_at`, and `last_authenticated_at` describe the current seat record but cannot reconstruct every prior daily assignment.

GitHub does not document a freshness SLA for these endpoints. Historical Copilot seat state must therefore be built from retained snapshots, optionally correlated with relevant audit log events for authoritative change and actor information.

#### Recommended daily collection

Take one complete paginated snapshot at a consistent UTC time every day:

1. Retrieve the organization billing summary.
2. Retrieve every page of seat assignments using `per_page=100`.
3. Publish the snapshot only after all pages have been retrieved successfully.
4. Store a collector-generated `snapshot_at` timestamp with every record.
5. Retain snapshots rather than overwriting the previous day so assignments, removals, inactivity, and pending cancellations can be analyzed historically.

Use organization ID and assignee ID as the seat identity. A second same-day snapshot may be appropriate when seat assignment changes drive financial or access-control alerts.

### Copilot usage APIs

The [Copilot usage metrics REST APIs](https://docs.github.com/en/rest/copilot/copilot-usage-metrics) provide adoption, engagement, code-generation, agent, CLI, and pull-request metrics. These APIs are separate from Copilot billing: `ai_credits_used` and usage counters are useful for consumption analysis but should not replace billing API amounts for invoice reconciliation.

The enterprise **Copilot usage metrics** policy must be set to **Enabled everywhere** before these reports can be retrieved.

#### Available reports

Reports are available at enterprise and organization scope:

| Report type | Example enterprise endpoint | Data available |
|---|---|---|
| Daily aggregate | `GET /enterprises/{enterprise}/copilot/metrics/reports/enterprise-1-day?day=YYYY-MM-DD` | One day of aggregate active-user, interaction, code-generation, feature, language, model, agent, CLI, adoption, and pull-request metrics |
| Latest 28-day aggregate | `GET /enterprises/{enterprise}/copilot/metrics/reports/enterprise-28-day/latest` | Daily aggregate records covering the latest fully processed 28-day period |
| Daily per-user | `GET /enterprises/{enterprise}/copilot/metrics/reports/users-1-day?day=YYYY-MM-DD` | Per-user engagement, feature indicators, adoption phase, models, languages, code activity, and `ai_credits_used` |
| Latest 28-day per-user | `GET /enterprises/{enterprise}/copilot/metrics/reports/users-28-day/latest` | Per-user metrics for the latest fully processed 28-day period |
| Daily repository | `GET /enterprises/{enterprise}/copilot/metrics/reports/repos-1-day?day=YYYY-MM-DD` | Repository-level pull-request activity, including Copilot coding agent and Copilot code review activity, for repositories active that day |
| Daily user-team mapping | `GET /enterprises/{enterprise}/copilot/metrics/reports/user-teams-1-day?day=YYYY-MM-DD` | User-to-team mappings that can be joined to per-user metrics to calculate team-level totals |

Equivalent organization report endpoints use `/orgs/{org}/copilot/metrics/reports/...`. Team totals are not supplied as pre-aggregated records; they must be produced by joining the daily user-team report to the daily per-user report.

The detailed field catalog is documented in [Data available in Copilot usage metrics](https://docs.github.com/en/copilot/reference/copilot-usage-metrics/copilot-usage-metrics). It includes:

- Daily, weekly, and trailing-28-day active users.
- User interactions, generated responses, code suggestions, accepted suggestions, acceptance rates, and lines added or deleted.
- Breakdowns by IDE, feature, language, model, and adoption phase.
- Copilot agent, chat, CLI, Copilot coding agent, Copilot code review, and recognized third-party agent activity.
- Pull requests created, reviewed, merged, and time-to-merge measures.
- Per-user AI credits used and feature-use indicators.

IDE-based details depend on user IDE telemetry. Users detected through server-side telemetry may appear in active-user totals while their IDE, feature, language, model, and lines-of-code breakdowns remain empty.

#### Date window and freshness

- Daily reports are available beginning **October 10, 2025**.
- Historical daily data can be requested for up to **one year** from the current date.
- The latest endpoints return the latest fully processed **28-day** period.
- Reports are generated daily and returned as short-lived signed download URLs. Download and archive the NDJSON files immediately instead of retaining only the URLs.
- According to [GitHub's reconciliation guidance](https://docs.github.com/en/copilot/reference/copilot-usage-metrics/reconciling-usage-metrics), recent telemetry typically finalizes within **three full UTC days**. A report downloaded earlier may be incomplete.

#### Recommended daily collection

For a collector running on UTC date `T`:

1. Collect all daily report types for `T-4`, the first date safely beyond the documented three-full-day processing interval.
2. Re-fetch `T-4` through `T-10` on every run and replace or upsert existing records to incorporate late telemetry.
3. Optionally collect `T-1` through `T-3` into a provisional partition, but do not treat these dates as final.
4. Download every returned report file immediately because the signed links expire.
5. Archive the original NDJSON and store its report date, scope, retrieval time, and report type.

Use report-specific upsert keys:

- Aggregate report: scope ID and day.
- Per-user report: scope ID, user ID, and day.
- Repository report: scope ID, repository ID, and day.
- User-team report: scope ID, user ID, team ID, and day.

The daily reports should be the system of record for historical analytics. The rolling 28-day reports are best used as reconciliation checks rather than appended datasets, because consecutive reports contain heavily overlapping dates.
