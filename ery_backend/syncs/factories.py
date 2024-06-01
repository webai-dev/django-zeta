import factory
import factory.fuzzy

from .models import Era


class EraFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'syncs.Era'

    name = factory.Sequence('era-{}'.format)
    comment = factory.fuzzy.FuzzyText(length=100)
    module_definition = factory.SubFactory('ery_backend.modules.factories.ModuleDefinitionFactory')
    action = factory.SubFactory('ery_backend.actions.factories.ActionFactory')
    slug = factory.LazyAttribute(lambda x: Era.create_unique_slug(x.name))
