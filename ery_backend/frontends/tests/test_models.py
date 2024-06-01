import json
from unittest import mock

from test_plus.test import TestCase

from ery_backend.base.cache import get_func_cache_key
from ery_backend.base.testcases import EryTestCase, create_test_hands
from ery_backend.base.utils import get_default_language
from ery_backend.frontends.models import Frontend
from ery_backend.modules.factories import ModuleDefinitionWidgetFactory
from ery_backend.stages.factories import StageFactory
from ery_backend.widgets.factories import WidgetFactory
from ..models import SMSStage
from ..factories import FrontendFactory, SMSStageFactory


class TestFrontEnd(TestCase):
    def setUp(self):
        self.frontend = FrontendFactory(name='test_frontend', comment='test_frontend comment here')

    def test_exists(self):
        self.assertIsNotNone(self.frontend)

    def test_expected_attributes(self):
        self.assertEqual(self.frontend.name, 'test_frontend')
        self.assertEqual(self.frontend.comment, 'test_frontend comment here')
        self.assertIsNotNone(self.frontend.slug)


class TestSMSStage(EryTestCase):
    def setUp(self):
        self.stage = StageFactory()
        self.sms_stage = SMSStageFactory(stage=self.stage, send=3, replayed=2, faulty_inputs=68)

    def test_exists(self):
        self.assertIsNotNone(self.sms_stage)

    def test_expected_attributes(self):
        self.assertEqual(self.sms_stage.stage, self.stage)
        self.assertEqual(self.sms_stage.send, 3)
        self.assertEqual(self.sms_stage.replayed, 2)
        self.assertEqual(self.sms_stage.faulty_inputs, 68)


class TestGetSMSWidgets(EryTestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.sms = Frontend.objects.get(name='SMS')
        cls.language = get_default_language()

    def setUp(self):
        self.hand = create_test_hands(
            frontend_type='SMS', render_args=['module_definition_widget'], signal_pubsub=False
        ).first()
        self.widgets = [
            ModuleDefinitionWidgetFactory(
                module_definition=self.hand.current_module_definition, widget=WidgetFactory(frontend=self.sms)
            )
            for _ in range(3)
        ]
        self.sms_stage = SMSStageFactory(stage=self.hand.stage)
        self.stage_template = self.hand.stage.stage_definition.stage_templates.get(template__frontend__name='SMS')
        self.cache_key = get_func_cache_key(SMSStage.get_sms_widgets, self.sms_stage, self.language)
        original_block = self.stage_template.blocks.get(name='ModuleDefinitionWidgets')
        translation = original_block.translations.first()
        translation.content += ''.join([f'<{widget.name}/>' for widget in self.widgets])
        translation.save()
        self.expected_cache_value = json.dumps([widget.get_cache_tag() for widget in self.widgets])

    @mock.patch('ery_backend.frontends.sms_utils.SMSStageTemplateRenderer.get_sms_widgets')
    def test_get_sms_widgets(self, mock_get_widgets):
        """
        Confirm method can be successfully called.
        """
        mock_get_widgets.return_value = {
            f'{widget.name}-StageTemplateBlock-{widget.get_privilege_ancestor().id}': widget for widget in self.widgets
        }
        widgets = self.sms_stage.get_sms_widgets(hand=self.hand)
        mock_get_widgets.assert_called_with()
        self.assertEqual(list(widgets), self.widgets)
