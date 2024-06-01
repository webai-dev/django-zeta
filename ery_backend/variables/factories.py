import random
import string

import factory
import factory.fuzzy

from ery_backend.base.utils import get_default_language
from .models import VariableDefinition, VariableChoiceItem


class VariableDefinitionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'variables.VariableDefinition'

    module_definition = factory.SubFactory('ery_backend.modules.factories.ModuleDefinitionFactory')
    name = factory.fuzzy.FuzzyText(length=10, chars=string.ascii_lowercase)
    comment = factory.fuzzy.FuzzyText(length=25)
    scope = factory.fuzzy.FuzzyChoice([scope for scope, _ in VariableDefinition.SCOPE_CHOICES])
    specifiable = factory.fuzzy.FuzzyChoice([True, False])
    is_payoff = False
    is_output_data = factory.fuzzy.FuzzyChoice([True, False])
    slug = factory.LazyAttribute(lambda x: VariableDefinition.create_unique_slug(x.name))

    class Params:
        exclude = [VariableDefinition.DATA_TYPE_CHOICES.stage]  # Specific data_types to be excluded from data_type choices.
        allow_choices = False  # Whether to add choices for variable_definition of choice data_type

    @factory.lazy_attribute
    def data_type(self):
        from ery_backend.base.testcases import random_dt

        return random_dt(self.exclude)

    @factory.lazy_attribute
    def default_value(self):
        from ery_backend.base.testcases import random_dt_value

        return random_dt_value(self.data_type)

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        # Overriden to handle choice data_type
        obj = model_class(*args, **kwargs)
        default_value = obj.default_value
        obj.default_value = None
        obj.save()
        if default_value is not None:
            if obj.data_type == obj.DATA_TYPE_CHOICES.choice:
                # This is done in VariableChoiceItem.__init__
                default_value = default_value.lower()  # pylint:disable=attribute-defined-outside-init
                VariableChoiceItem.objects.create(variable_definition=obj, value=default_value)
            obj.default_value = default_value
            obj.save()
        return obj


class VariableChoiceItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'variables.VariableChoiceItem'

    variable_definition = factory.SubFactory(
        'ery_backend.variables.factories.VariableDefinitionFactory', data_type=VariableDefinition.DATA_TYPE_CHOICES.choice
    )

    @factory.lazy_attribute
    def value(self):
        from ery_backend.base.testcases import random_dt_value

        existing_choices = self.variable_definition.variablechoiceitem_set.values_list('value', flat=True)
        value = str(random_dt_value(self.variable_definition.data_type)).lower()
        while value in existing_choices:
            value = str(random_dt_value(self.variable_definition.data_type)).lower()
        return value


class VariableChoiceItemTranslationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'variables.VariableChoiceItemTranslation'

    variable_choice_item = factory.SubFactory(
        'ery_backend.variables.factories.VariableChoiceItemFactory',
        variable_definition=factory.SubFactory(
            'ery_backend.variables.factories.VariableDefinitionFactory', data_type=VariableDefinition.DATA_TYPE_CHOICES.choice
        ),
    )
    language = factory.LazyFunction(get_default_language)
    caption = factory.fuzzy.FuzzyText(length=25)


class VariableFactoryBase(factory.django.DjangoModelFactory):
    """Provide data type, value for variable factories"""

    class Params:
        with_stint_definition_variable_definition = False  # Whether to use stint_def_var_def
        exclude = [VariableDefinition.DATA_TYPE_CHOICES.stage]  # Specific data_types to be excluded from data_type choices.

    @factory.lazy_attribute
    def variable_definition(self):
        from ery_backend.base.testcases import random_dt

        if self.with_stint_definition_variable_definition:
            return None

        data_type = random_dt(self.exclude)

        return VariableDefinitionFactory(data_type=data_type, scope=self.scope)

    @factory.lazy_attribute
    def stint_definition_variable_definition(self):
        from ery_backend.base.testcases import random_dt

        if not self.with_stint_definition_variable_definition:
            return None

        from ery_backend.stints.factories import StintDefinitionVariableDefinitionFactory

        sd = self.module.stint.stint_specification.stint_definition
        mds = sd.module_definitions

        data_type = random_dt(self.exclude)
        vd_count = random.randint(1, mds.count())
        vds = [
            VariableDefinitionFactory(module_definition=mds.all()[i], data_type=data_type, scope=self.scope)
            for i in range(vd_count)
        ]
        return StintDefinitionVariableDefinitionFactory(stint_definition=sd, variable_definitions=vds)

    @factory.lazy_attribute
    def value(self):
        from ery_backend.base.testcases import random_dt_value

        if self.with_stint_definition_variable_definition:
            data_type = self.stint_definition_variable_definition.variable_definitions.first().data_type
        else:
            data_type = self.variable_definition.data_type

        value = random_dt_value(data_type)
        if data_type == VariableDefinition.DATA_TYPE_CHOICES.choice:
            value = str(value).lower()
            vds = (
                self.stint_definition_variable_definition.variable_definitions.all()
                if self.with_stint_definition_variable_definition
                else [self.variable_definition]
            )
            for vd in vds:
                VariableChoiceItem.objects.get_or_create(variable_definition=vd, value=value)
        return value


class ModuleVariableFactory(VariableFactoryBase):
    class Meta:
        model = 'variables.ModuleVariable'

    class Params:
        scope = VariableDefinition.SCOPE_CHOICES.module

    module = factory.SubFactory('ery_backend.modules.factories.ModuleFactory')


class TeamVariableFactory(VariableFactoryBase):
    class Meta:
        model = 'variables.TeamVariable'

    class Params:
        scope = VariableDefinition.SCOPE_CHOICES.team

    team = factory.SubFactory('ery_backend.teams.factories.TeamFactory')
    module = factory.SubFactory('ery_backend.modules.factories.ModuleFactory')


class HandVariableFactory(VariableFactoryBase):
    class Meta:
        model = 'variables.HandVariable'

    class Params:
        scope = VariableDefinition.SCOPE_CHOICES.hand

    hand = factory.SubFactory('ery_backend.hands.factories.HandFactory')

    @factory.lazy_attribute
    def module(self):
        return self.hand.current_module
