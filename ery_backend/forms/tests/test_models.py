import random
import unittest

from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from languages_plus.models import Language

from ery_backend.base.testcases import EryTestCase, random_dt_value, create_test_stintdefinition
from ery_backend.conditions.factories import ConditionFactory
from ery_backend.frontends.factories import Frontend
from ery_backend.modules.factories import ModuleDefinitionFactory
from ery_backend.stint_specifications.factories import StintSpecificationFactory
from ery_backend.stint_specifications.models import StintSpecification
from ery_backend.users.factories import UserFactory
from ery_backend.variables.factories import VariableDefinitionFactory, VariableChoiceItemFactory
from ery_backend.variables.models import VariableDefinition
from ery_backend.widgets.factories import WidgetFactory
from ..factories import (
    FormFactory,
    FormFieldFactory,
    FormFieldChoiceFactory,
    FormFieldChoiceTranslationFactory,
    FormButtonListFactory,
    FormButtonFactory,
    FormItemFactory,
)
from ..models import FormField


class TestForm(EryTestCase):
    def setUp(self):
        self.module_definition = ModuleDefinitionFactory()
        self.message = 'A new form is dawning'
        self.form = FormFactory(module_definition=self.module_definition, name='TestForm', comment=self.message)

    def test_exists(self):
        self.assertIsNotNone(self.form)

    def test_expected_attributes(self):
        self.assertEqual(self.form.name, 'TestForm')
        self.assertEqual(self.form.comment, self.message)
        self.assertEqual(self.form.module_definition, self.module_definition)
        self.assertIsNotNone(self.form.slug)

    # XXX: Address in issue #816
    # def test_unique_together(self):
    #     # A form field's name should be unique in that form
    #     FormFieldFactory(name='LastNameEva', form=self.form)
    #     FormFieldFactory(name='FirstNameGreatest', form=self.form)
    #     # Fine for different forms
    #     FormFieldFactory(name='LastNameEva')

    #     # Not fine for the same form
    #     with self.assertRaises(IntegrityError):
    #         FormFieldFactory(name='FirstNameGreatest', form=self.form)

    def test_get_privilege_ancestor(self):
        self.assertEqual(self.form.get_privilege_ancestor(), self.form.module_definition)

    def test_get_privilege_ancestor_cls(self):
        self.assertEqual(self.form.get_privilege_ancestor_cls(), self.form.module_definition.__class__)

    def test_get_privilege_ancestor_filter_path(self):
        self.assertEqual(self.form.get_privilege_ancestor_filter_path(), 'module_definition')

    def test_duplicate(self):
        item_count = random.randint(1, 10)
        form_items = [FormItemFactory(form=self.form, child_type=False) for _ in range(item_count * 2)]

        fields, button_lists = [], []
        for form_item in form_items[:item_count]:
            fields.append(FormFieldFactory(form_item=form_item))
        for form_item in form_items[item_count:]:
            button_lists.append(FormButtonListFactory(form_item=form_item, add_buttons=False))
        buttons = [FormButtonFactory(button_list=random.choice(button_lists)) for _ in range(random.randint(1, 10))]

        choices = [FormFieldChoiceFactory(field=random.choice(fields)) for _ in range(random.randint(1, 2))]
        translations = [
            FormFieldChoiceTranslationFactory(field_choice=random.choice(choices)) for _ in range(random.randint(1, 10))
        ]

        form_2 = self.form.duplicate()
        # Expected fields
        self.assertEqual(form_2.items.exclude(field=None).count(), len(fields))
        for field in fields:
            self.assertTrue(form_2.items.filter(field__name=field.name))

        # Expected button_lists
        self.assertEqual(form_2.items.exclude(button_list=None).count(), len(button_lists))

        # Expected buttons
        button_count = 0
        for button_list_item in form_2.items.exclude(button_list=None):
            button_count += button_list_item.button_list.buttons.count()
        self.assertEqual(button_count, len(buttons))
        for button in buttons:
            self.assertTrue(form_2.items.exclude(button_list=None).filter(button_list__buttons__name=button.name).exists())

        # Expected items
        self.assertEqual(form_2.items.count(), len(form_items))
        for item in form_items:
            if hasattr(item, 'field'):
                self.assertTrue(form_2.items.filter(field__name=item.field.name, order=item.order).exists())
            elif hasattr(item, 'button_list'):
                self.assertTrue(form_2.items.filter(button_list__name=item.button_list.name, order=item.order).exists())

        # Expected choices
        form_fields = [item.field for item in form_2.items.exclude(field=None).all()]
        self.assertEqual(sum([field.choices.count() for field in form_fields]), len(choices))
        for choice in choices:
            self.assertTrue(
                form_2.items.get(field__name=choice.field.name).field.choices.filter(value__in=[choice.value]).exists()
            )

        # Expected translations
        translation_count = 0
        for field in form_fields:
            for choice in field.choices.all():
                translation_count += choice.translations.count()
        self.assertEqual(translation_count, len(translations))
        for translation in translations:
            self.assertTrue(
                form_2.items.get(field__name=translation.field_choice.field.name)
                .field.choices.filter(translations__caption__in=[translation.caption])
                .exists()
            )

        self.assertEqual('{}Copy'.format(self.form.name), form_2.name)
        self.assertNotEqual(self.form, form_2)
        # Parents should be equivalent
        self.assertEqual(self.form.module_definition, form_2.module_definition)


