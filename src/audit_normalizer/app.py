import gzip
import hashlib
import json
import os
import time
import uuid
import zlib
from datetime import datetime, timezone
from urllib.parse import unquote


SOURCE_BUCKET = os.environ.get("SOURCE_BUCKET", "")
DESTINATION_STREAM_NAME = os.environ.get("DESTINATION_STREAM_NAME", "")
QUARANTINE_BUCKET = os.environ.get("QUARANTINE_BUCKET", "")
QUARANTINE_PREFIX = os.environ.get("QUARANTINE_PREFIX", "quarantine/audit-logs")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "dev")
SCHEMA_VERSION = int(os.environ.get("SCHEMA_VERSION", "1"))
MAX_COMPRESSED_BYTES = int(os.environ.get("MAX_COMPRESSED_BYTES", str(20 * 1024 * 1024)))
MAX_UNCOMPRESSED_BYTES = int(os.environ.get("MAX_UNCOMPRESSED_BYTES", str(100 * 1024 * 1024)))
MAX_FIREHOSE_RECORD_BYTES = 1_000_000
MAX_FIREHOSE_BATCH_BYTES = 4_000_000
MAX_FIREHOSE_BATCH_RECORDS = 500
FIREHOSE_MAX_ATTEMPTS = 3

_clients = {}


class RecordValidationError(ValueError):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def _client(service_name):
    if service_name not in _clients:
        import boto3

        _clients[service_name] = boto3.client(service_name)
    return _clients[service_name]


def _log(level, event, **fields):
    print(json.dumps({"level": level, "event": event, **fields}, separators=(",", ":")))


def _emit_metrics(metrics):
    definitions = [{"Name": name, "Unit": "Count"} for name in metrics]
    payload = {
        "_aws": {
            "Timestamp": int(time.time() * 1000),
            "CloudWatchMetrics": [
                {
                    "Namespace": "GitHubDataLake/AuditLogs",
                    "Dimensions": [["Environment"]],
                    "Metrics": definitions,
                }
            ],
        },
        "Environment": ENVIRONMENT,
        **metrics,
    }
    print(json.dumps(payload, separators=(",", ":")))


def _read_gzip_bounded(body):
    chunks = []
    total_bytes = 0
    with gzip.GzipFile(fileobj=body, mode="rb") as decompressed:
        while True:
            chunk = decompressed.read(1024 * 1024)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > MAX_UNCOMPRESSED_BYTES:
                raise RecordValidationError("uncompressed_object_too_large")
            chunks.append(chunk)
    return b"".join(chunks)


def _parse_json_records(raw_json):
    text = raw_json.decode("utf-8-sig")
    decoder = json.JSONDecoder()
    records = []
    offset = 0
    parsed_value = False

    while offset < len(text):
        while offset < len(text) and text[offset].isspace():
            offset += 1
        if offset == len(text):
            break

        value, offset = decoder.raw_decode(text, offset)
        parsed_value = True
        if isinstance(value, list):
            records.extend(value)
        else:
            records.append(value)

    if not parsed_value:
        raise json.JSONDecodeError("No JSON values found", text, 0)
    return records


def _parse_timestamp(value):
    if value is None or isinstance(value, bool):
        raise RecordValidationError("missing_event_timestamp")

    if isinstance(value, (int, float)):
        epoch_value = float(value)
    elif isinstance(value, str):
        stripped = value.strip()
        try:
            epoch_value = float(stripped)
        except ValueError:
            try:
                parsed = datetime.fromisoformat(stripped.replace("Z", "+00:00"))
            except ValueError as error:
                raise RecordValidationError("invalid_event_timestamp") from error
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
    else:
        raise RecordValidationError("invalid_event_timestamp")

    if abs(epoch_value) >= 100_000_000_000:
        epoch_value /= 1000.0
    try:
        return datetime.fromtimestamp(epoch_value, tz=timezone.utc)
    except (OverflowError, OSError, ValueError) as error:
        raise RecordValidationError("invalid_event_timestamp") from error


def _format_timestamp(value):
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _optional_string(value):
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    return None


