from unittest import mock

from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError

from languages_plus.models import Language

from ery_backend.actions.factories import ActionFactory
from ery_backend.base.exceptions import EryValidationError
from ery_backend.base.testcases import EryTestCase
from ery_backend.base.utils import get_default_language
from ery_backend.frontends.factories import FrontendFactory
from ery_backend.frontends.models import Frontend
from ery_backend.hands.factories import HandFactory
from ery_backend.modules.factories import ModuleDefinitionFactory
from ery_backend.stint_specifications.factories import StintSpecificationAllowedLanguageFrontendFactory
from ery_backend.templates.factories import TemplateFactory
from ..factories import (
    CommandFactory,
    CommandTemplateFactory,
    CommandTemplateBlockFactory,
    CommandTemplateBlockTranslationFactory,
)


class TestCommand(EryTestCase):
    def setUp(self):
        self.module_definition = ModuleDefinitionFactory()
        self.action = ActionFactory(module_definition=self.module_definition)
        self.comment = "Provides some sarcasm to your buddies."
        self.trigger_pattern = r'Help[\w\W]*'
        self.name = 'help_out_i_guess'
        self.command = CommandFactory(
            module_definition=self.module_definition,
            action=self.action,
            trigger_pattern=self.trigger_pattern,
            name=self.name,
            comment=self.comment,
        )
        self.command_2 = CommandFactory(module_definition=self.module_definition, action=None, trigger_pattern='Help')
        self.co_1 = CommandTemplateFactory(command=self.command)
        self.co_2 = CommandTemplateFactory(command=self.command_2)

    def test_exists(self):
        self.assertIsNotNone(self.command)

    def test_expected_attributes(self):
        self.assertEqual(self.command.module_definition, self.module_definition)
        self.assertEqual(self.command.action, self.action)
        self.assertEqual(self.command.trigger_pattern, self.trigger_pattern)
        self.assertEqual(self.command.name, self.name)
        self.assertEqual(self.command.comment, self.comment)
        self.assertTrue(self.command.command_templates.filter(id=self.co_1.id).exists())
        self.assertTrue(self.command_2.command_templates.filter(id=self.co_2.id).exists())

    def test_duplicate(self):
        # with action
        duplicate_command = self.command.duplicate()
        self.assertIsNotNone(duplicate_command)
        self.assertEqual(duplicate_command.name, f'{self.command.name}_copy')
        self.assertTrue(duplicate_command.command_templates.filter(template__frontend=self.co_1.template.frontend).exists())
        # without action
        duplicate_command_2 = self.command_2.duplicate()
        self.assertIsNotNone(duplicate_command_2)
        self.assertEqual(duplicate_command_2.name, f'{self.command_2.name}_copy')
        self.assertTrue(duplicate_command_2.command_templates.filter(template__frontend=self.co_2.template.frontend).exists())

    def test_check_template_uniqueness(self):
        """
        Confirms all frontends belonging to template set in self.command_templates are unique
        """
        self.command._check_frontend_uniqueness()  # pylint: disable=protected-access
        unique_frontend_template = TemplateFactory(frontend=FrontendFactory())
        CommandTemplateFactory(command=self.command, template=unique_frontend_template)
        self.command._check_frontend_uniqueness()  # pylint: disable=protected-access
        duplicate_frontend_template = TemplateFactory(frontend=unique_frontend_template.frontend)
        with self.assertRaises(IntegrityError):
            CommandTemplateFactory(command=self.command, template=duplicate_frontend_template)

    def test_expected_naming_errors(self):
        """
        Confirm Command cannot violate js naming conventions.
        """
        # reserved words
        with self.assertRaises(ValidationError):
            CommandFactory(name='choices')
        with self.assertRaises(ValidationError):
            CommandFactory(name='var')
        with self.assertRaises(ValidationError):
            CommandFactory(name='in')
        with self.assertRaises(ValidationError):
            CommandFactory(name='for')

        # punctuation
        with self.assertRaises(ValidationError):
            CommandFactory(name='hasUppErS')
        # valid
        CommandFactory(name='$hasdollarsign')
        CommandFactory(name='has_underscore')
        # invalid
        with self.assertRaises(ValidationError):
            CommandFactory(name='incorrect.punctuation')

        # numbers
        # valid
        CommandFactory(name='endswith2')
        # invalid
        with self.assertRaises(ValidationError):
            CommandFactory(name='3time2time1timebop')

        # spaces
        with self.assertRaises(ValidationError):
            CommandFactory(name='has spaces')


class TestCommandRenderErrors(EryTestCase):
    def setUp(self):
        self.command = CommandFactory()
        self.sms = Frontend.objects.get(name='SMS')
        self.web = Frontend.objects.get(name='Web')
        self.hand = HandFactory(frontend=self.sms)

    @mock.patch('ery_backend.commands.models.CommandTemplate.render')
    def test_no_template(self, mock_template_render):
        # Correct frontend, but no template
        with self.assertRaises(EryValidationError):
            self.command.render(self.hand)


