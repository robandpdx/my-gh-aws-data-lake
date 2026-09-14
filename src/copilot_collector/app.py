import base64
import gzip
import hashlib
import json
import os
import tempfile
import time
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen


GITHUB_API_VERSION = "2026-03-10"
BILLING_ENDPOINTS = {
    "ai_credit": "/enterprises/{enterprise}/settings/billing/ai_credit/usage",
    "premium_request": "/enterprises/{enterprise}/settings/billing/premium_request/usage",
}
USAGE_ENDPOINTS = {
    "enterprise": "/enterprises/{enterprise}/copilot/metrics/reports/enterprise-1-day",
    "users": "/enterprises/{enterprise}/copilot/metrics/reports/users-1-day",
    "repositories": "/enterprises/{enterprise}/copilot/metrics/reports/repos-1-day",
    "user_teams": "/enterprises/{enterprise}/copilot/metrics/reports/user-teams-1-day",
}
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

_clients = {}


def _client(service_name):
    if service_name not in _clients:
        import boto3

        _clients[service_name] = boto3.client(service_name)
    return _clients[service_name]


def _secret_credentials(secret_arn, secrets_client):
    response = secrets_client.get_secret_value(SecretId=secret_arn)
    if "SecretString" in response:
        secret_value = response["SecretString"]
    else:
        secret_value = base64.b64decode(response["SecretBinary"]).decode("utf-8")
    credentials = json.loads(secret_value)
    required_fields = ("app_id", "installation_id", "private_key")
    missing = [field for field in required_fields if not credentials.get(field)]
    if missing:
        raise ValueError(
            f"GitHub App secret is missing required field(s): {', '.join(missing)}"
        )
    return credentials


def _create_app_jwt(credentials, now_epoch=None):
    from jose import jwt

    now_epoch = int(now_epoch or time.time())
    return jwt.encode(
        {
            "iat": now_epoch - 60,
            "exp": now_epoch + 540,
            "iss": str(credentials["app_id"]),
        },
        credentials["private_key"],
        algorithm="RS256",
    )


def _request_bytes(url, headers=None, method="GET", payload=None):
    request_body = None
    request_headers = dict(headers or {})
    if payload is not None:
        request_body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        request_headers["Content-Type"] = "application/json"

    for attempt in range(4):
        request = Request(
            url,
            data=request_body,
            headers=request_headers,
            method=method,
        )
        try:
            with urlopen(request, timeout=60) as response:
                return response.status, dict(response.headers), response.read()
        except HTTPError as error:
            error_body = error.read(2048).decode("utf-8", errors="replace")
            if error.code not in RETRYABLE_STATUS_CODES or attempt == 3:
                raise RuntimeError(
                    f"GitHub request failed with HTTP {error.code}: {error_body}"
                ) from error
            retry_after = error.headers.get("Retry-After")
            delay = int(retry_after) if retry_after and retry_after.isdigit() else 2**attempt
            time.sleep(delay)
        except URLError as error:
            if attempt == 3:
                raise RuntimeError("GitHub request failed after retries") from error
            time.sleep(2**attempt)


def _github_request(path, token, method="GET", payload=None):
    base_url = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
    return _request_bytes(
        f"{base_url}{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "github-copilot-data-lake-collector",
            "X-GitHub-Api-Version": os.environ.get(
                "GITHUB_API_VERSION", GITHUB_API_VERSION
            ),
        },
        method=method,
        payload=payload,
    )


def _installation_token(credentials):
    app_jwt = _create_app_jwt(credentials)
    installation_id = quote(str(credentials["installation_id"]), safe="")
    status, _, body = _github_request(
        f"/app/installations/{installation_id}/access_tokens",
        app_jwt,
        method="POST",
        payload={},
    )
    if status != 201:
        raise RuntimeError(f"GitHub installation token request returned HTTP {status}")
    token = json.loads(body).get("token")
    if not token:
        raise RuntimeError("GitHub installation token response did not contain a token")
    return token


