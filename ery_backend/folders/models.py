from django.db import models

from model_utils import Choices

from ery_backend.assets.models import ImageAsset
from ery_backend.base.cache import ery_cache
from ery_backend.base.mixins import PrivilegedMixin
from ery_backend.base.models import EryNamedPrivileged, EryFileReference
from ery_backend.procedures.models import Procedure
from ery_backend.modules.models import ModuleDefinition
from ery_backend.stints.models import StintDefinition
from ery_backend.templates.models import Template
from ery_backend.themes.models import Theme
from ery_backend.validators.models import Validator
from ery_backend.widgets.models import Widget


class Folder(EryNamedPrivileged):
    """
    Emulates a standard directory. Responsible for holding :class:`Link` objects.
    """

    @ery_cache(timeout=3)
    def query_files(self, user):  # pylint: disable=no-self-use
        """
        Return subset of :class:`~ery_backend.base.models.EryFileReference` instances belonging to current
        instance.

        Returns:
            List[Dict[`~ery_backend.base.models.EryModel`: Dict[str: Union[:class:`User`, :class:`EryModel`, str]]]]
        """
        file_models = [StintDefinition, ModuleDefinition, Template, Theme, Procedure, Widget, ImageAsset, Validator]
        objs = []

        for model in file_models:
            objs += list(model.objects.filter_privilege('read', user).add_popularity().all())

        return [{obj.get_field_name(): obj, 'owner': obj.get_owner(), 'popularity': obj.popularity} for obj in objs]


class Link(EryFileReference, PrivilegedMixin):
    """
    Connects :class:`~ery_backend.base.models.EryFile` objects to :class:`Folder` objects.

    Attributes:
        - parent_field (str): Attribute referring to parental instance. Used for tracing ancestry.
        - referenced_field_names (List): Attributes to be validated in inherited :py:meth:`exactly_one_reference_clean`.

    """

    parent_field = 'parent_folder'
    FILE_AND_FOLDER_CHOICES = EryFileReference.FILE_CHOICES + Choices(('folder', 'Folder'))

    reference_type = models.CharField(choices=FILE_AND_FOLDER_CHOICES, max_length=32)

    parent_folder = models.ForeignKey(
        'folders.Folder',
        related_name='links',
        on_delete=models.CASCADE,
        help_text="Storage location of EryFileReference object.",
    )
    folder = models.ForeignKey(
        'folders.Folder',
        related_name='from_links',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Optional connected EryFileReference object.",
    )

    @property
    def name(self):
        return self.get_obj().name

    def clean(self):
        super().clean()

        if (
            Link.objects.exclude(id=self.id)
            .filter(parent_folder=self.parent_folder)
            .filter(**{self.reference_type: self.get_obj()})
            .exists()
        ):
            raise ValueError(
                f"Can not link {self.FILE_AND_FOLDER_CHOICES[self.reference_type]} '{self.get_obj().name}'"
                f"to Folder {self.parent_folder}: Link already exists."
            )
