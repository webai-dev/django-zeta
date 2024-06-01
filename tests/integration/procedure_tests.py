from ery_backend.actions.factories import ActionStepFactory
from ery_backend.actions.models import ActionStep
from ery_backend.base.testcases import EryTestCase, create_test_hands
from ery_backend.conditions.factories import ConditionFactory
from ery_backend.conditions.models import Condition
from ery_backend.modules.factories import ModuleDefinitionProcedureFactory
from ery_backend.procedures.factories import ProcedureFactory, ProcedureArgumentFactory
from ery_backend.variables.factories import VariableDefinitionFactory, HandVariableFactory
from ery_backend.variables.models import VariableDefinition


class TestServerSideEvaluation(EryTestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.hand = create_test_hands(n=1).first()

    def test_server_side_evaluate(self):
        """
        Confirm engine_client's evaluate called as expected
        """
        procedure = ProcedureFactory(
            name='rand_int', comment="Return a random integer between 1 and 100", code='Math.floor(Math.random()*100) + 1;'
        )
        result = procedure.evaluate(self.hand)
        self.assertTrue(1 <= result <= 100)


class TestConditionEvaluation(EryTestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.hand = create_test_hands(n=1).first()
        cls.md = cls.hand.current_module.stint_definition_module_definition.module_definition

    def test_condition_evaluation(self):
        """
        Confirm procedures accessible during condition.evaluate.
        """
        procedure_1 = ProcedureFactory(name='make_number_three', code='3')
        ModuleDefinitionProcedureFactory(
            procedure=procedure_1, module_definition=self.hand.current_module_definition, name='make_number_three'
        )

        condition = ConditionFactory(
            left_type=Condition.TYPE_CHOICES.expression,
            left_expression='make_number_three()',
            right_type=Condition.TYPE_CHOICES.expression,
            right_expression='3',
            relation=Condition.RELATION_CHOICES.equal,
            module_definition=self.md,
        )
        self.assertTrue(condition.evaluate(self.hand))

    def test_condition_evaluation_with_args(self):
        """
        Confirm procedures work with args during condition.evaluate.
        """
        procedure_2 = ProcedureFactory(name='multiply', code='x * y')
        ProcedureArgumentFactory(procedure=procedure_2, name='x', order=0, default=3)
        ProcedureArgumentFactory(procedure=procedure_2, name='y', order=1, default=5)
        ModuleDefinitionProcedureFactory(
            procedure=procedure_2, module_definition=self.hand.current_module_definition, name='multiplyalias'
        )

        condition = ConditionFactory(
            left_type=Condition.TYPE_CHOICES.expression,
            left_expression='multiplyalias()',
            right_type=Condition.TYPE_CHOICES.expression,
            right_expression='15',
            relation=Condition.RELATION_CHOICES.equal,
            module_definition=self.md,
        )
        self.assertTrue(condition.evaluate(self.hand))


# XXX: Revisit on issue #270 concerning client-side evaluation.
# @override_settings(DEBUG=True, ERY_BABEL_HOSTPORT='localhost:30000', ERY_ENGINE_HOSTPORT='localhost:30001')
# class TestWebRender(EryLiveServerTestCase):
#     def setUp(self):
#         self.hand = create_test_hands(n=1).first()
#         self.driver = self.get_loggedin_driver(self.hand.user.username)
#         md = self.hand.current_module.stint_definition_module_definition.module_definition
#         procedure_1 = ProcedureFactory(name='makeTestText', code='document.getElementById(\'testSpan\').innerHTML = phrase',
#                                        server_side=False)
#         ProcedureArgumentFactory(procedure=procedure_1, name='phrase', comment='Inserted into testSpan')
#         # created via create_test_hands
#         content_block = TemplateBlock.objects.get(name='Content')
#         content_block_translation = content_block.templateblocktranslation_set.get(language=md.primary_language)
#         content_block_translation.content = '<span id="testSpan" />'
#         content_block_translation.save()

#     def test_template_evaluation(self):
#         """
#         Confirm procedures accessible to clientside Javascript
#         """
#         self.driver.get(f'{self.live_server_url}/stint/{self.hand.stint.id}/')

#         input()
#         test_span = self.driver.find_element_by_id('testSpan')
#         self.assertIn('test text here', test_span.get_attribute('innerHTML'))


class TestActionStep(EryTestCase):
    """
    Confirm procedure is used during actionstep execution.
    """

    def setUp(self):
        self.hand = create_test_hands(n=1).first()
        md = self.hand.current_module.stint_definition_module_definition.module_definition
        set_random_stage = ProcedureFactory(name='set_random_stage', code='Math.floor(Math.random()* stage_ids.length + 1);',)
        ModuleDefinitionProcedureFactory(
            procedure=set_random_stage, module_definition=self.hand.current_module_definition, name='set_random_stage_alias'
        )

        ProcedureArgumentFactory(procedure=set_random_stage, name='stage_ids', default=[1, 2, 3])
        stages_index = VariableDefinitionFactory(
            module_definition=md,
            scope=VariableDefinition.SCOPE_CHOICES.hand,
            data_type=VariableDefinition.DATA_TYPE_CHOICES.int,
            validator=None,
            name='stages_index',
        )
        self.stage_index = HandVariableFactory(hand=self.hand, variable_definition=stages_index, value=None)
        self.as_1 = ActionStepFactory(
            action__module_definition=md,
            for_each=ActionStep.FOR_EACH_CHOICES.current_hand_only,
            action_type=ActionStep.ACTION_TYPE_CHOICES.set_variable,
            variable_definition=stages_index,
            value='set_random_stage_alias()',
        )

    def test_function_in_setvar(self):
        self.as_1.run(self.hand)
        self.stage_index.refresh_from_db()
        # randomizer procedure function should be used to set 1 <= var value  <= 3
        self.assertIn(self.stage_index.value, [1, 2, 3])