class TestCommandTemplate(EryTestCase):
    def setUp(self):
        self.template = TemplateFactory()
        self.command = CommandFactory()
        self.comment = 'Drops aforementioned beat (conditional on swag levels)'
        self.command_template = CommandTemplateFactory(template=self.template, command=self.command)

    def test_exists(self):
        self.assertIsNotNone(self.command_template)

    def test_expected_attributes(self):
        self.assertEqual(self.command_template.command, self.command)
        self.assertEqual(self.command_template.template, self.template)


class TestCommandRender(EryTestCase):
    fixtures = [
        'countries',
        'command_render_sms',
        'languages',
        'roles_privileges',
    ]

    def test_render(self):
        """
        Confirms content is rendered as expected.
        Content is loaded from command_render_sms fixture.
        """
        from ery_backend.commands.models import CommandTemplate
        from ery_backend.stint_specifications.models import StintSpecification
        from ery_backend.users.factories import UserFactory

        sms = Frontend.objects.get(name='SMS')
        ss = StintSpecification.objects.get(name='render-command-sms-stintspecification')
        frontend_language = StintSpecificationAllowedLanguageFrontendFactory(frontend=sms, language=get_default_language())
        ss.allowed_language_frontend_combinations.add(frontend_language)
        jumpman = UserFactory()
        stint = ss.realize(jumpman)
        hand = HandFactory(stint=stint, frontend=sms, user=UserFactory())
        stint.start(jumpman, signal_pubsub=False)
        command_template = CommandTemplate.objects.get(command__name='Render')
        expected_output = """
This is a test of how our command templates work.
If you can see these. Either:
1) We're all awesome!
2) One of us thinks they are awesome enough for all of us!
I think it's both actually...""".lstrip(
            '\n'
        )
        self.assertEqual(command_template.render(hand), expected_output)


class TestCommandTemplateBlock(EryTestCase):
    def setUp(self):
        self.command_template = CommandTemplateFactory()
        self.ctb = CommandTemplateBlockFactory(name='Onthecorn', command_template=self.command_template)

    def test_exists(self):
        self.assertIsNotNone(self.ctb)

    def test_expected_attributes(self):
        self.assertEqual(self.ctb.name, 'Onthecorn')
        self.assertEqual(self.ctb.command_template, self.command_template)

    def test_get_privilege_ancestor(self):
        self.assertEqual(self.ctb.get_privilege_ancestor(), self.ctb.command_template.command.module_definition)

    def test_get_privilege_ancestor_cls(self):
        self.assertEqual(self.ctb.get_privilege_ancestor_cls(), self.ctb.command_template.command.module_definition.__class__)

    def test_get_privilege_ancestor_filter_path(self):
        self.assertEqual(self.ctb.get_privilege_ancestor_filter_path(), 'command_template__command__module_definition')

    def test_unique_together(self):
        CommandTemplateBlockFactory(command_template=self.command_template, name='Squares')
        CommandTemplateBlockFactory(command_template=self.command_template, name='Cubes')
        # different command templates should not trigger error
        CommandTemplateBlockFactory(command_template=CommandTemplateFactory(), name='Squares')
        with self.assertRaises(IntegrityError):
            CommandTemplateBlockFactory(command_template=self.command_template, name='Squares')


class TestCommandTemplateBlockTranslation(EryTestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.web = Frontend.objects.get(name='Web')

    def setUp(self):
        template = TemplateFactory(frontend=self.web)
        command_template = CommandTemplateFactory(template=template)
        self.ctb = CommandTemplateBlockFactory(command_template=command_template)
        self.translation = 'Cuddle the broskis'
        self.ctb_translation = CommandTemplateBlockTranslationFactory(
            command_template_block=self.ctb,
            content=self.translation,
            language=Language.objects.get(pk='ab'),
            frontend=self.web,
        )

    def test_exists(self):
        self.assertIsNotNone(self.ctb_translation)

    def test_expected_attributes(self):
        self.assertEqual(self.ctb_translation.command_template_block, self.ctb)
        self.assertEqual(self.ctb_translation.language, Language.objects.get(pk='ab'))
        self.assertEqual(self.ctb_translation.content, self.translation)
        self.assertEqual(self.ctb_translation.frontend, self.web)

    def test_unique_together(self):
        language = get_default_language()
        ctb = CommandTemplateBlockFactory()
        CommandTemplateBlockTranslationFactory(language=language, command_template_block=ctb, frontend=self.web)
        with self.assertRaises(IntegrityError):
            CommandTemplateBlockTranslationFactory(language=language, command_template_block=ctb, frontend=self.web)
