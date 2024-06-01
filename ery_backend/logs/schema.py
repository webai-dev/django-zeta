from ery_backend.base.schema_utils import EryObjectType
from ery_backend.roles.schema import RoleAssignmentNodeMixin

from .models import Log


class LogNode(RoleAssignmentNodeMixin, EryObjectType):
    class Meta:
        model = Log


LogQuery = LogNode.get_query_class()
