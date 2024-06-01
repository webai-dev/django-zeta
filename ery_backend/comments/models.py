from django.db import models

from ery_backend.base.mixins import PrivilegedMixin
from ery_backend.base.models import EryFileReference


class FileComment(EryFileReference, PrivilegedMixin):
    """
    Represent a user comment on ::class::~ery_backend.base.models.EryFileReference

    """

    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='file_comments')
    comment = models.CharField(max_length=2048)

    @property
    def parent_field(self):
        """
        Get attribute referring to parental instance. Used for tracing ancestry.

        Returns:
            str
        """
        for file_attr in ('stint_definition', 'module_definition', 'theme', 'procedure', 'widget', 'template', 'image_asset'):
            if getattr(self, file_attr) is not None:
                return file_attr

        raise Exception(f"No parent found for {self}")

    @classmethod
    def get_privilege_ancestor_cls(cls):
        """Return class of root ancestor from which privileges are inherited for permissions checking."""

        raise Exception(
            f"Because the parent of a {cls} instance is dynamically determined, get_privilege_ancestor_cls"
            " cannot be used on this model."
        )

    def __str__(self):
        return f"{self.parent_field}-Comment:{self.user}:{self.comment}"

    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='file_comments')
    comment = models.CharField(max_length=2048)


class FileStar(EryFileReference):
    """
    Represent a user star on ::class::~ery_backend.base.models.EryFileReference
    """

    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='file_stars')
