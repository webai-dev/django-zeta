import copy
from unittest import mock

from ery_backend.base.testcases import EryTestCase, create_test_hands
from ery_backend.frontends.models import Frontend
from ery_backend.frontends.sms_utils import SMSStageTemplateRenderer
from ery_backend.modules.factories import ModuleDefinitionWidgetFactory, WidgetChoiceFactory, WidgetChoiceTranslationFactory
from ery_backend.modules.models import ModuleDefinitionWidget
from ery_backend.teams.factories import TeamFactory
from ery_backend.variables.factories import (
    HandVariableFactory,
    TeamVariableFactory,
    ModuleVariableFactory,
    VariableDefinitionFactory,
)
from ery_backend.variables.models import VariableDefinition
from ..grpc.engine_pb2 import JavascriptOp, Result, Value
from ..engine_client import interpret_backend_variable, make_javascript_op, evaluate


class TestCaching(EryTestCase):
    """
    Confirm values cached as expected during engine_client.evaluate.
    """

    def setUp(self):
        self.hand = create_test_hands(n=1, signal_pubsub=False).first()

    @mock.patch('ery_backend.scripts.engine_client._run_javascript_op')
    def test_caching_off(self, mock_run_js):
        """
        Confirm result of evaluate is not cached when cached=False.

        Note: Since make_javascript_op timestamps and is impossible to recreate in a
        mock call, assert_called_once is caught and inspected.
        """
        mock_run_js.return_value = Result(value=Value(string_value='abc'))
        evaluate('test', self.hand, '3*3', cached=False)
        evaluate('test', self.hand, '3*3')
        failed = True
        try:
            mock_run_js.assert_called_once()
        except AssertionError as e:
            if 'Called 2 times' in e.args[0]:
                failed = False
        self.assertFalse(failed)

    @mock.patch('ery_backend.scripts.engine_client._run_javascript_op')
    def test_caching_on(self, mock_run_js):
        """
        Confirm result of evaluate is cached when cached=True.

        Note: Since make_javascript_op timestamps and is impossible to recreate in a
        mock call, assert_called_once is caught and inspected.
        """
        mock_run_js.return_value = Result(value=Value(string_value='abc'))
        evaluate('test', self.hand, '3*3', cached=True)
        evaluate('test', self.hand, '3*3')
        mock_run_js.assert_called_once()


