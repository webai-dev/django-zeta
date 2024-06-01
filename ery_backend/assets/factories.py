import os

import factory
import factory.fuzzy

from .models import ImageAsset

BASE_PATH = os.path.dirname(os.path.abspath(__name__))


class ImageAssetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'assets.ImageAsset'

    # pylint:disable=protected-access
    content_type = factory.fuzzy.FuzzyChoice(ImageAsset.HTTP_CONTENT_TYPES._db_values)

    @factory.lazy_attribute
    def file_data(self):
        files = {"gif": "ags.gif", "png": "burger.png", "jpeg": "iamnotacatidontsaymeow.jpg"}

        filename = files[self.content_type]

        with open("{}/ery_backend/assets/tests/data/{}".format(BASE_PATH, filename), "rb") as f:
            return f.read()

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Use the manager.create_file to create ImageAsset"""

        manager = cls._get_manager(model_class)
        kwargs.pop("content_type")
        return manager.create_file(*args, **kwargs)
