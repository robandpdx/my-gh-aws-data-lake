import argparse
import re
import sys
import uuid
from datetime import date, timedelta
from urllib.parse import urlparse


PAYLOAD_VERSION = 1
CATALOG_NAME = "glue_catalog"
BRONZE_TRANSFORMATION_CONTEXT = "webhook_bronze_source"

EVENT_FAMILY_BY_TYPE = {
    "check_run": "actions",
    "check_suite": "actions",
    "workflow_dispatch": "actions",
    "workflow_job": "actions",
    "workflow_run": "actions",
    "pull_request": "pull_requests",
    "pull_request_review": "pull_requests",
    "pull_request_review_comment": "pull_requests",
    "issues": "issues",
    "issue_comment": "issues",
    "code_scanning_alert": "security_alerts",
    "dependabot_alert": "security_alerts",
    "secret_scanning_alert": "security_alerts",
    "member": "organization_activity",
    "membership": "organization_activity",
    "organization": "organization_activity",
    "organization_block": "organization_activity",
    "repository": "organization_activity",
    "repository_import": "organization_activity",
    "team": "organization_activity",
    "team_add": "organization_activity",
}

EVENT_TIMESTAMP_PATHS = {
    "check_run": (
        "$.check_run.completed_at",
        "$.check_run.started_at",
    ),
    "check_suite": (
        "$.check_suite.updated_at",
        "$.check_suite.created_at",
    ),
    "workflow_job": (
        "$.workflow_job.completed_at",
        "$.workflow_job.started_at",
        "$.workflow_job.created_at",
    ),
    "workflow_run": (
        "$.workflow_run.updated_at",
        "$.workflow_run.run_started_at",
        "$.workflow_run.created_at",
    ),
    "pull_request": (
        "$.pull_request.updated_at",
        "$.pull_request.created_at",
    ),
    "pull_request_review": (
        "$.review.submitted_at",
        "$.pull_request.updated_at",
        "$.pull_request.created_at",
    ),
    "pull_request_review_comment": (
        "$.comment.updated_at",
        "$.comment.created_at",
        "$.pull_request.updated_at",
    ),
    "issues": (
        "$.issue.updated_at",
        "$.issue.created_at",
    ),
    "issue_comment": (
        "$.comment.updated_at",
        "$.comment.created_at",
        "$.issue.updated_at",
    ),
    "code_scanning_alert": (
        "$.alert.updated_at",
        "$.alert.created_at",
    ),
    "dependabot_alert": (
        "$.alert.updated_at",
        "$.alert.created_at",
    ),
    "secret_scanning_alert": (
        "$.alert.updated_at",
        "$.alert.created_at",
    ),
    "push": (
        "$.head_commit.timestamp",
        "$.repository.pushed_at",
    ),
    "release": (
        "$.release.published_at",
        "$.release.created_at",
    ),
}

DEFAULT_TIMESTAMP_PATHS = (
    "$.updated_at",
    "$.created_at",
)

FAMILY_EVENT_TYPES = {
    "actions_workflow_runs": ("workflow_run",),
    "actions_workflow_jobs": ("workflow_job",),
    "pull_requests": (
        "pull_request",
        "pull_request_review",
        "pull_request_review_comment",
    ),
    "issues": ("issues", "issue_comment"),
    "security_alerts": (
        "code_scanning_alert",
        "dependabot_alert",
        "secret_scanning_alert",
    ),
    "organization_activity": (
        "member",
        "membership",
        "organization",
        "organization_block",
        "repository",
        "repository_import",
        "team",
        "team_add",
    ),
}

CORE_COLUMNS = (
    ("delivery_id", "string"),
    ("event_type", "string"),
    ("action", "string"),
    ("event_family", "string"),
    ("received_at", "timestamp"),
    ("received_at_precision", "string"),
    ("event_at", "timestamp"),
    ("organization_id", "bigint"),
    ("organization_login", "string"),
    ("enterprise_id", "bigint"),
    ("enterprise_slug", "string"),
    ("repository_id", "bigint"),
    ("repository_full_name", "string"),
    ("repository_visibility", "string"),
    ("sender_id", "bigint"),
    ("sender_login", "string"),
    ("trust_state", "string"),
    ("signature_valid", "boolean"),
    ("payload_version", "int"),
    ("payload_sha256", "string"),
    ("raw_payload", "string"),
    ("bronze_object_path", "string"),
    ("processing_run_id", "string"),
    ("normalized_at", "timestamp"),
)

FAMILY_COMMON_COLUMNS = (
    ("delivery_id", "string"),
    ("event_type", "string"),
    ("action", "string"),
    ("received_at", "timestamp"),
    ("event_at", "timestamp"),
    ("organization_id", "bigint"),
    ("organization_login", "string"),
    ("enterprise_id", "bigint"),
    ("enterprise_slug", "string"),
    ("repository_id", "bigint"),
    ("repository_full_name", "string"),
    ("sender_id", "bigint"),
    ("sender_login", "string"),
    ("payload_version", "int"),
    ("payload_sha256", "string"),
    ("bronze_object_path", "string"),
    ("processing_run_id", "string"),
    ("normalized_at", "timestamp"),
)

