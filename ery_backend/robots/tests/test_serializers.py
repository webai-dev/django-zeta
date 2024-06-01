from ery_backend.base.testcases import EryTestCase

from ..factories import RobotFactory, RobotRuleFactory
from ..models import Robot, RobotRule


class TestRobotRuleBXMLSerializer(EryTestCase):
    def setUp(self):
        self.robot_rule = RobotRuleFactory()
        self.robot_rule.refresh_from_db()
        self.robot_rule_serializer = RobotRule.get_bxml_serializer()(self.robot_rule)

    def test_exists(self):
        self.assertIsNotNone(self.robot_rule_serializer)

    def test_expected_attributes(self):
        self.assertEqual(self.robot_rule_serializer.data['widget'], self.robot_rule.widget.name)
        self.assertEqual(self.robot_rule_serializer.data['rule_type'], self.robot_rule.rule_type)
        self.assertEqual(self.robot_rule_serializer.data['static_value'], str(self.robot_rule.static_value))


class TestRobotSerializer(EryTestCase):
    def setUp(self):
        self.robot = RobotFactory()
        self.robot_rule = RobotRuleFactory(robot=self.robot)
        self.robot_rule_2 = RobotRuleFactory(robot=self.robot)
        self.robot_serializer = Robot.get_bxml_serializer()(self.robot)

    def test_exists(self):
        self.assertIsNotNone(self.robot_serializer)

    def test_expected_attributes(self):
        self.assertEqual(self.robot_serializer.data['name'], self.robot.name)
        self.assertIn(RobotRule.get_bxml_serializer()(self.robot_rule).data, self.robot_serializer.data['rules'])
        self.assertIn(RobotRule.get_bxml_serializer()(self.robot_rule_2).data, self.robot_serializer.data['rules'])