class TestInterpretVariables(EryTestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.hand = create_test_hands(n=1, signal_pubsub=False).first()
        cls.team = TeamFactory(stint=cls.hand.stint)
        cls.hand.current_team = cls.team
        cls.hand.save()

    def test_interpret_hand(self):
        # int HandVariable
        hand_variable_definition = VariableDefinitionFactory(
            validator=None,
            name='testvd',
            module_definition=self.hand.current_module_definition,
            data_type=VariableDefinition.DATA_TYPE_CHOICES.int,
        )
        hand_var = HandVariableFactory(value=2, variable_definition=hand_variable_definition, hand=self.hand)
        hand_var.value = 2
        hand_var.save()
        interpreted_hand_var = interpret_backend_variable(hand_var)
        self.assertEqual(interpreted_hand_var.value.number_value, hand_var.value)

    def test_interpret_team(self):
        # bool TeamVariable
        team_variable_definition = VariableDefinitionFactory(
            validator=None,
            name='testvd3',
            module_definition=self.hand.current_module_definition,
            data_type=VariableDefinition.DATA_TYPE_CHOICES.bool,
        )
        team_var = TeamVariableFactory(team=self.team, value=True, variable_definition=team_variable_definition)
        interpreted_team_var = interpret_backend_variable(team_var)
        self.assertEqual(interpreted_team_var.value.bool_value, team_var.value)

    def test_interpret_module(self):
        # float ModuleVariable
        module_variable_definition = VariableDefinitionFactory(
            validator=None,
            name='testvd2',
            module_definition=self.hand.current_module_definition,
            data_type=VariableDefinition.DATA_TYPE_CHOICES.float,
        )

        module_var = ModuleVariableFactory(
            module=self.hand.current_module, value=3.4, variable_definition=module_variable_definition
        )
        interpreted_float_module_var = interpret_backend_variable(module_var)
        self.assertEqual(interpreted_float_module_var.value.number_value, module_var.value)


class TestJavascriptOp(EryTestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.hand = create_test_hands(n=1, frontend_type='SMS', signal_pubsub=False).first()
        cls.choice_widget = ModuleDefinitionWidgetFactory(
            required_widget=True, initial_value='starting-val', random_mode=ModuleDefinitionWidget.RANDOM_CHOICES.desc
        )
        WidgetChoiceFactory(widget=cls.choice_widget, order=0)
        WidgetChoiceFactory(widget=cls.choice_widget, order=1)

    def test_make_javascript_op(self):
        """
        Confirm javascript_op includes expected content
        """
        code = 'testvd * testvd2'
        result = make_javascript_op('Hej', code, self.hand)
        self.assertIsInstance(result, JavascriptOp)
        self.assertEqual(result.script.name, 'Hej')
        self.assertEqual(result.script.code, code)
        self.assertEqual(result.context.stint.name, self.hand.stint.stint_specification.stint_definition.slug)
        self.assertEqual(result.context.era.name, self.hand.era.name)
        self.assertEqual(result.context.stage.name, self.hand.stage.stage_definition.name)
        # test_hand includes extra variables that are not assigned values which should not be expected in op.
        expected_vars = [
            interpret_backend_variable(var)
            for var in list(self.hand.variables.all())
            + list(self.hand.current_team.variables.all())
            + list(self.hand.current_module.variables.all())
            if var.value is not None
        ]
        result_vars = list(result.context.variables.values())
        for var in expected_vars:
            self.assertIn(var, result_vars)


class TestEvaluate(EryTestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.sms = Frontend.objects.get(name='SMS')
        cls.hand = create_test_hands(n=1, frontend_type='SMS', signal_pubsub=False).first()
        cls.choice_widget = ModuleDefinitionWidgetFactory(
            required_widget=True,
            initial_value='starting-val',
            random_mode=ModuleDefinitionWidget.RANDOM_CHOICES.desc,
            variable_definition=None,
        )
        WidgetChoiceFactory(widget=cls.choice_widget, order=0)
        WidgetChoiceFactory(widget=cls.choice_widget, order=1)

    @mock.patch('ery_backend.scripts.engine_client._run_javascript_op')
    @mock.patch('ery_backend.scripts.engine_client.make_javascript_op')
    def test_add_extra_variables_to_context(self, mock_op, mock_eval):
        """
        Confirm protobuf List of protobuf Variables(WidgetChoices) added correctly to context of protobuf JavascriptOp
        """
        mock_eval.return_value = Result(value=Value(string_value='abc'))
        context = self.hand.stint.get_context(self.hand)
        for widget_choice in self.choice_widget.choices.all():
            WidgetChoiceTranslationFactory(
                language=self.hand.current_module_definition.primary_language, widget_choice=widget_choice
            )
        choices = self.choice_widget.get_choices_as_extra_variable(self.hand.current_module_definition.primary_language)
        context['variables']['choices'] = (None, choices['choices'])
        evaluate('test', self.hand, 'test some code', extra_variables=choices)
        mock_op.assert_called_with('test', 'test some code', self.hand, context)

    @mock.patch('ery_backend.scripts.engine_client.cache.get')
    @mock.patch('ery_backend.scripts.engine_client._run_javascript_op')
    @mock.patch('ery_backend.scripts.engine_client.make_javascript_op')
    def test_choices_if_widget_multiple_choice(self, mock_op, mock_eval, mock_cache):
        """
        Choices should only automatically appear in op if widget is multiple choice
        """
        stage_template = self.hand.stage.stage_definition.stage_templates.get(template__frontend=self.sms)
        renderer = SMSStageTemplateRenderer(stage_template, self.hand)
        mock_eval.return_value = Result(value=Value(string_value='abc'))
        mock_cache.return_value = None
        context = self.hand.stint.get_context(self.hand)
        for widget_choice in self.choice_widget.choices.all():
            WidgetChoiceTranslationFactory(
                language=self.hand.current_module_definition.primary_language, widget_choice=widget_choice
            )
        renderer.render_widget(self.choice_widget)
        choices = self.choice_widget.get_choices_as_extra_variable(self.hand.current_module_definition.primary_language)
        choice_context = copy.deepcopy(context)
        choice_context['variables']['choices'] = (None, choices['choices'])
        # should contain choices when multiple choice input
        mock_op.assert_called_with(
            f'render_{self.choice_widget.widget}', self.choice_widget.widget.code, self.hand, choice_context
        )

        no_choice_variable_definition = VariableDefinitionFactory(
            exclude=[VariableDefinition.DATA_TYPE_CHOICES.stage, VariableDefinition.DATA_TYPE_CHOICES.choice]
        )
        no_choice_widget = ModuleDefinitionWidgetFactory(variable_definition=no_choice_variable_definition)
        # should not contain choices
        renderer.render_widget(no_choice_widget)
        mock_op.assert_any_call(f'render_{no_choice_widget.widget}', no_choice_widget.widget.code, self.hand, context)
