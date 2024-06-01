from ery_backend.base.schema_utils import EryObjectType
from ery_backend.roles.schema import RoleAssignmentNodeMixin

from .models import Lab


class LabNode(RoleAssignmentNodeMixin, EryObjectType):
    class Meta:
        model = Lab


LabQuery = LabNode.get_query_class()
