import unittest
from datetime import date
from unittest.mock import patch

from copilot_collection_coordinator import app


class FakeSqs:
    def __init__(self, failed=None):
        self.requests = []
        self.failed = failed or []

    def send_message_batch(self, **request):
        self.requests.append(request)
        return {"Successful": [], "Failed": self.failed}


class CopilotCollectionCoordinatorTests(unittest.TestCase):
    def setUp(self):
        app._clients.clear()

    def test_builds_daily_reconciliation_windows(self):
        tasks = app.build_tasks({}, today=date(2026, 9, 14))

        self.assertEqual(len(tasks), 42)
        self.assertEqual(tasks[0]["report_day"], "2026-09-07")
        self.assertEqual(tasks[0]["source"], "billing")
        self.assertEqual(tasks[13]["report_day"], "2026-09-13")
        self.assertEqual(tasks[14]["report_day"], "2026-09-04")
        self.assertEqual(tasks[14]["source"], "usage")
        self.assertEqual(tasks[-1]["report_day"], "2026-09-10")
        self.assertEqual(tasks[-1]["collection_date"], "2026-09-14")

    def test_accepts_bounded_explicit_windows(self):
        tasks = app.build_tasks(
            {
                "collection_date": "2026-09-14",
                "billing_start_date": "2026-09-01",
                "billing_end_date": "2026-09-02",
                "usage_start_date": "2026-09-03",
                "usage_end_date": "2026-09-03",
            },
            today=date(2026, 9, 14),
        )

        self.assertEqual(len(tasks), 8)

    def test_rejects_incomplete_or_oversized_windows(self):
        with self.assertRaises(ValueError):
            app.build_tasks(
                {"billing_start_date": "2026-09-01"},
                today=date(2026, 9, 14),
            )
        with self.assertRaises(ValueError):
            app.build_tasks(
                {
                    "usage_start_date": "2026-08-01",
                    "usage_end_date": "2026-09-14",
                },
                today=date(2026, 9, 14),
            )

    def test_enqueues_tasks_in_sqs_batches(self):
        sqs = FakeSqs()
        app._clients["sqs"] = sqs

        with patch.dict(
            app.os.environ,
            {"COLLECTION_QUEUE_URL": "https://sqs.example/collection"},
            clear=True,
        ):
            result = app.lambda_handler({}, None)

        self.assertEqual(result["task_count"], 42)
        self.assertEqual([len(request["Entries"]) for request in sqs.requests], [10, 10, 10, 10, 2])

    def test_raises_when_sqs_rejects_a_task(self):
        with self.assertRaises(RuntimeError):
            app._enqueue(
                [{"source": "billing"}],
                "https://sqs.example/collection",
                FakeSqs(failed=[{"Id": "0"}]),
            )


if __name__ == "__main__":
    unittest.main()