def _validate_task(task):
    source = task.get("source")
    report_type = task.get("report_type")
    if source == "billing":
        valid_types = BILLING_ENDPOINTS
    elif source == "usage":
        valid_types = USAGE_ENDPOINTS
    else:
        raise ValueError("collection task source must be billing or usage")
    if report_type not in valid_types:
        raise ValueError(f"unsupported {source} report type: {report_type}")
    report_day = date.fromisoformat(task["report_day"]).isoformat()
    collection_date = date.fromisoformat(task["collection_date"]).isoformat()
    return {
        "source": source,
        "report_type": report_type,
        "report_day": report_day,
        "collection_date": collection_date,
    }


def _collection_id(task):
    return ":".join(
        (
            task["source"],
            task["report_type"],
            task["report_day"],
            task["collection_date"],
        )
    )


def _put_bytes(s3_client, bucket, key, body, content_type):
    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=body,
        ContentType=content_type,
        ServerSideEncryption="AES256",
        Metadata={"sha256": hashlib.sha256(body).hexdigest()},
    )


def _upload_file(s3_client, bucket, key, path, content_type):
    s3_client.upload_file(
        str(path),
        bucket,
        key,
        ExtraArgs={
            "ContentType": content_type,
            "ServerSideEncryption": "AES256",
        },
    )


def _bronze_key(task):
    report_day = date.fromisoformat(task["report_day"])
    return (
        f"bronze/copilot/{task['source']}/year={report_day.year:04d}/"
        f"month={report_day.month:02d}/day={report_day.day:02d}/"
        f"report_type={task['report_type']}/"
        f"collection-{task['collection_date']}.ndjson"
    )


def _raw_prefix(task):
    return (
        f"raw/copilot/{task['source']}/report_type={task['report_type']}/"
        f"report_day={task['report_day']}/collection_date={task['collection_date']}"
    )


def _coalesce(mapping, *keys):
    for key in keys:
        value = mapping.get(key)
        if value is not None:
            return value
    return None


def _billing_record(task, response, item, collected_at):
    cost_center = item.get("costCenter") or response.get("costCenter") or {}
    return {
        "collection_id": _collection_id(task),
        "collection_date": task["collection_date"],
        "collected_at": collected_at,
        "enterprise_slug": os.environ["GITHUB_ENTERPRISE_SLUG"],
        "report_day": task["report_day"],
        "organization_login": _coalesce(
            item, "organization", "organizationName"
        )
        or response.get("organization"),
        "user_login": item.get("user") or response.get("user"),
        "product": item.get("product"),
        "sku": item.get("sku"),
        "model": item.get("model") or response.get("model"),
        "unit_type": item.get("unitType"),
        "price_per_unit": item.get("pricePerUnit"),
        "gross_quantity": item.get("grossQuantity"),
        "gross_amount": item.get("grossAmount"),
        "discount_quantity": item.get("discountQuantity"),
        "discount_amount": item.get("discountAmount"),
        "net_quantity": item.get("netQuantity"),
        "net_amount": item.get("netAmount"),
        "cost_center_id": cost_center.get("id"),
        "cost_center_name": cost_center.get("name"),
        "raw_payload": json.dumps(item, separators=(",", ":"), sort_keys=True),
    }


def _usage_record(task, record, record_index, collected_at):
    user = record.get("user") if isinstance(record.get("user"), dict) else {}
    organization = (
        record.get("organization")
        if isinstance(record.get("organization"), dict)
        else {}
    )
    repository = (
        record.get("repository")
        if isinstance(record.get("repository"), dict)
        else {}
    )
    team = record.get("team") if isinstance(record.get("team"), dict) else {}
    canonical_payload = json.dumps(record, separators=(",", ":"), sort_keys=True)
    return {
        "collection_id": _collection_id(task),
        "collection_date": task["collection_date"],
        "collected_at": collected_at,
        "enterprise_slug": os.environ["GITHUB_ENTERPRISE_SLUG"],
        "report_day": task["report_day"],
        "record_index": record_index,
        "record_id": hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest(),
        "user_id": _coalesce(record, "user_id", "userId") or user.get("id"),
        "user_login": _coalesce(record, "user_login", "login") or user.get("login"),
        "organization_id": _coalesce(record, "organization_id", "org_id")
        or organization.get("id"),
        "organization_login": _coalesce(
            record, "organization_login", "org_login", "org"
        )
        or organization.get("login"),
        "repository_id": _coalesce(record, "repository_id", "repo_id")
        or repository.get("id"),
        "repository_full_name": _coalesce(
            record, "repository_full_name", "repo_full_name"
        )
        or repository.get("full_name"),
        "team_id": record.get("team_id") or team.get("id"),
        "team_slug": record.get("team_slug") or team.get("slug"),
        "raw_payload": canonical_payload,
    }


