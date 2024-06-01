import unittest
from unittest import mock

import grpc
from languages_plus.models import Language

from ery_backend.actions.exceptions import EryActionError
from ery_backend.actions.factories import ActionFactory, ActionStepFactory
from ery_backend.actions.models import ActionStep
from ery_backend.base.testcases import EryTestCase, create_test_hands
from ery_backend.base.utils import get_default_language
from ery_backend.commands.factories import (
    CommandFactory,
    CommandTemplateFactory,
    CommandTemplateBlockFactory,
    CommandTemplateBlockTranslationFactory,
)
from ery_backend.conditions.factories import ConditionFactory
from ery_backend.conditions.models import Condition
from ery_backend.frontends.models import Frontend
from ery_backend.hands.factories import HandFactory
from ery_backend.modules.factories import ModuleDefinitionWidgetFactory
from ery_backend.modules.factories import ModuleDefinitionProcedureFactory
from ery_backend.procedures.factories import ProcedureFactory, ProcedureArgumentFactory
from ery_backend.stages.factories import StageTemplateBlockFactory, StageTemplateBlockTranslationFactory, RedirectFactory
from ery_backend.scripts.engine_client import make_javascript_op, evaluate, evaluate_without_side_effects
from ery_backend.scripts.grpc.engine_pb2_grpc import JavascriptEngineStub
from ery_backend.stints.models import Stint
from ery_backend.templates.factories import TemplateFactory, TemplateBlockFactory, TemplateBlockTranslationFactory
from ery_backend.variables.factories import (
    VariableDefinitionFactory,
    HandVariableFactory,
    TeamVariableFactory,
    ModuleVariableFactory,
)
from ery_backend.variables.models import VariableDefinition
from ery_backend.widgets.factories import WidgetFactory


class TestEvaluateWithoutSideEffects(EryTestCase):
    """
    Verify that the method ery_backend.scripts.engine_client.evaluate_without_side_effects does not change values of variables.
    """

    def setUp(self):
        channel = grpc.insecure_channel('localhost:30001')
        self.engine = JavascriptEngineStub(channel)
        self.hand = create_test_hands(n=1, frontend_type='Web').first()

    def test_var_change(self):
        hand_vd = VariableDefinitionFactory(
            module_definition=self.hand.current_module_definition,
            scope=VariableDefinition.SCOPE_CHOICES.hand,
            data_type=VariableDefinition.DATA_TYPE_CHOICES.int,
            validator=None,
            name='handvar',
        )
        handvar = HandVariableFactory(variable_definition=hand_vd, hand=self.hand, value=25, module=self.hand.current_module)
        code = 'handvar = handvar * 2; handvar'
        value = evaluate_without_side_effects('test', code, self.hand)
        self.assertEqual(value, 50)
        handvar.refresh_from_db()
        self.assertEqual(handvar.value, 25)


class TestEngineRunErrors(EryTestCase):
    def setUp(self):
        channel = grpc.insecure_channel('localhost:30001')
        self.engine = JavascriptEngineStub(channel)
        self.hand = create_test_hands(n=1, frontend_type='Web').first()

    def test_endless_js(self):
        javascript_op = make_javascript_op('endless_js', 'while (1==1){a = 1;}', self.hand)
        with self.assertRaises(grpc.RpcError):
            self.engine.Run(javascript_op)

    def test_undefined_var(self):
        javascript_op = make_javascript_op('no_kalas :(', 'kalas * 42', self.hand)
        with self.assertRaises(grpc.RpcError):
            self.engine.Run(javascript_op)

    def test_invalid_js(self):
        javascript_op = make_javascript_op('no brackets!', 'for (i=0, i<10, i++1){1 + 1', self.hand)
        with self.assertRaises(grpc.RpcError):
            self.engine.Run(javascript_op)


