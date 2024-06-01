from django.db import models

from ery_backend.base.mixins import SluggedMixin
from ery_backend.modules.models import ModuleDefinitionNamedModel


class Era(ModuleDefinitionNamedModel, SluggedMixin):
    """
    Eras function as stopping points that synchronize Hands as they progress through a Module.

    Eras are created automatically through the Synchronizer.

    Parent: Module Definition

    Note: Eras exist at both the Hand and the Stint level, with the latter depending on the former.
        In other words, a Stint's era should only change when all Hand's participating in that Module have
        reached said era.
    """

    parent_field = 'module_definition'

    action = models.ForeignKey(
        "actions.Action", on_delete=models.SET_NULL, null=True, blank=True, related_name='triggering_eras'
    )
    is_team = models.BooleanField(default=False)  # Identifies group eras (dependent on Hands)
