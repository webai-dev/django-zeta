from ery_backend.base.schema_utils import EryObjectType

from .models import Keyword


class KeywordNode(EryObjectType):
    class Meta:
        model = Keyword
        filter_privilege = False


KeywordQuery = KeywordNode.get_query_class()
