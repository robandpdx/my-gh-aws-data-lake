import json
import os
import uuid
from datetime import datetime, timezone


SOURCE_BUCKET = os.environ.get("SOURCE_BUCKET", "")
DESTINATION_QUEUE_URL = os.environ.get("DESTINATION_QUEUE_URL", "")
MAX_OBJECTS_PER_INVOCATION = 10_000

_clients = {}


def _client(service_name):
    if service_name not in _clients:
        import boto3

        _clients[service_name] = boto3.client(service_name)
    return _clients[service_name]


def _eventbridge_message(source_object):
    object_detail = {
        "key": source_object["key"],
        "size": source_object.get("size"),
    }
    if source_object.get("version_id"):
        object_detail["version-id"] = source_object["version_id"]
    return {
        "version": "0",
        "id": str(uuid.uuid4()),
        "detail-type": "Object Created",
        "source": "aws.s3",
        "time": datetime.now(timezone.utc).isoformat(),
        "detail": {
            "reason": "audit-log-replay",
            "bucket": {"name": SOURCE_BUCKET},
            "object": object_detail,
        },
    }


def _send_objects(source_objects):
    sent = 0
    for offset in range(0, len(source_objects), 10):
        batch = source_objects[offset : offset + 10]
        response = _client("sqs").send_message_batch(
            QueueUrl=DESTINATION_QUEUE_URL,
            Entries=[
                {
                    "Id": str(index),
                    "MessageBody": json.dumps(_eventbridge_message(source_object), separators=(",", ":")),
                }
                for index, source_object in enumerate(batch)
            ],
        )
        failures = response.get("Failed", [])
        if failures:
            failure_codes = sorted({failure.get("Code", "Unknown") for failure in failures})
            raise RuntimeError(f"SQS rejected {len(failures)} replay message(s): {failure_codes}")
        sent += len(batch)
    return sent


def _validate_explicit_objects(objects):
    validated = []
    for source_object in objects:
        key = source_object.get("key")
        if not isinstance(key, str) or not key.endswith(".json.log.gz"):
            raise ValueError("Each replay object key must end with .json.log.gz")
        validated.append(
            {
                "key": key,
                "size": source_object.get("size"),
                "version_id": source_object.get("version_id"),
            }
        )
    return validated


def _list_objects(event, max_objects):
    prefix = event.get("prefix", "")
    start_after = event.get("start_after")
    end_key = event.get("end_key")
    continuation_token = event.get("continuation_token")
    objects = []
    reached_end = False

    while len(objects) < max_objects:
        request = {
            "Bucket": SOURCE_BUCKET,
            "Prefix": prefix,
            "MaxKeys": min(1000, max_objects - len(objects)),
        }
        if continuation_token:
            request["ContinuationToken"] = continuation_token
        elif start_after:
            request["StartAfter"] = start_after

        response = _client("s3").list_objects_v2(**request)
        for source_object in response.get("Contents", []):
            key = source_object["Key"]
            if end_key and key > end_key:
                reached_end = True
                break
            if key.endswith(".json.log.gz"):
                objects.append({"key": key, "size": source_object.get("Size")})

        if reached_end or not response.get("IsTruncated"):
            continuation_token = None
            break
        continuation_token = response.get("NextContinuationToken")

    return objects, continuation_token


def lambda_handler(event, context):
    del context
    requested_max = int(event.get("max_objects", 1000))
    if requested_max < 1 or requested_max > MAX_OBJECTS_PER_INVOCATION:
        raise ValueError(f"max_objects must be between 1 and {MAX_OBJECTS_PER_INVOCATION}")

    if "objects" in event:
        source_objects = _validate_explicit_objects(event["objects"])
        continuation_token = None
    else:
        source_objects, continuation_token = _list_objects(event, requested_max)

    sent = _send_objects(source_objects)
    print(
        json.dumps(
            {
                "level": "INFO",
                "event": "audit_log_replay_enqueued",
                "objects_enqueued": sent,
                "has_more": continuation_token is not None,
            },
            separators=(",", ":"),
        )
    )
    return {
        "objects_enqueued": sent,
        "continuation_token": continuation_token,
    }