class TestActionStepSaveVar(EryTestCase):
    """
    Confirms an ActionStep can set a variable to a value specified through Javascript.
    """

    def setUp(self):
        self.hand = create_test_hands(n=1, frontend_type='Web').first()
        module_definition = self.hand.current_module_definition
        self.use_me = VariableDefinitionFactory(
            module_definition=module_definition,
            name='useme',
            scope=VariableDefinition.SCOPE_CHOICES.hand,
            data_type=VariableDefinition.DATA_TYPE_CHOICES.int,
        )
        self.set_me = VariableDefinitionFactory(
            module_definition=module_definition,
            name='setme',
            scope=VariableDefinition.SCOPE_CHOICES.hand,
            data_type=VariableDefinition.DATA_TYPE_CHOICES.int,
        )
        self.use_var = HandVariableFactory(
            value=24, hand=self.hand, variable_definition=self.use_me, module=self.hand.current_module
        )
        self.set_var = HandVariableFactory(
            value=None, hand=self.hand, variable_definition=self.set_me, module=self.hand.current_module
        )
        self.action_step = ActionStepFactory(
            action_type=ActionStep.ACTION_TYPE_CHOICES.set_variable,
            value='useme * 2',
            variable_definition=self.set_me,
            for_each=ActionStep.FOR_EACH_CHOICES.current_hand_only,
        )

    def test_save(self):
        """
        Run actionstep and confirm expected value
        """

        self.action_step.run(self.hand)
        self.set_var.refresh_from_db()
        self.assertEqual(self.set_var.value, 24 * 2)

    @mock.patch('ery_backend.stints.models.Stint.set_status', autospec=True)
    def test_panic_on_undefined(self, mock_set_status):
        self.use_me.data_type = VariableDefinition.DATA_TYPE_CHOICES.str
        self.use_me.save()
        self.use_var.value = 'undefined_var'
        self.use_var.save()
        self.use_me.delete()

        with self.assertRaises(EryActionError):
            self.action_step.run(self.hand)
        mock_set_status.assert_any_call(self.hand.stint, Stint.STATUS_CHOICES.panicked)


class TestComplexSMSRender(EryTestCase):
    """
    Confirm non-block tag with declaration to other blocks is filled in appropriately.
    """

    def setUp(self):
        self.hand = create_test_hands(frontend_type='SMS').first()
        self.language = get_default_language()

    def test_mixed_nested_elements(self):
        widget = WidgetFactory(frontend=self.hand.frontend, code="output = 'abcd'; output;")
        ModuleDefinitionWidgetFactory(
            module_definition=self.hand.current_module_definition, name='MyModuleDefinitionWidget', widget=widget
        )
        stage_template = self.hand.stage.stage_definition.stage_templates.get(template__frontend__name='SMS')
        st_block = StageTemplateBlockFactory(stage_template=stage_template)
        StageTemplateBlockTranslationFactory(
            frontend=self.hand.frontend,
            stage_template_block=st_block,
            language=self.language,
            content='<Widget.MyModuleDefinitionWidget/>',
        )
        parental_block = stage_template.template.parental_template.blocks.first()
        parental_translation = parental_block.translations.first()
        parental_translation.content = f"""
<ul>
    <li>
        <{st_block.name}/>
    </li>
    <li>
        Something else.
    </li>
</ul>
"""
        parental_translation.save()
        output = self.hand.stage.render(self.hand)

        self.assertIn('abcd', output)
        self.assertIn('Something else.', output)