TABLE_DEFINITIONS = {
    "events": {
        "columns": CORE_COLUMNS,
        "partition_column": "received_at",
    },
    "actions_workflow_runs": {
        "columns": FAMILY_COMMON_COLUMNS
        + (
            ("workflow_run_id", "bigint"),
            ("workflow_id", "bigint"),
            ("workflow_name", "string"),
            ("display_title", "string"),
            ("run_number", "bigint"),
            ("run_attempt", "int"),
            ("workflow_event", "string"),
            ("status", "string"),
            ("conclusion", "string"),
            ("head_branch", "string"),
            ("head_sha", "string"),
            ("actor_id", "bigint"),
            ("actor_login", "string"),
            ("triggering_actor_id", "bigint"),
            ("triggering_actor_login", "string"),
            ("created_at", "timestamp"),
            ("run_started_at", "timestamp"),
            ("updated_at", "timestamp"),
        ),
        "partition_column": "received_at",
    },
    "actions_workflow_jobs": {
        "columns": FAMILY_COMMON_COLUMNS
        + (
            ("workflow_job_id", "bigint"),
            ("workflow_run_id", "bigint"),
            ("workflow_name", "string"),
            ("job_name", "string"),
            ("status", "string"),
            ("conclusion", "string"),
            ("head_branch", "string"),
            ("head_sha", "string"),
            ("runner_name", "string"),
            ("runner_group_id", "bigint"),
            ("runner_group_name", "string"),
            ("runner_labels", "array<string>"),
            ("created_at", "timestamp"),
            ("started_at", "timestamp"),
            ("completed_at", "timestamp"),
        ),
        "partition_column": "received_at",
    },
    "pull_requests": {
        "columns": FAMILY_COMMON_COLUMNS
        + (
            ("pull_request_id", "bigint"),
            ("pull_request_number", "bigint"),
            ("title", "string"),
            ("state", "string"),
            ("draft", "boolean"),
            ("locked", "boolean"),
            ("merged", "boolean"),
            ("author_id", "bigint"),
            ("author_login", "string"),
            ("author_association", "string"),
            ("base_ref", "string"),
            ("head_ref", "string"),
            ("head_sha", "string"),
            ("merge_commit_sha", "string"),
            ("additions", "bigint"),
            ("deletions", "bigint"),
            ("changed_files", "bigint"),
            ("commits", "bigint"),
            ("comments", "bigint"),
            ("review_comments", "bigint"),
            ("created_at", "timestamp"),
            ("updated_at", "timestamp"),
            ("closed_at", "timestamp"),
            ("merged_at", "timestamp"),
        ),
        "partition_column": "received_at",
    },
    "issues": {
        "columns": FAMILY_COMMON_COLUMNS
        + (
            ("issue_id", "bigint"),
            ("issue_number", "bigint"),
            ("title", "string"),
            ("state", "string"),
            ("state_reason", "string"),
            ("locked", "boolean"),
            ("author_id", "bigint"),
            ("author_login", "string"),
            ("author_association", "string"),
            ("issue_type_id", "bigint"),
            ("issue_type_name", "string"),
            ("comments", "bigint"),
            ("created_at", "timestamp"),
            ("updated_at", "timestamp"),
            ("closed_at", "timestamp"),
        ),
        "partition_column": "received_at",
    },
    "security_alerts": {
        "columns": FAMILY_COMMON_COLUMNS
        + (
            ("alert_kind", "string"),
            ("alert_number", "bigint"),
            ("state", "string"),
            ("severity", "string"),
            ("resolution", "string"),
            ("resolution_comment", "string"),
            ("secret_type", "string"),
            ("dependency_package", "string"),
            ("created_at", "timestamp"),
            ("updated_at", "timestamp"),
            ("resolved_at", "timestamp"),
            ("dismissed_at", "timestamp"),
            ("fixed_at", "timestamp"),
        ),
        "partition_column": "received_at",
    },
    "organization_activity": {
        "columns": FAMILY_COMMON_COLUMNS
        + (
            ("subject_type", "string"),
            ("subject_id", "bigint"),
            ("subject_login", "string"),
            ("subject_name", "string"),
            ("membership_role", "string"),
            ("team_privacy", "string"),
            ("subject_visibility", "string"),
            ("changes_json", "string"),
        ),
        "partition_column": "received_at",
    },
    "quarantined_events": {
        "columns": (
            ("quarantine_id", "string"),
            ("delivery_id", "string"),
            ("event_type", "string"),
            ("reason", "string"),
            ("payload_sha256", "string"),
            ("bronze_object_path", "string"),
            ("received_at", "timestamp"),
            ("processing_run_id", "string"),
            ("quarantined_at", "timestamp"),
        ),
        "partition_column": "quarantined_at",
    },
}