def _serialize_ndjson(records):
    return b"".join(
        json.dumps(record, separators=(",", ":"), sort_keys=True).encode("utf-8")
        + b"\n"
        for record in records
    )


def _collect_billing(task, token, s3_client, bucket, collected_at):
    endpoint = BILLING_ENDPOINTS[task["report_type"]].format(
        enterprise=quote(os.environ["GITHUB_ENTERPRISE_SLUG"], safe="")
    )
    report_day = date.fromisoformat(task["report_day"])
    query = urlencode(
        {"year": report_day.year, "month": report_day.month, "day": report_day.day}
    )
    status, _, body = _github_request(f"{endpoint}?{query}", token)
    if status != 200:
        raise RuntimeError(f"GitHub billing report returned HTTP {status}")
    response = json.loads(body)
    records = [
        _billing_record(task, response, item, collected_at)
        for item in response.get("usageItems", [])
    ]
    _put_bytes(
        s3_client,
        bucket,
        f"{_raw_prefix(task)}/response.json",
        body,
        "application/json",
    )
    _put_bytes(
        s3_client,
        bucket,
        _bronze_key(task),
        _serialize_ndjson(records),
        "application/x-ndjson",
    )
    return len(records)


def _download_to_path(url, path):
    parsed_url = urlparse(url)
    if parsed_url.scheme != "https" or not parsed_url.hostname:
        raise ValueError("Copilot usage report URL must use HTTPS")
    maximum_bytes = int(os.environ.get("MAX_REPORT_BYTES", str(1024 * 1024 * 1024)))
    for attempt in range(4):
        request = Request(
            url,
            headers={"User-Agent": "github-copilot-data-lake-collector"},
            method="GET",
        )
        total_bytes = 0
        try:
            with urlopen(request, timeout=120) as response, path.open("wb") as output:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        return
                    total_bytes += len(chunk)
                    if total_bytes > maximum_bytes:
                        raise ValueError(
                            "Copilot usage report exceeded MAX_REPORT_BYTES"
                        )
                    output.write(chunk)
        except HTTPError as error:
            if error.code not in RETRYABLE_STATUS_CODES or attempt == 3:
                raise RuntimeError("Copilot usage report download failed") from error
            retry_after = error.headers.get("Retry-After")
            delay = int(retry_after) if retry_after and retry_after.isdigit() else 2**attempt
            time.sleep(min(delay, 60))
        except URLError as error:
            if attempt == 3:
                raise RuntimeError("Copilot usage report download failed") from error
            time.sleep(2**attempt)


def _is_gzip(path):
    with path.open("rb") as stream:
        return stream.read(2) == b"\x1f\x8b"


