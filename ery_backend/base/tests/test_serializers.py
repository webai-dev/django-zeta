from io import BytesIO
import json
import os
import random

from languages_plus.models import Language
from rest_framework import serializers
import rest_framework

from ery_backend.actions.factories import ActionFactory
from ery_backend.actions.models import Action, ActionStep
from ery_backend.conditions.factories import ConditionFactory
from ery_backend.conditions.models import Condition
from ery_backend.forms.factories import FormFactory, FormFieldFactory
from ery_backend.forms.models import FormItem
from ery_backend.frontends.factories import FrontendFactory
from ery_backend.frontends.models import Frontend
from ery_backend.keywords.factories import KeywordFactory
from ery_backend.templates.factories import TemplateFactory
from ery_backend.templates.models import Template
from ery_backend.modules.factories import ModuleDefinitionFactory, ModuleDefinitionWidgetFactory, WidgetChoiceFactory
from ery_backend.modules.models import ModuleDefinition, ModuleDefinitionWidget
from ery_backend.stages.factories import StageDefinitionFactory, StageTemplateFactory, StageTemplateBlockFactory
from ery_backend.stages.models import StageDefinition
from ery_backend.stints.models import StintDefinition
from ery_backend.stint_specifications.factories import StintSpecificationFactory
from ery_backend.stint_specifications.models import StintSpecification
from ery_backend.syncs.factories import EraFactory
from ery_backend.themes.factories import ThemeFactory
from ery_backend.themes.models import Theme
from ery_backend.validators.models import Validator
from ery_backend.validators.factories import ValidatorFactory
from ery_backend.variables.factories import VariableDefinitionFactory, VariableChoiceItemFactory
from ery_backend.variables.models import VariableDefinition
from ery_backend.widgets.factories import WidgetFactory
from ery_backend.widgets.models import Widget

from ..serializers import (
    ModuleDefinitionXMLRenderer,
    ModuleDefinitionXMLParser,
    ErySerializer,
    StintDefinitionXMLRenderer,
    TemplateXMLRenderer,
    WidgetXMLRenderer,
    ThemeXMLRenderer,
    ValidatorXMLRenderer,
)
from ..testcases import EryTestCase


class TestXMLRenderer(EryTestCase):
    def setUp(self):
        self.xml_renderer = ModuleDefinitionXMLRenderer()

    def test_get_model(self):
        """Used in each export view's get method. Confirms value returned in as exported."""
        self.assertEqual(self.xml_renderer.get_model(), ModuleDefinition)
        self.assertEqual(StintDefinitionXMLRenderer.get_model(), StintDefinition)
        self.assertEqual(TemplateXMLRenderer.get_model(), Template)
        self.assertEqual(WidgetXMLRenderer.get_model(), Widget)
        self.assertEqual(ThemeXMLRenderer.get_model(), Theme)
        self.assertEqual(ValidatorXMLRenderer.get_model(), Validator)

    def test_render(self):
        """Confirm data correctly serialized as pretty printed xml."""
        module_definition = ModuleDefinitionFactory()
        data = module_definition.get_bxml_serializer()(module_definition).data
        xml_data = self.xml_renderer.render(data)
        self.assertIn(b"xml", xml_data)
        # confirm new line separation
        self.assertIn(b"<start_stage/>\n", xml_data)
        # confirm double space indentation
        self.assertEqual(xml_data.split(b"\n")[2][0:2], b"  ")

    def test_render_by_model(self):  # pylint: disable=no-self-use
        """Confirm all intended models can render xml."""
        from ...stints.factories import StintDefinitionFactory

        module_definition = ModuleDefinitionFactory()
        ModuleDefinitionXMLRenderer().render(module_definition.get_bxml_serializer()(module_definition).data)
        stint_definition = StintDefinitionFactory()
        StintDefinitionXMLRenderer().render(stint_definition.get_bxml_serializer()(stint_definition).data)
        # XXX: Fix this
        # StintDefinitionXMLRenderer().render(StintDefinitionFactory().simple_serialize())
        template = TemplateFactory()
        TemplateXMLRenderer().render(template.get_bxml_serializer()(template).data)
        widget = WidgetFactory()
        WidgetXMLRenderer().render(widget.get_bxml_serializer()(widget))
        theme = ThemeFactory()
        ThemeXMLRenderer().render(theme.get_bxml_serializer()(theme).data)
        validator = ValidatorFactory(code=None)
        ValidatorXMLRenderer().render(validator.get_bxml_serializer()(validator).data)


