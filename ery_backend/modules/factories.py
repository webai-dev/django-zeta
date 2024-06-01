import string

import factory
import factory.fuzzy

from ery_backend.base.testcases import ReactNamedFactoryMixin

from .models import ModuleDefinition

# pylint:disable=unused-import
from .widget_factories import (
    ModuleDefinitionWidgetFactory,
    WidgetChoiceFactory,
    WidgetChoiceTranslationFactory,
    ModuleEventFactory,
    ModuleEventStepFactory,
)


class ModuleDefinitionFactory(ReactNamedFactoryMixin):
    class Meta:
        model = 'modules.ModuleDefinition'

    name = factory.Sequence('ModuleDefinition{}'.format)
    comment = factory.fuzzy.FuzzyText(length=100)
    min_team_size = factory.fuzzy.FuzzyInteger(0, 5)
    max_team_size = factory.fuzzy.FuzzyInteger(5, 10)
    primary_frontend = factory.SubFactory('ery_backend.frontends.factories.FrontendFactory')
    default_template = factory.SubFactory('ery_backend.templates.factories.TemplateFactory')
    default_theme = factory.SubFactory('ery_backend.themes.factories.ThemeFactory')
    slug = factory.LazyAttribute(lambda x: ModuleDefinition.create_unique_slug(x.name))


class ModuleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'modules.Module'

    stint = factory.SubFactory('ery_backend.stints.factories.StintFactory')

    @factory.lazy_attribute
    def stint_definition_module_definition(self):
        from ery_backend.stints.factories import StintDefinitionModuleDefinitionFactory

        sdmd = StintDefinitionModuleDefinitionFactory(stint_definition=self.stint.stint_specification.stint_definition)
        return sdmd


class ModuleDefinitionProcedureFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'modules.ModuleDefinitionProcedure'

    name = factory.fuzzy.FuzzyText(length=10, chars=string.ascii_lowercase)
    procedure = factory.SubFactory('ery_backend.procedures.factories.ProcedureFactory')
    module_definition = factory.SubFactory('ery_backend.modules.factories.ModuleDefinitionFactory')
