import base64
import json
import os
import time
from datetime import date, datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


GITHUB_API_VERSION = "2026-03-10"
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_PAGES = 10000

_clients = {}


def _client(service_name):
    if service_name not in _clients:
        import boto3

        _clients[service_name] = boto3.client(service_name)
    return _clients[service_name]


def _secret_token(secret_arn, secrets_client):
    response = secrets_client.get_secret_value(SecretId=secret_arn)
    if "SecretString" in response:
        secret_value = response["SecretString"]
    else:
        secret_value = base64.b64decode(response["SecretBinary"]).decode("utf-8")
    credentials = json.loads(secret_value)
    token = credentials.get("token")
    if not isinstance(token, str) or not token.strip():
        raise ValueError("GitHub identity secret must contain a non-empty token")
    return token


def _request_json(path, token):
    base_url = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
    url = f"{base_url}{path}"
    for attempt in range(4):
        request = Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "User-Agent": "github-enterprise-identity-data-lake-collector",
                "X-GitHub-Api-Version": os.environ.get(
                    "GITHUB_API_VERSION", GITHUB_API_VERSION
                ),
            },
            method="GET",
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
            time.sleep(min(delay, 60))
        except URLError as error:
            if attempt == 3:
                raise RuntimeError("GitHub request failed after retries") from error
            time.sleep(2**attempt)


def _serialize_ndjson(records):
    return b"".join(
        json.dumps(record, separators=(",", ":"), sort_keys=True).encode("utf-8")
        + b"\n"
        for record in records
    )


def _put_bytes(s3_client, bucket, key, body, content_type):
    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=body,
        ContentType=content_type,
        ServerSideEncryption="AES256",
        Metadata={"record-format": "enterprise-identity-snapshot-v1"},
    )


def _user_record(user, snapshot_date, collected_at):
    login = user.get("github_com_login")
    return {
        "snapshot_date": snapshot_date,
        "collected_at": collected_at,
        "enterprise_slug": os.environ["GITHUB_ENTERPRISE_SLUG"],
        "github_login": login,
        "github_name": user.get("github_com_name"),
        "github_profile": user.get("github_com_profile"),
        "has_github_com_user": user.get("github_com_user"),
        "has_enterprise_server_user": user.get("enterprise_server_user"),
        "enterprise_server_user_ids": user.get("enterprise_server_user_ids") or [],
        "member_roles": user.get("github_com_member_roles") or [],
        "enterprise_roles": user.get("github_com_enterprise_roles") or [],
        "organizations_with_pending_invites": user.get(
            "github_com_orgs_with_pending_invites"
        )
        or [],
        "two_factor_authentication_enabled": user.get("github_com_two_factor_auth"),
    }


def _license_record(user, snapshot_date, collected_at):
    return {
        "snapshot_date": snapshot_date,
        "collected_at": collected_at,
        "enterprise_slug": os.environ["GITHUB_ENTERPRISE_SLUG"],
        "github_login": user.get("github_com_login"),
        "license_type": user.get("license_type"),
        "total_user_accounts": user.get("total_user_accounts"),
        "has_github_com_user": user.get("github_com_user"),
        "has_enterprise_server_user": user.get("enterprise_server_user"),
        "has_visual_studio_subscription": user.get(
            "visual_studio_subscription_user"
        ),
        "visual_studio_license_status": user.get("visual_studio_license_status"),
    }


