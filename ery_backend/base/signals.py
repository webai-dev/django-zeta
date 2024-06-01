from django.db.models.signals import m2m_changed, post_save

from ery_backend.commands.utils import assign_default_commands
from ery_backend.modules.models import ModuleDefinition
from ery_backend.roles.models import Role
from ery_backend.users.models import User

from .cache import invalidate_handler


for cls in (Role.privileges.through, User.groups.through):
    m2m_changed.connect(invalidate_handler, cls)

for cls in (ModuleDefinition,):
    post_save.connect(assign_default_commands, cls)
