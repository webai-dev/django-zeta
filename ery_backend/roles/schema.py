from ery_backend.base.schema import PrivilegedNodeMixin
from ery_backend.base.schema_utils import EryObjectType, EryFilterConnectionField

from .models import Role, RoleAssignment


class RoleAssignmentNode(EryObjectType):
    class Meta:
        model = RoleAssignment
        filter_privilege = False


RoleAssignmentQuery = RoleAssignmentNode.get_query_class()


class RoleAssignmentNodeMixin(PrivilegedNodeMixin):
    role_assignments = EryFilterConnectionField(RoleAssignmentNode)

    def resolve_role_assignments(self, info, **kwargs):
        content_type = self.get_content_type()
        qs = RoleAssignment.objects.filter(content_type=content_type, object_id=self.id)

        return qs.filter(**kwargs)


class RoleNode(RoleAssignmentNodeMixin, EryObjectType):
    class Meta:
        model = Role


RoleQuery = RoleNode.get_query_class()


RoleAssignmentNodeEdge = RoleAssignmentNode._meta.connection.Edge
