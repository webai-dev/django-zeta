import json
import unittest
from unittest import mock

from django.core.exceptions import ValidationError
from django.db import IntegrityError

from languages_plus.models import Language

from ery_backend.base.exceptions import EryValueError, EryValidationError
from ery_backend.base.testcases import EryTestCase, create_test_hands, create_test_stintdefinition, random_dt_value
from ery_backend.frontends.models import Frontend
from ery_backend.hands.factories import HandFactory
from ery_backend.modules.factories import (
    ModuleDefinitionFactory,
    ModuleFactory,
    ModuleDefinitionWidgetFactory,
    WidgetChoiceFactory,
)
from ery_backend.syncs.factories import EraFactory
from ery_backend.stages.factories import StageDefinitionFactory, StageFactory
from ery_backend.stint_specifications.factories import StintSpecificationFactory, StintSpecificationVariableFactory
from ery_backend.users.factories import UserFactory
from ery_backend.stints.factories import StintFactory
from ery_backend.teams.factories import TeamFactory
from ery_backend.teams.models import TeamHand
from ery_backend.validators.factories import ValidatorFactory
from ery_backend.variables.models import HandVariable, TeamVariable, ModuleVariable
from ..factories import (
    VariableDefinitionFactory,
    VariableChoiceItemFactory,
    ModuleVariableFactory,
    TeamVariableFactory,
    HandVariableFactory,
    VariableChoiceItemTranslationFactory,
)
from ..models import VariableDefinition, VariableChoiceItem


