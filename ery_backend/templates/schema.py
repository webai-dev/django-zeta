import graphene

from languages_plus.models import Language

from ery_backend.base.schema_utils import EryObjectType
from ery_backend.folders.schema import FileNodeMixin
from ery_backend.widgets.schema import WidgetNode

from .models import Template, TemplateBlock, TemplateBlockTranslation
from .widget_schema import TemplateWidgetNode  # pylint: disable=unused-import


class TemplateNode(FileNodeMixin, EryObjectType):
    class Meta:
        model = Template

    all_block_info = graphene.List(Template.BlockInfoNode, language=graphene.ID())

    preview = graphene.Field(graphene.String, language=graphene.ID())
    widgets = graphene.Field(graphene.List(WidgetNode))

    def resolve_all_block_info(self, info, language=None):
        from graphql_relay.node.node import from_global_id

        if not language:
            language = self.primary_language
        else:
            language = from_global_id(language)[1]

        block_infos = self.get_blocks(language)
        return [
            {
                "name": name,
                "content": info["content"],
                "block_type": "TemplateBlock",
                "ancestor_template_id": info["ancestor"].gql_id,
            }
            for name, info in block_infos.items()
        ]

    def resolve_preview(self, info, language=None):
        return self.render(Language.objects.get(pk=language) if language else self.primary_language)

    def resolve_widgets(self, info):
        return self.get_widgets()


TemplateQuery = TemplateNode.get_query_class()


class TemplateBlockNode(FileNodeMixin, EryObjectType):
    class Meta:
        model = TemplateBlock


TemplateBlockQuery = TemplateBlockNode.get_query_class()


class TemplateBlockTranslationNode(FileNodeMixin, EryObjectType):
    class Meta:
        model = TemplateBlockTranslation


TemplateBlockTranslationQuery = TemplateBlockTranslationNode.get_query_class()
