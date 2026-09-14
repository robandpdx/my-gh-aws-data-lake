import json
import os
from datetime import date, datetime, timedelta, timezone


BILLING_REPORT_TYPES = ("ai_credit", "premium_request")
USAGE_REPORT_TYPES = ("enterprise", "users", "repositories", "user_teams")
MAX_WINDOW_DAYS = 31

_clients = {}


def _client(service_name):
    if service_name not in _clients:
        import boto3

        _clients[service_name] = boto3.client(service_name)
    return _clients[service_name]


def _date_range(start_date, end_date):
    day_count = (end_date - start_date).days + 1
    if day_count < 1:
        raise ValueError("collection start date must not be after end date")
    if day_count > MAX_WINDOW_DAYS:
        raise ValueError(f"collection windows are limited to {MAX_WINDOW_DAYS} days")
    return [start_date + timedelta(days=offset) for offset in range(day_count)]


def _window(event, prefix, default_start, default_end):
    start_value = event.get(f"{prefix}_start_date")
    end_value = event.get(f"{prefix}_end_date")
    if bool(start_value) != bool(end_value):
        raise ValueError(
            f"{prefix}_start_date and {prefix}_end_date must be supplied together"
        )
    if not start_value:
        return _date_range(default_start, default_end)
    return _date_range(date.fromisoformat(start_value), date.fromisoformat(end_value))


def build_tasks(event, today=None):
    today = today or datetime.now(timezone.utc).date()
    collection_date = date.fromisoformat(
        event.get("collection_date", today.isoformat())
    ).isoformat()
    billing_days = _window(
        event,
        "billing",
        today - timedelta(days=7),
        today - timedelta(days=1),
    )
    usage_days = _window(
        event,
        "usage",
        today - timedelta(days=10),
        today - timedelta(days=4),
    )

    tasks = []
    for report_day in billing_days:
        for report_type in BILLING_REPORT_TYPES:
            tasks.append(
                {
                    "source": "billing",
                    "report_type": report_type,
                    "report_day": report_day.isoformat(),
                    "collection_date": collection_date,
                }
            )
    for report_day in usage_days:
        for report_type in USAGE_REPORT_TYPES:
            tasks.append(
                {
                    "source": "usage",
                    "report_type": report_type,
                    "report_day": report_day.isoformat(),
                    "collection_date": collection_date,
                }
            )
    return tasks


def _enqueue(tasks, queue_url, sqs_client):
    for offset in range(0, len(tasks), 10):
        batch = tasks[offset : offset + 10]
        response = sqs_client.send_message_batch(
            QueueUrl=queue_url,
            Entries=[
                {
                    "Id": str(index),
                    "MessageBody": json.dumps(task, separators=(",", ":")),
                }
                for index, task in enumerate(batch)
            ],
        )
        failed = response.get("Failed", [])
        if failed:
            raise RuntimeError(f"SQS rejected {len(failed)} collection task(s)")


def lambda_handler(event, context):
    tasks = build_tasks(event or {})
    queue_url = os.environ["COLLECTION_QUEUE_URL"]
    _enqueue(tasks, queue_url, _client("sqs"))
    result = {
        "event": "copilot_collection_tasks_enqueued",
        "task_count": len(tasks),
    }
    print(json.dumps(result, separators=(",", ":")))
    return result