class TestVariableDefinition(EryTestCase):
    def setUp(self):
        validator_regex_num = ValidatorFactory(code=None, regex="^\\d+\\.?\\d*$", name="validator_regex_num")
        validator_code = ValidatorFactory(code="some code", regex=None, name="validator_code", nullable=True)
        self.module_definition = ModuleDefinitionFactory()
        self.variable_definition1 = VariableDefinitionFactory(
            scope=VariableDefinition.SCOPE_CHOICES.hand,
            data_type=VariableDefinition.DATA_TYPE_CHOICES.float,
            specifiable=True,
            is_payoff=True,
            is_output_data=False,
            default_value=42,
            validator=validator_regex_num,
            comment='Testing comment attribute',
            name='test_var',
            module_definition=self.module_definition,
            monitored=True,
        )

        self.variable_definition2 = VariableDefinitionFactory(
            scope=VariableDefinition.SCOPE_CHOICES.team,
            data_type=VariableDefinition.DATA_TYPE_CHOICES.float,
            specifiable=False,
            is_payoff=False,
            is_output_data=True,
            default_value=1.234,
            validator=validator_code,
        )

        self.variable_definition3 = VariableDefinitionFactory(
            scope=VariableDefinition.SCOPE_CHOICES.module,
            data_type=VariableDefinition.DATA_TYPE_CHOICES.choice,
            specifiable=False,
            is_payoff=False,
            is_output_data=False,
            validator=validator_code,
        )

        self.choice_item = VariableChoiceItemFactory(variable_definition=self.variable_definition3)
        self.choice_item_2 = VariableChoiceItemFactory(variable_definition=self.variable_definition3)
        self.variable_definition3.default_value = self.choice_item.value
        self.variable_definition3.save()

    def test_exists(self):
        self.assertIsNotNone(self.variable_definition1)
        self.assertIsNotNone(self.variable_definition2)
        self.assertIsNotNone(self.variable_definition3)

    def test_expected_attributes1(self):
        self.variable_definition1.refresh_from_db()  # Get typecasted values
        self.assertEqual(self.variable_definition1.scope, VariableDefinition.SCOPE_CHOICES.hand)
        self.assertEqual(self.variable_definition1.data_type, VariableDefinition.DATA_TYPE_CHOICES.float)
        self.assertEqual(self.variable_definition1.specifiable, True)
        self.assertEqual(self.variable_definition1.is_payoff, True)
        self.assertEqual(self.variable_definition1.is_output_data, False)
        self.assertEqual(self.variable_definition1.default_value, 42)
        self.assertEqual(self.variable_definition1.validator.code, None)
        self.assertEqual(self.variable_definition1.validator.regex, "^\\d+\\.?\\d*$")
        self.assertEqual(self.variable_definition1.name, 'test_var')
        self.assertEqual(self.variable_definition1.comment, 'Testing comment attribute')
        self.assertEqual(self.variable_definition1.module_definition, self.module_definition)
        self.assertIsNotNone(self.variable_definition1.slug)
        self.assertTrue(self.variable_definition1.monitored)

    def test_expected_attributes2(self):
        self.variable_definition2.refresh_from_db()  # Get typecasted values
        self.assertEqual(self.variable_definition2.scope, VariableDefinition.SCOPE_CHOICES.team)
        self.assertEqual(self.variable_definition2.data_type, VariableDefinition.DATA_TYPE_CHOICES.float)
        self.assertEqual(self.variable_definition2.specifiable, False)
        self.assertEqual(self.variable_definition2.is_payoff, False)
        self.assertEqual(self.variable_definition2.is_output_data, True)
        self.assertEqual(self.variable_definition2.default_value, 1.234)
        self.assertEqual(self.variable_definition2.validator.code, "some code")
        self.assertEqual(self.variable_definition2.validator.regex, None)

    def test_expected_attributes3(self):
        self.variable_definition3.refresh_from_db()  # Get typecasted values
        self.assertEqual(self.variable_definition3.scope, VariableDefinition.SCOPE_CHOICES.module)
        self.assertEqual(self.variable_definition3.data_type, VariableDefinition.DATA_TYPE_CHOICES.choice)
        self.assertEqual(self.variable_definition3.specifiable, False)
        self.assertEqual(self.variable_definition3.is_payoff, False)
        self.assertEqual(self.variable_definition3.is_output_data, False)
        self.assertEqual(self.variable_definition3.default_value, self.choice_item.value)
        self.assertEqual(self.variable_definition3.validator.code, "some code")
        self.assertEqual(self.variable_definition3.validator.regex, None)

    def test_get_privilege_ancestor(self):
        self.assertEqual(self.variable_definition1.get_privilege_ancestor(), self.variable_definition1.module_definition)

    def test_get_privilege_ancestor_cls(self):
        self.assertEqual(
            self.variable_definition1.get_privilege_ancestor_cls(), self.variable_definition1.module_definition.__class__
        )

    def test_get_privilege_ancestor_filter_path(self):
        self.assertEqual(self.variable_definition1.get_privilege_ancestor_filter_path(), 'module_definition')

    def test_payoff_errors(self):
        """
        Confirm constraints related to is_payoff
        """
        with self.assertRaises(ValueError):
            # Must be hand scope
            VariableDefinitionFactory(
                is_payoff=True,
                scope=VariableDefinition.SCOPE_CHOICES.module,
                data_type=VariableDefinition.DATA_TYPE_CHOICES.float,
            )
        with self.assertRaises(TypeError):
            # Must be float
            VariableDefinitionFactory(
                is_payoff=True, scope=VariableDefinition.SCOPE_CHOICES.hand, data_type=VariableDefinition.DATA_TYPE_CHOICES.int
            )

    def test_duplicate(self):
        default_language = Language.objects.first()
        duplicate_me = VariableDefinitionFactory(data_type=VariableDefinition.DATA_TYPE_CHOICES.choice)
        vci = VariableChoiceItemFactory(variable_definition=duplicate_me)
        VariableChoiceItemTranslationFactory(variable_choice_item=vci, language=default_language, caption="test caption.")
        variable_2 = duplicate_me.duplicate()
        self.assertIsNotNone(variable_2)
        self.assertEqual('{}_copy'.format(duplicate_me.name), variable_2.name)
        variable_choice_item_2 = VariableChoiceItem.objects.filter(variable_definition=duplicate_me, value=vci.value).first()
        self.assertIsNotNone(variable_choice_item_2)
        # Parents should be equivalent
        self.assertEqual(duplicate_me.module_definition, variable_2.module_definition)
        # Siblings should be equivalent
        self.assertEqual(duplicate_me.validator, variable_2.validator)
        # Children should not be equivalent
        self.assertIn(variable_choice_item_2, duplicate_me.variablechoiceitem_set.all())

        self.assertEqual(variable_choice_item_2.translations.get(language=default_language).caption, "test caption.")

    def test_realize_errors(self):
        """
        Confirm errors arise for incorrect args.
        """
        hand = create_test_hands(signal_pubsub=False).first()
        module = hand.current_module
        teams = list(hand.stint.teams.all())
        hands = [hand]

        hand_vd = VariableDefinitionFactory(scope=VariableDefinition.SCOPE_CHOICES.hand)
        with self.assertRaises(EryValidationError):
            hand_vd.realize(module, teams, None)

        team_vd = VariableDefinitionFactory(scope=VariableDefinition.SCOPE_CHOICES.team)
        with self.assertRaises(EryValidationError):
            team_vd.realize(module, None, hands)

        module_vd = VariableDefinitionFactory(scope=VariableDefinition.SCOPE_CHOICES.module)
        with self.assertRaises(EryValidationError):
            module_vd.realize(None, teams, hands)

    def test_realize(self):
        stint = StintFactory()
        module = ModuleFactory(stint=stint)
        era = EraFactory()
        team0 = TeamFactory(stint=stint, era=era)
        team1 = TeamFactory(stint=stint, era=era)
        stage = StageFactory()

        user00 = UserFactory()
        user01 = UserFactory()
        user10 = UserFactory()
        user11 = UserFactory()
        user12 = UserFactory()

        hand00 = HandFactory(user=user00, stint=stint, era=era, stage=stage)
        hand01 = HandFactory(user=user01, stint=stint, era=era, stage=stage)
        hand10 = HandFactory(user=user10, stint=stint, era=era, stage=stage)
        hand11 = HandFactory(user=user11, stint=stint, era=era, stage=stage)
        hand12 = HandFactory(user=user12, stint=stint, era=era, stage=stage)

        team_hand_relationship0 = TeamHand(team=team0, hand=hand00)
        team_hand_relationship1 = TeamHand(team=team0, hand=hand01)
        team_hand_relationship2 = TeamHand(team=team1, hand=hand10)
        team_hand_relationship3 = TeamHand(team=team1, hand=hand11)
        team_hand_relationship4 = TeamHand(team=team1, hand=hand12)
        team_hand_relationship0.save()
        team_hand_relationship1.save()
        team_hand_relationship2.save()
        team_hand_relationship3.save()
        team_hand_relationship4.save()

        n_hand, n_team, n_module = self._get_number_of_variables()
        teams = stint.teams.all()
        hands = stint.hands.all()
        self.variable_definition1.realize(module, teams=teams, hands=hands)
        self._assert_number_of_variables(n_hand + 5, n_team, n_module)
        self.assertEqual(len(HandVariable.objects.filter(variable_definition=self.variable_definition1)), 5)
        self.assertEqual(len(HandVariable.objects.filter(variable_definition=self.variable_definition1, hand=hand00)), 1)
        self.assertEqual(len(HandVariable.objects.filter(variable_definition=self.variable_definition1, hand=hand01)), 1)
        self.assertEqual(len(HandVariable.objects.filter(variable_definition=self.variable_definition1, hand=hand10)), 1)
        self.assertEqual(len(HandVariable.objects.filter(variable_definition=self.variable_definition1, hand=hand11)), 1)
        self.assertEqual(len(HandVariable.objects.filter(variable_definition=self.variable_definition1, hand=hand12)), 1)

        self.variable_definition2.realize(module, teams=teams, hands=hands)
        self._assert_number_of_variables(n_hand + 5, n_team + 2, n_module)
        self.assertEqual(len(TeamVariable.objects.filter(variable_definition=self.variable_definition2, team=team0)), 1)
        self.assertEqual(len(TeamVariable.objects.filter(variable_definition=self.variable_definition2, team=team1)), 1)

        self.variable_definition3.realize(module, teams=teams, hands=hands)
        self._assert_number_of_variables(n_hand + 5, n_team + 2, n_module + 1)
        self.assertEqual(len(ModuleVariable.objects.filter(variable_definition=self.variable_definition3, module=module)), 1)

    def test_realize_with_value(self):
        """
        Confirm realize can override a default value with a value from a StintSpecificationVariable
        """
        sd = create_test_stintdefinition(Frontend.objects.get(name='Web'))
        module_def = sd.module_definitions.first()
        ss = StintSpecificationFactory(stint_definition=sd)
        variable_definition = VariableDefinitionFactory(
            exclude=(VariableDefinition.DATA_TYPE_CHOICES.stage), module_definition=module_def
        )

        ssv = StintSpecificationVariableFactory(
            stint_specification=ss,
            variable_definition=variable_definition,
            value=random_dt_value(variable_definition.data_type),
        )
        stint = sd.realize(ss)
        HandFactory(stint=stint)
        stint.start(UserFactory(), signal_pubsub=False)
        module = stint.modules.first()
        variable = VariableDefinition.get_variable_cls_from_scope(variable_definition.scope).objects.get(
            variable_definition__name=variable_definition.name, module=module
        )
        self.assertEqual(variable.value, ssv.value)

    def _assert_number_of_variables(self, n_hand, n_team, n_module):
        self.assertEqual(len(HandVariable.objects.all()), n_hand)
        self.assertEqual(len(TeamVariable.objects.all()), n_team)
        self.assertEqual(len(ModuleVariable.objects.all()), n_module)

    @staticmethod
    def _get_number_of_variables():
        return (len(HandVariable.objects.all()), len(TeamVariable.objects.all()), len(ModuleVariable.objects.all()))

    def test_expected_datatype_errors(self):
        """
        Confirm errors raised as expected on save.
        """
        # can't change VarDef type to int or float from choice if doing so invalidates connected inputs
        with self.assertRaises(EryValidationError):
            self.variable_definition3.data_type = VariableDefinition.DATA_TYPE_CHOICES.int
            self.variable_definition3.default_value = random_dt_value(self.variable_definition3.data_type)
            self.variable_definition3.save()
        with self.assertRaises(EryValidationError):
            self.variable_definition3.data_type = VariableDefinition.DATA_TYPE_CHOICES.float
            self.variable_definition3.default_value = random_dt_value(self.variable_definition3.data_type)
            self.variable_definition3.save()

        # can't change VarDef type to int, float, str from choice if has variablechoiceitems
        with self.assertRaises(EryValidationError):
            self.variable_definition3.data_type = VariableDefinition.DATA_TYPE_CHOICES.str
            self.variable_definition3.default_value = random_dt_value(self.variable_definition3.data_type)
            self.variable_definition3.save()
        with self.assertRaises(EryValidationError):
            self.variable_definition3.data_type = VariableDefinition.DATA_TYPE_CHOICES.float
            self.variable_definition3.default_value = random_dt_value(self.variable_definition3.data_type)
            self.variable_definition3.save()
        with self.assertRaises(EryValidationError):
            self.variable_definition3.data_type = VariableDefinition.DATA_TYPE_CHOICES.int
            self.variable_definition3.default_value = random_dt_value(self.variable_definition3.data_type)
            self.variable_definition3.save()

    @unittest.skip("XXX: Address in issue #813")
    def test_expected_default_errors(self):
        """
        Confirm errors raised as expected on save
        """
        # cannot save default_value that is not subset of variablechoiceitem values if vardef data_type is choice
        with self.assertRaises(EryValueError):
            self.variable_definition3.default_value = 3
            self.variable_definition3.save()

    def test_expected_naming_errors(self):
        """
        Confirm VariableDefinition cannot violate js naming conventions.
        """
        valid = ['x', 'y', 'z', 'abc1', 'x_1', 'test_variable', 'foo', '_foo', '_var1']
        invalid = ['abc-1', '1-abc', 'test-var', 'with', 'else', 'a b c', 'a+b', 'a + b', 'x*y']

        for n in valid:
            VariableDefinitionFactory(name=n)

        for n in invalid:
            with self.assertRaises(ValidationError):
                VariableDefinitionFactory(name=n)

        # reserved words
        default_kwargs = {'validator': None, 'is_payoff': False}
        with self.assertRaises(ValidationError):
            VariableDefinitionFactory(name='choices', **default_kwargs)
        with self.assertRaises(ValidationError):
            VariableDefinitionFactory(name='var', **default_kwargs)
        with self.assertRaises(ValidationError):
            VariableDefinitionFactory(name='in', **default_kwargs)
        with self.assertRaises(ValidationError):
            VariableDefinitionFactory(name='for', **default_kwargs)

        # punctuation
        # valid
        VariableDefinitionFactory(name='$hasdollarsign', **default_kwargs)
        VariableDefinitionFactory(name='has_underscore', **default_kwargs)
        # invalid
        with self.assertRaises(ValidationError):
            VariableDefinitionFactory(name='incorrect.punctuation', **default_kwargs)

        # numbers
        # valid
        VariableDefinitionFactory(name='endswith2')
        # invalid
        with self.assertRaises(ValidationError):
            VariableDefinitionFactory(name='3time2time1timebop')

        # spaces
        with self.assertRaises(ValidationError):
            VariableDefinitionFactory(name='has spaces')

    @unittest.skip("Address in issue #465")
    @mock.patch('ery_backend.variables.models.VariableDefinition.cast')
    @mock.patch('ery_backend.variables.models.VariableDefinition.validate')
    @mock.patch('ery_backend.variables.models.VariableDefinition._validate_choice_items', autospec=True)
    @mock.patch('ery_backend.variables.models.VariableDefinition._validate_payoff', autospec=True)
    def test_clean(self, mock_validate_payoff, mock_validate_choices, mock_validate, mock_cast):
        """
        Confirm expected methods are called during clean.
        """
        mock_cast.return_value = 42
        self.variable_definition1.clean()
        mock_cast.assert_called_with(42)
        mock_validate.assert_called_with(42)
        mock_validate_choices.assert_called_with(self.variable_definition1)

    @mock.patch('ery_backend.variables.models.VariableDefinition._validate_payoff', autospec=True)
    def test_post_clean(self, mock_validate_payoff):
        """
        Confirm expected methods are called during post-save-clean.
        """
        self.variable_definition1.validator = None
        self.variable_definition1.save()

        self.variable_definition1.post_save_clean()
        mock_validate_payoff.assert_called_with(self.variable_definition1)

    def test_expected_stage_save_errors(self):
        """
        Confirm save errors for save attribute.
        """
        vd = VariableDefinition.objects.create(
            data_type=VariableDefinition.DATA_TYPE_CHOICES.stage,
            default_value=None,
            name='test_vd',
            module_definition=ModuleDefinitionFactory(),
        )
        # stage with name does not exist
        with self.assertRaises(ValueError):
            vd.default_value = 'anti-test-stage'
            vd.save()
        # stage with name exists, but not for for action's module definition
        stage_definition = StageDefinitionFactory(name='TestStage')
        with self.assertRaises(ValueError):
            vd.default_value = 'TestStage'
            vd.save()
        # should work
        vd.module_definition = stage_definition.module_definition
        vd.save()
        vd.default_value = 'TestStage'
        vd.save()