class TestSaveData(EryTestCase):
    """
    Confirm form data can be saved through hand and field_name: value pairs
    """

    def test_save_data(self):
        web = Frontend.objects.get(name='Web')
        stint_definition = create_test_stintdefinition(frontend=web)
        form = FormFactory(module_definition=stint_definition.module_definitions.first())
        field_count = random.randint(1, 10)
        variable_definitions = [
            VariableDefinitionFactory(module_definition=form.module_definition, scope=VariableDefinition.SCOPE_CHOICES.hand)
            for _ in range(field_count)
        ]
        stint_spec = StintSpecificationFactory(
            stint_definition=stint_definition, late_arrival=True, where_to_run=StintSpecification.WHERE_TO_RUN_CHOICES.market
        )
        stint = stint_definition.realize(stint_spec)
        stint.start(UserFactory(), signal_pubsub=False)
        hand = stint.join_user(UserFactory(), web)
        form_items = [FormItemFactory(form=form, child_type=False) for _ in range(field_count)]
        for form_item in form_items:
            form_item.button_list = None
            form_item.save()
        fields = [
            FormFieldFactory(variable_definition=variable_definitions[i], form_item=form_items[i])
            for i in range(len(form_items))
        ]
        save_data = {field.name: random_dt_value(field.variable_definition.data_type) for field in fields}
        form.save_data(hand, save_data)
        for item in form.items.exclude(field=None).all():
            self.assertEqual(save_data[item.field.name], hand.stint.get_variable(item.field.variable_definition, hand).value)


