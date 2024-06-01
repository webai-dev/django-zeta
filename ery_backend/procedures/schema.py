from ery_backend.base.schema import VersionMixin, PrivilegedNodeMixin
from ery_backend.base.schema_utils import EryObjectType
from ery_backend.folders.schema import FileNodeMixin
from .models import Procedure, ProcedureArgument


class ProcedureNode(FileNodeMixin, VersionMixin, EryObjectType):
    class Meta:
        model = Procedure


ProcedureQuery = ProcedureNode.get_query_class()


class ProcedureArgumentNode(PrivilegedNodeMixin, EryObjectType):
    class Meta:
        model = ProcedureArgument


ProcedureArgumentQuery = ProcedureArgumentNode.get_query_class()