class TestConnectedModuleDefinitionWidget(EryTestCase):
    """
    Confirm VariableDefinition data_type can be changed with connected ModuleDefinitionWidgets.
    """

    def test_change_connected_variabledefinition(self):
        vd = VariableDefinitionFactory(data_type=VariableDefinition.DATA_TYPE_CHOICES.int)
        module_definition_widget = ModuleDefinitionWidgetFactory(
            variable_definition=vd, module_definition=vd.module_definition
        )
        # Confirm widget choice connection doesn't cause unexpected issues on type change
        WidgetChoiceFactory(widget=module_definition_widget)
        vd.data_type = VariableDefinition.DATA_TYPE_CHOICES.str
        vd.default_value = random_dt_value(vd.data_type)
        vd.save()
        vd.data_type = VariableDefinition.DATA_TYPE_CHOICES.dict
        vd.default_value = random_dt_value(vd.data_type)
        vd.save()
        vd.data_type = VariableDefinition.DATA_TYPE_CHOICES.list
        vd.default_value = random_dt_value(vd.data_type)
        vd.save()
        with self.assertRaises(EryValidationError):
            # no sir, not this one
            vd.data_type = VariableDefinition.DATA_TYPE_CHOICES.stage
            vd.save()


class TestCast(EryTestCase):
    """
    Confirm VariableDefinition.cast correctly typecasts values.
    """

    def test_int_casting(self):
        vd = VariableDefinitionFactory(data_type=VariableDefinition.DATA_TYPE_CHOICES.int)
        # correctly entered
        vd.cast(5)
        vd.cast('5')
        vd.cast(True)  # allowable in JS
        # incorrectly entered
        with self.assertRaises(ValueError):
            vd.cast('asdf')
        with self.assertRaises(ValueError):
            vd.cast(5.5)

    def test_float_casting(self):
        vd = VariableDefinitionFactory(data_type=VariableDefinition.DATA_TYPE_CHOICES.float)
        # correctly entered
        vd.cast(5.5)
        vd.cast('5.5')
        vd.cast(True)  # allowable in JS
        # self.variable_definition1.save()
        with self.assertRaises(ValueError):
            vd.cast('23 2')

    @staticmethod
    def test_str_casting():
        vd = VariableDefinitionFactory(data_type=VariableDefinition.DATA_TYPE_CHOICES.str)
        # correctly entered
        vd.cast('str')
        vd.cast(5)
        vd.cast(5.5)
        vd.cast(True)
        vd.cast({'possible': True})
        vd.cast(['How', 'You', 'Gon', 'Make', 'A', 'String'])

    def test_bool_casting(self):
        vd = VariableDefinitionFactory(data_type=VariableDefinition.DATA_TYPE_CHOICES.bool, validator=None)
        # correctly entered
        vd.cast(True)
        vd.cast(False)
        vd.cast('true')
        vd.cast('false')
        vd.cast(1)
        vd.cast('1')
        vd.cast(0)
        vd.cast('0')
        # obviously not a bool
        with self.assertRaises(ValueError):
            vd.cast(3)

    def test_list_casting(self):
        vd = VariableDefinitionFactory(data_type=VariableDefinition.DATA_TYPE_CHOICES.list, validator=None)
        # correctly entered
        vd.cast(['Its', 'A', 'List'])
        vd.cast(json.dumps(['Still', 'A', 'List']))

        # incorrectly entered
        with self.assertRaises(ValueError):
            vd.cast(5)
        with self.assertRaises(ValueError):
            vd.cast(5.5)
        with self.assertRaises(ValueError):
            vd.cast('asdf')
        with self.assertRaises(ValueError):
            vd.cast(True)
        with self.assertRaises(ValueError):
            vd.cast({'How you gon': 'Make a list'})
        with self.assertRaises(ValueError):
            vd.cast(json.dumps({'Its': 'Not a list'}))

    def test_dict_casting(self):
        vd = VariableDefinitionFactory(data_type=VariableDefinition.DATA_TYPE_CHOICES.dict, validator=None)
        # correctly entered
        vd.cast({'possible': True})
        vd.cast(json.dumps({'dictionary': True}))

        # incorrectly entered
        with self.assertRaises(ValueError):
            vd.cast(5)
        with self.assertRaises(ValueError):
            vd.cast(5.5)
        with self.assertRaises(ValueError):
            vd.cast('asdf')
        with self.assertRaises(ValueError):
            vd.cast(True)
        with self.assertRaises(ValueError):
            vd.cast(['How', 'You', 'Gon', 'Make', 'A', 'String'])
        with self.assertRaises(ValueError):
            vd.cast(json.dumps(['Not', 'A', 'Dict']))


