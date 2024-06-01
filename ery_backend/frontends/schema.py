from ery_backend.base.schema_utils import EryObjectType

from .models import Frontend


class FrontendNode(EryObjectType):
    class Meta:
        model = Frontend


FrontendQuery = FrontendNode.get_query_class()
