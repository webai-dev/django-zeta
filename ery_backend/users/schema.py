from django.contrib.auth import get_user_model
import graphene
from graphene import relay

from ery_backend.actions.schema import ActionQuery, ActionStepQuery
from ery_backend.assets.schema import ImageAssetQuery, DatasetAssetQuery
from ery_backend.base.locale_schema import LanguageQuery
from ery_backend.base.schema import VersionQuery, RevisionQuery, PrivilegedNodeMixin
from ery_backend.base.schema_utils import EryObjectType, EryFilterConnectionField
from ery_backend.commands.schema import CommandQuery
from ery_backend.comments.schema import FileCommentQuery, FileStarQuery, FileCommentNode
from ery_backend.conditions.schema import ConditionQuery
from ery_backend.datasets.schema import DatasetQuery
from ery_backend.folders.models import Folder
from ery_backend.folders.schema import LinkQuery, FolderQuery, FolderNode
from ery_backend.forms.schema import (
    FormQuery,
    FormButtonQuery,
    FormButtonListQuery,
    FormFieldQuery,
    FormFieldChoiceQuery,
    FormFieldChoiceTranslationQuery,
    FormItemQuery,
)
from ery_backend.frontends.schema import FrontendQuery
from ery_backend.hands.schema import HandQuery
from ery_backend.keywords.schema import KeywordQuery
from ery_backend.labs.schema import LabQuery
from ery_backend.logs.schema import LogQuery
from ery_backend.modules.models import ModuleDefinition
from ery_backend.modules.schema import ModuleDefinitionQuery, ModuleDefinitionNode, ModuleDefinitionProcedureQuery
from ery_backend.modules.widget_schema import ModuleDefinitionWidgetQuery, ModuleEventQuery, ModuleEventStepQuery
from ery_backend.news.schema import NewsItemQuery
from ery_backend.notifications.schema import NotificationQuery
from ery_backend.procedures.schema import ProcedureNode, Procedure, ProcedureQuery
from ery_backend.roles.schema import RoleQuery, RoleAssignmentQuery, RoleAssignmentNodeMixin
from ery_backend.robots.schema import RobotQuery, RobotRuleQuery
from ery_backend.stages.schema import StageDefinitionQuery, StageTemplateQuery
from ery_backend.stints.schema import StintQuery, StintDefinitionQuery, StintDefinitionNode, StintDefinition
from ery_backend.stint_specifications.schema import (
    StintSpecificationQuery,
    StintSpecificationVariableQuery,
    StintSpecificationRobotQuery,
    StintSpecificationCountryQuery,
    StintModuleSpecificationQuery,
)
from ery_backend.syncs.schema import EraQuery
from ery_backend.teams.schema import TeamQuery
from ery_backend.templates.schema import TemplateQuery, TemplateNode, Template
from ery_backend.templates.widget_schema import TemplateWidgetQuery
from ery_backend.themes.schema import ThemeQuery, ThemeNode, Theme
from ery_backend.widgets.schema import (
    WidgetQuery,
    WidgetConnectionQuery,
    WidgetEventQuery,
    WidgetEventStepQuery,
    WidgetPropQuery,
    WidgetStateQuery,
)
from ery_backend.users.utils import authenticated_user
from ery_backend.validators.schema import ValidatorQuery, ValidatorNode, Validator
from ery_backend.variables.schema import VariableDefinitionQuery, ModuleVariableQuery, TeamVariableQuery, HandVariableQuery
from ery_backend.vendors.schema import VendorQuery
from ery_backend.widgets.schema import WidgetNode, Widget

from .models import FileTouch, User


# FileTouch
class FileTouchNode(RoleAssignmentNodeMixin, EryObjectType):
    class Meta:
        model = FileTouch


class FileTouchQuery:
    file_touch = relay.Node.Field(FileTouchNode, id=graphene.ID(required=True))
    all_file_touches = EryFilterConnectionField(FileTouchNode)

    def resolve_all_file_touches(self, info):  # pylint: disable=no-self-use
        user = authenticated_user(info.context)
        return FileTouch.objects.filter(user=user)


class BaseUserNode:
    fullname = graphene.String()
    profile_image_url = graphene.String()

    def resolve_profile_image_url(self, info, **kwargs):
        return self.profile_image_url