class TestErySerializer(EryTestCase):
    def setUp(self):
        self.module_definition = ModuleDefinitionFactory()
        self.action = ActionFactory(module_definition=self.module_definition)
        self.widget = WidgetFactory()
        self.validator = ValidatorFactory(code=None)
        self.variable_definition = VariableDefinitionFactory(
            module_definition=self.module_definition,
            data_type=VariableDefinition.DATA_TYPE_CHOICES.choice,
            validator=self.validator,
            default_value='b',
        )
        self.variable_choice_item = VariableChoiceItemFactory(variable_definition=self.variable_definition, value='a')
        self.module_definition_widget = ModuleDefinitionWidgetFactory(
            module_definition=self.module_definition, widget=self.widget, variable_definition=self.variable_definition
        )

        self.widget_choice = WidgetChoiceFactory(widget=self.module_definition_widget, value='a')
        self.module_definition_widget_data = ModuleDefinitionWidget.get_bxml_serializer()(self.module_definition_widget).data
        self.start_stage = StageDefinitionFactory(module_definition=self.module_definition)
        self.warden_stage = StageDefinitionFactory(module_definition=self.module_definition)
        self.start_era = EraFactory(module_definition=self.module_definition, action=None)
        self.module_definition.start_stage = self.start_stage
        self.module_definition.warden_stage = self.warden_stage
        self.module_definition.start_era = self.start_era
        self.module_definition.save()
        # required to deserialize module_definition
        self.template = TemplateFactory(name='template-22', parental_template=None)
        self.stage_definition = StageDefinitionFactory(module_definition=self.module_definition)
        self.stage_template = StageTemplateFactory(stage_definition=self.stage_definition, template=self.template)
        self.stage_template_block = StageTemplateBlockFactory(stage_template=self.stage_template)
        self.condition = ConditionFactory(
            module_definition=self.module_definition,
            left_type=Condition.TYPE_CHOICES.variable,
            left_variable_definition=self.variable_definition,
            right_type=Condition.TYPE_CHOICES.expression,
            right_expression=1,
        )
        self.condition_data = self.condition.get_bxml_serializer()(self.condition).data
        self.module_definition_serializer = ModuleDefinition.get_bxml_serializer()(self.module_definition)
        self.module_definition_data = self.module_definition_serializer.data

    def test_xml_decode(self):
        base_xml = open('ery_backend/modules/tests/data/module_definition-0.bxml', 'rb')
        stream = base_xml.read()

        decoded_data = ModuleDefinition.get_bxml_serializer().xml_decode(stream)
        self.assertEqual(decoded_data, ModuleDefinitionXMLParser().parse(BytesIO(stream)))

    def test_set_empty(self):
        data_set_empty = [None, None, None]
        trick_set_one = [None, 1, None]
        trick_set_two = [0, 0, 0]
        trick_set_three = ['', '', '']
        trick_set_four = [[], {}, []]
        self.assertTrue(ErySerializer.set_empty(data_set_empty))
        self.assertFalse(ErySerializer.set_empty(trick_set_one))
        self.assertFalse(ErySerializer.set_empty(trick_set_two))
        self.assertFalse(ErySerializer.set_empty(trick_set_three))
        self.assertFalse(ErySerializer.set_empty(trick_set_four))


