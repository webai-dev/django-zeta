import factory
import factory.fuzzy

from .models import Lab


class LabFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'labs.Lab'

    name = factory.Sequence('lab_definition-{}'.format)
    comment = factory.fuzzy.FuzzyText(length=50)
    slug = factory.LazyAttribute(lambda x: Lab.create_unique_slug(x.name))
