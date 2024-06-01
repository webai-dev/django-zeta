import django_filters
import graphene
from graphene import relay

from django.db.models import Q

from ery_backend.roles.schema import RoleAssignmentNodeMixin
from ery_backend.base.mixins import StateMixin
from ery_backend.base.serializers import EryXMLRenderer
from ery_backend.base.schema import PrivilegedNodeMixin
from ery_backend.base.schema_utils import EryObjectType, EryFilterConnectionField
from ery_backend.comments.schema import FileCommentNode, FileStarNode
from ery_backend.users.utils import authenticated_user

from .models import Folder, Link


class CountableConnectionBase(relay.Connection):
    class Meta:
        abstract = True

    total_count = graphene.Int()

    def resolve_total_count(self, info, **kwargs):
        return self.iterable.count()


class LinkFilter(django_filters.FilterSet):
    class Meta:
        model = Link
        fields = ("parent_folder", "name")

    name = django_filters.CharFilter(method='filter_name')
    modified_before = django_filters.DateTimeFilter(method='filter_modified_before')
    modified_after = django_filters.DateTimeFilter(method='filter_modified_after')
    is_ready = django_filters.BooleanFilter(method='filter_is_ready')
    exclude_stint_definitions = django_filters.BooleanFilter(method='_exclude_stint_definitions')
    exclude_module_definitions = django_filters.BooleanFilter(method='_exclude_module_definitions')
    exclude_themes = django_filters.BooleanFilter(method='_exclude_themes')
    exclude_procedures = django_filters.BooleanFilter(method='_exclude_procedures')
    exclude_templates = django_filters.BooleanFilter(method='_exclude_templates')
    exclude_validators = django_filters.BooleanFilter(method='_exclude_validators')
    exclude_widgets = django_filters.BooleanFilter(method='_exclude_widgets')
    exclude_images = django_filters.BooleanFilter(method='_exclude_images')
    state = django_filters.ChoiceFilter(choices=StateMixin.STATE_CHOICES, method='filter_state')

    filter_model_attrs = (
        'stint_definition',
        'module_definition',
        'template',
        'procedure',
        'widget',
        'theme',
        'validator',
        'image_asset',
    )

    @classmethod
    def _make_or_condition(cls, argument, value, lookup_expression=None, operator=Q.OR):
        condition = Q()
        for filter_attr in cls.filter_model_attrs:
            if lookup_expression:
                filter_kwarg = {f'{filter_attr}__{argument}__{lookup_expression}': value}
            else:
                filter_kwarg = {f'{filter_attr}__{argument}': value}
            condition.add(Q(**filter_kwarg), operator)

        return condition

    @classmethod
    def filter_name(cls, queryset, name, value):
        return queryset.filter(cls._make_or_condition('name', value, 'contains'))

    @classmethod
    def filter_modified_before(cls, queryset, name, value):
        return queryset.filter(cls._make_or_condition('modified', value, 'lte'))

    @classmethod
    def filter_modified_after(cls, queryset, name, value):
        return queryset.filter(cls._make_or_condition('modified', value, 'gte'))

    @classmethod
    def filter_is_ready(cls, queryset, name, value):
        # XXX: Fix in #850
        # filter_statement = cls._make_or_condition('state', StateMixin.STATE_CHOICES.prealpha, operator=Q.OR)
        # if value is False:
        #    return queryset.filter(filter_statement)
        return queryset  # queryset.exclude(filter_statement)

    @classmethod
    def filter_state(cls, queryset, name, value):
        return queryset.filter(cls._make_or_condition('state', value, operator=Q.OR))

    @staticmethod
    def _exclude_stint_definitions(queryset, name, value):
        return queryset.exclude(reference_type="stint_definition") if value else queryset

    @staticmethod
    def _exclude_module_definitions(queryset, name, value):
        return queryset.exclude(reference_type="module_definition") if value else queryset

    @staticmethod
    def _exclude_themes(queryset, name, value):
        return queryset.exclude(reference_type="theme") if value else queryset

    @staticmethod
    def _exclude_procedures(queryset, name, value):
        return queryset.exclude(reference_type="procedure") if value else queryset

    @staticmethod
    def _exclude_templates(queryset, name, value):
        return queryset.exclude(reference_type="template") if value else queryset

    @staticmethod
    def _exclude_validators(queryset, name, value):
        return queryset.exclude(reference_type="validator") if value else queryset

    @staticmethod
    def _exclude_widgets(queryset, name, value):
        return queryset.exclude(reference_type="widget") if value else queryset

    @staticmethod
    def _exclude_images(queryset, name, value):
        return queryset.exclude(reference_type="image_asset") if value else queryset


class LinkNode(PrivilegedNodeMixin, EryObjectType):
    class Meta:
        model = Link
        filterset_class = LinkFilter

    name = graphene.String()
    modified_before = graphene.DateTime()
    modified_after = graphene.DateTime()
    is_ready = graphene.Boolean()
    exclude_stint_definitions = graphene.Boolean()
    exclude_module_definitions = graphene.Boolean()
    exclude_themes = graphene.Boolean()
    exclude_procedures = graphene.Boolean()
    exclude_templates = graphene.Boolean()
    exclude_validators = graphene.Boolean()
    exclude_widgets = graphene.Boolean()
    exclude_images = graphene.Boolean()
    state = graphene.String()


class FileNodeMixin(RoleAssignmentNodeMixin):
    comments = EryFilterConnectionField(FileCommentNode)
    stars = EryFilterConnectionField(FileStarNode)

    export_bxml = graphene.String()

    @classmethod
    def get_node(cls, info, node_id):
        return super().get_node(info, node_id, exclude_kwargs={'state': cls._meta.model.STATE_CHOICES.deleted})

    def resolve_export_bxml(self, info):
        if not hasattr(self, "get_bxml_serializer"):
            return ""

        serialized = self.get_bxml_serializer()(instance=self)
        renderer = EryXMLRenderer()
        renderer.root_tag_name = self._meta.model_name

        return renderer.render(serialized)


class EryFileNode(graphene.ObjectType):
    dataset = relay.node.Field('ery_backend.datasets.schema.DatasetNode', id=graphene.ID())
    image_asset = relay.node.Field('ery_backend.assets.schema.ImageAssetNode', id=graphene.ID())
    module_definition = relay.node.Field('ery_backend.modules.schema.ModuleDefinitionNode', id=graphene.ID())
    stint_definition = relay.node.Field('ery_backend.stints.schema.StintDefinitionNode', id=graphene.ID())
    template = relay.node.Field('ery_backend.templates.schema.TemplateNode', id=graphene.ID())
    theme = relay.node.Field('ery_backend.themes.schema.ThemeNode', id=graphene.ID())
    procedure = relay.node.Field('ery_backend.procedures.schema.ProcedureNode', id=graphene.ID())
    widget = relay.node.Field('ery_backend.widgets.schema.WidgetNode', id=graphene.ID())
    validator = relay.node.Field('ery_backend.validators.schema.ValidatorNode', id=graphene.ID())

    popularity = graphene.Int()
    owner = relay.node.Field('ery_backend.users.schema.UserNode', id=graphene.ID())


class FolderNode(RoleAssignmentNodeMixin, EryObjectType):
    class Meta:
        model = Folder

    files = graphene.List(EryFileNode)

    def resolve_files(self, info):
        user = authenticated_user(info.context)
        return [EryFileNode(**entry) for entry in self.query_files(user)]


FolderEdge = FolderNode._meta.connection.Edge
FolderQuery = FolderNode.get_query_class()

LinkQuery = LinkNode.get_query_class()
LinkEdge = LinkNode._meta.connection.Edge