class TestImportExceptions(EryTestCase):
    def test_genone_missing_field(self):
        """
        1st gen mandatory field is missing
        """
        # preload models
        WidgetFactory(slug='moduledefinitionw1-PkaJygiV')
        ValidatorFactory(slug='moduledefinitionvd1-IoZsobtv', code=None)
        TemplateFactory(slug='moduledefinitiontemplate1-smzEnmHy')
        ThemeFactory(slug='moduledefinitiontheme1-fftsSJcD')
        # left <condition> tag empty for Action
        import_file = open('ery_backend/base/tests/data/genone.bxml', 'rb')
        with self.assertRaises(serializers.ValidationError):
            ModuleDefinition.import_instance_from_xml(import_file)

    def test_genthree_missing_field(self):
        """
        3rd gen mandatory field is missing.
        """
        # preload models
        WidgetFactory(slug='moduledefinitionw1-PkaJygiV')
        ValidatorFactory(slug='moduledefinitionvd1-IoZsobtv', code=None)
        TemplateFactory(slug='moduledefinitiontemplate1-smzEnmHy')
        ThemeFactory(slug='moduledefinitiontheme1-fftsSJcD')
        # left <language> tag empty for StageTemplateBlockTranslation
        import_file = open('ery_backend/base/tests/data/genthree.bxml', 'rb')
        with self.assertRaises(serializers.ValidationError):
            ModuleDefinition.import_instance_from_xml(import_file)

    def test_duplication_error(self):
        """
        Confirms duplicate fields cannot exist in an imported object.
        """
        WidgetFactory(slug='moduledefinitionw1-PkaJygiV')
        ValidatorFactory(slug='moduledefinitionvd1-IoZsobtv', code=None)
        TemplateFactory(slug='moduledefinitiontemplate1-smzEnmHy')
        ThemeFactory(slug='moduledefinitiontheme1-fftsSJcD')
        # added duplication ActionStep to Action: module_definition-action-2
        import_file = open('ery_backend/base/tests/data/duplication.bxml', 'rb')
        with self.assertRaises(serializers.ValidationError):
            ModuleDefinition.import_instance_from_xml(import_file)


class TestErySerializerMeta(EryTestCase):
    """
    Model's meta class should be used to generate serializers
    """

    def test_meta_info_exists(self):
        self.assertIsNotNone(ModuleDefinition.SerializerMeta)
        expected_md_model_serializer_fields = (
            'action_set',
            'command_set',
            'condition_set',
            'era_set',
            'forms',
            'moduledefinitionprocedure_set',
            'module_widgets',
            'robots',
            'stage_definitions',
            'variabledefinition_set',
        )
        self.assertEqual(expected_md_model_serializer_fields, ModuleDefinition.SerializerMeta.model_serializer_fields)

    def test_generation_from_meta(self):
        serializer = Action.get_duplication_serializer()
        self.assertTrue(issubclass(serializer, ErySerializer))


class TestValidation(EryTestCase):
    def test_get_minimally_valid_serializer_with_md_having_invalid_action(self):
        TemplateFactory(slug='defaulttemplate-asd123')
        ThemeFactory(slug='defaulttheme-asd123')

        md_data = {
            'name': 'MyMD',
            'comment': 'Mine alone, not sharing',
            'primary_frontend': 'Web',
            'primary_language': 'en',
            'action_set': [{'comment': 'Im not acting ;)'}],
        }
        serializer, queued_methods = ModuleDefinition.get_bxml_serializer()(data=md_data).get_minimally_valid_serializer()
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.initial_data['name'], md_data['name'])
        self.assertEqual(serializer.initial_data['comment'], md_data['comment'])
        self.assertEqual(serializer.initial_data['primary_frontend'], md_data['primary_frontend'])
        self.assertEqual(serializer.initial_data['primary_language'], md_data['primary_language'])
        self.assertNotIn('action_set', serializer.initial_data)
        self.assertEqual(len(queued_methods), 2)  # update_or_create_direct/reverse relationships
        queued_method_names = [info[0].__qualname__ for info in queued_methods]
        self.assertIn('ErySerializer.update_or_create_direct_relations', queued_method_names)
        self.assertIn('ErySerializer.update_or_create_reverse_relations', queued_method_names)


