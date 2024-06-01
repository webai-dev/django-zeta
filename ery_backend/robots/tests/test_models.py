import unittest

from django.core.exceptions import ValidationError

from ery_backend.base.exceptions import EryValueError
from ery_backend.modules.factories import ModuleDefinitionWidgetFactory
from ery_backend.variables.factories import VariableDefinitionFactory, VariableChoiceItemFactory
from ery_backend.variables.models import VariableDefinition
from ery_backend.base.testcases import EryTestCase

from ..factories import RobotFactory, RobotRuleFactory


class TestRobot(EryTestCase):
    def setUp(self):
        self.message = 'Skynet, here we come'
        self.robot = RobotFactory(name='test_robot', comment=self.message)

    def test_exists(self):
        self.assertIsNotNone(self.robot)

    def test_expected_attributes(self):
        self.assertEqual(self.robot.name, 'test_robot')
        self.assertEqual(self.robot.comment, self.message)

    def test_duplicate(self):
        variable_definition = VariableDefinitionFactory(
            exclude=(VariableDefinition.DATA_TYPE_CHOICES.stage), module_definition=self.robot.module_definition
        )
        module_definition_widget = ModuleDefinitionWidgetFactory(
            name='ModuleDefinitionWidgetOne',
            module_definition=self.robot.module_definition,
            variable_definition=variable_definition,
        )
        RobotRuleFactory(widget=module_definition_widget, rule_type='static', robot=self.robot)
        robot_2 = self.robot.duplicate()
        self.assertIsNotNone(robot_2)
        self.assertNotEqual(robot_2, self.robot)
        self.assertEqual('{}_copy'.format(self.robot.name), robot_2.name)
        self.assertEqual(robot_2.rules.count(), self.robot.rules.count())
        for rule in robot_2.rules.all():
            self.assertEqual(rule.widget.name, module_definition_widget.name)


class TestRobotRule(EryTestCase):
    @unittest.skip("XXX: Address in issue #813")
    def test_clean(self):
        module_definition_widget = ModuleDefinitionWidgetFactory(name='ModuleDefinitionWidgetOne')
        with self.assertRaises(ValidationError):
            RobotRuleFactory(widget=module_definition_widget, rule_type='static', static_value=None)

        # Outside of subset
        variable_definition = VariableDefinitionFactory(
            data_type=VariableDefinition.DATA_TYPE_CHOICES.choice, default_value='a'
        )
        VariableChoiceItemFactory(variable_definition=variable_definition)
        module_definition_widget_two = ModuleDefinitionWidgetFactory(
            name='ModuleDefinitionWidgetTwo', variable_definition=variable_definition
        )

        with self.assertRaises(EryValueError):
            RobotRuleFactory(widget=module_definition_widget_two, static_value='b')

    def test_get_value_static(self):
        variable_definition = VariableDefinitionFactory(data_type=VariableDefinition.DATA_TYPE_CHOICES.str)
        widget = ModuleDefinitionWidgetFactory(
            variable_definition=variable_definition, module_definition=variable_definition.module_definition
        )
        robot = RobotFactory(module_definition=variable_definition.module_definition)
        robot_rule = RobotRuleFactory(widget=widget, robot=robot, rule_type='static', static_value='expect this')
        self.assertEqual(robot_rule.get_value(), 'expect this')