# XXX: Fix in 355
@unittest.skip("Fix in 355")
class TestActionStepCode(EryTestCase):
    """
    Confirm an Actionstep can set variable values via run_code
    """

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.hand = create_test_hands(n=1, frontend_type='Web').first()
        cls.vd_kwargs = {
            'module_definition': cls.hand.current_module_definition,
            'data_type': VariableDefinition.DATA_TYPE_CHOICES.int,
        }

    def setUp(self):
        self.action = ActionFactory(module_definition=self.hand.current_module_definition)

    def test_hand_var(self):
        hand_vd = VariableDefinitionFactory(name='handvar', scope=VariableDefinition.SCOPE_CHOICES.hand, **self.vd_kwargs)
        handvar = HandVariableFactory(value=24, hand=self.hand, variable_definition=hand_vd)
        ActionStepFactory(
            action=self.action,
            for_each=ActionStep.FOR_EACH_CHOICES.current_hand_only,
            action_type=ActionStep.ACTION_TYPE_CHOICES.run_code,
            value='handvar = handvar * 2; handvar',
        )

        self.action.run(self.hand)
        handvar.refresh_from_db()
        self.assertEqual(handvar.value, 48)

    def test_team_vars(self):
        team_vd = VariableDefinitionFactory(name='teamvar', scope=VariableDefinition.SCOPE_CHOICES.team, **self.vd_kwargs)
        team_vd2 = VariableDefinitionFactory(name='teamvarb', scope=VariableDefinition.SCOPE_CHOICES.team, **self.vd_kwargs)
        teamvar = TeamVariableFactory(value=25, team=self.hand.current_team, variable_definition=team_vd)
        teamvarb = TeamVariableFactory(value=50, team=self.hand.current_team, variable_definition=team_vd2)

        ActionStepFactory(
            action=self.action,
            for_each=ActionStep.FOR_EACH_CHOICES.current_hand_only,
            action_type=ActionStep.ACTION_TYPE_CHOICES.run_code,
            value='teamvar = teamvar * 2; teamvarb = teamvarb * 2;',
        )
        self.action.run(self.hand)
        teamvar.refresh_from_db()
        teamvarb.refresh_from_db()
        self.assertEqual(teamvar.value, 50)
        self.assertEqual(teamvarb.value, 100)

    def test_module_vars(self):
        module_vd = VariableDefinitionFactory(
            name='modulevar', scope=VariableDefinition.SCOPE_CHOICES.module, **self.vd_kwargs
        )
        modulevar = ModuleVariableFactory(value=100, module=self.hand.current_module, variable_definition=module_vd)
        ActionStepFactory(
            action=self.action,
            for_each=ActionStep.FOR_EACH_CHOICES.current_hand_only,
            action_type=ActionStep.ACTION_TYPE_CHOICES.run_code,
            value='modulevar = modulevar * 0',
        )
        self.action.run(self.hand)
        modulevar.refresh_from_db()
        self.assertEqual(modulevar.value, 0)


class TestForeignLanguage(EryTestCase):
    """
    Confirm foreign languages can be evaluated in engine.
    """

    def setUp(self):
        self.tamil = (
            'உங்கள் குடும்பத்தினருக்கு சொந்தமான கழிவறை உள்ளதா? நீங்கள்'
            ' உபயோகிக்ககூடிய ஒரு நிலையில் இல்லை என்றாலும், நீங்கள்'
            ' சொந்தமாக கழிவறை வைத்திருக்கிறீர்களா என்பதை தெரிந்து'
            ' கொள்வதில் நாங்கள் ஆர்வம் கொண்டிருக்கிறோம்.'
        )
        self.simple_tamil = 'உங்கள் குடும்பத்தினருக்கு சொந்தமான கழிவறை உள்ளதா?'
        self.hindi = (
            'क्या आपके घर में शौचालय है? हम जानना चाहते है यदि आपके पास शौचालय'
            ' है की नहीं भले ही वो उपयोग करने की दशा में न हो ।'
        )
        self.simple_hindi = 'क्या आपके घर में शौचालय है?'
        self.hand = create_test_hands(n=1).first()

    def test_condition(self):
        """
        Confirm conditions evaluate correctly with foreign languages.
        """
        # tamil
        condition = ConditionFactory(
            left_type=Condition.TYPE_CHOICES.expression,
            left_expression=f'"{self.tamil}"',
            right_type=Condition.TYPE_CHOICES.expression,
            right_expression=f'"{self.tamil}"',
            relation=Condition.RELATION_CHOICES.equal,
        )
        self.assertTrue(condition.evaluate(self.hand))

        condition.right_expression = f'"{self.simple_tamil}"'
        condition.save()
        self.assertFalse(condition.evaluate(self.hand))

        # hindi
        condition.left_expression = f'"{self.hindi}"'
        condition.right_expression = f'"{self.hindi}"'
        condition.save()
        self.assertTrue(condition.evaluate(self.hand))

    def test_actionstep_vardef(self):
        """
        Confirm actionstep sets variable correctly with foreign languages.
        """
        md = self.hand.current_module.stint_definition_module_definition.module_definition
        vd = VariableDefinitionFactory(
            module_definition=md,
            scope=VariableDefinition.SCOPE_CHOICES.hand,
            data_type=VariableDefinition.DATA_TYPE_CHOICES.str,
            validator=None,
            default_value=None,
        )
        hand_vd_var = HandVariableFactory(hand=self.hand, variable_definition=vd, value=None, module=self.hand.current_module)
        tamil_vd = VariableDefinitionFactory(
            module_definition=md,
            scope=VariableDefinition.SCOPE_CHOICES.hand,
            data_type=VariableDefinition.DATA_TYPE_CHOICES.str,
            validator=None,
            default_value=self.tamil,
        )
        HandVariableFactory(hand=self.hand, variable_definition=tamil_vd, value=None, module=self.hand.current_module)
        as_1 = ActionStepFactory(
            action__module_definition=md,
            action_type=ActionStep.ACTION_TYPE_CHOICES.set_variable,
            value=f'"{self.hindi}" + {tamil_vd.name}',
            variable_definition=vd,
            condition=None,
            for_each=ActionStep.FOR_EACH_CHOICES.current_hand_only,
        )
        as_1.run(self.hand)
        hand_vd_var.refresh_from_db()
        self.assertEqual(hand_vd_var.value, f'{self.hindi}{self.tamil}')


