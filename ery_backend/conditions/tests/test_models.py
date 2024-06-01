from unittest import mock

from django.core.cache import cache
from django.core.exceptions import ValidationError

from ery_backend.base.testcases import EryTestCase, create_test_hands
from ery_backend.base.cache import get_func_cache_key_for_hand
from ery_backend.modules.factories import ModuleDefinitionProcedureFactory
from ery_backend.procedures.factories import ProcedureFactory, ProcedureArgumentFactory
from ery_backend.procedures.utils import get_procedure_functions
from ery_backend.scripts.grpc.engine_pb2 import Result, Value
from ery_backend.variables.factories import VariableDefinitionFactory, HandVariableFactory
from ery_backend.variables.models import VariableDefinition
from ..factories import ConditionFactory
from ..models import Condition


class TestCondition(EryTestCase):
    def setUp(self):
        self.hand = create_test_hands(n=1, signal_pubsub=False).first()
        self.module_definition = self.hand.stint.stint_specification.stint_definition.module_definitions.first()
        self.variable_definition = VariableDefinitionFactory(module_definition=self.module_definition)
        self.sub_condition = ConditionFactory(
            left_type=Condition.TYPE_CHOICES.expression,
            right_type=Condition.TYPE_CHOICES.expression,
            left_expression=4.56,
            right_expression=5,
            module_definition=self.module_definition,
            relation=Condition.RELATION_CHOICES.equal,
        )
        self.condition = ConditionFactory(
            left_type=Condition.TYPE_CHOICES.expression,
            right_type=Condition.TYPE_CHOICES.variable,
            left_expression=10,
            right_variable_definition=self.variable_definition,
            relation=Condition.RELATION_CHOICES.equal,
            module_definition=self.module_definition,
        )
        self.condition_2 = ConditionFactory(
            left_type=Condition.TYPE_CHOICES.sub_condition,
            right_type=Condition.TYPE_CHOICES.sub_condition,
            operator=Condition.BINARY_OPERATOR_CHOICES.op_and,
            left_sub_condition=self.sub_condition,
            right_sub_condition=self.sub_condition,
            module_definition=self.module_definition,
        )
        self.duplicate_me = ConditionFactory(
            module_definition=self.module_definition,
            left_type=Condition.TYPE_CHOICES.variable,
            right_type=Condition.TYPE_CHOICES.variable,
            left_variable_definition=self.variable_definition,
            right_variable_definition=self.variable_definition,
            relation=Condition.RELATION_CHOICES.equal,
        )
        self.full_expression_condition = ConditionFactory(
            left_type=Condition.TYPE_CHOICES.expression,
            left_expression=12,
            right_type=Condition.TYPE_CHOICES.expression,
            right_expression=12,
            relation=Condition.RELATION_CHOICES.equal,
            module_definition=self.module_definition,
        )

        self.expression_condition = ConditionFactory(
            left_type=Condition.TYPE_CHOICES.expression,
            left_expression='1==1',
            right_type=Condition.TYPE_CHOICES.expression,
            right_expression='2==1',
            relation=Condition.RELATION_CHOICES.greater,
            module_definition=self.module_definition,
        )

    def test_exists(self):
        self.assertIsNotNone(self.condition)

    def test_expected_attributes(self):
        self.condition.refresh_from_db()  # get typecasted expressions
        self.sub_condition.refresh_from_db()
        self.assertEqual(self.sub_condition.module_definition, self.module_definition)
        self.assertEqual(self.condition.left_type, Condition.TYPE_CHOICES.expression)
        self.assertEqual(self.condition.right_type, Condition.TYPE_CHOICES.variable)
        self.assertEqual(self.condition.left_expression, '10')
        self.assertEqual(self.condition.right_variable_definition, self.variable_definition)
        self.assertEqual(self.sub_condition.left_expression, '4.56')
        self.assertEqual(self.condition_2.left_sub_condition, self.sub_condition)
        self.assertEqual(self.condition_2.operator, Condition.BINARY_OPERATOR_CHOICES.op_and)
        self.assertEqual(self.condition.relation, Condition.RELATION_CHOICES.equal)

    def test_validation_errors(self):
        # XXX: Address is issue #813
        # left_type expression with blank left_expression
        with self.assertRaises(ValidationError):
            ConditionFactory(
                left_type=Condition.TYPE_CHOICES.expression,
                left_expression=None,
                right_type=Condition.TYPE_CHOICES.expression,
                right_expression=12,
                relation=Condition.RELATION_CHOICES.equal,
                module_definition=self.module_definition,
            )
        # right_type expression with blank right_expression
        with self.assertRaises(ValidationError):
            ConditionFactory(
                left_type=Condition.TYPE_CHOICES.expression,
                left_expression=12,
                right_type=Condition.TYPE_CHOICES.expression,
                right_expression=None,
                relation=Condition.RELATION_CHOICES.equal,
                module_definition=self.module_definition,
            )
        # left_type variable_definition with blank left_variable_definition
        # with self.assertRaises(ValidationError):
        #     ConditionFactory(left_type=Condition.TYPE_CHOICES.variable, left_variable_definition=None,
        #                      right_type=Condition.TYPE_CHOICES.expression, right_expression=12,
        #                      relation=Condition.RELATION_CHOICES.equal, module_definition=self.module_definition)
        # right_type variable_definition with blank right_variable_definition
        # with self.assertRaises(ValidationError):
        #     ConditionFactory(left_type=Condition.TYPE_CHOICES.expression, left_expression=12,
        #                      right_type=Condition.TYPE_CHOICES.variable, right_variable_definition=None,
        #                      relation=Condition.RELATION_CHOICES.equal, module_definition=self.module_definition)

        # left_type sub_condition without right_type sub_condition
        # with self.assertRaises(ValidationError):
        #     ConditionFactory(left_type=Condition.TYPE_CHOICES.sub_condition,
        #                      left_sub_condition=self.sub_condition, right_type=Condition.TYPE_CHOICES.expression,
        #                      right_expression='true',
        #                      relation=Condition.RELATION_CHOICES.equal, module_definition=self.module_definition)

        # right_type sub_condition without left_type sub_condition
        # with self.assertRaises(ValidationError):
        #     ConditionFactory(left_type=Condition.TYPE_CHOICES.expression, left_expression='true',
        #                      right_type=Condition.TYPE_CHOICES.sub_condition,
        #                      right_sub_condition=self.sub_condition,
        #                      relation=Condition.RELATION_CHOICES.equal, module_definition=self.module_definition)

        # left_type sub_condition with blank left_sub_condition
        # with self.assertRaises(ValidationError):
        #     ConditionFactory(left_type=Condition.TYPE_CHOICES.sub_condition, left_sub_condition=None,
        #                      right_type=Condition.TYPE_CHOICES.sub_condition,
        #                      right_sub_condition=self.sub_condition,
        #                      operator=Condition.BINARY_OPERATOR_CHOICES.op_and, module_definition=self.module_definition)

        # right_type sub_condition with blank right_sub_condition
        # with self.assertRaises(ValidationError):
        #     ConditionFactory(left_type=Condition.TYPE_CHOICES.sub_condition, left_expression=12,
        #                      right_type=Condition.TYPE_CHOICES.sub_condition, right_sub_condition=None,
        #                      operator=Condition.BINARY_OPERATOR_CHOICES.op_and, relation=None,
        #                      module_definition=self.module_definition)

        # ConditionFactory(left_type=Condition.TYPE_CHOICES.sub_condition,
        #                  left_sub_condition=self.sub_condition, right_type=Condition.TYPE_CHOICES.sub_condition,
        #                  right_sub_condition=None,
        #                  operator=Condition.BINARY_OPERATOR_CHOICES.op_and, module_definition=self.module_definition)

        # type sub_condition with missing operator
        # with self.assertRaises(ValidationError):
        #     ConditionFactory(left_type=Condition.TYPE_CHOICES.sub_condition, left_sub_condition=self.sub_condition,
        #                      right_type=Condition.TYPE_CHOICES.sub_condition, right_sub_condition=self.sub_condition,
        #                      operator=None, module_definition=self.module_definition)

        # type expression with missing relation
        with self.assertRaises(ValidationError):
            ConditionFactory(
                left_type=Condition.TYPE_CHOICES.expression,
                left_expression=12,
                right_type=Condition.TYPE_CHOICES.expression,
                right_expression=12,
                relation=None,
                module_definition=self.module_definition,
            )

    def test_get_privilege_ancestor(self):
        self.assertEqual(self.condition.get_privilege_ancestor(), self.condition.module_definition)

    def test_get_privilege_ancestor_cls(self):
        self.assertEqual(self.condition.get_privilege_ancestor_cls(), self.condition.module_definition.__class__)

    def test_duplicate(self):
        condition_2 = self.duplicate_me.duplicate()
        self.assertIsNotNone(condition_2)
        self.assertEqual(condition_2.name, '{}_copy'.format(self.duplicate_me.name))
        self.assertNotEqual(condition_2, self.duplicate_me)

        # foreign key relationships that aren't children should be equal
        self.assertEqual(self.duplicate_me.left_variable_definition, condition_2.left_variable_definition)
        self.assertEqual(self.duplicate_me.right_variable_definition, condition_2.right_variable_definition)

        # self-referentials should be equal
        self.assertEqual(self.duplicate_me.left_sub_condition, condition_2.left_sub_condition)
        self.assertEqual(self.duplicate_me.right_sub_condition, condition_2.right_sub_condition)
        # parents should be equal
        self.assertEqual(self.duplicate_me.module_definition, condition_2.module_definition)

    @mock.patch('ery_backend.scripts.engine_client._run_javascript_op')
    def test_get_value(self, mock_run):
        # expression
        val = Condition.get_value(value_type=Condition.TYPE_CHOICES.expression, expression='1*vd1')
        self.assertEqual(val, '1*vd1')

        # variable definition
        vd1 = VariableDefinitionFactory(
            scope=VariableDefinition.SCOPE_CHOICES.hand,
            module_definition=self.module_definition,
            data_type=VariableDefinition.DATA_TYPE_CHOICES.int,
        )
        HandVariableFactory(hand=self.hand, variable_definition=vd1, value=7)
        self.assertEqual(Condition.get_value(value_type=Condition.TYPE_CHOICES.variable, variable_definition=vd1), vd1.name)

        mock_run.return_value = Result(value=Value(bool_value=True))

    @mock.patch('ery_backend.conditions.models.Condition.get_value')
    def test_get_sided_value(self, mock_value):
        """
        Note: Since Condition.get_value is tested above, this test confirms values are passed as expected.
        """
        self.condition.get_left_value()
        mock_value.assert_called_with(
            expression=self.condition.left_expression,
            value_type=Condition.TYPE_CHOICES.expression,
            variable_definition=None,
            sub_condition=None,
        )

        self.condition.get_right_value()
        mock_value.assert_called_with(
            expression=None,
            value_type=Condition.TYPE_CHOICES.variable,
            variable_definition=self.condition.right_variable_definition,
            sub_condition=None,
        )

    @mock.patch('ery_backend.scripts.engine_client.evaluate_without_side_effects')
    def test_as_javascript(self, mock_evaluate):
        cond = ConditionFactory(
            left_type=Condition.TYPE_CHOICES.expression,
            left_expression='1*1',
            right_type=Condition.TYPE_CHOICES.expression,
            right_expression='2/2',
            module_definition=self.module_definition,
        )
        self.assertEqual(cond.as_javascript(), '(1*1) == (2/2)')

        mock_evaluate.return_value = True
        cond2 = ConditionFactory(
            left_type=Condition.TYPE_CHOICES.sub_condition,
            left_sub_condition=cond,
            right_type=Condition.TYPE_CHOICES.sub_condition,
            right_sub_condition=cond,
            operator=Condition.BINARY_OPERATOR_CHOICES.op_and,
            module_definition=self.module_definition,
        )

        self.assertEqual(cond2.as_javascript(), '((1*1) == (2/2)) == ((1*1) == (2/2))')

    @mock.patch('ery_backend.scripts.engine_client._run_javascript_op')
    @mock.patch('ery_backend.scripts.engine_client.make_javascript_op')
    def test_evaluate(self, mock_make, mock_run):
        """
        Note: Since condition.evaluate with type expression is merely a wrapper of already tested engine_client.evaluate
        (on said expression), tests containing an expression focus on confirming expression value and hand
        make it to engine_client.evaluate.
        """
        # make sure everything shares stint and/or module_definition
        # test on var_defs
        vd1 = VariableDefinitionFactory(
            scope=VariableDefinition.SCOPE_CHOICES.hand,
            module_definition=self.module_definition,
            data_type=VariableDefinition.DATA_TYPE_CHOICES.int,
        )
        vd2 = VariableDefinitionFactory(
            scope=VariableDefinition.SCOPE_CHOICES.hand,
            module_definition=self.module_definition,
            data_type=VariableDefinition.DATA_TYPE_CHOICES.int,
        )
        HandVariableFactory(hand=self.hand, variable_definition=vd1, value=7)
        HandVariableFactory(hand=self.hand, variable_definition=vd2, value=8)
        mock_run.return_value = Result(value=Value(bool_value=True))
        var_cond = ConditionFactory(
            left_type=Condition.TYPE_CHOICES.variable,
            right_type=Condition.TYPE_CHOICES.variable,
            left_variable_definition=vd1,
            right_variable_definition=vd2,
            relation=Condition.RELATION_CHOICES.less,
            module_definition=self.module_definition,
        )
        self.assertTrue(var_cond.evaluate(self.hand))
        # make_javascript_op return value is passed into evaluate, which is tested elsewhere
        mock_make.assert_called_with(
            str(var_cond), f'({vd1.name}) < ({vd2.name})', self.hand, self.hand.stint.get_context(self.hand)
        )

        # test on expression
        expression_cond = ConditionFactory(
            left_type=Condition.TYPE_CHOICES.expression,
            right_type=Condition.TYPE_CHOICES.variable,
            left_expression='1==1',
            right_variable_definition=vd2,
            relation=Condition.RELATION_CHOICES.equal,
            module_definition=self.module_definition,
        )
        expression_cond.evaluate(self.hand)
        mock_make.assert_called_with(
            str(expression_cond), f'(1==1) == ({vd2.name})', self.hand, self.hand.stint.get_context(self.hand)
        )

        # test on sub_conditions
        # engine_client.evaluate should still be called in evaluation of sub_condition
        sub_cond_1 = ConditionFactory(
            left_type=Condition.TYPE_CHOICES.sub_condition,
            right_type=Condition.TYPE_CHOICES.sub_condition,
            left_sub_condition=var_cond,
            right_sub_condition=expression_cond,
            operator=Condition.BINARY_OPERATOR_CHOICES.op_and,
            module_definition=self.module_definition,
            relation=None,
        )
        sub_cond_1.evaluate(self.hand)
        mock_make.assert_called_with(
            str(sub_cond_1),
            f'(({vd1.name}) < ({vd2.name})) && ((1==1) == ({vd2.name}))',
            self.hand,
            self.hand.stint.get_context(self.hand),
        )

    @mock.patch('ery_backend.scripts.engine_client._run_javascript_op')
    def test_evaluate_caching(self, mock_engine):
        # test on var_defs
        vd1 = VariableDefinitionFactory(
            scope=VariableDefinition.SCOPE_CHOICES.hand,
            module_definition=self.module_definition,
            data_type=VariableDefinition.DATA_TYPE_CHOICES.int,
        )
        vd2 = VariableDefinitionFactory(
            scope=VariableDefinition.SCOPE_CHOICES.hand,
            module_definition=self.module_definition,
            data_type=VariableDefinition.DATA_TYPE_CHOICES.int,
        )
        HandVariableFactory(hand=self.hand, variable_definition=vd1, value=7)
        HandVariableFactory(hand=self.hand, variable_definition=vd2, value=8)
        mock_engine.return_value = Result(value=Value(bool_value=True))
        var_cond = ConditionFactory(
            left_type=Condition.TYPE_CHOICES.variable,
            right_type=Condition.TYPE_CHOICES.variable,
            left_variable_definition=vd1,
            right_variable_definition=vd2,
            relation=Condition.RELATION_CHOICES.less,
            module_definition=self.module_definition,
        )
        # should be cached
        var_cond.evaluate(self.hand)
        cache_key = get_func_cache_key_for_hand(var_cond.as_javascript(), self.hand)
        self.assertIn(cache_key, cache.keys('*'))
        # change code generated by as_javascript to change cache key
        var_cond.right_variable_definition = vd1
        var_cond.save()
        var_cond.evaluate(self.hand)
        cache_key_2 = get_func_cache_key_for_hand(var_cond.as_javascript(), self.hand)
        self.assertIn(cache_key, cache.keys('*'))
        self.assertIn(cache_key_2, cache.keys('*'))


