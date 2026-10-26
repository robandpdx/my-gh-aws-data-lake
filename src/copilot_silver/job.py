import argparse
import re
import sys
import uuid
from datetime import date, timedelta
from urllib.parse import urlparse


CATALOG_NAME = "glue_catalog"
MAX_BACKFILL_DAYS = 366
BILLING_TRANSFORMATION_CONTEXT = "copilot_billing_bronze_source"
USAGE_TRANSFORMATION_CONTEXT = "copilot_usage_bronze_source"

LINEAGE_COLUMNS = (
    ("collection_date", "date"),
    ("collected_at", "timestamp"),
    ("raw_payload", "string"),
    ("bronze_object_path", "string"),
    ("processing_run_id", "string"),
    ("normalized_at", "timestamp"),
)

ACTIVITY_COLUMNS = (
    ("user_initiated_interaction_count", "bigint"),
    ("code_generation_activity_count", "bigint"),
    ("code_acceptance_activity_count", "bigint"),
    ("loc_suggested_to_add_sum", "bigint"),
    ("loc_suggested_to_delete_sum", "bigint"),
    ("loc_added_sum", "bigint"),
    ("loc_deleted_sum", "bigint"),
)

SURFACE_COLUMNS = (
    ("cli_session_count", "bigint"),
    ("cli_request_count", "bigint"),
    ("cli_prompt_count", "bigint"),
    ("cli_output_tokens_sum", "bigint"),
    ("cli_prompt_tokens_sum", "bigint"),
    ("cli_avg_tokens_per_request", "double"),
    ("copilot_app_session_count", "bigint"),
    ("copilot_app_request_count", "bigint"),
    ("copilot_app_prompt_count", "bigint"),
    ("copilot_app_output_tokens_sum", "bigint"),
    ("copilot_app_prompt_tokens_sum", "bigint"),
    ("copilot_app_avg_tokens_per_request", "double"),
)

PULL_REQUEST_COLUMNS = (
    ("pull_requests_created", "bigint"),
    ("pull_requests_reviewed", "bigint"),
    ("pull_requests_merged", "bigint"),
    ("median_minutes_to_merge", "double"),
    ("pull_request_suggestions", "bigint"),
    ("pull_request_applied_suggestions", "bigint"),
    ("pull_requests_created_by_copilot", "bigint"),
    ("pull_requests_reviewed_by_copilot", "bigint"),
    ("pull_requests_merged_created_by_copilot", "bigint"),
    ("pull_requests_merged_reviewed_by_copilot", "bigint"),
    ("median_minutes_to_merge_copilot_authored", "double"),
    ("median_minutes_to_merge_copilot_reviewed", "double"),
    ("copilot_suggestions", "bigint"),
    ("copilot_applied_suggestions", "bigint"),
    ("copilot_suggestions_by_comment_type_json", "string"),
)

BREAKDOWN_COLUMNS = (
    ("totals_by_client_json", "string"),
    ("totals_by_skill_json", "string"),
    ("totals_by_custom_agent_json", "string"),
    ("totals_by_mcp_json", "string"),
    ("totals_by_slash_cmd_json", "string"),
    ("totals_by_plugin_json", "string"),
    ("totals_by_feature_json", "string"),
    ("totals_by_ide_json", "string"),
    ("totals_by_language_feature_json", "string"),
    ("totals_by_language_model_json", "string"),
    ("totals_by_model_feature_json", "string"),
    ("totals_by_third_party_agent_json", "string"),
)

USER_CUSTOMIZATION_COLUMNS = (
    ("distinct_skill_use_count", "bigint"),
    ("distinct_custom_agent_use_count", "bigint"),
    ("distinct_mcp_use_count", "bigint"),
    ("distinct_slash_cmd_use_count", "bigint"),
    ("distinct_plugin_use_count", "bigint"),
)

