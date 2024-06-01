import factory
import factory.fuzzy


class WardenFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'wardens.Warden'

    user = factory.SubFactory('ery_backend.users.factories.UserFactory')