@mock.patch('ery_backend.scripts.engine_client.make_javascript_op')
@mock.patch('ery_backend.scripts.engine_client._run_javascript_op')
class TestProcedureIntegration(EryTestCase):
    def test_functions_in_condition(self, mock_run, mock_make):  # pylint: disable=no-self-use
        """
        Confirm procedures are prefixed into code intended for evaluation.
        """
        mock_run.return_value = Result(value=Value(bool_value=True))
        hand = create_test_hands(n=1, signal_pubsub=False).first()
        md = hand.current_module.stint_definition_module_definition.module_definition
        procedure_1 = ProcedureFactory(name='make_number_three', code='3')
        ModuleDefinitionProcedureFactory(name='make_number_three', procedure=procedure_1, module_definition=md)
        procedure_2 = ProcedureFactory(name='bad_rap', code='"GucciGang " * length')
        ModuleDefinitionProcedureFactory(name='bad_rap', procedure=procedure_2, module_definition=md)
        ProcedureArgumentFactory(
            procedure=procedure_2, name='length', comment='Determines the length of your corny rap joint.', default=4
        )
        condition = ConditionFactory(
            left_type=Condition.TYPE_CHOICES.expression,
            left_expression='make_number_three()',
            right_type=Condition.TYPE_CHOICES.expression,
            right_expression='3',
            module_definition=md,
        )
        eval_code = f"{get_procedure_functions(md, 'engine')}\n{condition.as_javascript()}"
        condition.evaluate(hand)
        mock_make.assert_called_with(str(condition), eval_code, hand, hand.stint.get_context(hand))