class TestVariableChoiceItem(EryTestCase):
    def setUp(self):
        self.variable_definition = VariableDefinitionFactory(data_type=VariableDefinition.DATA_TYPE_CHOICES.choice)
        self.variable_choice_item = VariableChoiceItemFactory(variable_definition=self.variable_definition, value='test_val')

    def test_exists(self):
        self.assertIsNotNone(self.variable_choice_item)

    def test_expected_attributes(self):
        self.assertEqual(self.variable_choice_item.variable_definition, self.variable_definition)
        self.assertEqual(self.variable_choice_item.value, 'test_val')

    def test_unique_together(self):
        with self.assertRaises(IntegrityError):
            VariableChoiceItemFactory(variable_definition=self.variable_definition, value='test_val')

    def test_get_privilege_ancestor(self):
        self.assertEqual(
            self.variable_choice_item.get_privilege_ancestor(), self.variable_choice_item.variable_definition.module_definition
        )

    def test_get_privilege_ancestor_cls(self):
        self.assertEqual(
            self.variable_choice_item.get_privilege_ancestor_cls(),
            self.variable_choice_item.variable_definition.module_definition.__class__,
        )

    def test_get_privilege_ancestor_filter_path(self):
        self.assertEqual(
            self.variable_choice_item.get_privilege_ancestor_filter_path(), 'variable_definition__module_definition'
        )

    def test_delete_errors(self):
        """
        Cannot delete VariableChoiceItem when it will invalidate a connected input
        """
        # item is no longer a subset
        module_definition_widget = ModuleDefinitionWidgetFactory(variable_definition=self.variable_definition)
        WidgetChoiceFactory(widget=module_definition_widget, value='test_val')
        with self.assertRaises(EryValidationError):
            self.variable_choice_item.delete()

    def test_caseinsensitive_uniqueness(self):
        """
        Confirm value uniqueness is case insensitive within input.
        """
        vd = VariableDefinitionFactory(data_type=VariableDefinition.DATA_TYPE_CHOICES.choice)
        VariableChoiceItemFactory(variable_definition=vd, value='Subtle')
        with self.assertRaises(IntegrityError):
            VariableChoiceItemFactory(variable_definition=vd, value='SuBTle')

    def test_get_translation(self):
        """
        Confirm get_translation returns correct caption.
        """
        second_language = Language.objects.get(pk='aa')

        default_language = Language.objects.get(pk='en')
        VariableChoiceItemTranslationFactory(
            caption="English != American", language=default_language, variable_choice_item=self.variable_choice_item
        )

        VariableChoiceItemTranslationFactory(
            caption="test text", language=second_language, variable_choice_item=self.variable_choice_item
        )

        self.assertEqual(self.variable_choice_item.get_translation(second_language), "test text")

    def test_get_info(self):
        """
        Confirm get_info returns correct caption and value.
        """
        language = Language.objects.get(pk='aa')
        vci_translation = VariableChoiceItemTranslationFactory(
            variable_choice_item=self.variable_choice_item, caption='test text', language=language
        )
        self.assertEqual(
            self.variable_choice_item.get_info(language),
            {'value': self.variable_choice_item.value, 'caption': vci_translation.caption},
        )