def event_family(event_type):
    return EVENT_FAMILY_BY_TYPE.get(event_type, "other")


def event_timestamp_paths(event_type):
    return EVENT_TIMESTAMP_PATHS.get(event_type, DEFAULT_TIMESTAMP_PATHS)


def parse_job_arguments(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--JOB_NAME", required=True)
    parser.add_argument("--JOB_RUN_ID")
    parser.add_argument("--environment", required=True)
    parser.add_argument("--bronze_path", required=True)
    parser.add_argument("--silver_database", required=True)
    parser.add_argument("--warehouse_path", required=True)
    parser.add_argument("--quarantine_path", required=True)
    parser.add_argument("--start_date")
    parser.add_argument("--end_date")
    parser.add_argument("--job-bookmark-option", default="job-bookmark-enable")
    arguments, _ = parser.parse_known_args(argv)

    if bool(arguments.start_date) != bool(arguments.end_date):
        parser.error("--start_date and --end_date must be supplied together")
    if arguments.start_date:
        try:
            start_date = date.fromisoformat(arguments.start_date)
            end_date = date.fromisoformat(arguments.end_date)
        except ValueError as error:
            parser.error(str(error))
        if start_date > end_date:
            parser.error("--start_date must not be after --end_date")
        if arguments.job_bookmark_option != "job-bookmark-disable":
            parser.error("bounded backfills require --job-bookmark-option job-bookmark-disable")

    for value in (arguments.environment, arguments.silver_database):
        _validate_identifier(value)
    for value in (
        arguments.bronze_path,
        arguments.warehouse_path,
        arguments.quarantine_path,
    ):
        _validate_s3_path(value)

    return arguments


def source_paths(arguments):
    bronze_path = arguments.bronze_path.rstrip("/")
    if not arguments.start_date:
        return [f"{bronze_path}/"]

    current_date = date.fromisoformat(arguments.start_date)
    end_date = date.fromisoformat(arguments.end_date)
    paths = []
    while current_date <= end_date:
        paths.append(
            f"{bronze_path}/year={current_date:%Y}/month={current_date:%m}/day={current_date:%d}/"
        )
        current_date += timedelta(days=1)
    return paths


def paths_with_objects(paths, s3_client):
    populated_paths = []
    for path in paths:
        location = urlparse(path)
        response = s3_client.list_objects_v2(
            Bucket=location.netloc,
            Prefix=location.path.lstrip("/"),
            MaxKeys=1,
        )
        if response.get("KeyCount", len(response.get("Contents", []))) > 0:
            populated_paths.append(path)
    return populated_paths


def table_location(arguments, table_name):
    if table_name == "quarantined_events":
        return arguments.quarantine_path.rstrip("/") + "/"
    return f"{arguments.warehouse_path.rstrip('/')}/{table_name}/"


def create_table_sql(database_name, table_name, location):
    definition = TABLE_DEFINITIONS[table_name]
    qualified_name = qualified_table(database_name, table_name)
    _validate_s3_path(location)
    columns = ",\n  ".join(
        f"{_quote_identifier(column_name)} {column_type}"
        for column_name, column_type in definition["columns"]
    )
    partition_column = _quote_identifier(definition["partition_column"])
    return f"""CREATE TABLE IF NOT EXISTS {qualified_name} (
  {columns}
)
USING iceberg
PARTITIONED BY (days({partition_column}))
LOCATION '{location}'
TBLPROPERTIES (
  'format-version'='2',
  'write.format.default'='parquet',
  'write.parquet.compression-codec'='zstd',
  'write.target-file-size-bytes'='268435456'
)"""


def merge_sql(database_name, table_name, source_view, key_column):
    columns = [column_name for column_name, _ in TABLE_DEFINITIONS[table_name]["columns"]]
    target_name = qualified_table(database_name, table_name)
    source_name = _quote_identifier(source_view)
    key_name = _quote_identifier(key_column)
    assignments = ",\n  ".join(
        f"target.{_quote_identifier(column)} = source.{_quote_identifier(column)}"
        for column in columns
    )
    insert_columns = ", ".join(_quote_identifier(column) for column in columns)
    insert_values = ", ".join(
        f"source.{_quote_identifier(column)}" for column in columns
    )
    return f"""MERGE INTO {target_name} AS target
USING {source_name} AS source
ON target.{key_name} = source.{key_name}
WHEN MATCHED THEN UPDATE SET
  {assignments}
WHEN NOT MATCHED THEN INSERT ({insert_columns})
VALUES ({insert_values})"""


def qualified_table(database_name, table_name):
    return ".".join(
        (
            _quote_identifier(CATALOG_NAME),
            _quote_identifier(database_name),
            _quote_identifier(table_name),
        )
    )


def _validate_identifier(value):
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError(f"Invalid identifier: {value}")


def _quote_identifier(value):
    _validate_identifier(value)
    return f"`{value}`"


def _validate_s3_path(value):
    if not re.fullmatch(r"s3://[A-Za-z0-9][A-Za-z0-9.-]*/[^']*", value):
        raise ValueError(f"Invalid S3 path: {value}")


def _optional_column(frame, column_name, column_type, functions):
    if column_name in frame.columns:
        return functions.col(column_name).cast(column_type)
    return functions.lit(None).cast(column_type)


def _nonempty(column, functions):
    normalized = functions.trim(column.cast("string"))
    return functions.when(functions.length(normalized) > 0, normalized)


def _json_string(path, functions):
    return _nonempty(functions.get_json_object("raw_payload", path), functions)


def _json_long(path, functions):
    return functions.get_json_object("raw_payload", path).cast("long")


def _json_int(path, functions):
    return functions.get_json_object("raw_payload", path).cast("int")


def _json_boolean(path, functions):
    return functions.get_json_object("raw_payload", path).cast("boolean")


def _json_timestamp(path, functions):
    raw_value = functions.get_json_object("raw_payload", path)
    numeric_value = raw_value.cast("double")
    epoch_divisor = functions.when(functions.length(raw_value) >= 13, 1000.0).otherwise(1.0)
    return functions.coalesce(
        functions.to_timestamp(raw_value),
        functions.when(
            raw_value.rlike(r"^[0-9]+(?:\.[0-9]+)?$"),
            functions.to_timestamp(functions.from_unixtime(numeric_value / epoch_divisor)),
        ),
    )


def _event_at_column(functions):
    selected_timestamp = None
    for event_type, paths in EVENT_TIMESTAMP_PATHS.items():
        candidate = functions.coalesce(*[_json_timestamp(path, functions) for path in paths])
        condition = functions.col("event_type") == event_type
        if selected_timestamp is None:
            selected_timestamp = functions.when(condition, candidate)
        else:
            selected_timestamp = selected_timestamp.when(condition, candidate)

    default_timestamp = functions.coalesce(
        *[_json_timestamp(path, functions) for path in DEFAULT_TIMESTAMP_PATHS]
    )
    return selected_timestamp.otherwise(default_timestamp)


def _family_domain_key(functions):
    event_type = functions.col("event_type")
    return (
        functions.when(event_type == "workflow_run", _json_string("$.workflow_run.id", functions))
        .when(event_type == "workflow_job", _json_string("$.workflow_job.id", functions))
        .when(
            event_type.isin(
                "pull_request",
                "pull_request_review",
                "pull_request_review_comment",
            ),
            _json_string("$.pull_request.id", functions),
        )
        .when(
            event_type.isin("issues", "issue_comment"),
            _json_string("$.issue.id", functions),
        )
        .when(
            event_type.isin(
                "code_scanning_alert",
                "dependabot_alert",
                "secret_scanning_alert",
            ),
            _json_string("$.alert.number", functions),
        )
        .when(
            event_type.isin(*FAMILY_EVENT_TYPES["organization_activity"]),
            functions.coalesce(
                _json_string("$.member.id", functions),
                _json_string("$.membership.user.id", functions),
                _json_string("$.blocked_user.id", functions),
                _json_string("$.team.id", functions),
                _json_string("$.repository.id", functions),
                _json_string("$.organization.id", functions),
            ),
        )
    )


def _prepare_source(source, processing_run_id, functions):
    bronze_object_path = functions.input_file_name()
    delivery_id = _nonempty(_optional_column(source, "id", "string", functions), functions)
    event_type = functions.lower(
        _nonempty(_optional_column(source, "event_type", "string", functions), functions)
    )
    raw_payload = _optional_column(source, "raw_payload", "string", functions)
    received_at_epoch_ms = _optional_column(
        source, "received_at_epoch_ms", "long", functions
    )
    path_year = functions.regexp_extract(bronze_object_path, r"/year=(\d{4})/", 1)
    path_month = functions.regexp_extract(bronze_object_path, r"/month=(\d{2})/", 1)
    path_day = functions.regexp_extract(bronze_object_path, r"/day=(\d{2})/", 1)
    partition_timestamp = functions.to_timestamp(
        functions.concat_ws("-", path_year, path_month, path_day),
        "yyyy-MM-dd",
    )
    precise_received_at = functions.to_timestamp(
        functions.from_unixtime(received_at_epoch_ms.cast("double") / 1000.0)
    )
    received_at = functions.coalesce(precise_received_at, partition_timestamp)
    signature_valid = _optional_column(source, "signature_valid", "boolean", functions)
    source_trust_state = _nonempty(
        _optional_column(source, "trust_state", "string", functions), functions
    )
    family_mapping = functions.create_map(
        *[
            item
            for event_name, family_name in EVENT_FAMILY_BY_TYPE.items()
            for item in (functions.lit(event_name), functions.lit(family_name))
        ]
    )

    prepared = source.select(
        delivery_id.alias("delivery_id"),
        event_type.alias("event_type"),
        functions.coalesce(
            _nonempty(_optional_column(source, "action", "string", functions), functions),
            _json_string("$.action", functions),
        ).alias("action"),
        functions.coalesce(
            functions.element_at(family_mapping, event_type),
            functions.lit("other"),
        ).alias("event_family"),
        received_at.alias("received_at"),
        functions.when(received_at_epoch_ms.isNotNull(), "millisecond")
        .otherwise("day")
        .alias("received_at_precision"),
        functions.coalesce(_event_at_column(functions), received_at).alias("event_at"),
        _json_long("$.organization.id", functions).alias("organization_id"),
        _json_string("$.organization.login", functions).alias("organization_login"),
        _json_long("$.enterprise.id", functions).alias("enterprise_id"),
        _json_string("$.enterprise.slug", functions).alias("enterprise_slug"),
        _json_long("$.repository.id", functions).alias("repository_id"),
        _json_string("$.repository.full_name", functions).alias("repository_full_name"),
        _json_string("$.repository.visibility", functions).alias("repository_visibility"),
        _json_long("$.sender.id", functions).alias("sender_id"),
        _json_string("$.sender.login", functions).alias("sender_login"),
        functions.when(
            signature_valid.isNotNull(),
            functions.when(signature_valid, "signature_valid").otherwise("signature_invalid"),
        )
        .otherwise(functions.coalesce(source_trust_state, functions.lit("legacy_unverified")))
        .alias("trust_state"),
        signature_valid.alias("signature_valid"),
        functions.lit(PAYLOAD_VERSION).cast("int").alias("payload_version"),
        functions.sha2(raw_payload, 256).alias("payload_sha256"),
        raw_payload.alias("raw_payload"),
        bronze_object_path.alias("bronze_object_path"),
        functions.lit(processing_run_id).alias("processing_run_id"),
        functions.current_timestamp().alias("normalized_at"),
        functions.get_json_object(raw_payload, "$").isNotNull().alias("json_valid"),
    )
    family_event_types = tuple(
        event_name
        for table_event_types in FAMILY_EVENT_TYPES.values()
        for event_name in table_event_types
    )
    return prepared.withColumn("family_domain_key", _family_domain_key(functions)).withColumn(
        "reason",
        functions.when(functions.col("delivery_id").isNull(), "missing_delivery_id")
        .when(functions.col("event_type").isNull(), "missing_event_type")
        .when(functions.col("raw_payload").isNull(), "missing_raw_payload")
        .when(~functions.col("json_valid"), "invalid_json")
        .when(functions.col("received_at").isNull(), "missing_received_at")
        .when(functions.col("signature_valid") == functions.lit(False), "invalid_signature")
        .when(
            functions.col("event_type").isin(*family_event_types)
            & functions.col("family_domain_key").isNull(),
            "missing_family_domain_key",
        ),
    )


def _deduplicate_batch(eligible, functions, window_type):
    conflicting_ids = (
        eligible.groupBy("delivery_id")
        .agg(functions.countDistinct("payload_sha256").alias("payload_versions"))
        .where(functions.col("payload_versions") > 1)
        .select("delivery_id")
    )
    conflicts = eligible.join(conflicting_ids, "delivery_id", "inner").withColumn(
        "reason", functions.lit("conflicting_payload_hash")
    )
    nonconflicting = eligible.join(conflicting_ids, "delivery_id", "left_anti")
    selection_window = window_type.partitionBy("delivery_id").orderBy(
        functions.col("received_at").desc(),
        functions.col("bronze_object_path").desc(),
    )
    deduplicated = (
        nonconflicting.withColumn(
            "delivery_occurrence", functions.row_number().over(selection_window)
        )
        .where(functions.col("delivery_occurrence") == 1)
        .drop("delivery_occurrence")
    )
    return deduplicated, conflicts


def _exclude_target_conflicts(incoming, spark, database_name, functions):
    target = spark.table(qualified_table(database_name, "events")).select(
        functions.col("delivery_id").alias("target_delivery_id"),
        functions.col("payload_sha256").alias("target_payload_sha256"),
    )
    conflicting_ids = (
        incoming.join(
            target,
            incoming.delivery_id == target.target_delivery_id,
            "inner",
        )
        .where(functions.col("payload_sha256") != functions.col("target_payload_sha256"))
        .select("delivery_id")
        .distinct()
    )
    conflicts = incoming.join(conflicting_ids, "delivery_id", "inner").withColumn(
        "reason", functions.lit("conflicting_canonical_payload")
    )
    return incoming.join(conflicting_ids, "delivery_id", "left_anti"), conflicts


def _quarantine_frame(records, functions):
    quarantine_key = functions.concat_ws(
        "|",
        functions.coalesce(functions.col("delivery_id"), functions.lit("")),
        functions.coalesce(functions.col("payload_sha256"), functions.lit("")),
        functions.coalesce(functions.col("bronze_object_path"), functions.lit("")),
        functions.col("reason"),
    )
    return records.select(
        functions.sha2(quarantine_key, 256).alias("quarantine_id"),
        "delivery_id",
        "event_type",
        "reason",
        "payload_sha256",
        "bronze_object_path",
        "received_at",
        "processing_run_id",
        functions.current_timestamp().alias("quarantined_at"),
    ).dropDuplicates(["quarantine_id"])


def _family_common_columns(functions):
    return [functions.col(column_name) for column_name, _ in FAMILY_COMMON_COLUMNS]


def _family_frame(events, table_name, functions):
    selected = events.where(
        functions.col("event_type").isin(*FAMILY_EVENT_TYPES[table_name])
    )
    common = _family_common_columns(functions)

    if table_name == "actions_workflow_runs":
        domain_columns = [
            _json_long("$.workflow_run.id", functions).alias("workflow_run_id"),
            _json_long("$.workflow_run.workflow_id", functions).alias("workflow_id"),
            _json_string("$.workflow_run.name", functions).alias("workflow_name"),
            _json_string("$.workflow_run.display_title", functions).alias("display_title"),
            _json_long("$.workflow_run.run_number", functions).alias("run_number"),
            _json_int("$.workflow_run.run_attempt", functions).alias("run_attempt"),
            _json_string("$.workflow_run.event", functions).alias("workflow_event"),
            _json_string("$.workflow_run.status", functions).alias("status"),
            _json_string("$.workflow_run.conclusion", functions).alias("conclusion"),
            _json_string("$.workflow_run.head_branch", functions).alias("head_branch"),
            _json_string("$.workflow_run.head_sha", functions).alias("head_sha"),
            _json_long("$.workflow_run.actor.id", functions).alias("actor_id"),
            _json_string("$.workflow_run.actor.login", functions).alias("actor_login"),
            _json_long("$.workflow_run.triggering_actor.id", functions).alias(
                "triggering_actor_id"
            ),
            _json_string("$.workflow_run.triggering_actor.login", functions).alias(
                "triggering_actor_login"
            ),
            _json_timestamp("$.workflow_run.created_at", functions).alias("created_at"),
            _json_timestamp("$.workflow_run.run_started_at", functions).alias(
                "run_started_at"
            ),
            _json_timestamp("$.workflow_run.updated_at", functions).alias("updated_at"),
        ]
    elif table_name == "actions_workflow_jobs":
        domain_columns = [
            _json_long("$.workflow_job.id", functions).alias("workflow_job_id"),
            _json_long("$.workflow_job.run_id", functions).alias("workflow_run_id"),
            _json_string("$.workflow_job.workflow_name", functions).alias("workflow_name"),
            _json_string("$.workflow_job.name", functions).alias("job_name"),
            _json_string("$.workflow_job.status", functions).alias("status"),
            _json_string("$.workflow_job.conclusion", functions).alias("conclusion"),
            _json_string("$.workflow_job.head_branch", functions).alias("head_branch"),
            _json_string("$.workflow_job.head_sha", functions).alias("head_sha"),
            _json_string("$.workflow_job.runner_name", functions).alias("runner_name"),
            _json_long("$.workflow_job.runner_group_id", functions).alias("runner_group_id"),
            _json_string("$.workflow_job.runner_group_name", functions).alias(
                "runner_group_name"
            ),
            functions.from_json(
                functions.get_json_object("raw_payload", "$.workflow_job.labels"),
                "array<string>",
            ).alias("runner_labels"),
            _json_timestamp("$.workflow_job.created_at", functions).alias("created_at"),
            _json_timestamp("$.workflow_job.started_at", functions).alias("started_at"),
            _json_timestamp("$.workflow_job.completed_at", functions).alias("completed_at"),
        ]
    elif table_name == "pull_requests":
        domain_columns = [
            _json_long("$.pull_request.id", functions).alias("pull_request_id"),
            _json_long("$.pull_request.number", functions).alias("pull_request_number"),
            _json_string("$.pull_request.title", functions).alias("title"),
            _json_string("$.pull_request.state", functions).alias("state"),
            _json_boolean("$.pull_request.draft", functions).alias("draft"),
            _json_boolean("$.pull_request.locked", functions).alias("locked"),
            _json_boolean("$.pull_request.merged", functions).alias("merged"),
            _json_long("$.pull_request.user.id", functions).alias("author_id"),
            _json_string("$.pull_request.user.login", functions).alias("author_login"),
            _json_string("$.pull_request.author_association", functions).alias(
                "author_association"
            ),
            _json_string("$.pull_request.base.ref", functions).alias("base_ref"),
            _json_string("$.pull_request.head.ref", functions).alias("head_ref"),
            _json_string("$.pull_request.head.sha", functions).alias("head_sha"),
            _json_string("$.pull_request.merge_commit_sha", functions).alias(
                "merge_commit_sha"
            ),
            _json_long("$.pull_request.additions", functions).alias("additions"),
            _json_long("$.pull_request.deletions", functions).alias("deletions"),
            _json_long("$.pull_request.changed_files", functions).alias("changed_files"),
            _json_long("$.pull_request.commits", functions).alias("commits"),
            _json_long("$.pull_request.comments", functions).alias("comments"),
            _json_long("$.pull_request.review_comments", functions).alias(
                "review_comments"
            ),
            _json_timestamp("$.pull_request.created_at", functions).alias("created_at"),
            _json_timestamp("$.pull_request.updated_at", functions).alias("updated_at"),
            _json_timestamp("$.pull_request.closed_at", functions).alias("closed_at"),
            _json_timestamp("$.pull_request.merged_at", functions).alias("merged_at"),
        ]
    elif table_name == "issues":
        domain_columns = [
            _json_long("$.issue.id", functions).alias("issue_id"),
            _json_long("$.issue.number", functions).alias("issue_number"),
            _json_string("$.issue.title", functions).alias("title"),
            _json_string("$.issue.state", functions).alias("state"),
            _json_string("$.issue.state_reason", functions).alias("state_reason"),
            _json_boolean("$.issue.locked", functions).alias("locked"),
            _json_long("$.issue.user.id", functions).alias("author_id"),
            _json_string("$.issue.user.login", functions).alias("author_login"),
            _json_string("$.issue.author_association", functions).alias(
                "author_association"
            ),
            _json_long("$.issue.type.id", functions).alias("issue_type_id"),
            _json_string("$.issue.type.name", functions).alias("issue_type_name"),
            _json_long("$.issue.comments", functions).alias("comments"),
            _json_timestamp("$.issue.created_at", functions).alias("created_at"),
            _json_timestamp("$.issue.updated_at", functions).alias("updated_at"),
            _json_timestamp("$.issue.closed_at", functions).alias("closed_at"),
        ]
    elif table_name == "security_alerts":
        domain_columns = [
            functions.regexp_replace(functions.col("event_type"), "_alert$", "").alias(
                "alert_kind"
            ),
            _json_long("$.alert.number", functions).alias("alert_number"),
            _json_string("$.alert.state", functions).alias("state"),
            functions.coalesce(
                _json_string("$.alert.security_advisory.severity", functions),
                _json_string("$.alert.rule.security_severity_level", functions),
                _json_string("$.alert.rule.severity", functions),
            ).alias("severity"),
            functions.coalesce(
                _json_string("$.alert.resolution", functions),
                _json_string("$.alert.dismissed_reason", functions),
            ).alias("resolution"),
            functions.coalesce(
                _json_string("$.alert.resolution_comment", functions),
                _json_string("$.alert.dismissed_comment", functions),
            ).alias("resolution_comment"),
            _json_string("$.alert.secret_type", functions).alias("secret_type"),
            _json_string("$.alert.dependency.package.name", functions).alias(
                "dependency_package"
            ),
            _json_timestamp("$.alert.created_at", functions).alias("created_at"),
            _json_timestamp("$.alert.updated_at", functions).alias("updated_at"),
            _json_timestamp("$.alert.resolved_at", functions).alias("resolved_at"),
            _json_timestamp("$.alert.dismissed_at", functions).alias("dismissed_at"),
            _json_timestamp("$.alert.fixed_at", functions).alias("fixed_at"),
        ]
    elif table_name == "organization_activity":
        event_type = functions.col("event_type")
        domain_columns = [
            functions.when(
                event_type.isin("member", "membership", "organization_block"), "user"
            )
            .when(event_type.isin("team", "team_add"), "team")
            .when(event_type.isin("repository", "repository_import"), "repository")
            .otherwise("organization")
            .alias("subject_type"),
            functions.coalesce(
                _json_long("$.member.id", functions),
                _json_long("$.membership.user.id", functions),
                _json_long("$.blocked_user.id", functions),
                _json_long("$.team.id", functions),
                _json_long("$.repository.id", functions),
                _json_long("$.organization.id", functions),
            ).alias("subject_id"),
            functions.coalesce(
                _json_string("$.member.login", functions),
                _json_string("$.membership.user.login", functions),
                _json_string("$.blocked_user.login", functions),
                _json_string("$.organization.login", functions),
            ).alias("subject_login"),
            functions.coalesce(
                _json_string("$.team.name", functions),
                _json_string("$.repository.full_name", functions),
                _json_string("$.organization.login", functions),
            ).alias("subject_name"),
            _json_string("$.membership.role", functions).alias("membership_role"),
            _json_string("$.team.privacy", functions).alias("team_privacy"),
            _json_string("$.repository.visibility", functions).alias("subject_visibility"),
            functions.get_json_object("raw_payload", "$.changes").alias("changes_json"),
        ]
    else:
        raise ValueError(f"Unsupported family table: {table_name}")

    return selected.select(*(common + domain_columns))


def _merge_frame(frame, spark, database_name, table_name, key_column):
    source_view = f"incoming_{table_name}_{uuid.uuid4().hex}"
    columns = [column_name for column_name, _ in TABLE_DEFINITIONS[table_name]["columns"]]
    frame.select(*columns).createOrReplaceTempView(source_view)
    spark.sql(merge_sql(database_name, table_name, source_view, key_column))
    spark.catalog.dropTempView(source_view)


def _emit_metrics(environment, metrics):
    import boto3

    metric_data = [
        {
            "MetricName": metric_name,
            "Dimensions": [{"Name": "Environment", "Value": environment}],
            "Unit": "Count",
            "Value": metric_value,
        }
        for metric_name, metric_value in metrics.items()
    ]
    boto3.client("cloudwatch").put_metric_data(
        Namespace="GitHubDataLake/WebhookSilver",
        MetricData=metric_data,
    )


def run(argv=None):
    arguments = parse_job_arguments(argv or sys.argv[1:])

    import boto3
    from awsglue.context import GlueContext
    from awsglue.job import Job
    from pyspark import SparkContext
    from pyspark.sql import functions
    from pyspark.sql.window import Window

    glue_context = GlueContext(SparkContext.getOrCreate())
    spark = glue_context.spark_session
    spark.conf.set("spark.sql.session.timeZone", "UTC")
    spark.conf.set("spark.sql.ansi.enabled", "false")
    job = Job(glue_context)
    job.init(arguments.JOB_NAME, vars(arguments))

    for table_name in TABLE_DEFINITIONS:
        spark.sql(
            create_table_sql(
                arguments.silver_database,
                table_name,
                table_location(arguments, table_name),
            )
        )

    populated_source_paths = paths_with_objects(
        source_paths(arguments),
        boto3.client("s3"),
    )
    if not populated_source_paths:
        metrics = {"SourceRows": 0}
        _emit_metrics(arguments.environment, metrics)
        job.commit()
        return metrics

    source = glue_context.create_dynamic_frame.from_options(
        connection_type="s3",
        connection_options={
            "paths": populated_source_paths,
            "recurse": True,
        },
        format="parquet",
        transformation_ctx=BRONZE_TRANSFORMATION_CONTEXT,
    ).toDF()
    source_count = source.count()
    metrics = {"SourceRows": source_count}
    if source_count == 0:
        _emit_metrics(arguments.environment, metrics)
        job.commit()
        return metrics

    processing_run_id = arguments.JOB_RUN_ID or str(uuid.uuid4())
    prepared = _prepare_source(source, processing_run_id, functions).cache()
    invalid = prepared.where(functions.col("reason").isNotNull())
    eligible = prepared.where(functions.col("reason").isNull()).drop(
        "reason", "json_valid", "family_domain_key"
    )
    deduplicated, batch_conflicts = _deduplicate_batch(eligible, functions, Window)
    incoming, target_conflicts = _exclude_target_conflicts(
        deduplicated,
        spark,
        arguments.silver_database,
        functions,
    )
    incoming = incoming.cache()

    invalid_count = invalid.count()
    eligible_count = eligible.count()
    batch_conflict_count = batch_conflicts.count()
    target_conflict_count = target_conflicts.count()
    incoming_count = incoming.count()
    duplicate_count = (
        eligible_count - batch_conflict_count - target_conflict_count - incoming_count
    )

    invalid_for_quarantine = invalid.drop("json_valid", "family_domain_key")
    quarantine = _quarantine_frame(
        invalid_for_quarantine.select(*eligible.columns, "reason")
        .unionByName(batch_conflicts.select(*eligible.columns, "reason"))
        .unionByName(target_conflicts.select(*eligible.columns, "reason")),
        functions,
    ).cache()
    quarantine_count = quarantine.count()
    if quarantine_count:
        _merge_frame(
            quarantine,
            spark,
            arguments.silver_database,
            "quarantined_events",
            "quarantine_id",
        )

    if incoming_count:
        _merge_frame(
            incoming,
            spark,
            arguments.silver_database,
            "events",
            "delivery_id",
        )

    family_counts = {}
    for table_name in FAMILY_EVENT_TYPES:
        family = _family_frame(incoming, table_name, functions).cache()
        family_count = family.count()
        family_counts[table_name] = family_count
        if family_count:
            _merge_frame(
                family,
                spark,
                arguments.silver_database,
                table_name,
                "delivery_id",
            )
        family.unpersist()

    metrics.update(
        {
            "CanonicalRows": incoming_count,
            "DuplicateRows": max(duplicate_count, 0),
            "InvalidRows": invalid_count,
            "BatchConflicts": batch_conflict_count,
            "TargetConflicts": target_conflict_count,
            "QuarantinedRows": quarantine_count,
            "WorkflowRunRows": family_counts["actions_workflow_runs"],
            "WorkflowJobRows": family_counts["actions_workflow_jobs"],
            "PullRequestRows": family_counts["pull_requests"],
            "IssueRows": family_counts["issues"],
            "SecurityAlertRows": family_counts["security_alerts"],
            "OrganizationActivityRows": family_counts["organization_activity"],
        }
    )
    _emit_metrics(arguments.environment, metrics)
    quarantine.unpersist()
    incoming.unpersist()
    prepared.unpersist()
    job.commit()
    return metrics


if __name__ == "__main__":
    run()
