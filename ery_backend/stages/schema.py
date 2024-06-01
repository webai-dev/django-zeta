import graphene

from ery_backend.base.schema_utils import EryObjectType
from ery_backend.modules.widget_schema import ModuleDefinitionWidgetNode
from ery_backend.roles.schema import RoleAssignmentNodeMixin
from ery_backend.templates.schema import TemplateNode
from ery_backend.templates.widget_schema import TemplateWidgetNode
from ery_backend.widgets.schema import WidgetNode

from .models import StageDefinition, StageTemplate, StageTemplateBlockTranslation, Stage, StageTemplateBlock, Redirect


class StageDefinitionNode(RoleAssignmentNodeMixin, EryObjectType):
    class Meta:
        model = StageDefinition
        convert_choices_to_enum = False


DefaultStageDefinitionQuery = StageDefinitionNode.get_query_class()


class StageDefinitionQuery(DefaultStageDefinitionQuery):
    default_template = graphene.Field(TemplateNode)

    def resolve_default_template(self, info, **kwargs):
        stage_templates = self.stage_templates.filter(template__frontend=self.module_definition.default_frontend)
        # Note: Only one or zero stage_template allowed per frontend.
        return stage_templates[0].template if stage_templates else None


class StageTemplateNode(RoleAssignmentNodeMixin, EryObjectType):
    class Meta:
        model = StageTemplate
        filter_privilege = True

    all_block_info = graphene.List(StageTemplate.BlockInfoNode, language=graphene.ID())
    preview = graphene.Field(graphene.String, language=graphene.ID())

    module_widgets = graphene.List(ModuleDefinitionWidgetNode)
    template_widgets = graphene.List(TemplateWidgetNode)
    widgets = graphene.List(WidgetNode)

    def resolve_all_block_info(self, info, language=None):
        from graphql_relay.node.node import from_global_id

        if not language:
            language = self.stage_definition.module_definition.primary_language
        else:
            language = from_global_id(language)[1]

        block_infos = self.get_blocks(self.template.frontend, language)
        return [
            {
                "name": name,
                "content": info["content"],
                "block_type": info["block_type"],
                "ancestor_template_id": info["ancestor"].id if info["block_type"] == "TemplateBlock" else None,
            }
            for name, info in block_infos.items()
        ]

    def resolve_preview(self, info, language=None):
        from ery_backend.frontends.renderers import ReactStageRenderer

        if not language:
            language = self.stage_definition.module_definition.primary_language

        return f"""
{ReactStageRenderer(self, language).render(is_preview=True)}

render(<Stage{self.stage_definition.name} />);
"""

    def resolve_module_widgets(self, info):
        return self.get_module_widgets()

    def resolve_template_widgets(self, info):
        return self.get_template_widgets()

    def resolve_widgets(self, info):
        return self.get_widgets()


StageTemplateQuery = StageTemplateNode.get_query_class()


class StageTemplateBlockNode(RoleAssignmentNodeMixin, EryObjectType):
    class Meta:
        model = StageTemplateBlock


StageTemplateBlockQuery = StageTemplateBlockNode.get_query_class()


class StageTemplateBlockTranslationNode(RoleAssignmentNodeMixin, EryObjectType):
    class Meta:
        model = StageTemplateBlockTranslation


StageTemplateBlockTranslationQuery = StageTemplateBlockTranslationNode.get_query_class()


class RedirectNode(RoleAssignmentNodeMixin, EryObjectType):
    class Meta:
        model = Redirect


RedirectQuery = RedirectNode.get_query_class()


class StageNode(RoleAssignmentNodeMixin, EryObjectType):
    class Meta:
        model = Stage


StageQuery = StageNode.get_query_class()
