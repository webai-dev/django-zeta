import factory
import factory.fuzzy


class FolderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'folders.Folder'


class LinkFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'folders.Link'

    parent_folder = factory.SubFactory('ery_backend.folders.factories.FolderFactory')
