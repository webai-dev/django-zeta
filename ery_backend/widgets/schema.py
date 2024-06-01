import graphene

from ery_backend.base.schema import PrivilegedNodeMixin, VersionMixin
from ery_backend.base.schema_utils import EryObjectType
from ery_backend.folders.schema import FileNodeMixin

from .models import Widget, WidgetConnection, WidgetEvent, WidgetEventStep, WidgetProp, WidgetState


class WidgetNode(FileNodeMixin, VersionMixin, EryObjectType):
    class Meta:
        model = Widget

    preview = graphene.String()
    all_connected_widgets = graphene.List("ery_backend.widgets.schema.WidgetNode")

    def resolve_preview(self, info, language=None):
        from ery_backend.frontends.renderers import ReactWidgetRenderer

        widgets = [connection.target for connection in self.connections.all()]
        widgets.append(self)

        widget_code = "\n".join(
            [
                ReactWidgetRenderer(widget, language=(language or self.primary_language)).render(is_preview=True)
                for widget in widgets
            ]
        )

        return f"""
{widget_code}

render(<{self.name} />);
"""

    def resolve_all_connected_widgets(self, info):
        return self.get_all_connected_widgets()


WidgetQuery = WidgetNode.get_query_class()


class WidgetStateNode(PrivilegedNodeMixin, EryObjectType):
    class Meta:
        model = WidgetState


WidgetStateQuery = WidgetStateNode.get_query_class()


class WidgetEventStepNode(PrivilegedNodeMixin, EryObjectType):
    class Meta:
        model = WidgetEventStep


WidgetEventStepQuery = WidgetEventStepNode.get_query_class()


class WidgetEventNode(PrivilegedNodeMixin, EryObjectType):
    class Meta:
        model = WidgetEvent


WidgetEventQuery = WidgetEventNode.get_query_class()


class WidgetPropNode(PrivilegedNodeMixin, EryObjectType):
    class Meta:
        model = WidgetProp


WidgetPropQuery = WidgetPropNode.get_query_class()


class WidgetConnectionNode(PrivilegedNodeMixin, EryObjectType):
    class Meta:
        model = WidgetConnection


WidgetConnectionQuery = WidgetConnectionNode.get_query_class()