def _optional_int(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return None


def _optional_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized == "true":
            return True
        if normalized == "false":
            return False
    return None


def _repository_name(event):
    repository = event.get("repository")
    if isinstance(repository, dict):
        repository = repository.get("full_name") or repository.get("name")
    return _optional_string(repository) or _optional_string(event.get("repo"))


def _copilot_record_type(event):
    record_type = _optional_string(event.get("type"))
    if (
        record_type in {"request", "response"}
        and _optional_string(event.get("event_id"))
        and _optional_string(event.get("endpoint"))
        and "body" in event
    ):
        return record_type
    return None


def _normalize_record(event, source, record_index, normalized_at):
    if not isinstance(event, dict):
        raise RecordValidationError("record_is_not_an_object")

    raw_payload = json.dumps(event, separators=(",", ":"), sort_keys=True, ensure_ascii=False)
    payload_sha256 = hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()
    event_id = _optional_string(event.get("event_id"))
    document_id = _optional_string(event.get("_document_id")) or event_id or payload_sha256
    event_timestamp = _parse_timestamp(event.get("@timestamp", event.get("created_at")))
    action = _optional_string(event.get("action"))
    action_parts = action.split(".", 1) if action else []
    copilot_record_type = _copilot_record_type(event)
    truncated = _optional_bool(event.get("truncated"))
    if copilot_record_type and truncated is None:
        truncated = False

    return {
        "document_id": document_id,
        "event_timestamp": _format_timestamp(event_timestamp),
        "action": action,
        "action_category": action_parts[0] if action_parts else None,
        "action_name": action_parts[1] if len(action_parts) == 2 else None,
        "operation_type": _optional_string(event.get("operation_type")),
        "actor": _optional_string(event.get("actor")),
        "actor_id": _optional_int(event.get("actor_id")),
        "actor_is_bot": _optional_bool(event.get("actor_is_bot")),
        "business": _optional_string(event.get("business")),
        "business_id": _optional_int(event.get("business_id")),
        "organization": _optional_string(event.get("org", event.get("organization"))),
        "organization_id": _optional_int(event.get("org_id", event.get("organization_id"))),
        "repository": _repository_name(event),
        "repository_id": _optional_int(event.get("repository_id", event.get("repo_id"))),
        "user": _optional_string(event.get("user")),
        "user_id": _optional_int(event.get("user_id")),
        "request_id": _optional_string(event.get("request_id")),
        "source_ip": _optional_string(event.get("actor_ip")),
        "user_agent": _optional_string(event.get("user_agent")),
        "programmatic_access_type": _optional_string(event.get("programmatic_access_type")),
        "request_method": _optional_string(event.get("request_method")),
        "route": _optional_string(event.get("route")),
        "status_code": _optional_int(event.get("status_code")),
        "url_path": _optional_string(event.get("url_path")),
        "pull_request_id": _optional_int(event.get("pull_request_id")),
        "workflow_run_id": _optional_int(event.get("workflow_run_id")),
        "raw_payload": raw_payload,
        "payload_sha256": payload_sha256,
        "source_bucket": source["bucket"],
        "source_object_key": source["key"],
        "source_object_version": source.get("version_id"),
        "source_record_index": record_index,
        "schema_version": SCHEMA_VERSION,
        "normalized_at": _format_timestamp(normalized_at),
        "record_family": "copilot_usage" if copilot_record_type else "audit",
        "copilot_record_type": copilot_record_type,
        "event_id": event_id,
        "github_request_id": _optional_string(event.get("github_request_id")),
        "enterprise_id": _optional_int(event.get("enterprise_id")),
        "endpoint": _optional_string(event.get("endpoint")),
        "truncated": truncated if copilot_record_type else None,
    }


def _quarantine(source, record_index, reason):
    now = datetime.now(timezone.utc)
    key = (
        f"{QUARANTINE_PREFIX.rstrip('/')}/year={now:%Y}/month={now:%m}/day={now:%d}/"
        f"reason={reason}/{uuid.uuid4()}.json"
    )
    body = json.dumps(
        {
            "reason": reason,
            "source_bucket": source.get("bucket"),
            "source_object_key": source.get("key"),
            "source_object_version": source.get("version_id"),
            "source_record_index": record_index,
            "quarantined_at": _format_timestamp(now),
        },
        separators=(",", ":"),
    ).encode("utf-8")
    _client("s3").put_object(
        Bucket=QUARANTINE_BUCKET,
        Key=key,
        Body=body,
        ContentType="application/json",
        ServerSideEncryption="AES256",
    )


def _firehose_batches(records):
    batch = []
    batch_bytes = 0
    for record in records:
        record_size = len(record)
        if batch and (
            len(batch) == MAX_FIREHOSE_BATCH_RECORDS
            or batch_bytes + record_size > MAX_FIREHOSE_BATCH_BYTES
        ):
            yield batch
            batch = []
            batch_bytes = 0
        batch.append(record)
        batch_bytes += record_size
    if batch:
        yield batch


def _put_firehose_records(records):
    for batch in _firehose_batches(records):
        pending = batch
        for attempt in range(FIREHOSE_MAX_ATTEMPTS):
            response = _client("firehose").put_record_batch(
                DeliveryStreamName=DESTINATION_STREAM_NAME,
                Records=[{"Data": record} for record in pending],
            )
            results = response.get("RequestResponses", [])
            failed = [
                record
                for record, result in zip(pending, results)
                if result.get("ErrorCode")
            ]
            if len(results) < len(pending):
                failed.extend(pending[len(results) :])
            if not failed:
                break
            pending = failed
            if attempt + 1 < FIREHOSE_MAX_ATTEMPTS:
                time.sleep(0.2 * (2**attempt))
        else:
            raise RuntimeError(f"Firehose rejected {len(pending)} record(s) after retries")


def _source_from_sqs_record(sqs_record):
    event = json.loads(sqs_record["body"])
    detail = event["detail"]
    bucket = detail["bucket"]["name"]
    if bucket != SOURCE_BUCKET:
        raise ValueError("Unexpected source bucket")
    object_detail = detail["object"]
    return {
        "bucket": bucket,
        "key": unquote(object_detail["key"]),
        "version_id": object_detail.get("version-id"),
        "size": _optional_int(object_detail.get("size")),
    }


def _process_sqs_record(sqs_record):
    source = _source_from_sqs_record(sqs_record)
    if source["size"] is not None and source["size"] > MAX_COMPRESSED_BYTES:
        _quarantine(source, None, "compressed_object_too_large")
        return {"SourceObjectsProcessed": 1, "RecordsNormalized": 0, "RecordsQuarantined": 1}

    request = {"Bucket": source["bucket"], "Key": source["key"]}
    if source.get("version_id"):
        request["VersionId"] = source["version_id"]

    response = _client("s3").get_object(**request)
    body = response["Body"]
    try:
        raw_json = _read_gzip_bounded(body)
        source_records = _parse_json_records(raw_json)
    except (
        gzip.BadGzipFile,
        EOFError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        RecordValidationError,
        zlib.error,
    ) as error:
        reason = error.reason if isinstance(error, RecordValidationError) else "invalid_gzip_or_json"
        _quarantine(source, None, reason)
        return {"SourceObjectsProcessed": 1, "RecordsNormalized": 0, "RecordsQuarantined": 1}
    finally:
        body.close()

    normalized_at = datetime.now(timezone.utc)
    firehose_records = []
    quarantined = 0
    for record_index, event in enumerate(source_records):
        try:
            normalized = _normalize_record(event, source, record_index, normalized_at)
            serialized = json.dumps(normalized, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n"
            if len(serialized) > MAX_FIREHOSE_RECORD_BYTES:
                raise RecordValidationError("normalized_record_too_large")
            firehose_records.append(serialized)
        except RecordValidationError as error:
            _quarantine(source, record_index, error.reason)
            quarantined += 1

    if firehose_records:
        _put_firehose_records(firehose_records)

    _log(
        "INFO",
        "source_object_processed",
        source_bucket=source["bucket"],
        source_object_key=source["key"],
        normalized_records=len(firehose_records),
        quarantined_records=quarantined,
    )
    return {
        "SourceObjectsProcessed": 1,
        "RecordsNormalized": len(firehose_records),
        "RecordsQuarantined": quarantined,
    }


def lambda_handler(event, context):
    del context
    failures = []
    metrics = {
        "SourceObjectsProcessed": 0,
        "SourceObjectsFailed": 0,
        "RecordsNormalized": 0,
        "RecordsQuarantined": 0,
    }
    for sqs_record in event.get("Records", []):
        message_id = sqs_record.get("messageId", "unknown")
        try:
            result = _process_sqs_record(sqs_record)
            for name, value in result.items():
                metrics[name] += value
        except Exception as error:
            metrics["SourceObjectsFailed"] += 1
            failures.append({"itemIdentifier": message_id})
            _log(
                "ERROR",
                "source_object_failed",
                message_id=message_id,
                error_type=type(error).__name__,
            )
    _emit_metrics(metrics)
    return {"batchItemFailures": failures}