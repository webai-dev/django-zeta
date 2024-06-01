import factory
import factory.fuzzy


from .models import Frontend


class FrontendFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'frontends.Frontend'

    name = factory.Sequence('frontend-{0}'.format)
    comment = factory.fuzzy.FuzzyText(length=100)
    slug = factory.LazyAttribute(lambda x: Frontend.create_unique_slug(x.name))


class SMSStageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'frontends.SMSStage'

    stage = factory.SubFactory('ery_backend.stages.factories.SMSStageFactory')
    send = factory.fuzzy.FuzzyInteger(0, 999)
    replayed = factory.fuzzy.FuzzyInteger(0, 999)
    faulty_inputs = factory.fuzzy.FuzzyInteger(0, 999)