class UserNode(PrivilegedNodeMixin, BaseUserNode, EryObjectType):
    class Meta:
        model = get_user_model()

    owned_experiments = EryFilterConnectionField(StintDefinitionNode)
    owned_modules = EryFilterConnectionField(ModuleDefinitionNode)
    owned_templates = EryFilterConnectionField(TemplateNode)
    owned_themes = EryFilterConnectionField(ThemeNode)
    owned_widgets = EryFilterConnectionField(WidgetNode)
    owned_procedures = EryFilterConnectionField(ProcedureNode)
    owned_validators = EryFilterConnectionField(ValidatorNode)
    owned_folders = EryFilterConnectionField(FolderNode)

    def resolve_owned_experiments(self, info, **kwargs):
        return StintDefinition.objects.filter_owner(self).filter(**kwargs)

    def resolve_owned_modules(self, info, **kwargs):
        return ModuleDefinition.objects.filter_owner(self).filter(**kwargs)

    def resolve_owned_templates(self, info, **kwargs):
        return Template.objects.filter_owner(self).filter(**kwargs)

    def resolve_owned_themes(self, info, **kwargs):
        return Theme.objects.filter_owner(self).filter(**kwargs)

    def resolve_owned_widgets(self, info, **kwargs):
        return Widget.objects.filter_owner(self).filter(**kwargs)

    def resolve_owned_procedures(self, info, **kwargs):
        return Procedure.objects.filter_owner(self).filter(**kwargs)

    def resolve_owned_validators(self, info, **kwargs):
        return Validator.objects.filter_owner(self).filter(**kwargs)

    def resolve_owned_folders(self, info, **kwargs):
        return Folder.objects.filter_owner(self).filter(**kwargs)


UserQuery = UserNode.get_query_class()


class ViewerNode(
    ActionQuery,
    ActionStepQuery,
    CommandQuery,
    ConditionQuery,
    DatasetAssetQuery,
    DatasetQuery,
    EraQuery,
    FileCommentQuery,
    FileStarQuery,
    FileTouchQuery,
    FolderQuery,
    FormQuery,
    FormButtonQuery,
    FormButtonListQuery,
    FormFieldQuery,
    FormFieldChoiceQuery,
    FormFieldChoiceTranslationQuery,
    FormItemQuery,
    FrontendQuery,
    HandQuery,
    HandVariableQuery,
    ImageAssetQuery,
    KeywordQuery,
    LabQuery,
    LanguageQuery,
    LinkQuery,
    LogQuery,
    ModuleDefinitionQuery,
    ModuleDefinitionProcedureQuery,
    ModuleDefinitionWidgetQuery,
    ModuleEventQuery,
    ModuleEventStepQuery,
    ModuleVariableQuery,
    NewsItemQuery,
    NotificationQuery,
    ProcedureQuery,
    RevisionQuery,
    RoleQuery,
    RoleAssignmentQuery,
    RobotQuery,
    RobotRuleQuery,
    StageDefinitionQuery,
    StageTemplateQuery,
    StintQuery,
    StintDefinitionQuery,
    StintSpecificationQuery,
    StintSpecificationCountryQuery,
    StintModuleSpecificationQuery,
    StintSpecificationRobotQuery,
    StintSpecificationVariableQuery,
    TeamQuery,
    TeamVariableQuery,
    TemplateQuery,
    TemplateWidgetQuery,
    ThemeQuery,
    UserQuery,
    UserNode,
    ValidatorQuery,
    VariableDefinitionQuery,
    VendorQuery,
    VersionQuery,
    WidgetEventQuery,
    WidgetEventStepQuery,
    WidgetConnectionQuery,
    WidgetPropQuery,
    WidgetStateQuery,
    WidgetQuery,
    BaseUserNode,
    EryObjectType,
):
    class Meta:
        model = get_user_model()

    user_id = graphene.String()
    library = graphene.List('ery_backend.folders.schema.EryFileNode')
    recommended = EryFilterConnectionField(UserNode)
    followings = EryFilterConnectionField(UserNode)
    comments = EryFilterConnectionField(FileCommentNode)

    def resolve_user_id(self, info):
        return self.gql_id

    def resolve_library(self, info):
        from ery_backend.folders.schema import EryFileNode

        return [EryFileNode(**entry) for entry in self.query_library()]

    def resolve_recommended(self, info, **kwargs):
        return (
            User.objects.exclude(id=self.id)
            .exclude(followers=self)
            .exclude(id__in=self.followers.values_list('id', flat=True))
        )

    def resolve_followings(self, info, **kwargs):
        return User.objects.filter(followers=self)


class ViewerQuery:
    viewer = relay.node.Field(ViewerNode)

    def resolve_viewer(self, info):  # pylint: disable=no-self-use
        data_loader = info.context.get_data_loader(User)
        user = authenticated_user(info.context)
        return data_loader.load(user.id)
