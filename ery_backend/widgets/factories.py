import random

import factory
import factory.fuzzy

from django.utils.crypto import get_random_string
from languages_plus.models import Language

from ery_backend.base.testcases import ReactNamedFactoryMixin
from .models import WidgetEventStep, WidgetEvent, Widget


class WidgetEventStepFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'widgets.WidgetEventStep'

    widget_event = factory.SubFactory('ery_backend.widgets.factories.WidgetEventFactory')
    event_action_type = factory.fuzzy.FuzzyChoice([choice for choice, _ in WidgetEventStep.EVENT_ACTION_TYPE_CHOICES])
    order = factory.Sequence(lambda n: n)

    @factory.lazy_attribute
    def code(self):
        if self.event_action_type == WidgetEventStep.EVENT_ACTION_TYPE_CHOICES.run_code:
            return get_random_string(length=random.randint(1, 1000))
        return None


class WidgetEventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'widgets.WidgetEvent'

    widget = factory.SubFactory('ery_backend.widgets.factories.WidgetFactory')
    name = factory.Sequence('widgetevent{}'.format)

    @factory.lazy_attribute
    def event_type(self):
        if self.widget.frontend.name == 'Web':
            return random.choice([react_event for react_event, _ in WidgetEvent.REACT_EVENT_CHOICES])
        if self.widget.frontend.name == "SMS":
            return random.choice([sms_event for sms_event, _ in WidgetEvent.SMS_EVENT_CHOICES])
        return get_random_string(length=random.randint(1, 25))

    @factory.post_generation
    def include_event_steps(self, create, extracted, **kwargs):
        if extracted:
            event_step_count = random.randint(1, 10)
            for _ in range(event_step_count):
                WidgetEventStepFactory(widget_event=self)


class WidgetFactory(ReactNamedFactoryMixin):
    class Meta:
        model = 'widgets.Widget'

    name = factory.Sequence('Widget{}'.format)
    comment = factory.fuzzy.FuzzyText(length=50)
    frontend = factory.SubFactory('ery_backend.frontends.factories.FrontendFactory')
    primary_language = factory.LazyFunction(lambda: Language.objects.order_by('?').first())
    slug = factory.LazyAttribute(lambda x: Widget.create_unique_slug(x.name))
    external = factory.fuzzy.FuzzyChoice([True, False])

    @factory.lazy_attribute
    def address(self):
        if self.external:
            return get_random_string(random.randint(1, 7))
        return None

    @factory.lazy_attribute
    def code(self):
        if not self.external:
            return get_random_string(random.randint(1, 1000))
        return None


class WidgetConnectionFactory(ReactNamedFactoryMixin):
    class Meta:
        model = 'widgets.WidgetConnection'

    name = factory.Sequence('Widget{}'.format)
    originator = factory.SubFactory('ery_backend.widgets.factories.WidgetFactory')
    target = factory.SubFactory('ery_backend.widgets.factories.WidgetFactory')


class WidgetPropFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'widgets.WidgetProp'

    name = factory.Sequence('widget_prop_{}'.format)
    widget = factory.SubFactory('ery_backend.widgets.factories.WidgetFactory')
