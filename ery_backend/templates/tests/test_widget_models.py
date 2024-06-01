from unittest import mock
import unittest

from django.db.utils import IntegrityError

from ery_backend.base.testcases import EryTestCase
from ery_backend.hands.factories import HandFactory
from ery_backend.widgets.factories import WidgetFactory, WidgetEventFactory, WidgetEventStepFactory
from ery_backend.widgets.models import WidgetEvent, WidgetEventStep

from ..factories import TemplateFactory, TemplateWidgetFactory


class TestTemplateWidget(EryTestCase):
    def setUp(self):
        self.template = TemplateFactory()
        self.widget = WidgetFactory()
        self.name = 'EveryModelMustBeCombined'
        self.template_widget = TemplateWidgetFactory(template=self.template, widget=self.widget, name=self.name)

    def test_exists(self):
        self.assertIsNotNone(self.template_widget)

    def test_expected_attributes(self):
        self.template_widget.refresh_from_db()
        self.assertEqual(self.template_widget.template, self.template)
        self.assertEqual(self.template_widget.widget, self.widget)
        self.assertEqual(self.template_widget.name, self.name)

    @unittest.skip("XXX: Address in issue #815")
    def test_unique_together(self):
        # Can work with different names
        TemplateWidgetFactory(template=self.template, name='DifferentName')

        # Should fail with repeated name/template combination
        with self.assertRaises(IntegrityError):
            TemplateWidgetFactory(template=self.template, name=self.name)


class TestTriggerEvents(EryTestCase):
    """
    Confirm contained widget events are run as a result of running TemplateWidget.trigger_events.
    """

    def setUp(self):
        self.widget = WidgetFactory()
        self.tw = TemplateWidgetFactory(widget=self.widget)
        self.hand = HandFactory()

    @mock.patch('ery_backend.widgets.models.WidgetEvent.trigger', autospec=True)
    def test_one_event(self, mock_trigger):
        event_1 = WidgetEventFactory(widget=self.widget, event_type=WidgetEvent.REACT_EVENT_CHOICES.onClick)
        WidgetEventStepFactory(
            widget_event=event_1, event_action_type=WidgetEventStep.EVENT_ACTION_TYPE_CHOICES.run_code,
        )
        self.tw.trigger_events(event_1.name, WidgetEvent.REACT_EVENT_CHOICES.onClick, hand=self.hand)
        mock_trigger.assert_called_with(event_1, self.hand)

    @mock.patch('ery_backend.widgets.models.WidgetEvent.trigger', autospec=True)
    def test_many_events(self, mock_trigger):
        event_1 = WidgetEventFactory(widget=self.widget, event_type=WidgetEvent.REACT_EVENT_CHOICES.onClick)
        WidgetEventStepFactory(widget_event=event_1, event_action_type=WidgetEventStep.EVENT_ACTION_TYPE_CHOICES.run_code)
        WidgetEventStepFactory(widget_event=event_1, event_action_type=WidgetEventStep.EVENT_ACTION_TYPE_CHOICES.submit)
        WidgetEventStepFactory(widget_event=event_1, event_action_type=WidgetEventStep.EVENT_ACTION_TYPE_CHOICES.run_code)
        self.tw.trigger_events(event_1.name, WidgetEvent.REACT_EVENT_CHOICES.onClick, hand=self.hand)
        mock_trigger.assert_any_call(event_1, self.hand)
