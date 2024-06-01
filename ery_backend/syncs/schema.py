from ery_backend.base.schema import VersionMixin
from ery_backend.base.schema_utils import EryObjectType
from ery_backend.roles.schema import RoleAssignmentNodeMixin

from .models import Era


class EraNode(RoleAssignmentNodeMixin, VersionMixin, EryObjectType):
    class Meta:
        model = Era


EraQuery = EraNode.get_query_class()
