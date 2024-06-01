from ery_backend.base.schema_utils import EryObjectType

from .widgets import TemplateWidget


class TemplateWidgetNode(EryObjectType):
    class Meta:
        model = TemplateWidget


TemplateWidgetQuery = TemplateWidgetNode.get_query_class()
