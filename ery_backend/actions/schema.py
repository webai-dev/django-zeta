from ery_backend.base.schema import VersionMixin, PrivilegedNodeMixin
from ery_backend.base.schema_utils import EryObjectType

from .models import Action, ActionStep


class ActionNode(PrivilegedNodeMixin, VersionMixin, EryObjectType):
    class Meta:
        model = Action


ActionQuery = ActionNode.get_query_class()


class ActionStepNode(PrivilegedNodeMixin, VersionMixin, EryObjectType):
    class Meta:
        model = ActionStep


ActionStepQuery = ActionStepNode.get_query_class()
