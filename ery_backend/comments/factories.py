import factory
import factory.fuzzy

from .models import FileComment, FileStar


class FileCommentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FileComment

    user = factory.SubFactory("ery_backend.users.factories.UserFactory")
    comment = factory.fuzzy.FuzzyText(length=100)
    module_definition = factory.SubFactory("ery_backend.modules.factories.ModuleDefinitionFactory")


class FileStarFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FileStar

    user = factory.SubFactory("ery_backend.users.factories.UserFactory")
    module_definition = factory.SubFactory("ery_backend.modules.factories.ModuleDefinitionFactory")