TABLE_DEFINITIONS = {
    "billing_usage_daily": {
        "key": "billing_usage_key",
        "columns": (
            ("billing_usage_key", "string"),
            ("report_day", "date"),
            ("report_type", "string"),
            ("enterprise_slug", "string"),
            ("organization_login", "string"),
            ("user_login", "string"),
            ("product", "string"),
            ("sku", "string"),
            ("model", "string"),
            ("unit_type", "string"),
            ("price_per_unit", "decimal(38,12)"),
            ("gross_quantity", "decimal(38,12)"),
            ("gross_amount", "decimal(38,12)"),
            ("discount_quantity", "decimal(38,12)"),
            ("discount_amount", "decimal(38,12)"),
            ("net_quantity", "decimal(38,12)"),
            ("net_amount", "decimal(38,12)"),
            ("cost_center_id", "string"),
            ("cost_center_name", "string"),
        )
        + LINEAGE_COLUMNS,
    },
    "enterprise_usage_daily": {
        "key": "enterprise_usage_key",
        "columns": (
            ("enterprise_usage_key", "string"),
            ("report_day", "date"),
            ("enterprise_slug", "string"),
            ("enterprise_id", "string"),
            ("daily_active_users", "bigint"),
            ("weekly_active_users", "bigint"),
            ("monthly_active_users", "bigint"),
            ("monthly_active_chat_users", "bigint"),
            ("monthly_active_agent_users", "bigint"),
            ("daily_active_copilot_cloud_agent_users", "bigint"),
            ("weekly_active_copilot_cloud_agent_users", "bigint"),
            ("monthly_active_copilot_cloud_agent_users", "bigint"),
            ("daily_active_copilot_code_review_users", "bigint"),
            ("weekly_active_copilot_code_review_users", "bigint"),
            ("monthly_active_copilot_code_review_users", "bigint"),
            ("daily_passive_copilot_code_review_users", "bigint"),
            ("weekly_passive_copilot_code_review_users", "bigint"),
            ("monthly_passive_copilot_code_review_users", "bigint"),
            ("daily_active_cli_users", "bigint"),
            ("weekly_active_cli_users", "bigint"),
            ("monthly_active_cli_users", "bigint"),
            ("daily_active_copilot_app_users", "bigint"),
            ("weekly_active_copilot_app_users", "bigint"),
            ("monthly_active_copilot_app_users", "bigint"),
        )
        + ACTIVITY_COLUMNS
        + SURFACE_COLUMNS
        + PULL_REQUEST_COLUMNS
        + BREAKDOWN_COLUMNS
        + (("totals_by_ai_adoption_phase_json", "string"),)
        + LINEAGE_COLUMNS,
    },
    "user_usage_daily": {
        "key": "user_usage_key",
        "columns": (
            ("user_usage_key", "string"),
            ("report_day", "date"),
            ("enterprise_slug", "string"),
            ("enterprise_id", "string"),
            ("user_id", "bigint"),
            ("user_login", "string"),
            ("ai_credits_used", "decimal(38,12)"),
        )
        + USER_CUSTOMIZATION_COLUMNS
        + ACTIVITY_COLUMNS
        + (
            ("used_agent", "boolean"),
            ("used_chat", "boolean"),
            ("used_cli", "boolean"),
            ("used_copilot_app", "boolean"),
            ("used_copilot_cloud_agent", "boolean"),
            ("used_copilot_coding_agent", "boolean"),
            ("used_copilot_code_review_active", "boolean"),
            ("used_copilot_code_review_passive", "boolean"),
            ("ai_adoption_phase_number", "int"),
            ("ai_adoption_phase", "string"),
            ("ai_adoption_phase_version", "string"),
        )
        + SURFACE_COLUMNS
        + (
            ("last_known_cli_version", "string"),
            ("last_known_cli_version_sampled_at", "timestamp"),
        )
        + BREAKDOWN_COLUMNS
        + LINEAGE_COLUMNS,
    },
    "repository_usage_daily": {
        "key": "repository_usage_key",
        "columns": (
            ("repository_usage_key", "string"),
            ("report_day", "date"),
            ("enterprise_slug", "string"),
            ("enterprise_id", "string"),
            ("organization_id", "string"),
            ("repository_id", "bigint"),
            ("repository_owner", "string"),
            ("repository_name", "string"),
            ("repository_full_name", "string"),
            ("repository_visibility", "string"),
        )
        + PULL_REQUEST_COLUMNS
        + LINEAGE_COLUMNS,
    },
    "user_team_memberships_daily": {
        "key": "user_team_membership_key",
        "columns": (
            ("user_team_membership_key", "string"),
            ("report_day", "date"),
            ("enterprise_slug", "string"),
            ("enterprise_id", "string"),
            ("organization_id", "string"),
            ("user_id", "bigint"),
            ("user_login", "string"),
            ("team_id", "bigint"),
            ("team_slug", "string"),
        )
        + LINEAGE_COLUMNS,
    },
    "quarantined_records": {
        "key": "quarantine_id",
        "partition_column": "quarantined_at",
        "columns": (
            ("quarantine_id", "string"),
            ("source", "string"),
            ("report_type", "string"),
            ("report_day", "date"),
            ("collection_date", "date"),
            ("reason", "string"),
            ("raw_payload", "string"),
            ("bronze_object_path", "string"),
            ("processing_run_id", "string"),
            ("quarantined_at", "timestamp"),
        ),
    },
}