class TestVariableChoiceItemTranslation(EryTestCase):
    def setUp(self):
        self.vci = VariableChoiceItemFactory(variable_definition__data_type=VariableDefinition.DATA_TYPE_CHOICES.choice)
        self.caption = 'I change languages more than professors change their minds'
        self.language = Language.objects.get(pk='aa')
        self.vci_translation = VariableChoiceItemTranslationFactory(
            variable_choice_item=self.vci, caption=self.caption, language=self.language
        )

    def test_exists(self):
        self.assertIsNotNone(self.vci_translation)

    def test_expected_attributes(self):
        self.assertEqual(self.vci_translation.variable_choice_item, self.vci)
        self.assertEqual(self.vci_translation.caption, self.caption)
        self.assertEqual(self.vci_translation.language, self.language)


class TestVariableMixin(EryTestCase):
    def setUp(self):
        self.validator = ValidatorFactory(code=None, regex='inheresomewhere', nullable=False)
        self.variable_definition = VariableDefinitionFactory(
            validator=self.validator,
            data_type=VariableDefinition.DATA_TYPE_CHOICES.str,
            default_value='21meaningfullyricsinheresomewhere212121',
        )
        md = self.variable_definition.module_definition
        module = ModuleFactory(stint_definition_module_definition__module_definition=md)
        self.module_variable = ModuleVariableFactory(module=module, variable_definition=self.variable_definition, value=None)

    @unittest.skip("Address in issue #465")
    def test_set_error(self):
        with self.assertRaises(EryValueError):
            ModuleVariableFactory(variable_definition=self.variable_definition, value=4)

    @unittest.skip("Address in issue #465")
    def test_validate_failures(self):
        # Nonmatching regex for variable with variable_definition validator having regex
        with self.assertRaises(EryValueError):
            ModuleVariableFactory(variable_definition=self.variable_definition, value='asd')
        # Non-nullable value according to Validator
        with self.assertRaises(EryValueError):
            var = ModuleVariableFactory(variable_definition=self.variable_definition)
            var.value = None
            var.save()

    def test_expected_stage_save_errors(self):
        """
        Confirm save errors for save attribute.
        """
        vd = VariableDefinition.objects.create(
            data_type=VariableDefinition.DATA_TYPE_CHOICES.stage,
            default_value=None,
            module_definition=ModuleDefinitionFactory(),
            scope=VariableDefinition.SCOPE_CHOICES.hand,
            name='test_vd',
        )
        # stage with name does not exist
        with self.assertRaises(ValueError):
            ModuleVariableFactory(variable_definition=vd, value='AntiTestStage')
        # stage with name exists, but not for for action's module definition
        stage_definition = StageDefinitionFactory(name='TestStage')
        with self.assertRaises(ValueError):
            ModuleVariableFactory(variable_definition=vd, value='TestStage')
        # should work
        vd.module_definition = stage_definition.module_definition
        vd.save()
        ModuleVariableFactory(variable_definition=vd, value='TestStage')

    @mock.patch('ery_backend.variables.models.VariableDefinition.cast')
    @mock.patch('ery_backend.variables.models.VariableMixin.set_default', autospec=True)
    def test_clean(self, mock_default, mock_cast):
        """
        Confirm expected methods called on clean.
        """
        vd = VariableDefinition.objects.create(
            name='testvd',
            scope=VariableDefinition.SCOPE_CHOICES.hand,
            validator=None,
            is_payoff=False,
            module_definition=ModuleDefinitionFactory(),
        )
        self.module_variable.variable_definition = vd
        self.module_variable.value = None
        self.module_variable.save()
        mock_default.assert_called_with(self.module_variable)

        mock_cast.return_value = 'testsinheresomewhere'
        self.module_variable.value = 'testsinheresomewhere'
        self.module_variable.save()
        mock_cast.assert_called_with('testsinheresomewhere')

        # see expected_stage_save_errors for stage related clean validation

    def test_reset_payoff(self):
        variable_definition = self.module_variable.get_variable_definition()
        self.assertIsNot(variable_definition, None)

        variable_definition.validator = None
        variable_definition.save()
        self.module_variable.value = 25
        self.module_variable.save()

        # should not work on non-payoff variables
        with self.assertRaises(ValidationError):
            self.module_variable.reset_payoff()
        variable_definition.is_payoff = True
        variable_definition.scope = VariableDefinition.SCOPE_CHOICES.hand

        variable_definition.data_type = VariableDefinition.DATA_TYPE_CHOICES.float
        variable_definition.default_value = 0
        variable_definition.save()

        self.module_variable.reset_payoff()
        self.module_variable.refresh_from_db()
        self.assertEqual(self.module_variable.value, 0)

    def test_get_variable_definition(self):
        """
        get_variable_definition should produce the .variable_definition attribute one linked via
        :class:~ery_backend.stints.StintDefinitionVariableDefinition as appropriate
        """
        without_sdvd = ModuleVariableFactory()
        self.assertEqual(without_sdvd.get_variable_definition(), without_sdvd.variable_definition)
        with self.assertRaises(ValueError):
            without_sdvd.get_variable_definition(ModuleDefinitionFactory())

        with_sdvd = ModuleVariableFactory(with_stint_definition_variable_definition=True)
        module_definition = with_sdvd.module.stint_definition_module_definition.module_definition
        variable_definition = VariableDefinition.objects.get(module_definition=module_definition)
        self.assertEqual(with_sdvd.get_variable_definition(module_definition=module_definition), variable_definition)


