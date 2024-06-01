import string

import factory
import factory.fuzzy

from .models import Procedure


class ProcedureFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'procedures.Procedure'

    name = factory.fuzzy.FuzzyText(length=10, chars=string.ascii_lowercase)
    comment = factory.fuzzy.FuzzyText(length=10)
    code = factory.fuzzy.FuzzyText(length=25)
    slug = factory.LazyAttribute(lambda x: Procedure.create_unique_slug(x.name))


class ProcedureArgumentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'procedures.ProcedureArgument'

    name = factory.fuzzy.FuzzyText(length=10, chars=string.ascii_lowercase)
    comment = factory.fuzzy.FuzzyText(length=10)
    procedure = factory.SubFactory('ery_backend.procedures.factories.ProcedureFactory')
    order = factory.LazyAttribute(lambda obj: obj.procedure.arguments.count())
