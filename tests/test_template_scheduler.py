import unittest
from pathlib import Path


TEMPLATE_PATH = Path(__file__).resolve().parents[1] / "template.yml"


class SchedulerTemplateTests(unittest.TestCase):
    def test_execution_role_is_scoped_to_the_default_schedule_group(self):
        template = TEMPLATE_PATH.read_text(encoding="utf-8")

        self.assertIn(
            'aws:SourceArn: !Sub "arn:${AWS::Partition}:scheduler:${AWS::Region}:${AWS::AccountId}:schedule-group/default"',
            template,
        )
        self.assertNotIn(
            "arn:${AWS::Partition}:scheduler:${AWS::Region}:${AWS::AccountId}:schedule/default/",
            template,
        )


if __name__ == "__main__":
    unittest.main()