def collect_snapshot(token, snapshot_date=None, collected_at=None):
    snapshot_date = date.fromisoformat(
        snapshot_date or datetime.now(timezone.utc).date().isoformat()
    ).isoformat()
    collected_at = collected_at or datetime.now(timezone.utc).isoformat()
    enterprise = quote(os.environ["GITHUB_ENTERPRISE_SLUG"], safe="")
    pages = []
    users = []
    page = 1
    total_seats_consumed = None
    total_seats_purchased = None

    while page <= MAX_PAGES:
        query = urlencode({"per_page": 100, "page": page})
        status, _, body = _request_json(
            f"/enterprises/{enterprise}/consumed-licenses?{query}", token
        )
        if status != 200:
            raise RuntimeError(f"GitHub consumed licenses returned HTTP {status}")
        response = json.loads(body)
        if not isinstance(response, dict) or not isinstance(response.get("users"), list):
            raise ValueError("GitHub consumed licenses response must contain a users array")
        page_users = response["users"]
        pages.append(body)
        users.extend(page_users)
        total_seats_consumed = response.get(
            "total_seats_consumed", total_seats_consumed
        )
        total_seats_purchased = response.get(
            "total_seats_purchased", total_seats_purchased
        )
        if len(page_users) < 100:
            break
        page += 1
    else:
        raise RuntimeError(f"GitHub consumed licenses exceeded {MAX_PAGES} pages")

    s3_client = _client("s3")
    bucket = os.environ["DATA_LAKE_BUCKET"]
    raw_prefix = f"raw/identity/consumed-licenses/snapshot_date={snapshot_date}"
    for page_index, body in enumerate(pages, start=1):
        _put_bytes(
            s3_client,
            bucket,
            f"{raw_prefix}/page-{page_index:05d}.json",
            body,
            "application/json",
        )

    snapshot_day = date.fromisoformat(snapshot_date)
    partition = (
        f"year={snapshot_day.year:04d}/month={snapshot_day.month:02d}/"
        f"day={snapshot_day.day:02d}"
    )
    user_records = [_user_record(user, snapshot_date, collected_at) for user in users]
    license_records = [
        _license_record(user, snapshot_date, collected_at) for user in users
    ]
    summary = {
        "snapshot_date": snapshot_date,
        "collected_at": collected_at,
        "enterprise_slug": os.environ["GITHUB_ENTERPRISE_SLUG"],
        "total_seats_consumed": total_seats_consumed,
        "total_seats_purchased": total_seats_purchased,
        "user_count": len(users),
        "page_count": len(pages),
        "complete": True,
    }
    _put_bytes(
        s3_client,
        bucket,
        f"bronze/identity/users/{partition}/snapshot.ndjson",
        _serialize_ndjson(user_records),
        "application/x-ndjson",
    )
    _put_bytes(
        s3_client,
        bucket,
        f"bronze/identity/licenses/{partition}/snapshot.ndjson",
        _serialize_ndjson(license_records),
        "application/x-ndjson",
    )
    _put_bytes(
        s3_client,
        bucket,
        f"bronze/identity/license-summary/{partition}/snapshot.ndjson",
        _serialize_ndjson([summary]),
        "application/x-ndjson",
    )
    _put_bytes(
        s3_client,
        bucket,
        f"{raw_prefix}/manifest.json",
        json.dumps(summary, separators=(",", ":"), sort_keys=True).encode("utf-8"),
        "application/json",
    )
    return summary


def _emit_metrics(summary):
    try:
        _client("cloudwatch").put_metric_data(
            Namespace="GitHubDataLake/Identity",
            MetricData=[
                {
                    "MetricName": "UsersCollected",
                    "Dimensions": [
                        {"Name": "Environment", "Value": os.environ["ENVIRONMENT"]}
                    ],
                    "Unit": "Count",
                    "Value": summary["user_count"],
                },
                {
                    "MetricName": "SeatsConsumed",
                    "Dimensions": [
                        {"Name": "Environment", "Value": os.environ["ENVIRONMENT"]}
                    ],
                    "Unit": "Count",
                    "Value": summary["total_seats_consumed"] or 0,
                },
            ],
        )
    except Exception as error:
        print(
            json.dumps(
                {
                    "level": "WARNING",
                    "event": "identity_metric_publish_failed",
                    "error_type": type(error).__name__,
                },
                separators=(",", ":"),
            )
        )


def lambda_handler(event, context):
    token = _secret_token(
        os.environ["GITHUB_IDENTITY_SECRET_ARN"], _client("secretsmanager")
    )
    event = event or {}
    summary = collect_snapshot(token, snapshot_date=event.get("snapshot_date"))
    _emit_metrics(summary)
    print(
        json.dumps(
            {
                "event": "enterprise_identity_snapshot_collected",
                "snapshot_date": summary["snapshot_date"],
                "user_count": summary["user_count"],
                "page_count": summary["page_count"],
            },
            separators=(",", ":"),
        )
    )
    return summary