from unittest import mock
import unittest

from django.core.exceptions import ValidationError

from languages_plus.models import Language

from ery_backend.actions.factories import ActionFactory
from ery_backend.base.exceptions import EryValidationError, EryValueError
from ery_backend.frontends.factories import FrontendFactory
from ery_backend.frontends.models import Frontend
from ery_backend.modules.factories import ModuleDefinitionWidgetFactory, WidgetChoiceFactory, ModuleDefinitionFactory
from ery_backend.procedures.factories import ProcedureFactory
from ery_backend.roles.models import Role
from ery_backend.roles.utils import grant_role
from ery_backend.stages.factories import StageTemplateFactory, StageTemplateBlockFactory, StageTemplateBlockTranslationFactory
from ery_backend.templates.factories import TemplateFactory, TemplateBlockFactory, TemplateBlockTranslationFactory
from ery_backend.templates.models import Template
from ery_backend.users.factories import UserFactory

from ..testcases import EryTestCase, create_test_hands


class TestPrivilegedMixin(EryTestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.owner = Role.objects.get(name='owner')
        cls.user = UserFactory()

    def test_get_owner(self):
        md = ModuleDefinitionFactory()
        grant_role(self.owner, md, self.user)
        self.assertEqual(self.user, md.get_owner())


class TestBlockHolderMixin(EryTestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.default_language = Language.objects.get(pk='en')
        cls.web = Frontend.objects.get(name='Web')

    def setUp(self):
        self.hand = create_test_hands(n=1, signal_pubsub=False).first()

    def test_get_blocks_info(self):
        """
        Block info should include content, block_type, and ancestor_id.
        """
        from ery_backend.hands.factories import HandFactory

        hand = HandFactory()
        root_template = TemplateFactory(frontend=self.web)
        child_template = TemplateFactory(frontend=self.web, parental_template=root_template)
        template_block = TemplateBlockFactory(template=child_template)
        TemplateBlockTranslationFactory(
            template_block=template_block, frontend=self.web, language=self.default_language, content='Preferred web'
        )

        stage_template = StageTemplateFactory()
        stage_template.template.parental_template = child_template
        stage_template.template.save()
        st_block = StageTemplateBlockFactory(stage_template=stage_template)
        stage_template_translation = StageTemplateBlockTranslationFactory(
            stage_template_block=st_block, frontend=self.web, language=self.default_language, content='Preferred web'
        )
        blocks = stage_template.get_blocks(hand.frontend, hand.language)
        self.assertEqual(blocks[st_block.name]['block_type'], st_block.__class__.__name__)
        self.assertEqual(blocks[st_block.name]['content'], stage_template_translation.content)
        self.assertEqual(blocks[st_block.name]['ancestor_id'], st_block.get_privilege_ancestor().id)

    def test_get_blocks_with_frontend(self):
        """
        Confirm get_block performs as expected with frontend arg
        """
        preferred_language = Language.objects.get(pk='ab')
        self.hand.language = preferred_language
        self.hand.stint.stint_specification.save()
        sms = Frontend.objects.get(name='SMS')
        root_template = TemplateFactory(frontend=sms)
        child_template = TemplateFactory(frontend=sms, parental_template=root_template)
        template_block = TemplateBlockFactory(template=child_template)
        preferred_web_translation = TemplateBlockTranslationFactory(
            template_block=template_block, frontend=self.web, language=preferred_language, content='Preferred web'
        )
        TemplateBlockTranslationFactory(
            template_block=template_block, frontend=self.web, language=self.default_language, content='Default web'
        )
        TemplateBlockTranslationFactory(
            template_block=template_block, frontend=sms, language=preferred_language, content='Preferred sms'
        )
        TemplateBlockTranslationFactory(
            template_block=template_block, frontend=sms, language=self.default_language, content='Default sms'
        )
        # Return translation of correct frontend and language if exists
        blocks = child_template.get_blocks(self.hand.frontend, self.hand.language)
        self.assertEqual(blocks[template_block.name]['content'], preferred_web_translation.content)

    @unittest.skip('Re-add in issue #708')
    @mock.patch('ery_backend.base.mixins.BlockHolderMixin.evaluate_block')
    def test_get_blocks_uses_evaluate_block(self, mock_eval):
        """
        Confirm evaluate block is called once per block in get_blocks.
        """
        frontend = FrontendFactory()
        self.hand.frontend = frontend
        self.hand.save()
        root_template = TemplateFactory(frontend=frontend)
        language = root_template.primary_language
        child_template = TemplateFactory(parental_template=root_template, frontend=frontend)
        blocks = list()
        names = ('one', 'two')
        for i in range(2):
            tb = TemplateBlockFactory(template=child_template, name=f'tb{names[i]}')
            blocks.append(tb)
            TemplateBlockTranslationFactory(template_block=tb, language=language, content=f"{{{{{i}+1}}}}")
        st = StageTemplateFactory(template=child_template)
        for i in range(2):
            stb = StageTemplateBlockFactory(stage_template=st, name=f'stb{names[i]}')
            blocks.append(stb)
            StageTemplateBlockTranslationFactory(
                stage_template_block=stb, language=language, content=f"{{{{{i}+2}}}}", frontend=frontend
            )
        language = self.hand.language
        st.get_blocks(frontend, language)
        for block in blocks:
            mock_eval.assert_any_call(block.get_translation(frontend, language), self.hand)


class TestNameValidationMixin(EryTestCase):
    def test_validate_underscores(self):
        # has allow_underscores=False
        with self.assertRaises(ValidationError):
            ModuleDefinitionWidgetFactory(name='Has_underscore')

        # has allow_underscores=True
        ProcedureFactory(name='has_underscore')

    def test_validate_spaces(self):
        # has allow_spaces=False
        with self.assertRaises(ValidationError):
            ProcedureFactory(name='has space')

        # has allow_spaces=True
        ActionFactory(name='has space')


class TestJavascriptValidationMixin(EryTestCase):
    def test_reserved(self):
        with self.assertRaises(ValidationError):
            ProcedureFactory(name='var')
        with self.assertRaises(ValidationError):
            ProcedureFactory(name='if')
        with self.assertRaises(ValidationError):
            ProcedureFactory(name='in')

    def test_illegal_punctatuion(self):
        with self.assertRaises(ValidationError):
            ProcedureFactory(name='has.period')


class TestReactNamedMixin(EryTestCase):
    def test_require_capitalization(self):
        with self.assertRaises(EryValueError):
            ModuleDefinitionWidgetFactory(name='wronglynamedinput')
        ModuleDefinitionWidgetFactory(name='Correctlynamedinput')

    def test_cannot_start_with_number(self):
        with self.assertRaises(EryValueError):
            ModuleDefinitionWidgetFactory(name='6wronglynamedinputs')
        ModuleDefinitionWidgetFactory(name='Correctlynamed6inputs')


class TestJavascriptNamedMixin(EryTestCase):
    def test_cannot_have_caps(self):
        with self.assertRaises(ValidationError):
            ProcedureFactory(name='haSsomECaPs')

        ProcedureFactory(name='nocaps')


class TestJavascriptArgumentMixin(EryTestCase):
    """Same as JavaScriptNamedMixin"""


class TestSpecialGetTranslationFunctionality(EryTestCase):
    """
    Verify ChoiceMixin derivatives return value if translation not found.
    """

    def setUp(self):
        self.language = Language.objects.get(pk='en')

    def test_no_translation_returns_value(self):
        widget_choice = WidgetChoiceFactory()
        self.assertEqual(widget_choice.get_translation(language=self.language), widget_choice.value)


class TestGetTranslationErrors(EryTestCase):
    """
    Verify exception raised if no translation exists.
    """

    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.language = Language.objects.get(pk='en')

    def test_template_block(self):
        tb = TemplateBlockFactory()
        tb.translations.all().delete()
        with self.assertRaises(EryValidationError):
            tb.get_translation(frontend=tb.template.frontend, language=self.language)


class TestStateMixin(EryTestCase):
    """
    Confirm model can be created with one of states from StateMixin.
    """

    def test_state(self):
        template = TemplateFactory(state=Template.STATE_CHOICES.release)
        template.refresh_from_db()
        self.assertEqual(Template.STATE_CHOICES.release, template.state)
