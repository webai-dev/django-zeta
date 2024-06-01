from ery_backend.base.schema_utils import EryObjectType

from .models import NewsItem


class NewsItemNode(EryObjectType):
    class Meta:
        model = NewsItem


NewsItemQuery = NewsItemNode.get_query_class()