# XXX: Fix in 463
@unittest.skip("Fix in 463")
class TestBlockHolderMixin(EryTestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.template = TemplateFactory()
        cls.hand = create_test_hands(n=1).first()
        template_block = TemplateBlockFactory()
        cls.default_translation = TemplateBlockTranslationFactory(
            template_block=template_block, language=cls.template.primary_language
        )

    def test_general_ss_js_in_blocks(self):
        """
        Serverside evaluation on one match in block.
        """
        self.default_translation.content = "{{'This' + ' Is' + ' How' + ' We' + ' Dooo' + ' Iiit'}}"
        self.assertEqual(self.template.evaluate_block(self.default_translation.content, self.hand), 'This Is How We Dooo Iiit')

    def test_general_multiple_ss_js_in_blocks(self):
        """
        Serverside evaluation on multiple matches in block.
        """
        self.default_translation.content = (
            "If {{String(1+1)}} and {{String(2+1)}} is {{String(5)}}, then let's go to Subway" " and eat fresh!"
        )
        self.assertEqual(
            self.template.evaluate_block(self.default_translation.content, self.hand),
            "If 2 and 3 is 5, then let's go to Subway and eat fresh!",
        )

    @mock.patch('ery_backend.scripts.engine_client.evaluate')
    def test_general_escaping_in_blocks(self, mock_eval):
        """
        Verify escaped text is not evaluated via template.evaluate_block.
        """
        # pylint:disable=anomalous-backslash-in-string
        statement_1 = "\{\{ Dont Touch Me \}\}"
        # double braces escaped and therefore not evaluated
        self.default_translation.content = statement_1
        # double brace escapes should be removed after parsing
        self.assertEqual(self.template.evaluate_block(self.default_translation.content, self.hand), "{{ Dont Touch Me }}")
        mock_eval.assert_not_called()

    def test_escaping_by_engine_client_in_blocks(self):
        """
        Serverside evaluation considers escaped text. This is a test on how Node handles escaped brackets.
        """
        # pylint:disable=anomalous-backslash-in-string
        statement_1 = "'Inside of these braces is evaluated client side: \{1+1\}'"
        statement_2 = "'Double braces \{\{ \}\} can be escaped too'"
        statement_3 = "'This will probably crash the browser, but I will still send it! \{{1 + 2'"
        # single braces are escaped via engine client
        self.default_translation.content = f"{{{{{statement_1}}}}}"
        self.assertEqual(
            self.template.evaluate_block(self.default_translation.content, self.hand),
            "Inside of these braces is evaluated client side: {1+1}",
        )
        # engine client escapes double braces
        self.default_translation.content = f"{{{{{statement_2}}}}}"
        self.assertEqual(
            self.template.evaluate_block(self.default_translation.content, self.hand), "Double braces {{ }} can be escaped too"
        )
        # engine client ignores symmetry while escaping
        self.default_translation.content = f"{{{{{statement_3}}}}}"
        self.assertEqual(
            self.template.evaluate_block(self.default_translation.content, self.hand),
            "This will probably crash the browser, but I will still send it! {{1 + 2",
        )

    def test_nested_eval_error(self):
        """
        Serverside evaluation should not be nested.
        """
        # This statement consists of three nested server side calls.
        self.default_translation.content = "{{1+{{1+{{1+1}}}}}}"
        with self.assertRaises(grpc.RpcError):
            self.template.evaluate_block(self.default_translation.content, self.hand)

    def test_variable_evaluation(self):
        """
        Variables should be accessible via hand's context.
        """
        vd = VariableDefinitionFactory(
            module_definition=self.hand.stage.stage_definition.module_definition, scope=VariableDefinition.SCOPE_CHOICES.hand
        )
        var = HandVariableFactory(hand=self.hand, variable_definition=vd)
        self.default_translation.content = f"{{{{{vd.name} + ' is accessible in context.'}}}}"
        self.assertEqual(
            self.template.evaluate_block(self.default_translation.content, self.hand), f"{var.value} is accessible in context."
        )

    def test_procedure_evaluation(self):
        """
        Procedures should be accessible via hand's context.
        """
        procedure = ProcedureFactory(
            name='get_money', comment='Don\'t ask questions!', code='job_title * swag_quantity - hidden_fees'
        )
        ModuleDefinitionProcedureFactory(
            name='get_money', procedure=procedure, module_definition=self.hand.current_module_definition
        )
        ProcedureArgumentFactory(name='job_title', default=0, procedure=procedure, order=2)
        ProcedureArgumentFactory(name='swag_quantity', procedure=procedure, order=0)
        ProcedureArgumentFactory(name='hidden_fees', procedure=procedure, order=1)
        self.default_translation.content = "{{get_money(2, 100, 55)}}"
        # should calculate number of dollarydoos
        self.assertEqual(self.template.evaluate_block(self.default_translation.content, self.hand), '10.0')


@unittest.skip
class TestVariableDataTypes(EryTestCase):
    """
    Confirm expected Variable types can be sent to the engine
    """

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.hand = create_test_hands(n=1).first()
        cls.base_kwargs = {'scope': VariableDefinition.SCOPE_CHOICES.hand, 'validator': None}

    # def setUp(self):

    def test_bool(self):
        vd = VariableDefinitionFactory(data_type=VariableDefinition.DATA_TYPE_CHOICES.bool, **self.base_kwargs)
        hv = HandVariableFactory(hand=self.hand, variable_definition=vd, value=False)
        returned_value = evaluate('test', self.hand, f'{hv.variable_definition.name}')
        self.assertFalse(returned_value)

        hv.value = 'true'
        hv.save()
        returned_value = evaluate('test', self.hand, f'{hv.variable_definition.name}')
        self.assertTrue(returned_value)

    def test_list(self):
        vd = VariableDefinitionFactory(data_type=VariableDefinition.DATA_TYPE_CHOICES.list, **self.base_kwargs)
        hv = HandVariableFactory(hand=self.hand, variable_definition=vd, value=['This', 'A', 'List'])
        returned_value = evaluate('test', self.hand, f'{hv.variable_definition.name}')
        self.assertEqual(hv.value, returned_value)

    def test_dict(self):
        vd = VariableDefinitionFactory(data_type=VariableDefinition.DATA_TYPE_CHOICES.dict, **self.base_kwargs)
        hv = HandVariableFactory(hand=self.hand, variable_definition=vd, value={'is_dict': True})
        returned_value = evaluate('test', self.hand, f'{hv.variable_definition.name}')
        self.assertEqual(hv.value, returned_value)


class TestCommandTemplateRender(EryTestCase):
    def setUp(self):
        sms = Frontend.objects.get(name='SMS')
        language = Language.objects.get(pk='en')
        self.hand = HandFactory(frontend=sms)
        vd = VariableDefinitionFactory(name='answer', validator=None, data_type=VariableDefinition.DATA_TYPE_CHOICES.str)
        HandVariableFactory(hand=self.hand, value='Who I say I am!', variable_definition=vd)
        template = TemplateFactory(frontend=sms)
        root_block = TemplateBlockFactory(template=template)
        TemplateBlockTranslationFactory(
            content='<Question/>\n<Answer/>', frontend=sms, language=language, template_block=root_block
        )
        self.command = CommandFactory()
        command_render_template = TemplateFactory(frontend=sms, parental_template=template)
        command_template = CommandTemplateFactory(command=self.command, template=command_render_template)
        command_question_block = CommandTemplateBlockFactory(name='Question', command_template=command_template)
        CommandTemplateBlockTranslationFactory(
            content='Who am I?', frontend=sms, language=language, command_template_block=command_question_block
        )
        command_answer_block = CommandTemplateBlockFactory(name='Answer', command_template=command_template)
        CommandTemplateBlockTranslationFactory(
            content='{{answer}}', frontend=sms, language=language, command_template_block=command_answer_block
        )

    @unittest.skip("Address in issue #457")
    def test_sms_render(self):
        expected_content = 'Who am I?\nWho I say I am!'
        self.assertEqual(self.command.render(self.hand), expected_content)


class TestComplexRedirect(EryTestCase):
    """
    Confirms redirect occur based on condition evaluation.
    """

    def setUp(self):
        self.hand = create_test_hands(n=1, stage_n=5).first()
        self.stages = list(self.hand.current_module_definition.stage_definitions.order_by('id').all())
        self.condition_vd_1 = VariableDefinitionFactory(
            data_type=VariableDefinition.DATA_TYPE_CHOICES.int,
            scope=VariableDefinition.SCOPE_CHOICES.hand,
            module_definition=self.hand.current_module_definition,
            validator=None,
        )
        self.condition_vd_2 = VariableDefinitionFactory(
            data_type=VariableDefinition.DATA_TYPE_CHOICES.int,
            scope=VariableDefinition.SCOPE_CHOICES.hand,
            module_definition=self.hand.current_module_definition,
            validator=None,
        )
        self.hand_vd_1 = HandVariableFactory(
            variable_definition=self.condition_vd_1, hand=self.hand, value=1, module=self.hand.current_module
        )
        self.hand_vd_2 = HandVariableFactory(
            variable_definition=self.condition_vd_2, hand=self.hand, value=1, module=self.hand.current_module
        )
        self.vd_1_is_5 = ConditionFactory(
            left_type=Condition.TYPE_CHOICES.variable,
            right_type=Condition.TYPE_CHOICES.expression,
            left_variable_definition=self.condition_vd_1,
            right_expression=str(5),
        )
        self.vd_1_is_10 = ConditionFactory(
            left_type=Condition.TYPE_CHOICES.variable,
            right_type=Condition.TYPE_CHOICES.expression,
            left_variable_definition=self.condition_vd_1,
            right_expression=str(10),
        )
        self.vd_2_is_3 = ConditionFactory(
            left_type=Condition.TYPE_CHOICES.variable,
            right_type=Condition.TYPE_CHOICES.expression,
            left_variable_definition=self.condition_vd_2,
            right_expression=str(3),
        )
        self.vd_2_is_4 = ConditionFactory(
            left_type=Condition.TYPE_CHOICES.variable,
            right_type=Condition.TYPE_CHOICES.expression,
            left_variable_definition=self.condition_vd_2,
            right_expression=str(4),
        )
        RedirectFactory(
            condition=self.vd_1_is_5, stage_definition=self.stages[0], next_stage_definition=self.stages[1], order=2
        )
        RedirectFactory(
            condition=self.vd_1_is_10, stage_definition=self.stages[0], next_stage_definition=self.stages[2], order=1
        )
        RedirectFactory(
            condition=self.vd_2_is_3, stage_definition=self.stages[0], next_stage_definition=self.stages[3], order=3
        )
        RedirectFactory(
            condition=self.vd_2_is_4, stage_definition=self.stages[0], next_stage_definition=self.stages[3], order=4
        )

    def test_condition_evaluation(self):
        """Condition must be true for redirect to occur"""
        self.hand.stint.set_variable(self.condition_vd_2, 4, self.hand)
        self.assertFalse(self.vd_1_is_5.evaluate(self.hand))
        self.assertTrue(self.vd_2_is_4.evaluate(self.hand))
        # Since first encountered condition is false, latter is used
        self.hand.stage.stage_definition.submit(self.hand)
        self.hand.refresh_from_db()
        self.assertEqual(self.hand.stage.stage_definition, self.stages[3])

    def test_redirect_priority(self):
        """When both vd_2_is_4 and vd_1_is_5 are true, order forces priority"""
        self.hand.stint.set_variable(self.condition_vd_1, 5, self.hand)
        self.hand.stint.set_variable(self.condition_vd_2, 4, self.hand)
        self.assertTrue(self.vd_1_is_5.evaluate(self.hand))
        self.assertTrue(self.vd_2_is_4.evaluate(self.hand))
        self.hand.stage.stage_definition.submit(self.hand)
        self.hand.refresh_from_db()
        self.assertEqual(self.hand.stage.stage_definition, self.stages[1])
