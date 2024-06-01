from unittest import mock
import unittest

from django.core.exceptions import ObjectDoesNotExist
from django.db.utils import IntegrityError

from languages_plus.models import Language

from ery_backend.actions.factories import ActionFactory, ActionStepFactory
from ery_backend.actions.models import ActionStep
from ery_backend.base.testcases import EryTestCase, create_test_hands
from ery_backend.conditions.factories import ConditionFactory
from ery_backend.templates.factories import TemplateFactory, TemplateBlockFactory, TemplateBlockTranslationFactory
from ery_backend.templates.models import Template, TemplateBlock
from ery_backend.frontends.factories import FrontendFactory
from ery_backend.frontends.models import Frontend
from ery_backend.logs.models import Log
from ery_backend.modules.factories import ModuleDefinitionWidgetFactory
from ery_backend.modules.factories import ModuleDefinitionFactory
from ery_backend.stages.factories import StageDefinitionFactory
from ery_backend.stint_specifications.models import StintSpecificationAllowedLanguageFrontend
from ery_backend.themes.factories import ThemeFactory
from ery_backend.variables.factories import VariableDefinitionFactory
from ery_backend.variables.models import VariableDefinition
from ..factories import (
    StageDefinitionFactory,
    StageTemplateFactory,
    StageTemplateBlockFactory,
    StageTemplateBlockTranslationFactory,
    StageFactory,
    StageBreadcrumbFactory,
    RedirectFactory,
)
from ..models import StageTemplate, StageTemplateBlock, StageTemplateBlockTranslation, StageDefinition


