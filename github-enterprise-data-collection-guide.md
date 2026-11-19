# GitHub enterprise data collection guide

Source: [GitHub webhook events and payloads](https://docs.github.com/en/webhooks/webhook-events-and-payloads) (accessed September 11, 2026).

The event matrix and minimal-registration recipe are a dated baseline. Apply
the [September-November changelog additions and follow-up plans](#changelog-coverage-review-september-18-november-18-2026)
below before using them as a current subscription inventory.

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

### Implemented AWS Copilot bronze collector

The SAM application implements the daily enterprise-scope billing and usage
pattern with GitHub App installation authentication:

- EventBridge Scheduler invokes one coordinator at 08:30 UTC. It emits two
	billing report types for `T-1` through `T-7` and four usage report types for
	`T-4` through `T-10`, for 42 tasks per normal run.
- The App must be installed on the enterprise with read access to
	**Enterprise billing** and **Enterprise Copilot metrics**. GitHub's endpoint
	permission inventory explicitly supports installation access tokens for
	these routes. The enterprise Copilot usage metrics policy must also be
	enabled everywhere.
- Secrets Manager holds only `app_id`, `installation_id`, and `private_key`.
	The worker creates a short-lived App JWT and exchanges it for an installation
	token on each SQS invocation. Neither credential is stored in S3 or logs.
- Billing responses are archived exactly as JSON. Usage report links are
	downloaded immediately; only a sanitized manifest and the source NDJSON are
	archived, never the signed URLs.
- Raw objects use
	`raw/copilot/<source>/report_type=<type>/report_day=<date>/collection_date=<date>/`.
	Stable NDJSON envelopes use
	`bronze/copilot/<source>/year=<YYYY>/month=<MM>/day=<DD>/report_type=<type>/`.
- Deterministic object names make SQS retries idempotent within one collection
	date. Reconciled snapshots from later collection dates remain available so
	late billing adjustments and finalized usage can be compared.
- Glue partition projection exposes `billing_usage` and `usage_reports` in
	`github_copilot_bronze_<environment>` without crawlers or partition repair.

The implemented Glue 5.0 silver job selects the latest collection in each input
batch and conditionally merges by the report-specific keys above. It creates
typed daily billing, enterprise, user, repository, and user-team Iceberg tables
in `github_copilot_silver_<environment>`. Collection date and time remain on
every row so a replay from an older bronze snapshot cannot replace newer data.

Stable identities, scalar counters, billing decimals, adoption fields, CLI and
Copilot App counters, and pull-request metrics are promoted. Evolving nested
breakdowns by feature, IDE, language, model, third-party agent, comment type,
and aggregate adoption phase remain JSON strings with the complete source
payload. Records missing a required report date or natural-key identity are
written to `quarantined_records` with S3 lineage instead of being discarded.

The daily 10:30 UTC schedule follows the 08:30 UTC collector. Calendar
backfills accept up to 366 days per run only with Glue bookmarks disabled. The
user-team table can legitimately be empty because GitHub excludes teams with
fewer than five seated Copilot users from that report.

## Changelog coverage review: September 18-November 18, 2026

The local review retrieved and screened **210 unique announcements across 22 RSS
pages**, including full article content, published in
`[2026-09-18T00:00:00Z, 2026-11-19T02:55:34.913405Z)`. The end is the captured
review start time (November 18 in Pacific time), not a claim about later posts.
The boundary page reached September 16. Repository issues and pull requests
were checked for existing proposals; none existed at review time.

This is the local equivalent of the weekly workflow's draft change set and
consolidated follow-up issue. It does not enable sources, deploy resources,
backfill historical data, or prove that every GitHub dataset is covered.
The implementation deliberately extends existing ingestion paths; the new
collectors below are explicit follow-up work, not implemented functionality.

### Implemented and already-supported changes

| Announcement | Disposition and implementation |
| --- | --- |
| [September 18: dedicated VS Code Agents-window usage metrics](https://github.blog/changelog/2026-09-18-github-copilot-weekly-releases-september-14) | Existing daily raw/bronze collection already includes these fields. Silver now exposes daily/weekly/monthly active users, session and message totals, and the per-user indicator, independently of IDE agent mode. |
| [September 25: human PR review stages](https://github.blog/changelog/2026-09-25-usage-metrics-api-adds-pull-request-review-stages) | Silver now preserves the complete repository `pull_request_review_times` array as JSON, including author/reviewer cohorts and median/p90 durations. Data starts prospectively; PRs ready before September 21 are excluded upstream. Empty arrays are not zero-minute durations. |
| [September 25: issue relationships](https://github.blog/changelog/2026-09-25-personal-saved-views-for-repository-issues-and-more) | `issue_relates_to` now joins the webhook `issues` silver family. Add this event to the GitHub App or organization webhook subscription; Issues: read suffices for Apps. It is unavailable to enterprise webhooks. Cross-repository deliveries intentionally omit the related issue's identity. This adds one event to the older 70-event App recipe above. |
| [November 11: personal-account issue types and fields](https://github.blog/changelog/2026-11-11-issue-types-and-fields-are-available-for-personal-accounts) | Issue types were already typed. Silver now also preserves issue field definitions, values, and previous-value changes as JSON, including multi-select and zero/false values. Repository/App webhooks must cover personal repositories; organization installations alone do not. |
| [October 20: Dependabot dependency versions](https://github.blog/changelog/2026-10-20-dependabot-alerts-rest-api-now-includes-dependency-versions) | Silver now promotes `alert.dependency.version_requirement` as `dependency_version_requirement`. It is not necessarily an installed version or the advisory's vulnerable range. |
| [October 13: withdrawn Dependabot alerts](https://github.blog/changelog/2026-10-13-improved-detection-for-withdrawn-dependabot-alerts) | Already accepted without action/state allowlists. Regression coverage now includes a sparse `withdrawn` delivery; absent state/version fields remain null. A future alert poller must distinguish HTTP 410 from 404. |
| [November 5/6: telemetry and version gaps](https://github.blog/changelog/2026-11-05-usage-metrics-api-flags-telemetry-and-version-gaps) | Silver now promotes aggregate missing-telemetry/below-minimum counts, nullable per-user telemetry presence, and complete version assessments as JSON. Counts can overlap and are not additive across days. |
| [November 5/6: code review outcomes](https://github.blog/changelog/2026-11-05-usage-metrics-api-adds-code-review-details-and-addressed-rate) and [November 17: Repository insights](https://github.blog/changelog/2026-11-17-track-copilot-code-review-outcomes-in-repository-insights) | Silver now preserves the complete repository `copilot_code_review` object and typed evaluated/addressed counts and merged-without-later-human-change-request totals. Counts belong to the merge day. Queries use summed numerators/denominators with zero-denominator protection. |
| [October 22: named customizations](https://github.blog/changelog/2026-10-22-custom-skills-agents-and-mcp-servers-in-usage-metrics-api) and [October 23: server-counted clients](https://github.blog/changelog/2026-10-23-usage-metrics-api-adds-usage-from-tools-like-opencode) | Already implemented in Copilot silver with complete JSON breakdowns, user distinct-use counters, migration, replay, and query examples. No duplicate implementation. |
| [October 13: Code Quality audit events](https://github.blog/changelog/2026-10-13-audit-github-code-quality-finding-dismissals-and-reopenings), [October 16: license compliance](https://github.blog/changelog/2026-10-16-open-source-license-compliance-generally-available), and [November 17: code review administration audit events](https://github.blog/changelog/2026-11-17-copilot-code-review-adaptive-effort-secret-detection-and-more) | The normalizer has no action allowlist and retains full raw payloads, so newly streamed actions are already collected when the corresponding product emits them. Product enablement remains an administrator decision. |
| [October 20: secret scanning audit enterprise names](https://github.blog/changelog/2026-10-20-updates-to-github-secret-scanning) | The normalizer preserves `business` verbatim and types `business_id`. After November 12, affected events use the enterprise slug rather than display name. Join/filter on the stable numeric ID; do not assume one string format across history. Dismissal-request payload additions remain in raw webhook data. |
| [October 6: stacked PRs](https://github.blog/changelog/2026-10-06-stacked-pull-requests-generally-available) | Existing `pull_request` ingestion accepts the new `stacked` action and retains full payloads. No action enumeration needs changing. |
| [October 2: stateless installation tokens](https://github.blog/changelog/2026-10-02-stateless-github-app-installation-tokens-rolled-out) | The App collector already treats tokens as opaque strings with no fixed-length validation and does not send the retiring experimental header. No credential migration is required here. |
| [October 29: webhook IP ranges](https://github.blog/changelog/2026-10-29-webhook-ip-ranges-added-to-the-meta-api) | No static GitHub source-IP allowlist is configured in this stack. If an external firewall is used, synchronize its webhook ranges from the Meta API instead of copying a fixed list. |
| [October 6: missing IDE telemetry](https://github.blog/changelog/2026-10-06-update-your-ide-to-restore-agent-activity-in-copilot-usage-metrics) | An upstream coverage limitation, not a recoverable collector outage. Upgrade supported IDEs/extensions; historical missing agent activity and misattributed CLI usage cannot be reconstructed by replay. |

Both silver jobs now evolve existing Iceberg tables additively before processing
data. They retain unknown columns, current natural keys, source-faithful raw
payloads, and replay semantics. No API credentials, collection schedules,
permissions, or privacy boundaries change. Deploy the scripts normally, then
replay retained bronze dates with bookmarks disabled to populate new columns.
SQL null, false/zero, and empty arrays remain distinguishable.

### Deferred collection work and acceptance criteria

These are real gaps, not promises that the stack already ingests the data.
Implement them as separately reviewable, disabled-by-default sources with scoped
credentials, raw retention, stable bronze envelopes, projected catalogs, complete
snapshot publication, observability, and tested pagination/replay. Do not silently
extend the current collectors' credential scopes.

| Source and evidence | Required follow-up and acceptance criteria |
| --- | --- |
| [September 21: enterprise credential inventory](https://github.blog/changelog/2026-09-21-github-enterprise-adds-credential-inventory-exports) | Add an opt-in asynchronous CSV snapshot collector using [credential export endpoints](https://docs.github.com/en/enterprise-cloud@latest/rest/enterprise-admin/token-inventory): POST `/enterprises/{enterprise}/credentials/exports`, then poll GET `/enterprises/{enterprise}/credentials/exports/{export_id}`. Do not build on the retired synchronous inventory routes. Requires an enterprise owner or View enterprise credentials role and a documented compatible credential. Bound polling/export quotas; download immediately without forwarding authorization across hosts or persisting signed URLs. Retain `as_of`, original CSV and a completion manifest; test RFC 4180 quoting, blank-versus-false semantics, one row per credential/authorizing organization, and identifier collisions across credential types. Restrict metadata, fingerprints, and token hashes to security administrators. No secret token values should be collected. |
| [October 23: public monitoring API and enterprise webhook](https://github.blog/changelog/2026-10-23-public-monitoring-adds-triage-validity-api-and-webhooks), [October 28: general availability](https://github.blog/changelog/2026-10-28-public-monitoring-for-enterprises-generally-available), [November 12: alert links](https://github.blog/changelog/2026-11-12-public-monitoring-alerts-now-have-direct-links) | Configure an additional enterprise webhook for `secret_scanning_public_monitoring_alert`; the older App-plus-organization recipe cannot cover this event. Generic webhook bronze/core raw retention can accept deliveries, but typed family promotion is not implemented. Add an opt-in paginated REST baseline/reconciler at `/enterprises/{enterprise}/secret-scanning/public-monitoring-alerts`, after confirming its [current payload and permission contract](https://docs.github.com/en/enterprise-cloud@latest/code-security/concepts/secret-security/public-monitoring). Requires eligible licensing and enterprise security administration. Test enterprise-wide identities without assuming the leaked repository belongs to the enterprise; keep exposed-secret content and locations restricted, never in broad dashboards. Verified-domain attribution differs from membership attribution for data-resident enterprises. |
| [November 17: Event Streams preview](https://github.blog/changelog/2026-11-17-github-event-streams-is-now-in-preview) | Requires waitlist approval. Evaluate documented event coverage, resume/replay, retention, duplicates, disconnections, and enterprise scope before choosing it as an additional source. Do not replace durable webhook/audit ingestion with an assumed equivalent preview stream. |
| [September 22/23: client OpenTelemetry](https://github.blog/changelog/2026-09-22-opentelemetry-in-the-github-copilot-app), [October 12: capture classes](https://github.blog/changelog/2026-10-12-client-telemetry-user-attribution-and-configurable-capture), [November 17: Agent 365](https://github.blog/changelog/2026-11-17-monitor-github-copilot-activity-through-microsoft-agent-365) | Design an approved authenticated OTLP receiver and buffering/storage path; managed client settings alone cannot send OTLP into this stack's webhook endpoint. Keep identity, prompts, responses, tool arguments/output, and policy details independently opt-in and off by default. Test schema/version compatibility, redaction, tenant isolation, payload limits, and duplicate/replay behavior. Existing audit streaming captures only the events GitHub actually sends, not all client OTel spans. |
| [November 6: 28-day feature engagement](https://github.blog/changelog/2026-11-06-copilot-impact-dashboard-adds-chat-and-vs-code-agent-usage) | Add a separate latest-28-day report snapshot task/table for `copilot_feature_engagement`. The current daily collector does not retrieve the wrapper-only object. Preserve actual report start/end days and retrieval time, reconcile overlapping windows, and never append each window's daily totals into additive daily usage. Chat-first users still map to `No Cohort`; do not reinterpret existing adoption phases. |
| [November 3: resource cost-center membership](https://github.blog/changelog/2026-11-03-look-up-a-resources-cost-center-with-the-github-rest-api), [November 10/11: enterprise App seat management](https://github.blog/changelog/2026-11-10-github-app-support-for-enterprise-copilot-seat-management), [October 28: included Copilot access](https://github.blog/changelog/2026-10-28-github-enterprise-now-includes-access-to-github-copilot) | Add current-state cost-center membership and enterprise/organization Copilot seat/subscription snapshots with explicit billing/seat-read authorization and an enumerated resource universe. Existing billing rows and consumed-license snapshots do not replace these datasets. Preserve empty membership versus request failure; publish only complete paginated snapshots and do not invent historical assignments. Enterprise App license management is a different permission from the existing Copilot metrics permission. |
| [October 19: model policies](https://github.blog/changelog/2026-10-19-copilot-model-policy-api-for-enterprise-orgs-and-teams), [November 6/7: review configuration and attribution](https://github.blog/changelog/2026-11-06-copilot-code-review-api-management-and-review-overview-updates), [October 23: App governance coverage](https://github.blog/changelog/2026-10-23-enterprise-installations-for-github-apps-generally-available) | Add read-only policy/configuration snapshots for enterprise, organization, team, App, and repository scopes where documented, retaining inherited/effective policy distinctions. Add review/comment metadata enrichment only with verified response schemas. Enterprise/organization code-review settings do not support Apps or fine-grained PATs as of the announcement; do not silently reuse the current App or administrator token. Test scope-specific authorization failures without emitting success-shaped empty snapshots. |
| [September 18: code coverage rules](https://github.blog/changelog/2026-09-18-manage-the-code-coverage-ruleset-condition-with-the-rest-api), [September 29: external custom properties](https://github.blog/changelog/2026-09-29-bring-business-context-with-external-custom-properties), [October 12: commit push attribution](https://github.blog/changelog/2026-10-12-push-attribution-public-preview), [October 16: license-policy APIs](https://github.blog/changelog/2026-10-16-open-source-license-compliance-generally-available) | Add read-only ruleset/custom-property/license-policy inventory snapshots and, after preview approval, authenticated per-commit pusher enrichment. Existing change webhooks are not complete baselines. Preserve external namespaces, effective dates, and policy inheritance; never treat author/committer strings or webhook `pusher.name` as the new authenticated per-commit identity. Do not use mutating policy/compliance-check endpoints as inventory reads. |
| [October 2: advisory GraphQL fields](https://github.blog/changelog/2026-10-02-new-fields-for-securityadvisory-graphql-api), [October 2: advisory comments API](https://github.blog/changelog/2026-10-02-repository-security-advisory-comments-api-in-public-preview) | Add paginated advisory snapshots and incremental comment collection with updated-since watermarks, authorized repository coverage, and restricted raw access. Include newly available CVE/source/review/NVD/repository-link fields. The comments API cannot retrieve confidential comments; do not claim complete private advisory discussions or scrape restricted UI content. |
| [October 28: Dependabot reachability](https://github.blog/changelog/2026-10-28-prioritize-dependabot-alerts-with-reachability-analysis), [November 10: inactive repository pauses](https://github.blog/changelog/2026-11-10-dependabot-alerts-will-pause-on-inactive-repositories) | Add an opt-in REST alert snapshot/reconciliation source; new reachability values can change without an alert lifecycle transition, so webhook-only capture is not sufficient. Preserve verdict/reason and source time; distinguish unavailable/disabled/potentially reachable from unreachable, and never auto-dismiss on that basis. Test pagination, preview/language coverage and 410 withdrawal behavior. A quiet or paused repository is not evidence that no vulnerabilities exist. |
| [September 24: expired artifacts](https://github.blog/changelog/2026-09-24-expired-github-actions-artifacts-no-longer-shown-in-ui-and-api), [September 25: bounded Actions queries](https://github.blog/changelog/2026-09-25-changes-to-query-results-in-the-github-actions-api-and-ui), [October 1: expanded retention](https://github.blog/changelog/2026-10-01-actions-retention-now-covers-checks-runs-and-statuses) | Add bounded-window polling for check/status/run metadata, artifacts, and logs if their full contents/history are required. The stack currently retains delivered webhook payloads, not artifact/log bytes or every REST resource. Partition queries by time to stay below result caps, follow pagination independently of reported counts, archive before expiry, and report irrecoverable gaps. Account for S3 costs and sensitive log content. |
| [October 15: Code Quality license CSV](https://github.blog/changelog/2026-10-15-download-github-code-quality-license-usage-as-a-csv), [October 13: AI Scan overview metrics](https://github.blog/changelog/2026-10-13-code-scanning-ai-scan-metrics-in-security-overview), [November 13: AI Scan settings API](https://github.blog/changelog/2026-11-13-manage-ai-scan-for-repositories-using-the-rest-api), [November 18: automatic risk assessments](https://github.blog/changelog/2026-11-18-security-risk-assessments-run-automatically-on-github-team) | Add administrator-supplied CSV ingestion for documented UI-only exports, preserving source effective dates and access restrictions. Add read-only AI Scan settings snapshots through the documented organization/repository GET routes. UI dashboard aggregates/risk assessments are not automatically API datasets; verify an export/read contract before adding a collector. Do not enable scans or consume AI credits to collect configuration. |
| [October 28: issue artifacts](https://github.blog/changelog/2026-10-28-issue-artifacts-are-now-in-public-preview) and [November 11: issue fields](https://github.blog/changelog/2026-11-11-issue-types-and-fields-are-available-for-personal-accounts) | Add permission-aware issue/type/field/artifact baselines and artifact content retrieval where documented; webhook deltas are not complete current state or attachment contents. Preserve private artifact visibility, content types, source versions, and updates/deletions without granting extra access. Test personal as well as organization repositories. |
| [September 28: runner version deprecations](https://github.blog/changelog/2026-09-28-self-hosted-runner-version-enforcement-date-has-moved) | An optional runner-inventory/deprecation dataset needs its own scheduled API polling and administration-read scope. Existing workflow-job events do not enumerate idle/offline runners or their deprecation deadlines. Test source validity dates and never infer fleet completeness from observed jobs. |

New model releases/deprecations and additional secret detectors do not require
hard-coded model or secret-type lists: existing raw payloads and JSON breakdowns
retain new values. UI/editor improvements and write-only administration changes
without a new readable dataset do not justify a collector. Dashboard-only
[industry comparisons](https://github.blog/changelog/2026-10-22-industry-comparisons-in-the-copilot-impact-dashboard)
are explicitly absent from API/NDJSON exports; do not fabricate them.

The [current Copilot field reference](https://docs.github.com/en/copilot/reference/copilot-usage-metrics/copilot-usage-metrics)
and [webhook reference](https://docs.github.com/en/webhooks/webhook-events-and-payloads)
were used to verify extraction paths and missing/null semantics. Tests cover new
field extraction and additive upgrades; optional Spark/Iceberg checks cover
missing/null/empty/populated payloads, repeated and stale replay, cross-repository
issue privacy, issue field changes, and sparse withdrawn alerts. See the README
for local validation and replay commands.
