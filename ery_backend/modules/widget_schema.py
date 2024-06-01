from ery_backend.base.schema import VersionMixin
from ery_backend.base.schema_utils import EryObjectType
from ery_backend.roles.schema import RoleAssignmentNodeMixin

from .models import ModuleDefinitionWidget, WidgetChoice, WidgetChoiceTranslation, ModuleEvent, ModuleEventStep


class ModuleDefinitionWidgetNode(RoleAssignmentNodeMixin, VersionMixin, EryObjectType):
    class Meta:
        model = ModuleDefinitionWidget


ModuleDefinitionWidgetQuery = ModuleDefinitionWidgetNode.get_query_class()


class WidgetChoiceNode(RoleAssignmentNodeMixin, VersionMixin, EryObjectType):
    class Meta:
        model = WidgetChoice


WidgetChoiceQuery = WidgetChoiceNode.get_query_class()


class WidgetChoiceTranslationNode(RoleAssignmentNodeMixin, VersionMixin, EryObjectType):
    class Meta:
        model = WidgetChoiceTranslation


WidgetChoiceTranslationQuery = WidgetChoiceTranslationNode.get_query_class()


class ModuleEventNode(RoleAssignmentNodeMixin, VersionMixin, EryObjectType):
    class Meta:
        model = ModuleEvent


ModuleEventQuery = ModuleEventNode.get_query_class()


class ModuleEventStepNode(RoleAssignmentNodeMixin, VersionMixin, EryObjectType):
    class Meta:
        model = ModuleEventStep


ModuleEventStepQuery = ModuleEventStepNode.get_query_class()