class TestStageDefinition(EryTestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.default_language = Language.objects.get(pk='en')

    def setUp(self):
        self.template = TemplateFactory()
        self.module_definition = ModuleDefinitionFactory()
        self.pre_action = ActionFactory(module_definition=self.module_definition)
        self.variable_definition = VariableDefinitionFactory(data_type=VariableDefinition.DATA_TYPE_CHOICES.str)
        # Should have same module_definition in stage_template_block
        self.stage_definition = StageDefinitionFactory(
            end_stage=False,
            module_definition=self.module_definition,
            pre_action=self.pre_action,
            name='TestStint',
            comment="test_stint comment here",
            breadcrumb_type=StageDefinition.BREADCRUMB_TYPE_CHOICES.none,
        )
        self.stage_template = StageTemplate(stage_definition=self.stage_definition, template=self.template)
        self.stage_template.save()
        self.stage_template_block = StageTemplateBlockFactory(stage_template=self.stage_template)
        self.base_stage_definition = StageDefinitionFactory(pre_action=None)

    def test_exists(self):
        self.assertIsNotNone(self.stage_definition)

    def test_choice_fields(self):
        self.stage_definition.breadcrumb_type = StageDefinition.BREADCRUMB_TYPE_CHOICES.none
        self.stage_definition.save()
        self.stage_definition.breadcrumb_type = StageDefinition.BREADCRUMB_TYPE_CHOICES.back
        self.stage_definition.save()
        self.stage_definition.breadcrumb_type = StageDefinition.BREADCRUMB_TYPE_CHOICES.all
        self.stage_definition.save()

    def test_expected_attributes(self):
        self.stage_definition.refresh_from_db()
        self.assertEqual(self.stage_definition.name, 'TestStint')
        self.assertEqual(self.stage_definition.comment, 'test_stint comment here')
        self.assertFalse(self.stage_definition.end_stage)
        self.assertEqual(self.stage_definition.module_definition, self.module_definition)
        self.assertEqual(self.stage_definition.pre_action, self.pre_action)
        self.assertIn(self.template, self.stage_definition.templates.all())
        self.assertEqual(self.stage_definition.breadcrumb_type, StageDefinition.BREADCRUMB_TYPE_CHOICES.none)

    def test_get_privilege_ancestor(self):
        self.assertEqual(self.stage_definition.get_privilege_ancestor(), self.stage_definition.module_definition)

    def test_get_privilege_ancestor_cls(self):
        self.assertEqual(self.stage_definition.get_privilege_ancestor_cls(), self.stage_definition.module_definition.__class__)

    def test_get_privilege_ancestor_filter_path(self):
        self.assertEqual(self.stage_definition.get_privilege_ancestor_filter_path(), 'module_definition')

    def test_get_template(self):
        """
        Confirm stage_definition can retrieve connect template (through stage_templates)
        """
        self.stage_definition.stage_templates.all().delete()
        web_frontend = Frontend.objects.get(name='Web')
        sms_frontend = Frontend.objects.get(name='SMS')
        email_frontend = Frontend.objects.get(name='Email')
        web_template = TemplateFactory(frontend=web_frontend, name='WebTemplate')
        sms_template = TemplateFactory(frontend=sms_frontend, name='SMSTemplate')
        email_template = TemplateFactory(frontend=email_frontend, name='EmailTemplate')
        StageTemplateFactory(stage_definition=self.stage_definition, template=web_template)
        StageTemplateFactory(stage_definition=self.stage_definition, template=sms_template)
        StageTemplateFactory(stage_definition=self.stage_definition, template=email_template)
        self.assertEqual(self.stage_definition.get_template(web_frontend), web_template)
        self.assertEqual(self.stage_definition.get_template(sms_frontend), sms_template)
        self.assertEqual(self.stage_definition.get_template(email_frontend), email_template)

    def test_duplicate(self):
        redirects = [
            RedirectFactory(
                stage_definition=self.stage_definition,
                condition=ConditionFactory(module_definition=self.stage_definition.module_definition),
            )
            for _ in range(3)
        ]
        StageTemplateBlockTranslationFactory(
            content='Test translation', stage_template_block=self.stage_template_block, language=Language.objects.get(pk='aa')
        )
        stage_definition_2 = self.stage_definition.duplicate()
        self.assertIsNotNone(stage_definition_2)
        self.assertNotEqual(stage_definition_2, self.stage_definition)
        self.assertEqual('{}Copy'.format(self.stage_definition.name), stage_definition_2.name)
        # Parents should be equivalent
        self.assertEqual(self.stage_definition.module_definition, stage_definition_2.module_definition)
        # Siblings should be equivalent
        self.assertEqual(self.stage_definition.pre_action, stage_definition_2.pre_action)
        stage_template_2 = StageTemplate.objects.filter(
            stage_definition=stage_definition_2, template=self.stage_template.template
        ).first()
        self.assertIsNotNone(stage_template_2)
        stage_template_block_2 = StageTemplateBlock.objects.filter(stage_template=stage_template_2).first()
        # Children should not be equivalent
        self.assertNotIn(stage_template_2, self.stage_definition.stage_templates.all())
        self.assertIsNotNone(stage_template_block_2)
        self.assertTrue(
            StageTemplateBlockTranslation.objects.exclude(stage_template_block=self.stage_template_block).filter(
                content='Test translation'
            )
        )
        for redirect in redirects:
            self.assertTrue(
                stage_definition_2.redirects.filter(
                    next_stage_definition=redirect.next_stage_definition, condition=redirect.condition
                ).exists()
            )

    def test_check_template_uniqueness(self):
        """
        Confirms all frontends belonging to template set in self.stage_templates are unique
        """
        self.stage_definition._check_frontend_uniqueness()  # pylint: disable=protected-access
        unique_frontend_template = TemplateFactory(frontend=FrontendFactory())
        StageTemplateFactory(stage_definition=self.stage_definition, template=unique_frontend_template)
        self.stage_definition._check_frontend_uniqueness()  # pylint: disable=protected-access
        duplicate_frontend_template = TemplateFactory(frontend=self.template.frontend)
        with self.assertRaises(IntegrityError):
            StageTemplateFactory(stage_definition=self.stage_definition, template=duplicate_frontend_template)

    def test_stage_block_prioritization(self):
        """
        Test prioritization of get_blocks among StageTemplateBlockTranslations
        """
        preferred_language = Language.objects.first()
        hand = create_test_hands(n=1, signal_pubsub=False).first()
        hand.stint.stint_specification.allowed_language_frontend_combinations.add(
            StintSpecificationAllowedLanguageFrontend.objects.get_or_create(
                frontend=hand.frontend, language=preferred_language, stint_specification=hand.stint.stint_specification
            )[0]
        )
        hand.language = preferred_language
        hand.save()
        frontend = Frontend.objects.get(name='Web')
        template = TemplateFactory(frontend=frontend)
        stage_template = StageTemplateFactory(template=template)
        stage_definition = stage_template.stage_definition
        stage_template_block_1 = StageTemplateBlockFactory(name='Child', stage_template=stage_template)
        StageTemplateBlockTranslationFactory(
            language=self.default_language, stage_template_block=stage_template_block_1, frontend=frontend
        )
        preferred_stb1_translation = StageTemplateBlockTranslationFactory(
            stage_template_block=stage_template_block_1, frontend=frontend, language=preferred_language
        )
        stage_template_2 = StageTemplateFactory(template=TemplateFactory())
        stage_template_block_2 = StageTemplateBlockFactory(name='ChildNi', stage_template=stage_template_2)
        StageTemplateBlockTranslationFactory(
            language=preferred_language, stage_template_block=stage_template_block_2, frontend=frontend
        )

        # stage translation with nonpreferred language should not be preferred over stage translation of preferred language
        self.assertEqual(stage_definition.get_blocks(hand)['Child']['content'], preferred_stb1_translation.content)

        # stage translation of different frontend should not be included
        self.assertNotIn('ChildNi', stage_definition.get_blocks(hand))

    def test_get_blocks_prioritization(self):
        preferred_language = Language.objects.get(pk='ab')
        hand = create_test_hands(n=1, signal_pubsub=False).first()
        hand.stint.stint_specification.allowed_language_frontend_combinations.add(
            StintSpecificationAllowedLanguageFrontend.objects.get_or_create(
                language=preferred_language, frontend=hand.frontend, stint_specification=hand.stint.stint_specification
            )[0]
        )
        hand.language = preferred_language
        hand.stint.stint_specification.save()
        frontend = Frontend.objects.get(name='Web')
        template = TemplateFactory(frontend=frontend, primary_language=self.default_language)
        child_template = TemplateFactory(frontend=frontend, parental_template=template)
        stage_template = StageTemplateFactory(template=child_template)
        stage_definition = stage_template.stage_definition

        template_block = TemplateBlockFactory(template=template)
        TemplateBlockTranslationFactory(template_block=template_block, language=preferred_language)
        child_template_block_1 = TemplateBlockFactory(template=child_template, name='ChildIchi')
        child_block_1_preferred_translation = TemplateBlockTranslationFactory(
            template_block=child_template_block_1, language=preferred_language
        )
        TemplateBlockTranslationFactory(template_block=child_template_block_1, language=self.default_language)
        child_template_block_2 = TemplateBlockFactory(template=child_template, name='ChildNi')
        child_block_2_preferred_translation = TemplateBlockTranslationFactory(
            template_block=child_template_block_2, language=preferred_language
        )
        template_block_2 = TemplateBlockFactory(template=child_template, name='ChildSan')
        TemplateBlockTranslationFactory(template_block=template_block_2, language=preferred_language)
        child_stage_block_3 = StageTemplateBlockFactory(stage_template=stage_template, name='ChildSan')
        child_block_3_preferred_translation = StageTemplateBlockTranslationFactory(
            stage_template_block=child_stage_block_3, frontend=frontend, language=preferred_language
        )
        child_template_block_4 = TemplateBlockFactory(template=child_template, name='ChildShi')
        TemplateBlockTranslationFactory(template_block=child_template_block_4, language=preferred_language)
        # template translation with preferred or default language and unique name should be included
        child_stage_block_4 = StageTemplateBlockFactory(stage_template=stage_template, name='ChildShi')
        child_block_4_preferred_translation = StageTemplateBlockTranslationFactory(
            stage_template_block=child_stage_block_4, frontend=frontend, language=preferred_language
        )
        self.assertEqual(
            stage_definition.get_blocks(hand)['ChildIchi']['content'], child_block_1_preferred_translation.content
        )
        self.assertEqual(stage_definition.get_blocks(hand)['ChildNi']['content'], child_block_2_preferred_translation.content)

        # regardless of whether stage translation is of preferred language, should be preferred over template translation
        self.assertEqual(stage_definition.get_blocks(hand)['ChildSan']['content'], child_block_3_preferred_translation.content)
        self.assertEqual(stage_definition.get_blocks(hand)['ChildShi']['content'], child_block_4_preferred_translation.content)

    def test_realize(self):
        """
        Confirm stage instantiation occurs as expected.
        """
        stage = self.stage_definition.realize()
        stage_2 = self.stage_definition.realize()

        # should instantiate different objects
        self.assertEqual(stage.stage_definition, self.stage_definition)
        self.assertNotEqual(stage, stage_2)


class TestRedirectFlow(EryTestCase):
    """
    Confirm redirects perform as expected from StageDefinition
    """

    def setUp(self):
        self.hand = create_test_hands(n=1, signal_pubsub=False).first()
        self.module_definition = self.hand.current_module_definition
        self.stage_definition_1 = StageDefinitionFactory(module_definition=self.module_definition)
        self.stage_definition_2 = StageDefinitionFactory(module_definition=self.module_definition)
        self.stage_definition_3 = StageDefinitionFactory(module_definition=self.module_definition)
        self.redirect_1 = RedirectFactory(
            stage_definition=self.stage_definition_1, next_stage_definition=self.stage_definition_2, order=1
        )
        self.redirect_2 = RedirectFactory(
            stage_definition=self.stage_definition_1, next_stage_definition=self.stage_definition_3, order=2
        )

    def test_get_redirect_stage_no_conditions(self):
        """
        First match should be based only on order if no conditions.
        """
        self.assertEqual(self.stage_definition_1.get_redirect_stage(self.hand), self.redirect_1.next_stage_definition)

    @mock.patch('ery_backend.conditions.models.Condition.evaluate')
    def test_get_redirect_stage_with_conditions(self, mock_eval):
        mock_eval.return_value = False
        self.redirect_1.condition = ConditionFactory(module_definition=self.module_definition)
        self.redirect_1.save()
        self.assertEqual(self.stage_definition_1.get_redirect_stage(self.hand), self.redirect_2.next_stage_definition)

    @mock.patch('ery_backend.conditions.models.Condition.evaluate')
    def test_get_redirect_stage_errors(self, mock_eval):
        """
        No match found.
        """
        mock_eval.return_value = False
        for redirect in (self.redirect_1, self.redirect_2):
            redirect.condition = ConditionFactory(module_definition=self.hand.current_module_definition)
            redirect.save()
        with self.assertRaises(ObjectDoesNotExist):
            self.stage_definition_1.get_redirect_stage(self.hand)


class TestAddBreadcrumb(EryTestCase):
    def setUp(self):
        self.hand = create_test_hands(n=1, stage_n=2, redirects=True, signal_pubsub=False).first()
        self.md = self.hand.stage.stage_definition.module_definition

    @mock.patch('ery_backend.hands.models.Hand.pay')
    def test_breadcrumb(self, mock_pay):
        """
        Confirm redirect adds breadcrumb.
        """
        initial_breadcrumb = self.hand.current_breadcrumb
        self.assertIsNone(self.hand.current_breadcrumb.next_breadcrumb)
        self.hand.submit()
        self.assertNotEqual(initial_breadcrumb, self.hand.current_breadcrumb)
        self.assertEqual(initial_breadcrumb, self.hand.current_breadcrumb.previous_breadcrumb)


class TestEndStageProgression(EryTestCase):
    """
    Confirm a hand can transition from one Module to another via redirect.
    """

    def test_progression(self):
        """
        Confirm progression between Modules.
        """
        hand = create_test_hands(n=1, stage_n=2, module_definition_n=2, redirects=True, signal_pubsub=False).first()
        stint_definition = hand.stint.stint_specification.stint_definition
        module_definition_1 = stint_definition.module_definitions.first()
        module_definition_2 = stint_definition.module_definitions.exclude(id=module_definition_1.id).first()
        self.assertEqual(hand.stage.stage_definition, module_definition_1.start_stage)
        hand.submit()
        hand.refresh_from_db()
        self.assertEqual(hand.stage.stage_definition, module_definition_2.start_stage)
        self.assertEqual(hand.current_module_definition, module_definition_2)


class TestStageDeletion(EryTestCase):
    """
    Confirm a stage can be successfully deleted by first updating breadcrumb references.
    """

    def setUp(self):
        self.hand = create_test_hands(n=1, signal_pubsub=False).first()

    def test_normal_stage_delete(self):
        """
        Confirm nodes updated correctly on Stage (with all breadcrumbs allowed) deletion.
        """
        stage_1_definition = StageDefinitionFactory(module_definition=self.hand.current_module_definition)
        stage_1_a = StageFactory(stage_definition=stage_1_definition)
        delete_stage_definition = StageDefinitionFactory(module_definition=self.hand.current_module_definition)
        delete_stage_a = StageFactory(stage_definition=delete_stage_definition)
        stage_2_definition = StageDefinitionFactory(module_definition=self.hand.current_module_definition)
        stage_2 = StageFactory(stage_definition=stage_2_definition)

        start_crumb = StageBreadcrumbFactory(stage=stage_1_a, hand=self.hand)
        self.hand.current_breadcrumb = start_crumb
        self.hand.save()

        self.hand.set_breadcrumb(self.hand.create_breadcrumb(delete_stage_a))

        # has back_ref to start_crumb
        chain_crumb_1 = self.hand.create_breadcrumb(stage_2)
        self.hand.set_breadcrumb(chain_crumb_1)

        delete_stage_b = StageFactory(stage_definition=delete_stage_definition)
        # has back_ref to chain_crumb_1
        chain_crumb_2 = self.hand.create_breadcrumb(delete_stage_b)
        self.hand.set_breadcrumb(chain_crumb_2)
        stage_1_b = StageFactory(stage_definition=stage_2_definition)
        # has back_ref to chain_crumb_2
        last_breadcrumb = self.hand.create_breadcrumb(stage_1_b)
        delete_stage_definition.delete()

        # should have forward reference updated after next is deleted
        chain_crumb_1.refresh_from_db()
        self.assertEqual(chain_crumb_1.next_breadcrumb, last_breadcrumb)
        last_breadcrumb.refresh_from_db()
        self.assertEqual(last_breadcrumb.previous_breadcrumb, chain_crumb_1)

        self.hand.refresh_from_db()
        # hand's connection should be updated to the most recent remaining crumb
        self.assertEqual(self.hand.current_breadcrumb, last_breadcrumb)

    def test_forward_stage_delete(self):
        """
        Confirm nodes updated correctly on Stage (with no forward breadcrumbs allowed) deletion.
        """
        definition_1 = StageDefinitionFactory(
            module_definition=self.hand.current_module_definition, breadcrumb_type=StageDefinition.BREADCRUMB_TYPE_CHOICES.back
        )
        delete_definition = StageDefinitionFactory(module_definition=self.hand.current_module_definition)
        definition_2 = StageDefinitionFactory(module_definition=self.hand.current_module_definition)

        # starts with no forward crumb
        start_crumb = StageBreadcrumbFactory(stage=StageFactory(stage_definition=definition_1), hand=self.hand)
        self.hand.set_breadcrumb(start_crumb)
        chain_crumb = self.hand.create_breadcrumb(stage=StageFactory(stage_definition=delete_definition))
        self.hand.set_breadcrumb(chain_crumb)
        self.hand.create_breadcrumb(stage=StageFactory(stage_definition=definition_2))
        delete_definition.delete()

        start_crumb.refresh_from_db()
        # deletion of chain_crumb via cascade should not cause addition of last_crumb as next_breadcrumb
        self.assertIsNone(start_crumb.next_breadcrumb)

    def test_backward_stage_delete(self):
        """
        Confirm nodes updated correctly on Stage (with no backward breadcrumbs allowed) deletion.
        """
        definition_1 = StageDefinitionFactory(module_definition=self.hand.current_module_definition)
        delete_definition = StageDefinitionFactory(module_definition=self.hand.current_module_definition)
        definition_2 = StageDefinitionFactory(
            module_definition=self.hand.current_module_definition, breadcrumb_type=StageDefinition.BREADCRUMB_TYPE_CHOICES.none
        )

        start_crumb = StageBreadcrumbFactory(stage=StageFactory(stage_definition=definition_1), hand=self.hand)
        self.hand.set_breadcrumb(start_crumb)
        chain_crumb = self.hand.create_breadcrumb(stage=StageFactory(stage_definition=delete_definition))
        self.hand.set_breadcrumb(chain_crumb)
        # starts with no back_crumb
        last_crumb = self.hand.create_breadcrumb(stage=StageFactory(stage_definition=definition_2))
        delete_definition.delete()

        last_crumb.refresh_from_db()
        # deletion of chain_crumb via cascade should not cause addition of start_crumb as previous_breadcrumb
        self.assertIsNone(last_crumb.previous_breadcrumb)


class TestStageTemplate(EryTestCase):
    def setUp(self):
        self.stage_definition = StageDefinitionFactory()
        self.template = TemplateFactory()
        self.theme = ThemeFactory()
        self.stage_template = StageTemplateFactory(
            template=self.template, stage_definition=self.stage_definition, theme=self.theme,
        )

    def test_exists(self):
        self.assertIsNotNone(self.stage_template)

    def test_expected_attributes(self):
        self.assertEqual(self.stage_template.template, self.template)
        self.assertEqual(self.stage_template.stage_definition, self.stage_definition)
        self.assertEqual(self.stage_template.theme, self.theme)

    def test_get_privilege_ancestor(self):
        self.assertEqual(self.stage_template.get_privilege_ancestor(), self.stage_template.stage_definition.module_definition)

    def test_get_privilege_ancestor_cls(self):
        self.assertEqual(
            self.stage_template.get_privilege_ancestor_cls(), self.stage_template.stage_definition.module_definition.__class__
        )

    def test_get_privilege_ancestor_filter_path(self):
        self.assertEqual(self.stage_template.get_privilege_ancestor_filter_path(), 'stage_definition__module_definition')

    def test_clean(self):
        """
        Confirm one StageTemplate per frontend per stage
        """
        original_frontend = self.template.frontend
        original_stagedef = self.stage_template.stage_definition

        # Can have StageTemplate with nonunique frontend for a different stagedefinition
        unique_stagedef = StageDefinitionFactory()
        StageTemplateFactory(template__frontend=original_frontend, stage_definition=unique_stagedef)

        # Can have StageTemplate with unique frontend for same stagedefinition
        StageTemplateFactory(stage_definition=original_stagedef)

        # Cannot have StageTemplate with same frontend and same stagedefinition
        with self.assertRaises(IntegrityError):
            StageTemplateFactory(template__frontend=original_frontend, stage_definition=original_stagedef)


class TestStageTemplateBlock(EryTestCase):
    def setUp(self):
        self.stage_template = StageTemplateFactory()
        self.variable_definition = VariableDefinitionFactory(data_type=VariableDefinition.DATA_TYPE_CHOICES.str)
        self.module_definition_widget = ModuleDefinitionWidgetFactory(variable_definition=self.variable_definition)
        self.stage_definition_block = StageTemplateBlockFactory(stage_template=self.stage_template, name='Squares')
        self.stage_definition_block.save()

    def test_exists(self):
        self.assertIsNotNone(self.stage_definition_block)

    def test_expected_attributes(self):
        self.assertEqual(self.stage_definition_block.stage_template, self.stage_template)
        self.assertEqual(self.stage_definition_block.name, 'Squares')

    def test_expected_errors(self):
        """
        Verify frontend required in get_translation.
        """
        language = Language.objects.get(pk='en')
        frontend = self.stage_definition_block.stage_template.template.frontend
        StageTemplateBlockTranslationFactory(
            stage_template_block=self.stage_definition_block, frontend=frontend, language=language
        )
        self.stage_definition_block.get_translation(frontend, language)

    def test_get_privilege_ancestor(self):
        self.assertEqual(
            self.stage_definition_block.get_privilege_ancestor(),
            self.stage_definition_block.stage_template.stage_definition.module_definition,
        )

    def test_get_privilege_ancestor_cls(self):
        self.assertEqual(
            self.stage_definition_block.get_privilege_ancestor_cls(),
            self.stage_definition_block.stage_template.stage_definition.module_definition.__class__,
        )

    def test_get_privilege_ancestor_filter_path(self):
        self.assertEqual(
            self.stage_definition_block.get_privilege_ancestor_filter_path(),
            'stage_template__stage_definition__module_definition',
        )

    def test_unique_together(self):
        StageTemplateBlock(
            stage_template=self.stage_template, name='Squares',
        )
        StageTemplateBlock(
            stage_template=self.stage_template, name='Cubes',
        )
        StageTemplateBlock(
            stage_template=StageTemplateFactory(), name='Squares',
        )
        with self.assertRaises(IntegrityError):
            StageTemplateBlockFactory(
                stage_template=self.stage_template, name='Squares',
            )


class TestStageTemplateBlockTranslation(EryTestCase):
    """
    Test functionality of StageTemplateBlockTranslation
    """

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.web = Frontend.objects.get(name='Web')

    # pylint: disable=missing-docstring
    # pylint: disable=invalid-name
    def setUp(self):
        self.stage_template_block = StageTemplateBlockFactory()
        self.stb_translation = StageTemplateBlockTranslationFactory(
            language=Language.objects.first(),
            content='These names are getting too long',
            stage_template_block=self.stage_template_block,
            frontend=self.web,
        )

    def test_exists(self):  # pylint: disable=missing-docstring
        self.assertIsNotNone(self.stb_translation)

    def test_expected_attributes(self):  # pylint: disable=missing-docstring
        self.assertEqual(self.stb_translation.language, Language.objects.first())
        self.assertEqual(self.stb_translation.content, 'These names are getting too long')
        self.assertEqual(self.stb_translation.stage_template_block, self.stage_template_block)
        self.assertEqual(self.stb_translation.frontend, self.web)

    def test_unique_together(self):
        stage_template_block = StageTemplateBlockFactory()
        StageTemplateBlockTranslationFactory(language=Language.objects.get(pk='ab'), stage_template_block=stage_template_block)
        with self.assertRaises(IntegrityError):
            StageTemplateBlockTranslationFactory(
                language=Language.objects.get(pk='ab'), stage_template_block=stage_template_block
            )


class TestStageBreadcrumb(EryTestCase):
    def setUp(self):
        self.hand = create_test_hands(n=1, signal_pubsub=False).first()
        self.stage = self.hand.stage
        self.breadcrumb = StageBreadcrumbFactory(hand=self.hand, stage=self.stage)

    def test_exists(self):
        self.assertIsNotNone(self.breadcrumb)

    def test_expected_attributes(self):
        self.assertEqual(self.breadcrumb.hand, self.hand)
        self.assertEqual(self.breadcrumb.stage, self.stage)


class TestStage(EryTestCase):
    """
    Test functionality of Stage
    """

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.sms = Frontend.objects.get(name='SMS')
        cls.web = Frontend.objects.get(name='Web')
        cls.default_language = Language.objects.get(pk='en')

    def setUp(self):
        self.web_hand = create_test_hands(n=1, frontend_type='Web', signal_pubsub=False).first()
        self.web_stage_definition = self.web_hand.stage.stage_definition
        self.web_stage = StageFactory(stage_definition=self.web_stage_definition, preaction_started=True)

    def test_exists(self):
        self.assertIsNotNone(self.web_stage)

    def test_expected_attributes(self):
        self.assertEqual(self.web_stage.stage_definition, self.web_stage_definition)
        self.assertTrue(self.web_stage.preaction_started)

    @unittest.skip('Fix in issue #457')
    @mock.patch('ery_backend.scripts.engine_client.evaluate_without_side_effects')
    def test_render_sms(self, mock_eval):
        """
        Rendered sms should be one string in which blocks are replaced by the content of said blocks.
        """
        sms_hand = create_test_hands(
            n=1, frontend_type='SMS', render_args=['procedure', 'variable'], signal_pubsub=False
        ).first()
        mock_eval.return_value = 'Eval returns'
        # get blocks that overwrite each other
        originator = sms_hand.stage.stage_definition.stage_templates.get(template__frontend=self.sms)
        blocks = originator.get_blocks(sms_hand)
        expected_content = '\n'.join([blocks[tag] for tag in ['Questions', 'Answers', 'Procedure', 'Variable']]) + '\n'
        self.assertEqual(expected_content, originator.render_sms(sms_hand))

    @mock.patch('ery_backend.scripts.engine_client.evaluate_without_side_effects')
    def test_sms_tail_text(self, mock_eval):
        """
        Confirm tail text is rendered as expected.
        """
        sms_hand = create_test_hands(n=1, frontend_type='SMS', render_args=['procedure', 'variable']).first()
        mock_eval.return_value = 'Eval returns'
        originator = sms_hand.stage.stage_definition.stage_templates.get(template__frontend=sms_hand.frontend)
        tail_text = 'tail text test (say that three times fast)'
        answers_block = TemplateBlock.objects.get(template__frontend=sms_hand.frontend, name='Answers')
        translation = answers_block.translations.first()
        translation.content += tail_text
        translation.save()
        blocks = originator.get_blocks(self.sms, sms_hand.language)
        self.assertIn(blocks['Answers']['content'], originator.render_sms(sms_hand))

    @unittest.skip('Address in issue #401')
    # @mock.patch('ery_backend.base.mixins.BlockHolderMixin.render_web')
    # @mock.patch('ery_backend.modules.models.ModuleDefinitionWidget.render')
    def test_preaction_on_render(self):
        """
        Confirm preaction is executed on render if preaction_started is false
        """
        # mock_render.return_value = 'code'
        md = self.web_hand.current_module.stint_definition_module_definition.module_definition
        pre_action = ActionFactory(module_definition=md)
        stage_definition = StageDefinitionFactory(module_definition=md, pre_action=pre_action)
        stage = StageFactory(stage_definition=stage_definition)
        template = Template.objects.get(name='Root', frontend__name='Web')
        StageTemplateFactory(stage_definition=stage_definition, template=template)
        self.web_hand.stage = stage
        self.web_hand.save()
        message = 'By Gorge it worked!'
        ActionStepFactory(
            action=pre_action,
            for_each=ActionStep.FOR_EACH_CHOICES.current_hand_only,
            action_type=ActionStep.ACTION_TYPE_CHOICES.log,
            log_message=message,
        )
        self.web_hand.refresh_from_db()
        self.web_hand.stage.render(self.web_hand)
        # 2nd execution should not trigger preaction
        self.web_hand.stage.render(self.web_hand)
        # confirm preaction was executed
        self.assertTrue(Log.objects.filter(message=message).exists())
        # verify no repeats
        self.assertEqual(len(list(Log.objects.filter(message=message).all())), 1)

    @unittest.skip('Fix in issue #457')
    @mock.patch('ery_backend.frontends.renderers.SMSStageTemplateRenderer.render_widget')
    def test_module_definition_widgets_in_render_sms(self, mock_eval):
        """
        Confirm module_definition_widgets rendered as expected.
        """
        # some module_definition_widget in content
        # Fake value should appear in position of module_definition_widget.
        sms_module_definition_widget_hand = create_test_hands(
            n=1, frontend_type='SMS', render_args=['module_definition_widget']
        ).first()
        mock_eval.return_value = '7'
        originator = sms_module_definition_widget_hand.stage.stage_definition.stage_templates.get(
            template__frontend=sms_module_definition_widget_hand.frontend
        )
        content_block = TemplateBlock.objects.get(
            template__frontend=sms_module_definition_widget_hand.frontend, name='Content'
        )
        translation = content_block.translations.get(frontend=sms_module_definition_widget_hand.frontend)
        content = "A lil something something and a bit of ... "
        translation.content = content
        translation.save()
        expected_content = '\n'.join([content, '7']) + '\n'
        self.assertEqual(originator.render_sms(sms_module_definition_widget_hand), expected_content)


class TestRedirect(EryTestCase):
    def setUp(self):
        self.condition = ConditionFactory()
        self.stage_definition = StageDefinitionFactory()
        self.next_stage_definition = StageDefinitionFactory(module_definition=self.stage_definition.module_definition)
        self.redirect = RedirectFactory(
            condition=self.condition,
            stage_definition=self.stage_definition,
            next_stage_definition=self.next_stage_definition,
            order=5,
        )

    def test_exists(self):
        self.assertIsNotNone(self.redirect)

    def test_expected_attributes(self):
        self.redirect.refresh_from_db()
        self.assertEqual(self.redirect.stage_definition, self.stage_definition)
        self.assertEqual(self.redirect.next_stage_definition, self.next_stage_definition)
        self.assertEqual(self.redirect.order, 5)
        self.assertEqual(self.redirect.condition, self.condition)

    def test_multiple_modules(self):
        """
        To preserve modularity, a Redirect cannot connect StageDefinitions from different
        ModuleDefintion.
        """
        with self.assertRaises(IntegrityError):
            RedirectFactory(stage_definition=StageDefinitionFactory(), next_stage_definition=StageDefinitionFactory())