class TestFileDependentField(EryTestCase):
    """
    Confirm file dependent field validation/lookup works as expected.
    """

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.frontend = FrontendFactory()
        cls.web = Frontend.objects.get(name='Web')
        cls.primary_language = Language.objects.get(iso_639_1='en')
        cls.default_template = TemplateFactory(slug='defaulttemplate-asd123')
        cls.default_theme = ThemeFactory(slug='defaulttheme-asd123')
        cls.base_md_data = {
            'name': "MyModule",
            'comment': "For modularity",
            'primary_frontend': cls.frontend.id,
            'primary_language': cls.primary_language.pk,
            'default_template': cls.default_template.id,
            'default_theme': cls.default_theme.id,
        }
        cls.duplication_serializer = ModuleDefinition.get_duplication_serializer()

    def test_invalid_reference(self):
        """Given name of an instance that doesn't exist (even after retry) because it is not serialized"""
        md_data = {
            'action_set': [
                {
                    'name': 'MyAction',
                    'steps': [
                        {'action_type': ActionStep.ACTION_TYPE_CHOICES.log, 'condition': 'MyCond', 'log_message': "A message"}
                    ],
                }
            ],
        }

        serializer = self.duplication_serializer(data={**self.base_md_data, **md_data})
        with self.assertRaises(rest_framework.exceptions.ValidationError) as cm:
            serializer.validate_and_save()

        self.assertIn('action_step.condition', cm.exception.detail[0])

    def test_invalid_nested_format(self):
        stint_spec = StintSpecificationFactory()
        data = stint_spec.get_mutation_serializer()(stint_spec).data
        del data['id']
        data['name'] = 'StintSpecClone'
        data['allowed_language_frontend_combinations'] = 'abc'  # Should be a list or dict, not str
        with self.assertRaises(rest_framework.exceptions.ValidationError) as cm:
            stint_spec.get_mutation_serializer()(data=data).validate_and_save()

        self.assertIn('stint_specification.allowed_language_frontend_combinations.', cm.exception.detail)

    def test_depth_level_1_nested(self):
        """FK of child (stage_def.pre_action) requires file info (module_definition) """
        # Note: Always use serializer.save instead of just serializer.is_valid, since the
        # serializer may need to loop validation due to order
        md_data = {
            'action_set': [{'name': 'MyAction',}],
            'stage_definitions': [
                {
                    'name': 'MyStage',
                    'breadcrumb_type': StageDefinition.BREADCRUMB_TYPE_CHOICES.all,
                    'end_stage': True,
                    'pre_action': 'MyAction',  # depth level 2 reference pre_action.stage_definition.module_definition
                }
            ],
        }
        serializer = self.duplication_serializer(data={**self.base_md_data, **md_data})
        instance = serializer.validate_and_save()
        self.assertIsInstance(instance, ModuleDefinition)
        self.assertTrue(instance.stage_definitions.filter(name='MyStage').exists())

    def test_self_referentials(self):
        """Self referential fields (stage_def.redirects.next_stage_definition)"""
        md_data = {
            'stage_definitions': [
                {
                    'name': 'MyStage',
                    'breadcrumb_type': StageDefinition.BREADCRUMB_TYPE_CHOICES.all,
                    'end_stage': True,
                    'redirects': [{'order': 1, 'next_stage_definition': 'MyStage2'}],
                },
                {
                    'name': 'MyStage2',
                    'breadcrumb_type': StageDefinition.BREADCRUMB_TYPE_CHOICES.all,
                    'end_stage': True,
                    'redirects': [
                        {
                            'order': 1,
                            # This is FINE! CIRCLES ARE FINE!
                            'next_stage_definition': 'MyStage',
                        }
                    ],
                },
            ]
        }
        serializer = self.duplication_serializer(data={**self.base_md_data, **md_data})
        instance = serializer.validate_and_save()

        self.assertTrue(
            instance.stage_definitions.get(name='MyStage').redirects.filter(next_stage_definition__name='MyStage2').exists()
        )
        self.assertTrue(
            instance.stage_definitions.get(name='MyStage2').redirects.filter(next_stage_definition__name='MyStage').exists()
        )

    def test_upper_level_ref_to_lower_level(self):
        """A file might have nullable field that needs said file"""
        md_data = {
            'start_era': 'MyEra',
            'era_set': [{'name': 'MyEra', 'is_team': True,},],
        }
        serializer = self.duplication_serializer(data={**self.base_md_data, **md_data})
        instance = serializer.validate_and_save()
        era = instance.era_set.filter(name='MyEra').first()
        self.assertIsNotNone(era)

    def test_many_file_dependent(self):
        md_data = {
            'name': 'MyModuleDef',
            'primary_frontend': Frontend.objects.get(name='Web').id,
            'primary_language': self.primary_language.pk,
            'default_template': self.default_template.id,
            'default_theme': self.default_theme.id,
            'action_set': [
                {
                    'name': 'MyAction',
                    'steps': [
                        {
                            'action_type': ActionStep.ACTION_TYPE_CHOICES.save_data,
                            'for_each': random.choice([choice for choice, _ in ActionStep.FOR_EACH_CHOICES]),
                            'order': 12,
                            'to_save': ['my_vd', 'my_vd2', 'my_vd3'],
                        }
                    ],
                }
            ],
            'variabledefinition_set': [
                {
                    'name': 'my_vd',
                    'data_type': VariableDefinition.DATA_TYPE_CHOICES.int,
                    'scope': VariableDefinition.SCOPE_CHOICES.hand,
                },
                {
                    'name': 'my_vd2',
                    'data_type': VariableDefinition.DATA_TYPE_CHOICES.int,
                    'scope': VariableDefinition.SCOPE_CHOICES.hand,
                },
                {
                    'name': 'my_vd3',
                    'data_type': VariableDefinition.DATA_TYPE_CHOICES.int,
                    'scope': VariableDefinition.SCOPE_CHOICES.hand,
                },
            ],
        }

        serializer = self.duplication_serializer(data=md_data)
        instance = serializer.validate_and_save()
        action = instance.action_set.filter(name='MyAction').first()
        self.assertIsNotNone(action)
        self.assertTrue(action.steps.filter(to_save__name='my_vd').exists())
        self.assertTrue(action.steps.filter(to_save__name='my_vd2').exists())
        self.assertTrue(action.steps.filter(to_save__name='my_vd3').exists())