class TestModuleVariable(EryTestCase):
    def setUp(self):
        self.validator = ValidatorFactory(regex='inheresomewhere', code=None)
        self.variable_definition_w_choice = VariableDefinitionFactory(
            data_type=VariableDefinition.DATA_TYPE_CHOICES.choice, default_value=None, validator=self.validator
        )
        self.variable_choice_item = VariableChoiceItemFactory(
            variable_definition=self.variable_definition_w_choice, value='4:44frankoceaninheresomewhere'
        )
        self.variable_definition_w_choice.default_value = '4:44frankoceaninheresomewhere'
        self.variable_definition_w_choice.save()
        self.variable_definition = VariableDefinitionFactory(
            data_type=VariableDefinition.DATA_TYPE_CHOICES.str, default_value=None, validator=self.validator
        )
        self.module = ModuleFactory()
        self.module_variable = ModuleVariableFactory(
            variable_definition=self.variable_definition_w_choice, module=self.module, value='4:44frankoceaninheresomewhere'
        )

    def test_exists(self):
        self.assertIsNotNone(self.module_variable)

    def test_expected_attributes(self):
        self.module_variable.refresh_from_db()
        self.assertEqual(self.module_variable.variable_definition, self.variable_definition_w_choice)
        self.assertEqual(self.module_variable.value, '4:44frankoceaninheresomewhere')
        self.assertEqual(self.module_variable.module, self.module)

    def test_unique_together(self):
        ModuleVariableFactory(
            module=self.module, variable_definition=self.variable_definition, value='4:44beckyinheresomewhere'
        )

        with self.assertRaises(IntegrityError):
            ModuleVariableFactory(
                module=self.module, variable_definition=self.variable_definition, value='4:44beckyinheresomewhere'
            )


