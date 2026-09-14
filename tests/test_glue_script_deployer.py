import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from glue_script_deployer import app


class FakeS3:
    def __init__(self):
        self.put_requests = []
        self.delete_requests = []

    def put_object(self, **request):
        self.put_requests.append(request)

    def delete_object(self, **request):
        self.delete_requests.append(request)


class GlueScriptDeployerTests(unittest.TestCase):
    def setUp(self):
        app._clients.clear()
        self.s3 = FakeS3()
        app._clients["s3"] = self.s3

    def test_publishes_the_packaged_job_script(self):
        with tempfile.TemporaryDirectory() as directory:
            script_path = Path(directory) / "job.py"
            script_path.write_text("print('silver')\n", encoding="utf-8")
            with patch.dict(app.SCRIPT_PATHS, {"webhook_silver": script_path}):
                app._publish_script("data-bucket", "glue-scripts/webhook-silver.py")

        request = self.s3.put_requests[0]
        self.assertEqual(request["Bucket"], "data-bucket")
        self.assertEqual(request["Key"], "glue-scripts/webhook-silver.py")
        self.assertEqual(request["Body"], b"print('silver')\n")
        self.assertEqual(request["ServerSideEncryption"], "AES256")

    def test_publishes_the_selected_copilot_script(self):
        with tempfile.TemporaryDirectory() as directory:
            script_path = Path(directory) / "job.py"
            script_path.write_text("print('copilot')\n", encoding="utf-8")
            with patch.dict(app.SCRIPT_PATHS, {"copilot_silver": script_path}):
                app._publish_script(
                    "data-bucket",
                    "glue-scripts/copilot-silver.py",
                    "copilot_silver",
                )

        self.assertEqual(
            self.s3.put_requests[0]["Body"], b"print('copilot')\n"
        )

    def test_rejects_an_unknown_script_name(self):
        with self.assertRaisesRegex(ValueError, "Unsupported Glue script"):
            app._publish_script(
                "data-bucket", "glue-scripts/unknown.py", "unknown"
            )

    def test_deletes_the_deployment_artifact(self):
        app._delete_script("data-bucket", "glue-scripts/webhook-silver.py")

        self.assertEqual(
            self.s3.delete_requests,
            [{"Bucket": "data-bucket", "Key": "glue-scripts/webhook-silver.py"}],
        )


if __name__ == "__main__":
    unittest.main()