def _iter_report_records(path):
    opener = gzip.open if _is_gzip(path) else open
    with opener(path, "rt", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if line.strip():
                try:
                    yield json.loads(line)
                except json.JSONDecodeError as error:
                    raise ValueError(
                        f"invalid NDJSON in usage report at line {line_number}"
                    ) from error


def _collect_usage(task, token, s3_client, bucket, collected_at):
    endpoint = USAGE_ENDPOINTS[task["report_type"]].format(
        enterprise=quote(os.environ["GITHUB_ENTERPRISE_SLUG"], safe="")
    )
    status, _, body = _github_request(
        f"{endpoint}?{urlencode({'day': task['report_day']})}", token
    )
    no_data = status == 204
    if no_data:
        response = {"download_links": [], "report_day": task["report_day"]}
    elif status == 200:
        response = json.loads(body)
        if response == "":
            no_data = True
            response = {"download_links": [], "report_day": task["report_day"]}
        elif not isinstance(response, dict):
            raise ValueError("GitHub usage report response must be a JSON object")
    else:
        raise RuntimeError(f"GitHub usage report returned HTTP {status}")

    download_links = response.get("download_links", [])
    if not isinstance(download_links, list) or not all(
        isinstance(download_link, str) for download_link in download_links
    ):
        raise ValueError("GitHub usage report download_links must be a string array")
    manifest = {
        "collection_id": _collection_id(task),
        "collected_at": collected_at,
        "enterprise_slug": os.environ["GITHUB_ENTERPRISE_SLUG"],
        "no_data": no_data,
        "report_day": task["report_day"],
        "report_type": task["report_type"],
        "part_count": len(download_links),
    }
    _put_bytes(
        s3_client,
        bucket,
        f"{_raw_prefix(task)}/manifest.json",
        json.dumps(manifest, separators=(",", ":"), sort_keys=True).encode("utf-8"),
        "application/json",
    )

    record_count = 0
    with tempfile.TemporaryDirectory() as directory:
        directory_path = Path(directory)
        bronze_path = directory_path / "records.ndjson"
        with bronze_path.open("wb") as bronze_output:
            for part_index, download_link in enumerate(download_links):
                raw_path = directory_path / f"part-{part_index:03d}"
                _download_to_path(download_link, raw_path)
                compressed = _is_gzip(raw_path)
                raw_key = (
                    f"{_raw_prefix(task)}/part-{part_index:03d}.ndjson"
                    + (".gz" if compressed else "")
                )
                _upload_file(
                    s3_client,
                    bucket,
                    raw_key,
                    raw_path,
                    "application/gzip" if compressed else "application/x-ndjson",
                )
                for record in _iter_report_records(raw_path):
                    normalized = _usage_record(
                        task, record, record_count, collected_at
                    )
                    bronze_output.write(
                        json.dumps(
                            normalized, separators=(",", ":"), sort_keys=True
                        ).encode("utf-8")
                        + b"\n"
                    )
                    record_count += 1
        _upload_file(
            s3_client,
            bucket,
            _bronze_key(task),
            bronze_path,
            "application/x-ndjson",
        )
    return record_count


def _emit_metric(task, record_count):
    dimensions = [
        {"Name": "Environment", "Value": os.environ["ENVIRONMENT"]},
        {"Name": "Source", "Value": task["source"]},
        {"Name": "ReportType", "Value": task["report_type"]},
    ]
    try:
        _client("cloudwatch").put_metric_data(
            Namespace="GitHubDataLake/Copilot",
            MetricData=[
                {
                    "MetricName": "RecordsCollected",
                    "Dimensions": dimensions,
                    "Unit": "Count",
                    "Value": record_count,
                },
                {
                    "MetricName": "ReportsCollected",
                    "Dimensions": dimensions,
                    "Unit": "Count",
                    "Value": 1,
                },
            ],
        )
    except Exception as error:
        print(
            json.dumps(
                {
                    "level": "WARNING",
                    "event": "copilot_metric_publish_failed",
                    "error_type": type(error).__name__,
                },
                separators=(",", ":"),
            )
        )


def collect_task(task, token, collected_at=None):
    task = _validate_task(task)
    collected_at = collected_at or datetime.now(timezone.utc).isoformat()
    s3_client = _client("s3")
    bucket = os.environ["DATA_LAKE_BUCKET"]
    if task["source"] == "billing":
        record_count = _collect_billing(
            task, token, s3_client, bucket, collected_at
        )
    else:
        record_count = _collect_usage(
            task, token, s3_client, bucket, collected_at
        )
    _emit_metric(task, record_count)
    print(
        json.dumps(
            {
                "event": "copilot_report_collected",
                "source": task["source"],
                "report_type": task["report_type"],
                "report_day": task["report_day"],
                "record_count": record_count,
            },
            separators=(",", ":"),
        )
    )
    return record_count


def lambda_handler(event, context):
    credentials = _secret_credentials(
        os.environ["GITHUB_APP_SECRET_ARN"], _client("secretsmanager")
    )
    token = _installation_token(credentials)
    failures = []
    for record in event.get("Records", []):
        try:
            collect_task(json.loads(record["body"]), token)
        except Exception as error:
            print(
                json.dumps(
                    {
                        "level": "ERROR",
                        "event": "copilot_report_collection_failed",
                        "message_id": record.get("messageId"),
                        "error_type": type(error).__name__,
                    },
                    separators=(",", ":"),
                )
            )
            failures.append({"itemIdentifier": record["messageId"]})
    return {"batchItemFailures": failures}