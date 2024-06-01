import random

import factory
import factory.fuzzy

from django.utils.crypto import get_random_string
from languages_plus.models import Language

from ery_backend.base.utils import get_default_language
from ery_backend.variables.factories import VariableDefinitionFactory
from ery_backend.variables.models import VariableDefinition, VariableChoiceItem

from .models import ModuleDefinitionWidget, ModuleEventStep, ModuleEvent


def _name_module_definition_widget():
    module_definition_widget_n = ModuleDefinitionWidget.objects.count() + 1
    return f"ModuleDefinitionWidget{'a'*module_definition_widget_n}"


class ModuleDefinitionWidgetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'modules.ModuleDefinitionWidget'

    name = factory.LazyFunction(_name_module_definition_widget)
    comment = factory.fuzzy.FuzzyText(length=100)
    module_definition = factory.SubFactory('ery_backend.modules.factories.ModuleDefinitionFactory')
    required_widget = factory.fuzzy.FuzzyChoice([True, False])
    # XXX: Add user related randomization in issue #724
    random_mode = factory.fuzzy.FuzzyChoice(['asc', 'desc', 'shuffle', 'random_asc_desc'])
    widget = factory.SubFactory('ery_backend.widgets.factories.WidgetFactory')

    @factory.lazy_attribute
    def variable_definition(self):
        vd = VariableDefinitionFactory(module_definition=self.module_definition)
        return vd

    @factory.lazy_attribute
    def initial_value(self):
        from ery_backend.base.testcases import random_dt_value, random_dt

        choice = VariableDefinition.DATA_TYPE_CHOICES.choice
        has_variable_definition = self.variable_definition is not None
        if has_variable_definition and self.variable_definition.data_type == choice:
            value = str(random_dt_value(self.variable_definition.data_type)).lower()
        else:
            value = random_dt_value(random_dt())
        if (
            self.variable_definition
            and self.variable_definition.data_type == self.variable_definition.DATA_TYPE_CHOICES.choice
        ):
            VariableChoiceItem.objects.get_or_create(variable_definition=self.variable_definition, value=value)
        return value


class WidgetChoiceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'modules.WidgetChoice'

    widget = factory.SubFactory('ery_backend.modules.widget_factories.ModuleDefinitionWidgetFactory')

    @factory.lazy_attribute
    def order(self):
        last_order = self.widget.choices.order_by('-order').values_list('order', flat=True).first()
        if last_order is not None:
            return last_order + 1
        return 0

    @factory.lazy_attribute
    def value(self):
        from ery_backend.base.testcases import random_dt_value, random_dt

        existing_choices = list(self.widget.choices.values_list('value', flat=True))

        def _create_value(has_vd=True):
            if has_vd:
                # This is done on __init__ of var choice
                value = str(random_dt_value(self.widget.variable_definition.data_type)).lower()
            else:
                value = str(
                    random_dt_value(
                        random_dt(
                            exclude=[VariableDefinition.DATA_TYPE_CHOICES.choice, VariableDefinition.DATA_TYPE_CHOICES.stage]
                        )
                    )
                ).lower()
            return value

        has_vd = self.widget.variable_definition is not None
        value = _create_value(has_vd)
        while value in existing_choices:
            if (
                self.widget.variable_definition.data_type == VariableDefinition.DATA_TYPE_CHOICES.bool
                and len(existing_choices) >= 2
            ):
                raise Exception("Cannot set more than two choices for widget with boolean variable_definition!")
            value = _create_value(has_vd)

        if has_vd and self.widget.variable_definition.data_type == VariableDefinition.DATA_TYPE_CHOICES.choice:
            VariableChoiceItem.objects.get_or_create(variable_definition=self.widget.variable_definition, value=value)
        return value

    @factory.post_generation
    def add_translation(self, create, extracted, **kwargs):
        if extracted:
            if not isinstance(extracted, Language):
                language = Language.objects.order_by('?').first()
            else:
                language = extracted
            WidgetChoiceTranslationFactory(
                language=language,
                caption=f"Caption for {self.__class__.__name__}, order: {self.order}, value: {self.value}",
                widget_choice=self,
            )


class WidgetChoiceTranslationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'modules.WidgetChoiceTranslation'

    widget_choice = factory.SubFactory('ery_backend.modules.factories.WidgetChoiceFactory')
    language = factory.LazyFunction(get_default_language)
    caption = factory.fuzzy.FuzzyText(length=5)


class ModuleEventStepFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'modules.ModuleEventStep'

    module_event = factory.SubFactory('ery_backend.modules.factories.ModuleEventFactory')
    event_action_type = factory.fuzzy.FuzzyChoice([choice for choice, _ in ModuleEventStep.EVENT_ACTION_TYPE_CHOICES])
    order = factory.Sequence(lambda n: n)

    @factory.lazy_attribute
    def action(self):
        from ery_backend.actions.factories import ActionFactory

        if self.event_action_type == ModuleEventStep.EVENT_ACTION_TYPE_CHOICES.run_action:
            return ActionFactory(module_definition=self.module_event.widget.module_definition)
        return None


class ModuleEventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'modules.ModuleEvent'

    name = factory.Sequence('widgetevent{}'.format)
    widget = factory.SubFactory('ery_backend.modules.factories.ModuleDefinitionWidgetFactory')

    @factory.lazy_attribute
    def event_type(self):
        if self.widget.widget.frontend.name == 'Web':
            return random.choice([react_event for react_event, _ in ModuleEvent.REACT_EVENT_CHOICES])
        if self.widget.widget.frontend.name == "SMS":
            return random.choice([sms_event for sms_event, _ in ModuleEvent.SMS_EVENT_CHOICES])
        return get_random_string(length=random.randint(1, 25))

    @factory.post_generation
    def include_event_steps(self, create, extracted, **kwargs):
        if extracted:
            event_step_count = random.randint(1, 10)
            for _ in range(event_step_count):
                ModuleEventStepFactory(module_event=self)
