import datetime as dt
import random

import pytz

import factory
import factory.fuzzy

from ery_backend.base.exceptions import EryValidationError
from ery_backend.base.testcases import ReactNamedFactoryMixin
from ery_backend.variables.models import VariableDefinition
from ery_backend.variables.factories import VariableDefinitionFactory

from .models import StintDefinition


class StintDefinitionFactory(ReactNamedFactoryMixin):
    class Meta:
        model = 'stints.StintDefinition'

    name = factory.Sequence(lambda n: f'StintDefinition{n}')
    comment = factory.fuzzy.FuzzyText(length=100)
    slug = factory.LazyAttribute(lambda x: StintDefinition.create_unique_slug(x.name))


class StintFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'stints.Stint'

    stint_specification = factory.SubFactory('ery_backend.stint_specifications.factories.StintSpecificationFactory')
    started_by = factory.SubFactory('ery_backend.users.factories.UserFactory')
    # Avoids circular import from era -> module_definition
    warden = factory.SubFactory('ery_backend.wardens.factories.WardenFactory')
    lab = factory.SubFactory('ery_backend.labs.factories.LabFactory')
    started = factory.fuzzy.FuzzyDateTime(dt.datetime(2000, 1, 1, tzinfo=pytz.UTC))
    ended = factory.LazyAttribute(lambda instance: instance.started + dt.timedelta(days=1))


class StintDefinitionModuleDefinitionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'stints.StintDefinitionModuleDefinition'

    stint_definition = factory.SubFactory('ery_backend.stints.factories.StintDefinitionFactory')
    module_definition = factory.SubFactory('ery_backend.modules.factories.ModuleDefinitionFactory')
    order = factory.LazyAttribute(lambda x: x.stint_definition.module_definitions.count() + 1)


class StintDefinitionVariableDefinitionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'stints.StintDefinitionVariableDefinition'

    stint_definition = factory.SubFactory('ery_backend.stints.factories.StintDefinitionFactory')

    @factory.post_generation
    def variable_definitions(self, create, extracted, **kwargs):
        from ery_backend.base.testcases import random_dt

        if extracted is not None:
            for vd in extracted:
                if self.variable_definitions.filter(module_definition=vd.module_definition).exists():
                    raise EryValidationError(f"{vd} is already a part of {self}")

                self.variable_definitions.add(vd)
        else:
            data_type = kwargs.get("data_type", random_dt(exclude=[VariableDefinition.DATA_TYPE_CHOICES.stage]))
            count = kwargs.get("count", random.randint(1, 5))
            scope = kwargs.get("scope", random.choice([s[0] for s in VariableDefinition.SCOPE_CHOICES]))

            for _ in range(count):
                self.variable_definitions.add(VariableDefinitionFactory(data_type=data_type, scope=scope))

        for vd in self.variable_definitions.all():
            if not self.stint_definition.stint_definition_module_definitions.filter(
                stint_definition=self.stint_definition, module_definition=vd.module_definition
            ).exists():
                self.stint_definition.stint_definition_module_definitions.add(
                    StintDefinitionModuleDefinitionFactory(
                        stint_definition=self.stint_definition, module_definition=vd.module_definition
                    )
                )
