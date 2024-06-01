import random
import unittest

from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError

from languages_plus.models import Language

from ery_backend.base.cache import cache
from ery_backend.base.testcases import EryTestCase, create_test_hands
from ery_backend.keywords.factories import KeywordFactory
from ery_backend.frontends.factories import FrontendFactory
from ery_backend.frontends.models import Frontend
from ery_backend.stint_specifications.models import StintSpecificationAllowedLanguageFrontend
from ery_backend.widgets.factories import WidgetFactory, WidgetConnectionFactory
from ery_backend.widgets.models import WidgetConnection
from ..factories import TemplateFactory, TemplateBlockFactory, TemplateBlockTranslationFactory, TemplateWidgetFactory
from ..models import TemplateBlock, Template, TemplateWidget


def get_translation(template_block, language_code):
    return template_block.translations.get(template_block=template_block, language=Language.objects.get(pk=language_code))


class TestTemplate(EryTestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.primary_language = Language.objects.get(pk='en')
        cls.web = Frontend.objects.get(name='Web')
        cls.sms = Frontend.objects.get(name='SMS')

    def setUp(self):
        self.frontend = FrontendFactory()
        self.template_3 = TemplateFactory(name='template_3')
        self.template_2 = TemplateFactory(name='template_2', parental_template=self.template_3)
        self.template = TemplateFactory(
            name='test_template',
            comment='test_template comment here',
            parental_template=self.template_2,
            frontend=self.frontend,
        )

    def test_exists(self):
        self.assertIsNotNone(self.template)

    def test_expected_attributes(self):
        self.assertEqual(self.template.name, 'test_template')
        self.assertEqual(self.template.comment, 'test_template comment here')
        self.assertEqual(self.template.parental_template, self.template_2)
        self.assertEqual(self.template.frontend, self.frontend)
        self.assertEqual(self.template.primary_language, Language.objects.get(pk='en'))
        self.assertIsNotNone(self.template.slug)

    def test_get_widgets(self):
        """Confirm method is frontend specific"""
        nested_web_widgets = []
        tw_1 = TemplateWidgetFactory(template=self.template, widget=WidgetFactory(frontend=self.web))
        nested_web_widgets += [
            WidgetConnectionFactory(originator=tw_1.widget, target=WidgetFactory(frontend=self.web)).target
            for _ in range(random.randint(1, 10))
        ]
        nested_web_widgets += [
            WidgetConnectionFactory(
                originator=random.choice(nested_web_widgets), target=WidgetFactory(frontend=self.web)
            ).target
            for _ in range(random.randint(1, 10))
        ]
        tw_2 = TemplateWidgetFactory(template=self.template, widget=WidgetFactory(frontend=self.web))
        web_widgets = self.template.get_widgets()
        for template_widget in (tw_1, tw_2):
            self.assertIn(template_widget.widget, web_widgets)
        for nested_web_widget in nested_web_widgets:
            self.assertIn(nested_web_widget, web_widgets)

    def test_circuluar_parent(self):
        circular_template_1 = TemplateFactory()
        circular_template_2 = TemplateFactory()
        circular_template_3 = TemplateFactory()
        circular_template_4 = TemplateFactory()
        circular_template_5 = TemplateFactory()
        circular_template_6 = TemplateFactory()
        self.assertTrue(circular_template_1._validate_not_circular())  # pylint: disable=protected-access

        # self referential
        with self.assertRaises(ValidationError):
            circular_template_1.parental_template = circular_template_1
            circular_template_1.save()

        # 1 gen circle
        with self.assertRaises(ValidationError):
            circular_template_2.parental_template = circular_template_3
            circular_template_2.save()
            circular_template_3.parental_template = circular_template_2
            circular_template_3.save()

        # mutli gen circle
        with self.assertRaises(ValidationError):
            circular_template_4.parental_template = circular_template_5
            circular_template_4.save()
            circular_template_5.parental_template = circular_template_6
            circular_template_5.save()
            circular_template_6.parental_template = circular_template_4
            circular_template_6.save()

    def test_duplicate(self):
        preload_keywords = [KeywordFactory() for _ in range(3)]
        for keyword in preload_keywords:
            self.template.keywords.add(keyword)
        template_block = TemplateBlockFactory(template=self.template)
        template_block_translation_1 = TemplateBlockTranslationFactory(
            template_block=template_block, language=Language.objects.all()[0]
        )
        template_block_translation_2 = TemplateBlockTranslationFactory(
            template_block=template_block, language=Language.objects.all()[1]
        )
        template_widget_1 = TemplateWidgetFactory(template=self.template)
        template_widget_2 = TemplateWidgetFactory(template=self.template)
        template_2 = self.template.duplicate()
        # existence
        self.assertIsNotNone(template_2)
        # expected attributes
        self.assertNotEqual(template_2, self.template)
        self.assertEqual(template_2.name, '{}_copy'.format(self.template.name))
        self.assertEqual(template_2.frontend, self.template.frontend)
        self.assertEqual(template_2.parental_template, self.template.parental_template)
        # expected children
        template_block_2 = TemplateBlock.objects.filter(template=template_2).first()
        self.assertIsNotNone(template_block_2)
        self.assertEqual(template_block_2.name, template_block.name)
        self.assertTrue(
            template_block_2.translations.filter(
                language=template_block_translation_1.language, content=template_block_translation_1.content
            ).exists()
        )
        self.assertTrue(
            template_block_2.translations.filter(
                language=template_block_translation_2.language, content=template_block_translation_2.content
            ).exists()
        )
        self.assertTrue(
            template_2.template_widgets.filter(
                name=template_widget_1.name, comment=template_widget_1.comment, widget=template_widget_1.widget
            ).exists()
        )
        self.assertTrue(
            template_2.template_widgets.filter(
                name=template_widget_2.name, comment=template_widget_2.comment, widget=template_widget_2.widget
            ).exists()
        )
        # Expected keywords
        for keyword in preload_keywords:
            self.assertIn(keyword, template_2.keywords.all())

    def test_get_blocks(self):
        hand = create_test_hands(n=1, signal_pubsub=False).first()
        preferred_language = Language.objects.get(pk='aa')
        hand.language = preferred_language
        hand.save()
        hand.stint.stint_specification.allowed_language_frontend_combinations.add(
            StintSpecificationAllowedLanguageFrontend.objects.get_or_create(
                frontend=hand.frontend, language=preferred_language, stint_specification=hand.stint.stint_specification
            )[0]
        )

        ancestral_template = TemplateFactory()
        parental_template = TemplateFactory(parental_template=ancestral_template)
        # template_block content should be of preferred language
        template = TemplateFactory(parental_template=parental_template)
        template_block_1 = TemplateBlockFactory(template=template)
        TemplateBlockTranslationFactory(template_block=template_block_1, language=preferred_language)
        template_block_2 = TemplateBlockFactory(template=template)
        TemplateBlockTranslationFactory(template_block=template_block_2, language=preferred_language)
        template_block_3 = TemplateBlockFactory(template=template)
        TemplateBlockTranslationFactory(template_block=template_block_3, language=preferred_language)
        expected_results = {}
        for template_block in [template_block_1, template_block_2, template_block_3]:
            expected_results[template_block.name] = template_block.get_translation(language=preferred_language).content

        blocks = template.get_blocks(language=hand.language)
        for block in expected_results:
            self.assertTrue(blocks[block]['content'] == expected_results[block])

        # blocks should include unique blocks of parental generations
        parental_template_block = TemplateBlockFactory(template=parental_template)
        preferred_parental_translation = TemplateBlockTranslationFactory(
            template_block=parental_template_block, language=preferred_language
        )
        self.assertEqual(
            template.get_blocks(hand.language)[parental_template_block.name]['content'],
            preferred_parental_translation.content,
        )

        # blocks should include unique blocks of ancestral generations
        ancestral_template_block = TemplateBlockFactory(template=ancestral_template)
        ancestral_translation = TemplateBlockTranslationFactory(
            template_block=ancestral_template_block, language=preferred_language, content='Filler content'
        )
        self.assertEqual(
            template.get_blocks(hand.language)[ancestral_template_block.name]['content'], ancestral_translation.content,
        )

        # nonunique parental blocks should not be included, as they are to be overwritten
        conflict_parental_template_block = TemplateBlockFactory(template=parental_template, name=template_block_1.name)
        preferred_conflict_translation = TemplateBlockTranslationFactory(
            template_block=conflict_parental_template_block, language=preferred_language
        )
        self.assertNotEqual(
            template.get_blocks(hand.language)[conflict_parental_template_block.name]['content'],
            preferred_conflict_translation.content,
        )

    def test_parental_template_restrictions(self):
        """
        Cannot remove parental_template if template has more than one associated block.
        """
        TemplateBlockFactory(template=self.template)
        TemplateBlockFactory(template=self.template)
        with self.assertRaises(ValidationError):
            self.template.parental_template = None
            self.template.save()

    def test_import(self):
        # preload dependencies as defined in xml
        frontend = Frontend.objects.get(name='Web')
        preload_widget_1 = WidgetFactory(slug='testwidget-abc123')
        preload_widget_2 = WidgetFactory(slug='testwidget-abc456')
        parental_template = TemplateFactory(slug='moduledefinitiontemplate2-mXsMkPUQ')
        top_xml = open('ery_backend/templates/tests/data/module_definition-template-1.bxml', 'rb')
        top_template = Template.import_instance_from_xml(top_xml, name='instance_new')
        # check expected attributes
        self.assertIsNotNone(top_template)
        self.assertEqual(top_template.name, 'instance_new')
        # retrieved via get
        self.assertEqual(top_template.parental_template, parental_template)
        self.assertEqual(top_template.frontend, frontend)
        # created
        template_block = top_template.blocks.filter(name='ModuleDefinitionTb').first()
        self.assertIsNotNone(template_block)
        self.assertTrue(template_block.translations.filter(language='en').exists())
        self.assertTrue(template_block.translations.filter(language='aa').exists())
        self.assertTrue(top_template.template_widgets.filter(widget=preload_widget_1).exists())
        self.assertTrue(top_template.template_widgets.filter(widget=preload_widget_2).exists())

        first_child_xml = open('ery_backend/templates/tests/data/template-1.bxml', 'rb')
        first_child_template = Template.import_instance_from_xml(first_child_xml)
        # check expected attributes
        self.assertIsNotNone(first_child_template)
        self.assertEqual(first_child_template.name, 'template-1')
        # retrieved via get
        self.assertEqual(first_child_template.parental_template, top_template)
        self.assertEqual(first_child_template.frontend, frontend)

        second_child_xml = open('ery_backend/templates/tests/data/template-2.bxml', 'rb')
        second_child_template = Template.import_instance_from_xml(second_child_xml)
        # check expected attributes
        self.assertIsNotNone(second_child_template)
        self.assertEqual(second_child_template.name, 'template-2')
        # retrieved via get
        self.assertEqual(second_child_template.parental_template, top_template)
        self.assertEqual(second_child_template.frontend, frontend)

        grandchild_xml = open('ery_backend/templates/tests/data/template-3.bxml', 'rb')
        grandchild_template = Template.import_instance_from_xml(grandchild_xml)
        # check expected attributes
        self.assertIsNotNone(grandchild_template)
        self.assertEqual(grandchild_template.name, 'template-3')
        # retrieved via get
        self.assertEqual(grandchild_template.parental_template, second_child_template)
        self.assertEqual(grandchild_template.frontend, frontend)

    def test_is_ready(self):
        """
        Verify method passes only if all blocks of given frontend are ready.
        """
        template = TemplateFactory(primary_language=self.primary_language)

        # should not work if no blocks
        result, _ = template.is_ready(self.primary_language)
        self.assertFalse(result)

        template_block = TemplateBlockFactory(template=template)
        TemplateBlockTranslationFactory(template_block=template_block, language=self.primary_language)
        result, _ = template.is_ready(self.primary_language)
        self.assertTrue(result)

        # should work
        child_template = TemplateFactory(parental_template=template)
        template_block_2 = TemplateBlockFactory(template=child_template)
        template_block_3 = TemplateBlockFactory(template=child_template)
        TemplateBlockTranslationFactory(template_block=template_block_2, language=self.primary_language)
        TemplateBlockTranslationFactory(template_block=template_block_3, language=self.primary_language)

        result, _ = template.is_ready(self.primary_language)
        self.assertTrue(result)

        # should not work if template has ancestral template that is not ready
        ancestral_template = TemplateFactory(primary_language=self.primary_language)
        ancestral_tb = TemplateBlockFactory(template=ancestral_template)
        TemplateBlockTranslationFactory(template_block=ancestral_tb, language=self.primary_language)
        SUPER_ANCESTRAL_TEMPLATE = TemplateFactory()
        ancestral_template.parental_template = SUPER_ANCESTRAL_TEMPLATE
        ancestral_template.save()
        template.parental_template = ancestral_template
        template.save()

        result, _ = template.is_ready(self.primary_language)
        self.assertFalse(result)


@unittest.skip('Address in issue #710')
class TestGetWidgetsCaching(EryTestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.web = Frontend.objects.get(name='Web')

    def setUp(self):
        self.template = TemplateFactory()
        TemplateWidgetFactory(template=self.template, widget=WidgetFactory(frontend=self.web))
        TemplateWidgetFactory(template=self.template, widget=WidgetFactory(frontend=self.web))

    def test_get_widgets_cached(self):

        key = Template.get_widgets.cache_key(self.template, self.web)
        self.assertIsNone(cache.get(key))
        widgets = self.template.get_widgets(self.web)
        self.assertEqual(list(cache.get(key)), list(widgets))

    def test_invalidation_on_parental_template_addition(self):
        """
        Cache should invalidate on change to target template.
        """
        key = Template.get_widgets.cache_key(self.template, self.web)
        self.template.get_widgets(self.web)
        self.template.parental_template = TemplateFactory(frontend=self.web)
        self.template.save()
        self.assertIsNone(cache.get(key))

    def test_invalidation_on_ancestral_template_change(self):
        """
        Cache should invalidate on change to ancestral template of target template.
        """
        key = Template.get_widgets.cache_key(self.template, self.web)
        ancestral_template = TemplateFactory(frontend=self.web)
        parental_template = TemplateFactory(frontend=self.web, parental_template=ancestral_template)
        self.template.parental_template = parental_template
        self.template.save()
        self.template.get_widgets(self.web)
        self.assertIsNotNone(cache.get(key))
        ancestral_template.save()
        self.assertIsNone(cache.get(key))

    def test_invalidation_on_ancestral_templatewidget_addition(self):
        """
        Addition of a new template_widget to ancestor should invalidate cache key.
        """
        key = Template.get_widgets.cache_key(self.template, self.web)
        ancestral_template = TemplateFactory(frontend=self.web)
        parental_template = TemplateFactory(frontend=self.web, parental_template=ancestral_template)
        self.template.parental_template = parental_template
        self.template.save()
        self.template.get_widgets(self.web)
        self.assertIsNotNone(cache.get(key))
        TemplateWidget.objects.create(widget=WidgetFactory(frontend=self.web), template=ancestral_template, name='Name')
        self.assertIsNone(cache.get(key))

    def test_invalidation_on_ancestral_widgetconnection_addition(self):
        """
        Addition of a new widget_connection to ancestor should invalidate cache key.
        """
        key = Template.get_widgets.cache_key(self.template, self.web)
        ancestral_template = TemplateFactory(frontend=self.web)
        parental_template = TemplateFactory(frontend=self.web, parental_template=ancestral_template)
        self.template.parental_template = parental_template
        self.template.save()
        tw = TemplateWidget.objects.create(widget=WidgetFactory(frontend=self.web), template=ancestral_template, name='Name')
        self.template.get_widgets(self.web)
        self.assertIsNotNone(cache.get(key))
        WidgetConnection.objects.create(originator=tw.widget, target=WidgetFactory(frontend=self.web), name='Name')
        self.assertIsNone(cache.get(key))


class TestTemplateBlock(EryTestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.web = Frontend.objects.get(name='Web')
        cls.sms = Frontend.objects.get(name='SMS')

    def setUp(self):
        self.template = TemplateFactory()
        self.template_block = TemplateBlockFactory(template=self.template, name='Root',)

    def test_exists(self):
        self.assertIsNotNone(self.template_block)

    def test_expected_attributes(self):
        self.assertEqual(self.template_block.template, self.template)
        self.assertEqual(self.template_block.name, 'Root')

    def test_get_privilege_ancestor(self):
        self.assertEqual(self.template_block.get_privilege_ancestor(), self.template_block.template)

    def test_get_privilege_ancestor_cls(self):
        self.assertEqual(self.template_block.get_privilege_ancestor_cls(), self.template_block.template.__class__)

    def test_get_privilege_ancestor_filter_path(self):
        self.assertEqual(self.template_block.get_privilege_ancestor_filter_path(), 'template')

    @unittest.skip("XXX: Address in issue #815")
    def test_unique_together(self):
        parental_template = TemplateFactory()
        template = TemplateFactory(parental_template=parental_template)
        with self.assertRaises(IntegrityError):
            TemplateBlockFactory(template=template, name='IntegrityViolationTemplate')
            TemplateBlockFactory(template=template, name='IntegrityViolationTemplate')

    def test_validation_errors(self):
        validation_fail_template_block = TemplateBlockFactory()
        with self.assertRaises(ValidationError):  # template w/ no parental_template can only have one block
            validation_fail_template_block.template = self.template
            validation_fail_template_block.save()

        self.template.parental_template = TemplateFactory()  # adding parental template fixes
        # must update name, which is root by default when no template.parental_template
        validation_fail_template_block.name = 'Child'
        validation_fail_template_block.template = self.template
        validation_fail_template_block.save()

    def test_naming_default(self):
        """
        If template_block.template has no parental template, name must be restricted to 'Root'.
        """
        # removing parental relationship should cause auto name change
        parental_template = TemplateFactory()
        self.template.parental_template = parental_template
        self.template.save()
        self.template_block.name = 'NotRoot'
        self.template_block.save()
        self.template_block.refresh_from_db()
        self.assertEqual(self.template_block.name, 'NotRoot')

        # name should be reset if parental_template removed
        self.template.parental_template = None
        self.template.save()
        self.template_block.refresh_from_db()
        self.assertEqual(self.template_block.name, 'Root')

        # name should be overriden on initial save if no parental template
        self.template.blocks.all().delete()
        block = TemplateBlockFactory(template=self.template, name='NotRoot')
        block.refresh_from_db()
        self.assertEqual(block.name, 'Root')

    def test_get_translation(self):
        preferred_language = Language.objects.get(pk='aa')
        nonpreferred_language = Language.objects.get(pk='ab')
        template_block = TemplateBlockFactory()
        TemplateBlockTranslationFactory(template_block=template_block, language=Language.objects.get(pk='en'))
        TemplateBlockTranslationFactory(language=nonpreferred_language, template_block=template_block)

        # if preffered, default, and nonpreferred exist, preferred should be returned
        preferred_translation = TemplateBlockTranslationFactory(language=preferred_language, template_block=template_block)
        self.assertEqual(template_block.get_translation(language=preferred_language).content, preferred_translation.content)

    def test_is_ready(self):
        other_language = Language.objects.get(pk='ab')
        primary_language = Language.objects.get(pk='en')
        # Ready if matching translation for primary_language
        template_block = TemplateBlockFactory()

        # No translations
        self.assertFalse(template_block.is_ready(primary_language)[0])

        # Incorrect language
        TemplateBlockTranslationFactory(template_block=template_block, language=other_language)
        self.assertFalse(template_block.is_ready(primary_language)[0])

        # Should pass
        TemplateBlockTranslationFactory(template_block=template_block, language=primary_language)
        self.assertTrue(template_block.is_ready(primary_language)[0])


class TestTemplateBlockTranslation(EryTestCase):
    def setUp(self):
        self.frontend = FrontendFactory()
        self.template_block = TemplateBlockFactory()
        self.template_block_translation = TemplateBlockTranslationFactory(
            template_block=self.template_block, language=Language.objects.first(), content='El pollo feo',
        )

    def test_exists(self):
        self.assertIsNotNone(self.template_block_translation)

    def test_expected_attributes(self):
        self.assertEqual(self.template_block_translation.template_block, self.template_block)
        self.assertEqual(self.template_block_translation.language, Language.objects.first())
        self.assertEqual(self.template_block_translation.content, 'El pollo feo')

    @unittest.skip("XXX: Address in issue #815")
    def test_unique_together(self):
        TemplateBlockTranslationFactory(language=self.template_block_translation.language, template_block=self.template_block)
        with self.assertRaises(IntegrityError):
            TemplateBlockTranslationFactory(
                language=self.template_block_translation.language, template_block=self.template_block
            )
