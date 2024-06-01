import factory
import factory.fuzzy

from ery_backend.roles.utils import grant_ownership

from .models import FileTouch


class UserFactory(factory.django.DjangoModelFactory):
    """
    Factory for custom django user class
    """

    class Meta:
        model = 'users.User'

    @classmethod
    def _adjust_kwargs(cls, **kwargs):
        kwargs['my_folder'].name = f"MyFolder_{kwargs['my_folder'].name}"
        return kwargs

    username = factory.Sequence('user-{}'.format)
    profile = factory.Dict({"email": factory.LazyAttribute(lambda a: '{}@stintery.com'.format(factory.Faker('name')).lower())})
    my_folder = factory.SubFactory('ery_backend.folders.factories.FolderFactory', name=factory.SelfAttribute('..username'))

    @factory.post_generation
    def grant_ownership_to_folder(self, *args, **kwargs):
        grant_ownership(self.my_folder, self)


class GroupFactory(factory.django.DjangoModelFactory):
    """
    Factory for custom django group class
    """

    class Meta:
        model = 'users.Group'

    name = factory.Sequence('group-{}'.format)


class FileTouchFactory(factory.django.DjangoModelFactory):
    """
    Factory for :class:~ery_backend.users.models.FileTouch
    """

    class Meta:
        model = FileTouch

    user = factory.SubFactory(UserFactory)
    module_definition = factory.SubFactory("ery_backend.modules.factories.ModuleDefinitionFactory")
