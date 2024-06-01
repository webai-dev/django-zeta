from ery_backend.base.schema import VersionMixin
from ery_backend.base.schema_utils import EryObjectType
from ery_backend.roles.schema import RoleAssignmentNodeMixin

from .models import Vendor


class VendorNode(RoleAssignmentNodeMixin, VersionMixin, EryObjectType):
    class Meta:
        model = Vendor


VendorQuery = VendorNode.get_query_class()