def parse_job_arguments(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--JOB_NAME", required=True)
    parser.add_argument("--JOB_RUN_ID")
    parser.add_argument("--environment", required=True)
    parser.add_argument("--billing_bronze_path", required=True)
    parser.add_argument("--usage_bronze_path", required=True)
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
        if (end_date - start_date).days + 1 > MAX_BACKFILL_DAYS:
            parser.error(f"backfills are limited to {MAX_BACKFILL_DAYS} days")
        if arguments.job_bookmark_option != "job-bookmark-disable":
            parser.error(
                "bounded backfills require --job-bookmark-option job-bookmark-disable"
            )

    for value in (arguments.environment, arguments.silver_database):
        _validate_identifier(value)
    for value in (
        arguments.billing_bronze_path,
        arguments.usage_bronze_path,
        arguments.warehouse_path,
        arguments.quarantine_path,
    ):
        _validate_s3_path(value)
    return arguments


def source_paths(bronze_path, start_date=None, end_date=None):
    bronze_path = bronze_path.rstrip("/")
    if not start_date:
        return [f"{bronze_path}/"]

    current_date = date.fromisoformat(start_date)
    final_date = date.fromisoformat(end_date)
    paths = []
    while current_date <= final_date:
        paths.append(
            f"{bronze_path}/year={current_date:%Y}/month={current_date:%m}/"
            f"day={current_date:%d}/"
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
    if table_name == "quarantined_records":
        return arguments.quarantine_path.rstrip("/") + "/"
    return f"{arguments.warehouse_path.rstrip('/')}/{table_name}/"


def create_table_sql(database_name, table_name, location):
    definition = TABLE_DEFINITIONS[table_name]
    columns = ",\n  ".join(
        f"{_quote_identifier(column_name)} {column_type}"
        for column_name, column_type in definition["columns"]
    )
    partition_column = _quote_identifier(
        definition.get("partition_column", "report_day")
    )
    _validate_s3_path(location)
    return f"""CREATE TABLE IF NOT EXISTS {qualified_table(database_name, table_name)} (
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


def ensure_table(spark, database_name, table_name, location):
    spark.sql(create_table_sql(database_name, table_name, location))
    target = qualified_table(database_name, table_name)
    existing_columns = set(spark.table(target).columns)
    missing_columns = [
        f"{_quote_identifier(column_name)} {column_type}"
        for column_name, column_type in TABLE_DEFINITIONS[table_name]["columns"]
        if column_name not in existing_columns
    ]
    if missing_columns:
        spark.sql(
            f"ALTER TABLE {target} ADD COLUMNS ({', '.join(missing_columns)})"
        )


def merge_sql(database_name, table_name, source_view):
    definition = TABLE_DEFINITIONS[table_name]
    columns = [column_name for column_name, _ in definition["columns"]]
    key_name = _quote_identifier(definition["key"])
    assignments = ",\n  ".join(
        f"target.{_quote_identifier(column)} = source.{_quote_identifier(column)}"
        for column in columns
    )
    insert_columns = ", ".join(_quote_identifier(column) for column in columns)
    insert_values = ", ".join(
        f"source.{_quote_identifier(column)}" for column in columns
    )
    recency_condition = "" if table_name == "quarantined_records" else """
AND (
  source.`collection_date` > target.`collection_date`
  OR (
    source.`collection_date` = target.`collection_date`
    AND source.`collected_at` >= target.`collected_at`
  )
)"""
    return f"""MERGE INTO {qualified_table(database_name, table_name)} AS target
USING {_quote_identifier(source_view)} AS source
ON target.{key_name} = source.{key_name}
WHEN MATCHED{recency_condition} THEN UPDATE SET
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


def _json_double(path, functions):
    return functions.get_json_object("raw_payload", path).cast("double")


def _json_decimal(path, functions):
    return functions.get_json_object("raw_payload", path).cast("decimal(38,12)")


def _json_boolean(path, functions):
    return functions.get_json_object("raw_payload", path).cast("boolean")


def _json_timestamp(path, functions):
    return functions.to_timestamp(functions.get_json_object("raw_payload", path))


def _json_object(path, functions):
    return functions.get_json_object("raw_payload", path)


def _hash_key(functions, *columns):
    normalized = [
        functions.coalesce(column.cast("string"), functions.lit(""))
        for column in columns
    ]
    return functions.sha2(functions.concat_ws("|", *normalized), 256)


def _prepare_base(source, source_name, processing_run_id, functions):
    source_path = functions.input_file_name()
    report_type = _nonempty(
        functions.regexp_extract(source_path, r"/report_type=([^/]+)/", 1),
        functions,
    )
    return (
        source.withColumn("_source", functions.lit(source_name))
        .withColumn("_report_type", report_type)
        .withColumn("_report_day", functions.to_date(functions.col("report_day")))
        .withColumn(
            "_collection_date", functions.to_date(functions.col("collection_date"))
        )
        .withColumn("_collected_at", functions.to_timestamp("collected_at"))
        .withColumn("_bronze_object_path", source_path)
        .withColumn("_processing_run_id", functions.lit(processing_run_id))
        .withColumn("_normalized_at", functions.current_timestamp())
    )


def _with_reason(prepared, functions):
    report_type = functions.col("_report_type")
    raw_valid = functions.get_json_object("raw_payload", "$").isNotNull()
    enterprise_id = _json_string("$.enterprise_id", functions)
    user_id = functions.coalesce(
        _optional_column(prepared, "user_id", "long", functions),
        _json_long("$.user_id", functions),
    )
    repository_id = functions.coalesce(
        _optional_column(prepared, "repository_id", "long", functions),
        _json_long("$.repo_id", functions),
    )
    team_id = functions.coalesce(
        _optional_column(prepared, "team_id", "long", functions),
        _json_long("$.team_id", functions),
    )
    reason = (
        functions.when(functions.col("_report_day").isNull(), "missing_report_day")
        .when(functions.col("_collection_date").isNull(), "missing_collection_date")
        .when(functions.col("raw_payload").isNull(), "missing_raw_payload")
        .when(~raw_valid, "invalid_raw_payload")
        .when(
            (functions.col("_source") == "billing")
            & ~report_type.isin("ai_credit", "premium_request"),
            "unsupported_billing_report_type",
        )
        .when(
            (functions.col("_source") == "billing")
            & _optional_column(prepared, "product", "string", functions).isNull(),
            "missing_product",
        )
        .when(
            (functions.col("_source") == "billing")
            & _optional_column(prepared, "sku", "string", functions).isNull(),
            "missing_sku",
        )
        .when(
            (functions.col("_source") == "usage")
            & ~report_type.isin(
                "enterprise", "users", "repositories", "user_teams"
            ),
            "unsupported_usage_report_type",
        )
        .when(
            (report_type == "enterprise") & enterprise_id.isNull(),
            "missing_enterprise_id",
        )
        .when((report_type == "users") & user_id.isNull(), "missing_user_id")
        .when(
            (report_type == "repositories") & repository_id.isNull(),
            "missing_repository_id",
        )
        .when(
            (report_type == "user_teams") & user_id.isNull(),
            "missing_user_id",
        )
        .when(
            (report_type == "user_teams") & team_id.isNull(),
            "missing_team_id",
        )
    )
    return prepared.withColumn("_reason", reason)


def _lineage_expressions(functions):
    return [
        functions.col("_collection_date").alias("collection_date"),
        functions.col("_collected_at").alias("collected_at"),
        functions.col("raw_payload").alias("raw_payload"),
        functions.col("_bronze_object_path").alias("bronze_object_path"),
        functions.col("_processing_run_id").alias("processing_run_id"),
        functions.col("_normalized_at").alias("normalized_at"),
    ]


def _activity_expressions(functions):
    return [
        _json_long(f"$.{column_name}", functions).alias(column_name)
        for column_name, _ in ACTIVITY_COLUMNS
    ]


def _surface_expressions(functions):
    paths = {
        "cli_session_count": "$.totals_by_cli.session_count",
        "cli_request_count": "$.totals_by_cli.request_count",
        "cli_prompt_count": "$.totals_by_cli.prompt_count",
        "cli_output_tokens_sum": "$.totals_by_cli.token_usage.output_tokens_sum",
        "cli_prompt_tokens_sum": "$.totals_by_cli.token_usage.prompt_tokens_sum",
        "cli_avg_tokens_per_request": "$.totals_by_cli.token_usage.avg_tokens_per_request",
        "copilot_app_session_count": "$.totals_by_copilot_app.session_count",
        "copilot_app_request_count": "$.totals_by_copilot_app.request_count",
        "copilot_app_prompt_count": "$.totals_by_copilot_app.prompt_count",
        "copilot_app_output_tokens_sum": "$.totals_by_copilot_app.token_usage.output_tokens_sum",
        "copilot_app_prompt_tokens_sum": "$.totals_by_copilot_app.token_usage.prompt_tokens_sum",
        "copilot_app_avg_tokens_per_request": "$.totals_by_copilot_app.token_usage.avg_tokens_per_request",
    }
    double_columns = {
        "cli_avg_tokens_per_request",
        "copilot_app_avg_tokens_per_request",
    }
    return [
        (
            _json_double(path, functions)
            if column_name in double_columns
            else _json_long(path, functions)
        ).alias(column_name)
        for column_name, path in paths.items()
    ]


def _pull_request_expressions(functions):
    paths = {
        "pull_requests_created": "$.pull_requests.total_created",
        "pull_requests_reviewed": "$.pull_requests.total_reviewed",
        "pull_requests_merged": "$.pull_requests.total_merged",
        "median_minutes_to_merge": "$.pull_requests.median_minutes_to_merge",
        "pull_request_suggestions": "$.pull_requests.total_suggestions",
        "pull_request_applied_suggestions": "$.pull_requests.total_applied_suggestions",
        "pull_requests_created_by_copilot": "$.pull_requests.total_created_by_copilot",
        "pull_requests_reviewed_by_copilot": "$.pull_requests.total_reviewed_by_copilot",
        "pull_requests_merged_created_by_copilot": "$.pull_requests.total_merged_created_by_copilot",
        "pull_requests_merged_reviewed_by_copilot": "$.pull_requests.total_merged_reviewed_by_copilot",
        "median_minutes_to_merge_copilot_authored": "$.pull_requests.median_minutes_to_merge_copilot_authored",
        "median_minutes_to_merge_copilot_reviewed": "$.pull_requests.median_minutes_to_merge_copilot_reviewed",
        "copilot_suggestions": "$.pull_requests.total_copilot_suggestions",
        "copilot_applied_suggestions": "$.pull_requests.total_copilot_applied_suggestions",
    }
    double_columns = {
        "median_minutes_to_merge",
        "median_minutes_to_merge_copilot_authored",
        "median_minutes_to_merge_copilot_reviewed",
    }
    expressions = [
        (
            _json_double(path, functions)
            if column_name in double_columns
            else _json_long(path, functions)
        ).alias(column_name)
        for column_name, path in paths.items()
    ]
    expressions.append(
        _json_object(
            "$.pull_requests.copilot_suggestions_by_comment_type", functions
        ).alias("copilot_suggestions_by_comment_type_json")
    )
    return expressions


def _breakdown_expressions(functions):
    paths = {
        "totals_by_client_json": "$.totals_by_client",
        "totals_by_skill_json": "$.totals_by_skill",
        "totals_by_custom_agent_json": "$.totals_by_custom_agent",
        "totals_by_mcp_json": "$.totals_by_mcp",
        "totals_by_slash_cmd_json": "$.totals_by_slash_cmd",
        "totals_by_plugin_json": "$.totals_by_plugin",
        "totals_by_feature_json": "$.totals_by_feature",
        "totals_by_ide_json": "$.totals_by_ide",
        "totals_by_language_feature_json": "$.totals_by_language_feature",
        "totals_by_language_model_json": "$.totals_by_language_model",
        "totals_by_model_feature_json": "$.totals_by_model_feature",
        "totals_by_third_party_agent_json": "$.totals_by_3rd_party_agent",
    }
    return [
        _json_object(path, functions).alias(column_name)
        for column_name, path in paths.items()
    ]


def _billing_frame(prepared, functions):
    selected = prepared.where(functions.col("_report_type").isin("ai_credit", "premium_request"))
    report_day = functions.col("_report_day")
    report_type = functions.col("_report_type")
    enterprise_slug = _optional_column(selected, "enterprise_slug", "string", functions)
    organization_login = _optional_column(
        selected, "organization_login", "string", functions
    )
    user_login = _optional_column(selected, "user_login", "string", functions)
    product = _optional_column(selected, "product", "string", functions)
    sku = _optional_column(selected, "sku", "string", functions)
    model = _optional_column(selected, "model", "string", functions)
    unit_type = _optional_column(selected, "unit_type", "string", functions)
    cost_center_id = _optional_column(selected, "cost_center_id", "string", functions)
    return selected.select(
        _hash_key(
            functions,
            enterprise_slug,
            report_type,
            report_day,
            organization_login,
            user_login,
            product,
            sku,
            model,
            unit_type,
            cost_center_id,
        ).alias("billing_usage_key"),
        report_day.alias("report_day"),
        report_type.alias("report_type"),
        enterprise_slug.alias("enterprise_slug"),
        organization_login.alias("organization_login"),
        user_login.alias("user_login"),
        product.alias("product"),
        sku.alias("sku"),
        model.alias("model"),
        unit_type.alias("unit_type"),
        *[
            _optional_column(selected, column_name, "decimal(38,12)", functions).alias(
                column_name
            )
            for column_name in (
                "price_per_unit",
                "gross_quantity",
                "gross_amount",
                "discount_quantity",
                "discount_amount",
                "net_quantity",
                "net_amount",
            )
        ],
        cost_center_id.alias("cost_center_id"),
        _optional_column(selected, "cost_center_name", "string", functions).alias(
            "cost_center_name"
        ),
        *_lineage_expressions(functions),
    )


def _enterprise_frame(prepared, functions):
    selected = prepared.where(functions.col("_report_type") == "enterprise")
    enterprise_id = _json_string("$.enterprise_id", functions)
    active_count_names = [
        column_name
        for column_name, _ in TABLE_DEFINITIONS["enterprise_usage_daily"]["columns"]
        if column_name.startswith(("daily_", "weekly_", "monthly_"))
    ]
    return selected.select(
        _hash_key(functions, enterprise_id, functions.col("_report_day")).alias(
            "enterprise_usage_key"
        ),
        functions.col("_report_day").alias("report_day"),
        _optional_column(selected, "enterprise_slug", "string", functions).alias(
            "enterprise_slug"
        ),
        enterprise_id.alias("enterprise_id"),
        *[
            _json_long(f"$.{column_name}", functions).alias(column_name)
            for column_name in active_count_names
        ],
        *_activity_expressions(functions),
        *_surface_expressions(functions),
        *_pull_request_expressions(functions),
        *_breakdown_expressions(functions),
        _json_object("$.totals_by_ai_adoption_phase", functions).alias(
            "totals_by_ai_adoption_phase_json"
        ),
        *_lineage_expressions(functions),
    )


def _user_frame(prepared, functions):
    selected = prepared.where(functions.col("_report_type") == "users")
    enterprise_id = _json_string("$.enterprise_id", functions)
    user_id = functions.coalesce(
        _optional_column(selected, "user_id", "long", functions),
        _json_long("$.user_id", functions),
    )
    return selected.select(
        _hash_key(
            functions, enterprise_id, functions.col("_report_day"), user_id
        ).alias("user_usage_key"),
        functions.col("_report_day").alias("report_day"),
        _optional_column(selected, "enterprise_slug", "string", functions).alias(
            "enterprise_slug"
        ),
        enterprise_id.alias("enterprise_id"),
        user_id.alias("user_id"),
        functions.coalesce(
            _optional_column(selected, "user_login", "string", functions),
            _json_string("$.user_login", functions),
        ).alias("user_login"),
        _json_decimal("$.ai_credits_used", functions).alias("ai_credits_used"),
        *[
            _json_long(f"$.{column_name}", functions).alias(column_name)
            for column_name, _ in USER_CUSTOMIZATION_COLUMNS
        ],
        *_activity_expressions(functions),
        *[
            _json_boolean(f"$.{column_name}", functions).alias(column_name)
            for column_name in (
                "used_agent",
                "used_chat",
                "used_cli",
                "used_copilot_app",
                "used_copilot_cloud_agent",
                "used_copilot_coding_agent",
                "used_copilot_code_review_active",
                "used_copilot_code_review_passive",
            )
        ],
        _json_int("$.ai_adoption_phase.phase_number", functions).alias(
            "ai_adoption_phase_number"
        ),
        _json_string("$.ai_adoption_phase.phase", functions).alias(
            "ai_adoption_phase"
        ),
        _json_string("$.ai_adoption_phase.version", functions).alias(
            "ai_adoption_phase_version"
        ),
        *_surface_expressions(functions),
        _json_string(
            "$.totals_by_cli.last_known_cli_version.cli_version", functions
        ).alias("last_known_cli_version"),
        _json_timestamp(
            "$.totals_by_cli.last_known_cli_version.sampled_at", functions
        ).alias("last_known_cli_version_sampled_at"),
        *_breakdown_expressions(functions),
        *_lineage_expressions(functions),
    )


def _repository_frame(prepared, functions):
    selected = prepared.where(functions.col("_report_type") == "repositories")
    enterprise_id = _json_string("$.enterprise_id", functions)
    repository_id = functions.coalesce(
        _optional_column(selected, "repository_id", "long", functions),
        _json_long("$.repo_id", functions),
    )
    owner = _json_string("$.repo_owner_name", functions)
    name = _json_string("$.repo_name", functions)
    return selected.select(
        _hash_key(
            functions,
            enterprise_id,
            functions.col("_report_day"),
            repository_id,
        ).alias("repository_usage_key"),
        functions.col("_report_day").alias("report_day"),
        _optional_column(selected, "enterprise_slug", "string", functions).alias(
            "enterprise_slug"
        ),
        enterprise_id.alias("enterprise_id"),
        _json_string("$.organization_id", functions).alias("organization_id"),
        repository_id.alias("repository_id"),
        owner.alias("repository_owner"),
        name.alias("repository_name"),
        functions.concat_ws("/", owner, name).alias("repository_full_name"),
        functions.lower(_json_string("$.repo_visibility", functions)).alias(
            "repository_visibility"
        ),
        *_pull_request_expressions(functions),
        *_lineage_expressions(functions),
    )


def _user_team_frame(prepared, functions):
    selected = prepared.where(functions.col("_report_type") == "user_teams")
    enterprise_id = _json_string("$.enterprise_id", functions)
    user_id = functions.coalesce(
        _optional_column(selected, "user_id", "long", functions),
        _json_long("$.user_id", functions),
    )
    team_id = functions.coalesce(
        _optional_column(selected, "team_id", "long", functions),
        _json_long("$.team_id", functions),
    )
    return selected.select(
        _hash_key(
            functions,
            enterprise_id,
            functions.col("_report_day"),
            user_id,
            team_id,
        ).alias("user_team_membership_key"),
        functions.col("_report_day").alias("report_day"),
        _optional_column(selected, "enterprise_slug", "string", functions).alias(
            "enterprise_slug"
        ),
        enterprise_id.alias("enterprise_id"),
        _json_string("$.organization_id", functions).alias("organization_id"),
        user_id.alias("user_id"),
        functions.coalesce(
            _optional_column(selected, "user_login", "string", functions),
            _json_string("$.user_login", functions),
        ).alias("user_login"),
        team_id.alias("team_id"),
        functions.coalesce(
            _optional_column(selected, "team_slug", "string", functions),
            _json_string("$.slug", functions),
        ).alias("team_slug"),
        *_lineage_expressions(functions),
    )


def _quarantine_frame(prepared, functions):
    invalid = prepared.where(functions.col("_reason").isNotNull())
    quarantine_material = functions.concat_ws(
        "|",
        functions.col("_source"),
        functions.coalesce(functions.col("_report_type"), functions.lit("")),
        functions.coalesce(
            functions.col("_report_day").cast("string"), functions.lit("")
        ),
        functions.coalesce(functions.col("_bronze_object_path"), functions.lit("")),
        functions.col("_reason"),
    )
    return invalid.select(
        functions.sha2(quarantine_material, 256).alias("quarantine_id"),
        functions.col("_source").alias("source"),
        functions.col("_report_type").alias("report_type"),
        functions.col("_report_day").alias("report_day"),
        functions.col("_collection_date").alias("collection_date"),
        functions.col("_reason").alias("reason"),
        functions.col("raw_payload").alias("raw_payload"),
        functions.col("_bronze_object_path").alias("bronze_object_path"),
        functions.col("_processing_run_id").alias("processing_run_id"),
        functions.current_timestamp().alias("quarantined_at"),
    ).dropDuplicates(["quarantine_id"])


def _latest_batch(frame, table_name, functions, window_type):
    definition = TABLE_DEFINITIONS[table_name]
    selection_window = window_type.partitionBy(definition["key"]).orderBy(
        functions.col("collection_date").desc(),
        functions.col("collected_at").desc(),
        functions.col("bronze_object_path").desc(),
    )
    return (
        frame.withColumn("_snapshot_rank", functions.row_number().over(selection_window))
        .where(functions.col("_snapshot_rank") == 1)
        .drop("_snapshot_rank")
    )


def _merge_frame(frame, spark, database_name, table_name):
    source_view = f"incoming_{table_name}_{uuid.uuid4().hex}"
    columns = [column_name for column_name, _ in TABLE_DEFINITIONS[table_name]["columns"]]
    materialized = frame.select(*columns).localCheckpoint(eager=True)
    materialized.createOrReplaceTempView(source_view)
    try:
        spark.sql(merge_sql(database_name, table_name, source_view))
    finally:
        spark.catalog.dropTempView(source_view)
        materialized.unpersist()


def _read_json_source(
    glue_context,
    populated_paths,
    transformation_context,
    use_bookmark,
):
    kwargs = {
        "connection_type": "s3",
        "connection_options": {"paths": populated_paths, "recurse": True},
        "format": "json",
        "format_options": {"multiline": False},
    }
    if use_bookmark:
        kwargs["transformation_ctx"] = transformation_context
    return glue_context.create_dynamic_frame.from_options(**kwargs).toDF()


def _emit_metrics(environment, metrics):
    import boto3

    boto3.client("cloudwatch").put_metric_data(
        Namespace="GitHubDataLake/CopilotSilver",
        MetricData=[
            {
                "MetricName": metric_name,
                "Dimensions": [{"Name": "Environment", "Value": environment}],
                "Unit": "Count",
                "Value": metric_value,
            }
            for metric_name, metric_value in metrics.items()
        ],
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
        ensure_table(
            spark,
            arguments.silver_database,
            table_name,
            table_location(arguments, table_name),
        )

    s3_client = boto3.client("s3")
    requested_sources = (
        (
            "billing",
            arguments.billing_bronze_path,
            BILLING_TRANSFORMATION_CONTEXT,
        ),
        ("usage", arguments.usage_bronze_path, USAGE_TRANSFORMATION_CONTEXT),
    )
    processing_run_id = arguments.JOB_RUN_ID or str(uuid.uuid4())
    prepared_sources = {}
    metrics = {"BillingSourceRows": 0, "UsageSourceRows": 0}
    for source_name, bronze_path, transformation_context in requested_sources:
        populated_paths = paths_with_objects(
            source_paths(bronze_path, arguments.start_date, arguments.end_date),
            s3_client,
        )
        if not populated_paths:
            continue
        source = _read_json_source(
            glue_context,
            populated_paths,
            transformation_context,
            not arguments.start_date,
        )
        source_count = source.count()
        metrics[f"{source_name.title()}SourceRows"] = source_count
        if source_count:
            prepared_sources[source_name] = _with_reason(
                _prepare_base(source, source_name, processing_run_id, functions),
                functions,
            ).cache()

    if not prepared_sources:
        _emit_metrics(arguments.environment, metrics)
        job.commit()
        return metrics

    quarantine = None
    for prepared in prepared_sources.values():
        invalid = _quarantine_frame(prepared, functions)
        quarantine = (
            invalid
            if quarantine is None
            else quarantine.unionByName(invalid, allowMissingColumns=False)
        )
    quarantine = quarantine.cache()
    quarantine_count = quarantine.count()
    metrics["QuarantinedRows"] = quarantine_count
    if quarantine_count:
        _merge_frame(
            quarantine,
            spark,
            arguments.silver_database,
            "quarantined_records",
        )

    table_frames = {}
    if "billing" in prepared_sources:
        eligible_billing = prepared_sources["billing"].where(
            functions.col("_reason").isNull()
        )
        table_frames["billing_usage_daily"] = _billing_frame(
            eligible_billing, functions
        )
    if "usage" in prepared_sources:
        eligible_usage = prepared_sources["usage"].where(
            functions.col("_reason").isNull()
        )
        table_frames.update(
            {
                "enterprise_usage_daily": _enterprise_frame(
                    eligible_usage, functions
                ),
                "user_usage_daily": _user_frame(eligible_usage, functions),
                "repository_usage_daily": _repository_frame(
                    eligible_usage, functions
                ),
                "user_team_memberships_daily": _user_team_frame(
                    eligible_usage, functions
                ),
            }
        )

    for table_name, frame in table_frames.items():
        latest = _latest_batch(frame, table_name, functions, Window).cache()
        row_count = latest.count()
        metrics[f"{table_name.title().replace('_', '')}Rows"] = row_count
        if row_count:
            _merge_frame(latest, spark, arguments.silver_database, table_name)
        latest.unpersist()

    for prepared in prepared_sources.values():
        prepared.unpersist()
    quarantine.unpersist()
    _emit_metrics(arguments.environment, metrics)
    job.commit()
    return metrics


if __name__ == "__main__":
    run()