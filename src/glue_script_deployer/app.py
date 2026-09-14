import json
import os
from pathlib import Path
from urllib.request import Request, urlopen


SOURCE_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATHS = {
    "webhook_silver": SOURCE_ROOT / "webhook_silver" / "job.py",
    "copilot_silver": SOURCE_ROOT / "copilot_silver" / "job.py",
}

_clients = {}


def _client(service_name):
    if service_name not in _clients:
        import boto3

        _clients[service_name] = boto3.client(service_name)
    return _clients[service_name]


def _publish_script(bucket, key, script_name="webhook_silver"):
    try:
        script_path = SCRIPT_PATHS[script_name]
    except KeyError as error:
        raise ValueError(f"Unsupported Glue script: {script_name}") from error
    _client("s3").put_object(
        Bucket=bucket,
        Key=key,
        Body=script_path.read_bytes(),
        ContentType="text/x-python",
        ServerSideEncryption="AES256",
    )


def _delete_script(bucket, key):
    _client("s3").delete_object(Bucket=bucket, Key=key)


def _send_response(event, context, status, physical_resource_id, reason=None):
    response = {
        "Status": status,
        "Reason": reason or f"See CloudWatch log stream {context.log_stream_name}",
        "PhysicalResourceId": physical_resource_id,
        "StackId": event["StackId"],
        "RequestId": event["RequestId"],
        "LogicalResourceId": event["LogicalResourceId"],
        "NoEcho": False,
        "Data": {},
    }
    body = json.dumps(response).encode("utf-8")
    request = Request(
        event["ResponseURL"],
        data=body,
        method="PUT",
        headers={"content-type": "", "content-length": str(len(body))},
    )
    with urlopen(request, timeout=10) as response_stream:
        response_stream.read()


def lambda_handler(event, context):
    properties = event["ResourceProperties"]
    bucket = properties["BucketName"]
    key = properties["ScriptKey"]
    script_name = properties.get("ScriptName", "webhook_silver")
    physical_resource_id = f"s3://{bucket}/{key}"

    try:
        if event["RequestType"] == "Delete":
            _delete_script(bucket, key)
        else:
            _publish_script(bucket, key, script_name)
            if event["RequestType"] == "Update":
                old_properties = event.get("OldResourceProperties", {})
                old_bucket = old_properties.get("BucketName")
                old_key = old_properties.get("ScriptKey")
                if old_bucket and old_key and (old_bucket, old_key) != (bucket, key):
                    _delete_script(old_bucket, old_key)
    except Exception as error:
        _send_response(
            event,
            context,
            "FAILED",
            physical_resource_id,
            f"{type(error).__name__}: {error}",
        )
        raise

    _send_response(event, context, "SUCCESS", physical_resource_id)
    return {"PhysicalResourceId": physical_resource_id}