class TestTeamVariable(EryTestCase):
    def setUp(self):
        self.module = ModuleFactory()
        self.team = TeamFactory()
        self.validator = ValidatorFactory(regex='inheresomewhere', code=None)
        self.variable_definition = VariableDefinitionFactory(
            data_type=VariableDefinition.DATA_TYPE_CHOICES.str, validator=self.validator
        )
        self.team_variable = TeamVariableFactory(
            team=self.team,
            variable_definition=self.variable_definition,
            value='4:44shamelesstidalpromotionsinheresomewhere',
            module=self.module,
        )

    def test_exists(self):
        self.assertIsNotNone(self.team_variable)

    def test_expected_attributes(self):
        self.team_variable.refresh_from_db()
        self.assertEqual(self.team_variable.variable_definition, self.variable_definition)
        self.assertEqual(self.team_variable.value, '4:44shamelesstidalpromotionsinheresomewhere')
        self.assertEqual(self.team_variable.team, self.team)
        self.assertEqual(self.team_variable.module, self.module)

    def test_unique_together(self):
        with self.assertRaises(IntegrityError):
            TeamVariableFactory(
                team=self.team, variable_definition=self.variable_definition, value="4:44churchchoirinheresomewhere"
            )


class TestHandVariable(EryTestCase):
    def setUp(self):
        self.module = ModuleFactory()
        self.hand = HandFactory()
        self.validator = ValidatorFactory(regex='inheresomewhere', code=None)
        self.variable_definition = VariableDefinitionFactory(
            data_type=VariableDefinition.DATA_TYPE_CHOICES.str, validator=self.validator
        )
        self.hand_variable = HandVariableFactory(
            hand=self.hand,
            variable_definition=self.variable_definition,
            value='4:44hotsauceinheresomewhere',
            module=self.module,
        )

    def test_exists(self):
        self.assertIsNotNone(self.hand_variable)

    def test_expected_attributes(self):
        self.hand_variable.refresh_from_db()
        self.assertEqual(self.hand_variable.variable_definition, self.variable_definition)
        self.assertEqual(self.hand_variable.value, '4:44hotsauceinheresomewhere')
        self.assertEqual(self.hand_variable.hand, self.hand)
        self.assertEqual(self.hand_variable.module, self.module)

    def test_unique_together(self):
        with self.assertRaises(IntegrityError):
            HandVariableFactory(
                hand=self.hand,
                variable_definition=self.variable_definition,
                value='4:4440yearlateapologytowomeninheresomewhere',
            )