class TestEryBXMLSerializerSave(EryTestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.primary_language = Language.objects.get(iso_639_1='en')
        cls.default_template = TemplateFactory(slug='defaulttemplate-asd123')
        cls.default_theme = ThemeFactory(slug='defaulttheme-asd123')

    def test_missing_data(self):
        """Serializer should fail to save if required data is missing"""
        module_data = {'comment': '123', 'primary_frontend': 'Web', 'primary_language': 'en'}  # No name

        with self.assertRaises(rest_framework.exceptions.ValidationError) as cm:
            ModuleDefinition.get_bxml_serializer()(data=module_data).validate_and_save()

        self.assertIn('name', cm.exception.detail['ModuleDefinitionBXMLSerializer'])

    def test_invalid_required_relation(self):
        module_data = {
            'name': 'MyModule',
            'primary_frontend': 'abc',
        }

        with self.assertRaises(serializers.ValidationError) as cm:
            ModuleDefinition.get_bxml_serializer()(data=module_data).validate_and_save()

        self.assertIn('primary_frontend', cm.exception.detail['ModuleDefinitionBXMLSerializer'])

    def test_fill_defaults(self):
        """Omitted default fields should be seen as valid and filled as necessary"""
        module_data = {'name': 'IssaMe', 'primary_frontend': 'Web'}

        md = ModuleDefinition.get_bxml_serializer()(data=module_data).validate_and_save()
        self.assertIsNotNone(md.primary_frontend)
        self.assertIsNotNone(md.primary_language)
        self.assertIsNotNone(md.default_template)

    def test_basic_atomic(self):
        """ModuleDefinition should not be created if there is an invalid action"""
        test_bxml = open(f'{os.getcwd()}/ery_backend/base/tests/data/invalid_action.bxml', 'rb')
        with self.assertRaises(serializers.ValidationError):
            ModuleDefinition.import_instance_from_xml(test_bxml)
        self.assertFalse(ModuleDefinition.objects.filter(name='ActionMD').exists())

    def test_complex_atomic(self):
        """ModuleDefinition should not be created if there is an invalid reference to a condition inside of an ActionStep"""
        correct_test_bxml = open(f'{os.getcwd()}/ery_backend/base/tests/data/complex_action.bxml', 'rb')
        # Same as above, but with referene to non-existent condition
        test_bxml = open(f'{os.getcwd()}/ery_backend/base/tests/data/invalid_complex_action.bxml', 'rb')
        correct_md = ModuleDefinition.import_instance_from_xml(correct_test_bxml)
        self.assertEqual(correct_md.name, 'ActionMD')
        action_1 = correct_md.action_set.get(name='IHaveAName')
        self.assertEqual(action_1.steps.count(), 2)
        action_2 = correct_md.action_set.get(name='IHaveAName2')
        self.assertEqual(action_2.steps.count(), 1)
        action_3 = correct_md.action_set.get(name='IHaveAName3')
        self.assertEqual(action_3.steps.count(), 0)

        # Has same name as module_def in test_bxml
        correct_md.delete()
        with self.assertRaises(serializers.ValidationError):
            ModuleDefinition.import_instance_from_xml(test_bxml)
        self.assertFalse(ModuleDefinition.objects.filter(name='ActionMD').exists())

    def test_generation(self):
        """create_bxml_serializer should return a serializer"""
        serializer = Action.create_bxml_serializer()
        self.assertTrue(issubclass(serializer, ErySerializer))

    def test_base_attributes(self):
        """default attributes for bxml serializers"""
        serializer = Action.create_bxml_serializer()
        fields = serializer().fields
        # Default exclude
        self.assertNotIn('created', fields)
        self.assertNotIn('modified', fields)
        self.assertIn('created', serializer.Meta.exclude)
        self.assertIn('modified', serializer.Meta.exclude)

        # Non-related attrs
        self.assertIn('name', fields)
        self.assertIn('comment', fields)

        # Pk fields
        self.assertIsInstance(fields['id'], rest_framework.relations.PrimaryKeyRelatedField)
        self.assertIsInstance(fields['module_definition'], rest_framework.relations.PrimaryKeyRelatedField)

        # ModelSerializerFields
        self.assertTrue(issubclass(fields['steps'].child.__class__, ErySerializer))

    def test_slug_field(self):
        """Confirm slugfields are autogenerated and work as expected"""
        form_field = FormFieldFactory()
        self.assertEqual(form_field.get_bxml_serializer()().fields['widget'].__class__.__name__, 'SlugRelatedField')
        data = form_field.get_bxml_serializer()(form_field).data
        self.assertEqual(data['widget'], form_field.widget.slug)

    def test_empty_data(self):
        """Must have data to be saved"""
        serializer = Action.get_bxml_serializer()()
        with self.assertRaises(rest_framework.exceptions.ValidationError):
            serializer.validate_and_save()

    def test_no_parents(self):
        """
        A parent should be write only so it doesn't appear in the data.
        A user does not refer to it unless said parent is a FileDependentField. Instead, we inject needed parent ids.
        """
        module_definition = ModuleDefinitionFactory()
        StageDefinitionFactory(module_definition=module_definition)
        data = module_definition.get_bxml_serializer()(instance=module_definition).data
        self.assertNotIn('module_definition', data['stage_definitions'])

    def test_nullable_choice_field(self):
        """
        A nullable choice char field, which has allow_blank=True, should also automatically have allow_null=True
        """
        field = StintSpecification.get_bxml_serializer()().get_fields()['immediate_payment_method']
        self.assertTrue(field.allow_blank)
        self.assertTrue(field.allow_null)


class TestEryDuplicationSerializerSave(EryTestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.moduledef_duplication_serializer = ModuleDefinition.get_duplication_serializer()

    def test_empty_data(self):
        """Must have data to be saved"""
        serializer = self.moduledef_duplication_serializer()
        with self.assertRaises(rest_framework.exceptions.ValidationError):
            serializer.validate_and_save()

    def test_single_id_related_field(self):
        web = Frontend.objects.get(name='Web')
        md_data = {
            'name': "MyModule",
            'comment': "For modularity",
            'primary_frontend': web.id,
        }
        serializer = self.moduledef_duplication_serializer(data=md_data)
        instance = serializer.validate_and_save()
        self.assertEqual(instance.primary_frontend, web)

    def test_nested_many_relationships(self):
        """
        Confirm nested many relationships are properly deserialized
        """
        md_data = {
            'name': "MyModule",
            'comment': "For modularity",
            'primary_frontend': Frontend.objects.get(name='Web').id,
            'stage_definitions': [
                {'name': 'StageDef1', 'comment': 'The first'},
                {'name': 'StageDef2', 'comment': 'The latter'},
            ],
            'action_set': [{'name': 'Action1', 'comment': 'The first'}, {'name': 'Action2', 'comment': 'The second'}],
        }
        serializer = self.moduledef_duplication_serializer(data=md_data)
        instance = serializer.validate_and_save()
        self.assertTrue(instance.stage_definitions.filter(name='StageDef1').exists())
        self.assertTrue(instance.stage_definitions.filter(name='StageDef2').exists())
        self.assertTrue(instance.action_set.filter(name='Action1').exists())
        self.assertTrue(instance.action_set.filter(name='Action2').exists())

    def test_many_id_related_field(self):
        keywords = [KeywordFactory() for _ in range(random.randint(1, 5))]
        md_data = {
            'name': "MyModule",
            'comment': "For modularity",
            'primary_frontend': Frontend.objects.get(name='Web').id,
            'keywords': [keyword.id for keyword in keywords],
        }
        serializer = self.moduledef_duplication_serializer(data=md_data)
        instance = serializer.validate_and_save()
        for keyword in keywords:
            self.assertTrue(instance.keywords.filter(name=keyword.name).exists())

    def test_many_slug_related_field(self):
        keywords = [KeywordFactory() for _ in range(random.randint(1, 5))]
        md_data = {
            'name': "MyModule",
            'comment': "For modularity",
            'primary_frontend': 'Web',
            'keywords': [keyword.name for keyword in keywords],
        }
        serializer = ModuleDefinition.get_bxml_serializer()(data=md_data)
        instance = serializer.validate_and_save()
        for keyword in keywords:
            self.assertTrue(instance.keywords.filter(name=keyword.name).exists())

    def test_one_to_one_relationships(self):
        """
        Confirm a nested one to one model serializer is properly deserialized.
        """

        form = FormFactory()
        condition = ConditionFactory(module_definition=form.module_definition)
        validator = ValidatorFactory()
        vd = VariableDefinitionFactory(
            module_definition=form.module_definition, data_type=VariableDefinition.DATA_TYPE_CHOICES.int
        )
        web = Frontend.objects.get(name='Web')
        widget = WidgetFactory(frontend=web)
        data = {
            'form': form.id,
            'order': 0,
            'tab_order': 0,
            'field': {
                'name': 'MyField',
                'widget': widget.id,
                'variable_definition': vd.name,
                'random_mode': 'asc',
                'disable': condition.name,
                'validator': validator.id,
                'initial_value': json.dumps(32),
                'helper_text': "All of my help is big for my heart is deep",
                'required': False,
            },
        }
        # Confirm data validatity
        serializer = FormItem.get_duplication_serializer()(data=data)
        instance = serializer.validate_and_save()
        self.assertIsNotNone(instance)


class TestErySerializerUpdateManyRelateds(EryTestCase):
    def setUp(self):
        self.module_definition = ModuleDefinitionFactory()
        self.keywords = sorted(
            [KeywordFactory() for _ in range(random.randint(1, 10))], key=lambda keyword: keyword.name.lower()
        )
        self.module_definition.keywords.set(self.keywords)
        self.keep_keywords = self.keywords.copy()
        for _ in range(random.randint(1, len(self.keywords))):
            self.keep_keywords.remove(random.choice(self.keep_keywords))
        self.new_keywords = sorted(
            [KeywordFactory() for _ in range(random.randint(1, 5))], key=lambda keyword: keyword.name.lower()
        )

    def test_update_preexisting_manyrelateds_bxml(self):
        serializer_cls = self.module_definition.get_bxml_serializer()
        data = serializer_cls(self.module_definition).data
        self.assertEqual([keyword.name for keyword in self.keywords], data['keywords'])
        data['keywords'] = [keyword.name for keyword in self.keep_keywords + self.new_keywords]
        new_md = serializer_cls(data=data).validate_and_save()
        self.assertEqual(
            list(new_md.keywords.values_list('name', flat=True)),
            sorted([keyword.name for keyword in self.keep_keywords + self.new_keywords], key=lambda name: name.lower()),
        )

    def test_update_preexisting_manyrelateds_mutation(self):
        serializer_cls = self.module_definition.get_mutation_serializer()
        data = serializer_cls(self.module_definition).data
        del data['id']
        self.assertEqual([keyword.id for keyword in self.keywords], data['keywords'])
        data['keywords'] = [keyword.id for keyword in self.keep_keywords + self.new_keywords]
        new_md = serializer_cls(data=data).validate_and_save()

        self.assertEqual(
            sorted(list(new_md.keywords.values_list('id', flat=True))),
            sorted(keyword.id for keyword in self.keep_keywords + self.new_keywords),
        )