class TestFormField(EryTestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.language = Language.objects.get(pk='en')

    def setUp(self):
        self.variable_definition = VariableDefinitionFactory(data_type=VariableDefinition.DATA_TYPE_CHOICES.choice)
        self.widget = WidgetFactory()
        self.disable_condition = ConditionFactory(module_definition=self.variable_definition.module_definition)
        self.form = FormFactory(module_definition=self.variable_definition.module_definition)
        self.form_item = FormItemFactory(form=self.form, child_type=False)
        self.form_item.field, self.form_item.button_list = None, None
        self.form_item.save()
        self.field = FormFieldFactory(
            variable_definition=self.variable_definition,
            name='MyField',
            comment='Yup dassa me',
            widget=self.widget,
            required=True,
            initial_value=self.variable_definition.default_value,
            form_item=self.form_item,
            helper_text='NO HELP',
            disable=self.disable_condition,
        )

    def test_exists(self):
        self.assertIsNotNone(self.field)

    def test_expected_attributes(self):
        self.field.refresh_from_db()
        self.assertEqual(self.field.form_item, self.form_item)
        self.assertEqual(self.field.variable_definition, self.variable_definition)
        self.assertEqual(self.field.name, 'MyField')
        self.assertEqual(self.field.comment, 'Yup dassa me')
        self.assertEqual(self.field.widget, self.widget)
        self.assertEqual(self.field.required, True)
        self.assertEqual(self.field.initial_value, self.variable_definition.default_value)
        self.assertEqual(self.field.helper_text, 'NO HELP')
        self.assertEqual(self.field.disable, self.disable_condition)

    @unittest.skip("XXX: Address in issue #813")
    def test_expected_save_errors(self):
        # switching variable_definition from nonchoice to choice
        str_variable_definition = VariableDefinitionFactory(data_type=VariableDefinition.DATA_TYPE_CHOICES.str)
        form_item = FormItemFactory(form=self.form)
        form_item.field, form_item.button_list = None, None
        form_item.save()
        field = FormFieldFactory(form_item=form_item, variable_definition=str_variable_definition)
        FormFactory(module_definition=str_variable_definition.module_definition)

        # switching variable_definition type from nonchoice to choice, without VariableChoiceItems
        field.variable_definition = str_variable_definition
        with self.assertRaises(ValidationError):
            # Otherwise EryValueError due to no choice items for default_value
            field.variable_definition.default_value = None
            field.variable_definition.save()
            field.variable_definition.data_type = VariableDefinition.DATA_TYPE_CHOICES.choice
            field.variable_definition.save()

    def test_get_choices_as_extra_variable(self):
        """
        Confirm WidgetChoices are converted to a dictionary with name(choices), value(choice info)
        """
        choices = self.field.get_choices(Language.objects.first())
        expected_results = self.field.get_choices_as_extra_variable(choices)
        self.assertEqual(expected_results, {'choices': choices})

    def test_is_multiple_choice(self):
        """
        Confirm correct boolean returned by field.is_multiple_choice.
        """
        # Should pass so long as WidgetChoices exist
        field_choice = FormFieldChoiceFactory(field=self.field, order=0, value=self.variable_definition.default_value)
        FormFieldChoiceTranslationFactory(field_choice=field_choice, language=self.language)
        self.assertTrue(self.field.choices.exists())
        self.assertTrue(self.field.is_multiple_choice)

        # Should not fail still if there are no WidgetChoices as it is a VariableDefinition with data_type set to 'choice'
        self.field.choices.all().delete()

        # No widget choices, but variable choice items present
        self.assertTrue(self.field.is_multiple_choice)

        # Should fail still as there are no WidgetChoices and the VariableDefinition has not data_type set to 'choice'
        self.field.variable_definition = self.variable_definition
        variable_definition = self.field.variable_definition
        variable_definition.variablechoiceitem_set.all().delete()
        variable_definition.data_type = VariableDefinition.DATA_TYPE_CHOICES.str
        variable_definition.save()
        # No widget choices, but variable choice items present
        self.assertFalse(self.field.is_multiple_choice)

    def test_get_choices(self):
        """
        Confirm expected results for each randomization option in ModuleDefinitionWidget.get_choices.
        """
        VariableChoiceItemFactory(variable_definition=self.variable_definition, value='a')
        VariableChoiceItemFactory(variable_definition=self.variable_definition, value='b')
        VariableChoiceItemFactory(variable_definition=self.variable_definition, value='c')
        language = self.variable_definition.module_definition.primary_language
        field_choice = FormFieldChoiceFactory(field=self.field, order=0, value='a')
        FormFieldChoiceTranslationFactory(field_choice=field_choice, language=self.language)
        field_choice2 = FormFieldChoiceFactory(field=self.field, order=1, value='b')
        FormFieldChoiceTranslationFactory(field_choice=field_choice2, language=self.language)
        field_choice3 = FormFieldChoiceFactory(field=self.field, order=2, value='c')
        FormFieldChoiceTranslationFactory(field_choice=field_choice3, language=self.language)

        # ascending results
        self.field.random_mode = FormField.RANDOM_CHOICES.asc
        asc_results = [
            {'value': choice.value, 'caption': choice.get_translation(language)}
            for choice in [field_choice, field_choice2, field_choice3]
        ]
        self.assertEqual(self.field.get_choices(language=language), asc_results)

        # descending results
        self.field.random_mode = FormField.RANDOM_CHOICES.desc
        desc_results = [
            {'value': choice.value, 'caption': choice.get_translation(language)}
            for choice in [field_choice3, field_choice2, field_choice]
        ]
        self.assertEqual(self.field.get_choices(language=language), desc_results)

        # shuffled results
        self.field.random_mode = FormField.RANDOM_CHOICES.shuffle
        equals = True  # Asserts all results are always equal
        for _ in range(100):
            result = self.field.get_choices(language=language) == self.field.get_choices(language=language)
            if not result:
                equals = False
                break
        self.assertFalse(equals)

        # random ascend/descend results
        self.field.random_mode = FormField.RANDOM_CHOICES.random_asc_desc
        equals = False  # Assert results don't match any of expected results
        output = self.field.get_choices(language=language)
        if output in (asc_results, desc_results):
            equals = True
        self.assertTrue(equals)

    @staticmethod
    def get_translation(field_choice, language):
        return field_choice.translations.get(language=language)

    def test_get_choices_by_language(self):
        correct_lang = Language.objects.get(iso_639_1='aa')
        incorrect_lang = Language.objects.get(iso_639_1='ab')
        default_lang = self.variable_definition.module_definition.primary_language
        field = FormFieldFactory(
            variable_definition=self.variable_definition, random_mode=FormField.RANDOM_CHOICES.random_asc_desc
        )
        field_choice1 = FormFieldChoiceFactory(field=field, order=1)
        field_choice1_correct = FormFieldChoiceTranslationFactory(
            field_choice=field_choice1, caption='Correct One', language=correct_lang
        )
        FormFieldChoiceTranslationFactory(field_choice=field_choice1, caption='Incorrect One', language=incorrect_lang)

        FormFieldChoiceTranslationFactory(field_choice=field_choice1, caption='Default One', language=default_lang)
        # Get one choice of correct with correct translation caption (when other caption exists)
        choices = field.get_choices(language=correct_lang)
        self.assertIn({'value': field_choice1.value, 'caption': field_choice1_correct.caption}, choices)

        # Return value when desired translation does not exist to provide caption
        field_choice2 = FormFieldChoiceFactory(field=field, order=2)
        FormFieldChoiceTranslationFactory(
            field_choice=field_choice2, language=Language.objects.get(pk='ab'), caption='Also Correct'
        )
        choices_2 = field.get_choices(language=self.language)
        self.assertIn({'value': field_choice2.value, 'caption': field_choice2.value}, choices_2)

    def test_expected_get_choices_errors(self):
        # Does not pass multiple choice check
        str_vd = VariableDefinitionFactory(data_type=VariableDefinition.DATA_TYPE_CHOICES.str)
        no_choice_input = FormFieldFactory(variable_definition=str_vd, random_mode=FormField.RANDOM_CHOICES.asc)
        with self.assertRaises(TypeError):
            no_choice_input.get_choices()


class TestFormFieldChoice(EryTestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.language = Language.objects.get(pk='en')

    def setUp(self):
        self.variable_definition = VariableDefinitionFactory(
            data_type=VariableDefinition.DATA_TYPE_CHOICES.choice, default_value=None
        )
        self.variable_choice_item = VariableChoiceItemFactory(variable_definition=self.variable_definition, value='a')
        form = FormFactory(module_definition=self.variable_definition.module_definition)
        form_item = FormItemFactory(form=form, child_type=False)
        form_item.button_list = None
        form.save()
        self.field = FormFieldFactory(variable_definition=self.variable_definition, form_item=form_item)
        self.field_choice = FormFieldChoiceFactory(field=self.field, value='a', order=2)

    def test_exists(self):
        self.assertIsNotNone(self.field_choice)

    def test_expected_attributes(self):
        self.assertEqual(self.field_choice.field, self.field)
        self.assertEqual(self.field_choice.value, 'a')
        self.assertEqual(self.field_choice.order, 2)

    def test_get_info(self):
        FormFieldChoiceTranslationFactory(field_choice=self.field_choice, caption='this one', language=self.language)
        self.assertEqual(
            self.field_choice.get_info(self.language),
            {'value': self.field_choice.value, 'caption': self.field_choice.get_translation(self.language)},
        )

    def test_get_privilege_ancestor(self):
        self.assertEqual(self.field_choice.get_privilege_ancestor(), self.field_choice.field.form_item.form.module_definition)

    def test_get_privilege_ancestor_cls(self):
        self.assertEqual(
            self.field_choice.get_privilege_ancestor_cls(), self.field_choice.field.form_item.form.module_definition.__class__
        )

    def test_get_privilege_ancestor_filter_path(self):
        self.assertEqual(self.field_choice.get_privilege_ancestor_filter_path(), 'field__form_item__form__module_definition')

    @unittest.skip("XXX: Address in issue #813")
    def test_expected_save_errors(self):
        """
        Confirm expected errors on save.
        """
        variable_definition = VariableDefinitionFactory(
            data_type=VariableDefinition.DATA_TYPE_CHOICES.choice, name='test_vd', default_value=None
        )
        # No VariableChoiceItems
        with self.assertRaises(ValidationError):
            form = FormFactory(module_definition=variable_definition.module_definition)
            form_item = FormItemFactory(form=form, child_type=False)
            form_field = FormField.objects.create(
                variable_definition=variable_definition,
                form_item=form_item,
                required=False,
                name='MyField',
                widget=WidgetFactory(),
            )

        # Outside of subset
        VariableChoiceItemFactory(variable_definition=variable_definition, value='a')
        form_field = FormFieldFactory(variable_definition=variable_definition)
        with self.assertRaises(ValueError):
            FormFieldChoiceFactory(field=form_field, value='b')

    def test_get_translation(self):
        """
        Confirm get_translation returns expected translation or value if Does Not Exist.
        """
        # Confirm intended translation returned if exists
        FormFieldChoiceTranslationFactory(field_choice=self.field_choice, caption='this one', language=self.language)
        preferred = FormFieldChoiceTranslationFactory(
            field_choice=self.field_choice, caption='not this one', language=Language.objects.get(pk='aa')
        )
        self.assertEqual(self.field_choice.get_translation(language=Language.objects.get(pk='aa')), preferred.caption)

        # Confirm value returned if requested Does Not Exist
        self.assertEqual(self.field_choice.get_translation(Language.objects.get(pk='ab')), self.field_choice.value)

    def test_unique_together(self):
        variable_definition = VariableDefinitionFactory(data_type=VariableDefinition.DATA_TYPE_CHOICES.str)
        form = FormFactory(module_definition=variable_definition.module_definition)
        form_item = FormItemFactory(form=form, child_type=False)
        field = FormFieldFactory(variable_definition=variable_definition, form_item=form_item)
        FormFieldChoiceFactory(field=field, value='a', order=1)
        with self.assertRaises(IntegrityError):
            FormFieldChoiceFactory(field=field, value='a')
        with self.assertRaises(IntegrityError):
            FormFieldChoiceFactory(field=field, order=1)

    def test_caseinsensitive_uniqueness(self):
        """
        Confirm value uniqueness is case insensitive within input.
        """
        variable_definition = VariableDefinitionFactory(data_type=VariableDefinition.DATA_TYPE_CHOICES.str)
        field = FormFieldFactory(variable_definition=variable_definition)
        FormFieldChoiceFactory(field=field, value='TomAto', order=1)
        with self.assertRaises(IntegrityError):
            FormFieldChoiceFactory(field=field, value='Tomato', order=2)


class TestFormFieldChoiceTranslation(EryTestCase):
    def setUp(self):
        self.field_choice = FormFieldChoiceFactory()
        self.form_field_choice_translation = FormFieldChoiceTranslationFactory(
            field_choice=self.field_choice, caption='Choice Un', language=Language.objects.first()
        )

    def test_exists(self):
        self.assertIsNotNone(self.form_field_choice_translation)

    def test_expected_attributes(self):
        self.assertEqual(self.form_field_choice_translation.field_choice, self.field_choice)
        self.assertEqual(self.form_field_choice_translation.language, Language.objects.first())
        self.assertEqual(self.form_field_choice_translation.caption, 'Choice Un')

    def test_unique_togther(self):
        variable_definition = VariableDefinitionFactory(data_type=VariableDefinition.DATA_TYPE_CHOICES.choice)
        form = FormFactory(module_definition=variable_definition.module_definition)
        form_item = FormItemFactory(form=form, child_type=False)
        form_item.button_list, form_item.field = None, None
        form_item.save()
        field = FormFieldFactory(form_item=form_item, variable_definition=variable_definition)
        field_choice = FormFieldChoiceFactory(field=field)
        FormFieldChoiceTranslationFactory(field_choice=field_choice, language=Language.objects.first())
        with self.assertRaises(IntegrityError):
            FormFieldChoiceTranslationFactory(field_choice=field_choice, language=Language.objects.first())


class TestFormButton(EryTestCase):
    def setUp(self):
        self.form = FormFactory()
        self.form_item = FormItemFactory(form=self.form, child_type=False)
        self.button_list = FormButtonListFactory(form_item=self.form_item)
        self.widget = WidgetFactory()
        self.disable_condition = ConditionFactory(module_definition=self.form.module_definition)
        self.hide_condition = ConditionFactory(module_definition=self.form.module_definition)
        self.button = FormButtonFactory(
            button_list=self.button_list,
            name='MyButton',
            button_text='My Button',
            widget=self.widget,
            submit=True,
            disable=self.disable_condition,
            hide=self.hide_condition,
        )

    def test_exists(self):
        self.assertIsNotNone(self.button)

    def test_expected_attributes(self):
        self.button.refresh_from_db()
        self.assertEqual(self.button.name, 'MyButton')
        self.assertEqual(self.button.button_list, self.button_list)
        self.assertEqual(self.button.widget, self.widget)
        self.assertTrue(self.button.submit)
        self.assertEqual(self.button.disable, self.disable_condition)
        self.assertEqual(self.button.hide, self.hide_condition)
        self.assertEqual(self.button.button_text, 'My Button')

    # XXX: Address in issue #816
    # def test_unique_together(self):
    #     form = FormFactory()
    #     # This is fine
    #     FormButtonFactory(name='TestButton', form=form)
    #     FormButtonFactory(name='TestButton')

    #     with self.assertRaises(IntegrityError):
    #         FormButtonFactory(name='TestButton', form=form)


class TestFormButtonList(EryTestCase):
    def setUp(self):
        self.form = FormFactory()
        self.form_button_list = FormButtonListFactory(name='MyList')

    def test_exists(self):
        self.assertIsNotNone(self.form_button_list)


class TestFormItem(EryTestCase):
    def setUp(self):
        self.blank_item = FormItemFactory(child_type=False)
        self.random_field_item = FormItemFactory(child_type='field')
        self.random_list_item = FormItemFactory(child_type='button_list')

    def test_exists(self):
        self.assertIsNotNone(self.blank_item)
        self.assertIsNotNone(self.random_field_item)
        self.assertIsNotNone(self.random_list_item)

    def test_factory_creation(self):
        """Confirm child_type allows specific factory creation"""
        self.assertFalse(hasattr(self.blank_item, 'field'))
        self.assertFalse(hasattr(self.blank_item, 'button_list'))
        self.assertIsNotNone(self.random_field_item.field)
        self.assertFalse(hasattr(self.random_field_item, 'button_list'))
        self.assertIsNotNone(self.random_list_item.button_list)
        self.assertFalse(hasattr(self.random_list_item, 'field'))
