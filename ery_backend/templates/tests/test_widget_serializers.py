from ery_backend.base.testcases import EryTestCase
from ery_backend.widgets.factories import WidgetFactory

from ..factories import TemplateFactory, TemplateWidgetFactory
from ..models import TemplateWidget


class TestTemplateWidgetBXMLSerializer(EryTestCase):
    def setUp(self):
        self.template = TemplateFactory()
        self.widget = WidgetFactory()
        self.template_widget = TemplateWidgetFactory(widget=self.widget, template=self.template)
        self.template_widget_serializer = TemplateWidget.get_bxml_serializer()(self.template_widget)

    def test_exists(self):
        self.assertIsNotNone(self.template_widget_serializer)

    def test_expected_attributes(self):
        self.assertEqual(self.template_widget_serializer.data['comment'], self.template_widget.comment)
        self.assertEqual(self.template_widget_serializer.data['name'], self.template_widget.name)
        self.assertEqual(self.template_widget_serializer.data['widget'], self.template_widget.widget.slug)
