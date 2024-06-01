import factory
import factory.fuzzy


class LogFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'logs.Log'

    stint = factory.SubFactory('ery_backend.stints.factories.StintFactory')
    message = factory.fuzzy.FuzzyText(length=100)
