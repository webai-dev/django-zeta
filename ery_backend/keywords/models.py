from django.db import models

from ery_backend.base.models import EryNamedPrivileged


class Keyword(EryNamedPrivileged):
    """
    Keywords are used as indices by a creator (:class:`~ery_backend.users.models.User`) to group
    :class:`~ery_backend.base.models.EryFile` instances by a specific concept, such as
    "Competition" or "Categorization".
    """

    name = models.CharField(max_length=512, unique=True, help_text="Name of the model instance.")
