import graphene

from ery_backend.base.schema import PrivilegedNodeMixin
from ery_backend.base.schema_utils import EryObjectType, EryFilterConnectionField
from ery_backend.folders.schema import FileNodeMixin
from ery_backend.frontends.schema import Frontend
from ery_backend.modules.widgets import ModuleDefinitionWidget
from ery_backend.widgets.schema import WidgetNode

from .models import Module, ModuleDefinition, ModuleDefinitionProcedure


# pylint: disable=unused-import
from .widget_schema import (
    ModuleDefinitionWidgetNode,
    WidgetChoiceNode,
    WidgetChoiceTranslationNode,
    ModuleEventNode,
    ModuleEventStepNode,
)


class ModuleDefinitionNode(FileNodeMixin, EryObjectType):
    class Meta:
        model = ModuleDefinition

    module_widgets = EryFilterConnectionField(ModuleDefinitionWidgetNode)
    widgets = graphene.Field(graphene.List(WidgetNode), frontend=graphene.String())

    def resolve_widgets(self, info, frontend=None):
        return self.get_widgets(Frontend.objects.filter(name=frontend) if frontend else self.primary_frontend)

    def resolve_module_widgets(self, info, **kwargs):
        return self.module_widgets.exclude(form_field__isnull=False)


BaseModuleDefinitionQuery = ModuleDefinitionNode.get_query_class()


class ModuleDefinitionQuery(BaseModuleDefinitionQuery):
    all_module_widgets = EryFilterConnectionField(ModuleDefinitionWidgetNode)

    def resolve_all_module_widgets(self, info):
        return self.module_widgets.objects.exclude(form_field__isnull=True)


class ModuleNode(PrivilegedNodeMixin, EryObjectType):
    class Meta:
        model = Module

    module_definition = graphene.Field(ModuleDefinitionNode)


ModuleQuery = ModuleNode.get_query_class()


class ModuleDefinitionProcedureNode(PrivilegedNodeMixin, EryObjectType):
    class Meta:
        model = ModuleDefinitionProcedure


ModuleDefinitionProcedureQuery = ModuleDefinitionProcedureNode.get_query_class()
