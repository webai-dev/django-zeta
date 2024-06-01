import graphene

from ery_backend.base.schema import PrivilegedNodeMixin
from ery_backend.base.schema_utils import EryObjectType
from ery_backend.modules.widget_schema import ModuleDefinitionWidgetNode
from ery_backend.widgets.schema import WidgetNode

from .models import Form, FormField, FormFieldChoice, FormFieldChoiceTranslation, FormButton, FormButtonList, FormItem


class FormItemNode(PrivilegedNodeMixin, EryObjectType):
    class Meta:
        model = FormItem


FormItemQuery = FormItemNode.get_query_class()
FormItemMutation = FormItemNode.get_mutation_class()


class FormFieldNode(PrivilegedNodeMixin, EryObjectType):
    class Meta:
        model = FormField


FormFieldQuery = FormFieldNode.get_query_class()


class FormFieldChoiceNode(PrivilegedNodeMixin, EryObjectType):
    class Meta:
        model = FormFieldChoice


FormFieldChoiceQuery = FormFieldChoiceNode.get_query_class()


class FormFieldChoiceTranslationNode(PrivilegedNodeMixin, EryObjectType):
    class Meta:
        model = FormFieldChoiceTranslation


FormFieldChoiceTranslationQuery = FormFieldChoiceTranslationNode.get_query_class()


class FormButtonListNode(PrivilegedNodeMixin, EryObjectType):
    class Meta:
        model = FormButtonList


FormButtonListQuery = FormButtonListNode.get_query_class()


class FormButtonNode(PrivilegedNodeMixin, EryObjectType):
    class Meta:
        model = FormButton


FormButtonQuery = FormButtonNode.get_query_class()


class FormNode(PrivilegedNodeMixin, EryObjectType):
    class Meta:
        model = Form

    module_widgets = graphene.List(ModuleDefinitionWidgetNode)
    widgets = graphene.List(WidgetNode)

    def resolve_module_widgets(self, info):
        return self.get_module_widgets()

    def resolve_widgets(self, info):
        return self.get_widgets()


FormQuery = FormNode.get_query_class()
