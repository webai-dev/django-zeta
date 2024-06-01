from ery_backend.base.testcases import EryTestCase

from ..factories import WidgetFactory, WidgetEventFactory, WidgetConnectionFactory, WidgetEventStepFactory
from ..models import Widget, WidgetConnection, WidgetEvent, WidgetEventStep


class TestWidgetEventBXMLSerializer(EryTestCase):
    def setUp(self):
        self.widget_event = WidgetEventFactory(include_event_steps=False)
        self.widget_event_serializer = WidgetEvent.get_bxml_serializer()(self.widget_event)

    def test_exists(self):
        self.assertIsNotNone(self.widget_event_serializer)

    def test_expected_attributes(self):
        self.assertEqual(self.widget_event_serializer.data['event_type'], self.widget_event.event_type)


class TestWidgetEventStepBXMLSerializer(EryTestCase):
    def setUp(self):
        self.widget_event_step = WidgetEventStepFactory(event_action_type=WidgetEventStep.EVENT_ACTION_TYPE_CHOICES.run_code)
        self.widget_event_serializer = WidgetEventStep.get_bxml_serializer()(self.widget_event_step)

    def test_exists(self):
        self.assertIsNotNone(self.widget_event_serializer)

    def test_expected_attributes(self):
        self.assertEqual(self.widget_event_serializer.data['event_action_type'], self.widget_event_step.event_action_type)
        self.assertEqual(self.widget_event_serializer.data['code'], self.widget_event_step.code)


class TestWidgetBXMLSerializer(EryTestCase):
    def setUp(self):
        self.other_widget = WidgetFactory()
        self.widget = WidgetFactory()
        self.widget.connect(self.other_widget)
        self.widget_event = WidgetEventFactory(widget=self.widget)
        self.widget_serializer = Widget.get_bxml_serializer()(self.widget)

    def test_exists(self):
        self.assertIsNotNone(self.widget_serializer)

    def test_expected_attributes(self):
        self.assertEqual(self.widget_serializer.data['name'], self.widget.name)
        self.assertEqual(self.widget_serializer.data['comment'], self.widget.comment)
        self.assertEqual(self.widget_serializer.data['code'], self.widget.code)
        self.assertEqual(self.widget_serializer.data['frontend'], self.widget.frontend.slug)


class TestWidgetConnectionBXMLSerializer(EryTestCase):
    def setUp(self):
        self.target = WidgetFactory()
        self.widget_connection = WidgetConnectionFactory(target=self.target)
        self.widget_connection_serializer = WidgetConnection.get_bxml_serializer()(self.widget_connection)

    def test_exists(self):
        self.assertIsNotNone(self.widget_connection_serializer)

    def test_expected_attributes(self):
        self.assertEqual(self.widget_connection_serializer.data['target'], self.widget_connection.target.slug)
