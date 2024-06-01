from ery_backend.base.testcases import EryTestCase
from ery_backend.conditions.factories import ConditionFactory
from ery_backend.conditions.models import Condition
from ery_backend.variables.factories import VariableDefinitionFactory


class TestConditionBXMLSerializer(EryTestCase):
    def setUp(self):
        self.variabledefinition_1 = VariableDefinitionFactory()
        self.variabledefinition_2 = VariableDefinitionFactory()
        self.sub_condition = ConditionFactory(
            left_type=Condition.TYPE_CHOICES.expression,
            left_expression=1,
            right_type=Condition.TYPE_CHOICES.expression,
            right_expression=1,
            relation=Condition.RELATION_CHOICES.equal,
        )
        self.sub_condition.refresh_from_db()

        self.condition = ConditionFactory(
            left_type=Condition.TYPE_CHOICES.variable,
            right_type=Condition.TYPE_CHOICES.variable,
            left_variable_definition=self.variabledefinition_1,
            right_variable_definition=self.variabledefinition_2,
            relation=Condition.RELATION_CHOICES.equal,
        )

        self.condition_2 = ConditionFactory(
            left_type=Condition.TYPE_CHOICES.sub_condition,
            right_type=Condition.TYPE_CHOICES.sub_condition,
            left_sub_condition=self.sub_condition,
            right_sub_condition=self.sub_condition,
            operator=Condition.BINARY_OPERATOR_CHOICES.op_and,
        )

        condition_serializer = Condition.get_bxml_serializer()
        self.condition_serializer = condition_serializer(self.condition)
        self.condition_serializer_2 = condition_serializer(self.condition_2)
        self.sub_condition_serializer = condition_serializer(self.sub_condition)

    def test_exists(self):
        self.assertIsNotNone(self.condition_serializer)

    def test_expected_attributes(self):
        self.assertEqual(self.condition_serializer.data['left_type'], self.condition.left_type)
        self.assertEqual(self.condition_serializer.data['right_type'], self.condition.right_type)
        self.assertEqual(self.sub_condition_serializer.data['right_expression'], self.sub_condition.right_expression)
        self.assertEqual(self.sub_condition_serializer.data['left_expression'], self.sub_condition.left_expression)
        self.assertEqual(self.condition_serializer.data['left_variable_definition'], self.variabledefinition_1.name)
        self.assertEqual(self.condition_serializer.data['right_variable_definition'], self.variabledefinition_2.name)
        self.assertEqual(self.condition_serializer_2.data['left_sub_condition'], self.sub_condition.name)
        self.assertEqual(self.condition_serializer_2.data['right_sub_condition'], self.sub_condition.name)
