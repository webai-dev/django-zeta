from ery_backend.base.schema import PrivilegedNodeMixin
from ery_backend.base.schema_utils import EryObjectType

from .models import Condition


class ConditionNode(PrivilegedNodeMixin, EryObjectType):
    class Meta:
        model = Condition
        convert_choices_to_enum = False


ConditionQuery = ConditionNode.get_query_class()
