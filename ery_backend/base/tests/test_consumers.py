from django.core.exceptions import ValidationError

from ery_backend.hands.factories import HandFactory
from ery_backend.templates.widget_factories import TemplateWidgetFactory
from ery_backend.stints.factories import StintFactory
from ery_backend.users.factories import UserFactory

from ..consumers import WebRunnerConsumer
from ..testcases import EryTestCase


class TestWidgetEventErrors(EryTestCase):
    def test_required_keys(self):
        """Error should be triggered if required keys not present in data attribute."""
        user = UserFactory()
        consumer = WebRunnerConsumer(scope={'user': user})
        data = {}
        with self.assertRaises(ValidationError):
            consumer.trigger_widget_events(data)
        template_widget = TemplateWidgetFactory()
        data['gql_id'] = template_widget.gql_id
        with self.assertRaises(ValidationError):
            consumer.trigger_widget_events(data)
        stint = StintFactory()
        data['stint_id'] = stint.pk
        with self.assertRaises(ValidationError):
            consumer.trigger_widget_events(data)
        data['event_type'] = 'onClick'
        data['current_stage_id'] = 1
        data['name'] = 'waaaayleft'
        # Should pass
        HandFactory(user=user, stint=stint)
        consumer.trigger_widget_events(data)
