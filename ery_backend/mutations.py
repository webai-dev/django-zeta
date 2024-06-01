from graphene_django.rest_framework.mutation import RelaySerializerMutation

from ery_backend.actions.schema import ActionNode, ActionStepNode
from ery_backend.assets.mutations import UploadImageAsset
from ery_backend.assets.schema import ImageAssetNode
from ery_backend.base.schema import ErySerializerMutationMixin
from ery_backend.commands.schema import (
    CommandNode,
    CommandTemplateNode,
    CommandTemplateBlockNode,
    CommandTemplateBlockTranslationNode,
)
from ery_backend.comments.mutations import (
    CreateFileComment,
    UpdateFileComment,
    DeleteFileComment,
    CreateFileStar,
    DeleteFileStar,
)
from ery_backend.conditions.schema import ConditionNode
from ery_backend.datasets.mutations import UploadDataset
from ery_backend.datasets.schema import DatasetNode
from ery_backend.folders.mutations import (
    CreateFolder,
    UpdateFolder,
    DeleteFolder,
    DuplicateFolder,
    BaseLinkMutation,
    DuplicateLink,
)
from ery_backend.forms.schema import (
    FormFieldNode,
    FormFieldChoiceNode,
    FormFieldChoiceTranslationNode,
    FormButtonListNode,
    FormButtonNode,
    FormNode,
    FormItemNode,
)
from ery_backend.forms.mutations import BaseFormFieldInput, CreateFormField, BaseFormButtonListInput, CreateFormButtonList
from ery_backend.keywords.schema import KeywordNode
from ery_backend.labs.mutations import DefaultLabMutation, SetLabStint, StartLabStint, StopLabStint, ChangeLabStint
from ery_backend.modules.models import ModuleDefinition
from ery_backend.modules.schema import (
    ModuleDefinitionNode,
    ModuleDefinitionProcedureNode,
    ModuleDefinitionWidgetNode,
    WidgetChoiceNode,
    WidgetChoiceTranslationNode,
    ModuleEventNode,
    ModuleEventStepNode,
)
from ery_backend.notifications.mutations import (
    CreateNotification,
    UpdateNotification,
    DeleteNotification,
    CreateNotificationContent,
    UpdateNotificationContent,
    DeleteNotificationContent,
)
from ery_backend.procedures.schema import ProcedureNode, ProcedureArgumentNode
from ery_backend.robots.mutations import (
    CreateRobot,
    UpdateRobot,
    DeleteRobot,
    CreateRobotRule,
    UpdateRobotRule,
    DeleteRobotRule,
)
from ery_backend.roles.mutations import CreateRole, UpdateRole, DeleteRole, GrantRole, RevokeRole
from ery_backend.stages.schema import (
    StageDefinitionNode,
    StageTemplateNode,
    StageTemplateBlockNode,
    StageTemplateBlockTranslationNode,
    RedirectNode,
    StageNode,
)
from ery_backend.stint_specifications.mutations import (
    BaseStintSpecificationMutation,
    SerializedStintSpecification,
    RealizeStintSpecification,
)
from ery_backend.stint_specifications.schema import (
    StintSpecificationAllowedLanguageFrontendNode,
    StintSpecificationRobotNode,
    StintSpecificationVariableNode,
    StintSpecificationCountryNode,
    StintModuleSpecificationNode,
)
from ery_backend.stints.schema import StintDefinitionNode
from ery_backend.stints.mutations import UpdateStint, StartStint, StopStint
from ery_backend.syncs.schema import EraNode
from ery_backend.teams.mutations import AddTeamMembership, DeleteTeamMembership
from ery_backend.templates.schema import TemplateNode, TemplateBlockNode, TemplateBlockTranslationNode, TemplateWidgetNode
from ery_backend.themes.schema import ThemeNode, ThemePaletteNode, ThemeTypographyNode
from ery_backend.users.mutations import (
    DefaultFileTouchMutation,
    CreateFileTouch,
    UpdateUserProfile,
    FollowUser,
    UnfollowUser,
    UpdateUser,
)
from ery_backend.variables.schema import VariableDefinitionNode, ModuleVariableNode, TeamVariableNode, HandVariableNode
from ery_backend.validators.mutations import CreateValidator, UpdateValidator, DeleteValidator
from ery_backend.vendors.schema import VendorNode
from ery_backend.widgets.schema import (
    WidgetNode,
    WidgetStateNode,
    WidgetEventStepNode,
    WidgetEventNode,
    WidgetPropNode,
    WidgetConnectionNode,
)


# Actions
ActionMutation = ActionNode.get_mutation_class()
ActionStepMutation = ActionStepNode.get_mutation_class()

# Assets
class ImageAssetMutation:
    upload_image_asset = UploadImageAsset.Field()
    delete_image_asset = ImageAssetNode.get_delete_mutation_class(ImageAssetNode.get_mutation_input()).Field()


# Commands
CommandMutation = CommandNode.get_mutation_class()
CommandTemplateMutation = CommandTemplateNode.get_mutation_class()
CommandTemplateBlockMutation = CommandTemplateBlockNode.get_mutation_class()
CommandTemplateBlockTranslationMutation = CommandTemplateBlockTranslationNode.get_mutation_class()

# Comments
class FileCommentMutation:
    create_file_comment = CreateFileComment.Field()
    update_file_comment = UpdateFileComment.Field()
    delete_file_comment = DeleteFileComment.Field()


class FileStarMutation:
    create_file_star = CreateFileStar.Field()
    delete_file_star = DeleteFileStar.Field()


# Conditions
ConditionMutation = ConditionNode.get_mutation_class()


# Datasets
class DatasetMutation:
    upload_dataset = UploadDataset.Field()
    delete_dataset = DatasetNode.get_delete_mutation_class(DatasetNode.get_mutation_input()).Field()


# Folders
class FolderMutation:
    create_folder = CreateFolder.Field()
    update_folder = UpdateFolder.Field()
    delete_folder = DeleteFolder.Field()
    duplicate_folder = DuplicateFolder.Field()


class LinkMutation(BaseLinkMutation):
    duplicate_link = DuplicateLink.Field()


# Forms
class FormFieldMutation:
    create_form_field = CreateFormField.Field()
    update_form_field = FormFieldNode.get_update_mutation_class(BaseFormFieldInput).Field()
    delete_form_field = FormFieldNode.get_delete_mutation_class(BaseFormFieldInput).Field()


class FormButtonListMutation:
    create_form_button_list = CreateFormButtonList.Field()
    update_form_button_list = FormButtonListNode.get_update_mutation_class(BaseFormButtonListInput).Field()
    delete_form_button_list = FormButtonListNode.get_delete_mutation_class(BaseFormButtonListInput).Field()


FormMutation = FormNode.get_mutation_class()
FormItemMutation = FormItemNode.get_mutation_class()
FormButtonMutation = FormButtonNode.get_mutation_class()
FormFieldChoiceMutation = FormFieldChoiceNode.get_mutation_class()
FormFieldChoiceTranslationMutation = FormFieldChoiceTranslationNode.get_mutation_class()


# Keywords
KeywordMutation = KeywordNode.get_mutation_class()


# Labs
class LabMutation(DefaultLabMutation):
    set_lab_stint = SetLabStint.Field()
    start_lab_stint = StartLabStint.Field()
    stop_lab_stint = StopLabStint.Field()
    change_lab_stint = ChangeLabStint.Field()


# Notifications
class NotificationMutation:
    create_notification = CreateNotification.Field()
    update_notification = UpdateNotification.Field()
    delete_notification = DeleteNotification.Field()


class NotificationContentMutation:
    create_notification_content = CreateNotificationContent.Field()
    update_notification_content = UpdateNotificationContent.Field()
    delete_notification_content = DeleteNotificationContent.Field()


# Procedures
ProcedureMutation = ProcedureNode.get_mutation_class()
ProcedureArgumentMutation = ProcedureArgumentNode.get_mutation_class()


# Robots
class RobotMutation:
    create_robot = CreateRobot.Field()
    update_robot = UpdateRobot.Field()
    delete_robot = DeleteRobot.Field()


class RobotRuleMutation:
    create_robot_rule = CreateRobotRule.Field()
    update_robot_rule = UpdateRobotRule.Field()
    delete_robot_rule = DeleteRobotRule.Field()


# Roles
class RoleMutation:
    create_role = CreateRole.Field()
    update_role = UpdateRole.Field()
    delete_role = DeleteRole.Field()
    grant_role = GrantRole.Field()
    revoke_role = RevokeRole.Field()


# Stages
StageDefinitionMutation = StageDefinitionNode.get_mutation_class()
StageTemplateMutation = StageTemplateNode.get_mutation_class()
StageTemplateBlockMutation = StageTemplateBlockNode.get_mutation_class()
StageTemplateBlockTranslationMutation = StageTemplateBlockTranslationNode.get_mutation_class()
RedirectMutation = RedirectNode.get_mutation_class()
StageMutation = StageNode.get_mutation_class()


# StintSpecifications
class StintSpecificationMutation(BaseStintSpecificationMutation):
    realize_stint_specification = RealizeStintSpecification.Field()
    serialized_stint_specification = SerializedStintSpecification.Field()


StintSpecificationAllowedLanguageFrontendMutation = StintSpecificationAllowedLanguageFrontendNode.get_mutation_class()
StintSpecificationRobotMutation = StintSpecificationRobotNode.get_mutation_class()
StintSpecificationVariableMutation = StintSpecificationVariableNode.get_mutation_class()
StintSpecificationCountryMutation = StintSpecificationCountryNode.get_mutation_class()
StintModuleSpecificationMutation = StintModuleSpecificationNode.get_mutation_class()


# Syncs
EraMutation = EraNode.get_mutation_class()


# Teams
class TeamMutation:
    add_team_membership = AddTeamMembership.Field()
    delete_team_membership = DeleteTeamMembership.Field()


# Templates
TemplateMutation = TemplateNode.get_mutation_class()
TemplateBlockMutation = TemplateBlockNode.get_mutation_class()
TemplateBlockTranslationMutation = TemplateBlockTranslationNode.get_mutation_class()
TemplateWidgetMutation = TemplateWidgetNode.get_mutation_class()


# Themes
ThemeMutation = ThemeNode.get_mutation_class()
ThemePaletteMutation = ThemePaletteNode.get_mutation_class()
ThemeTypographyMutation = ThemeTypographyNode.get_mutation_class()


# Users
class FileTouchMutation(DefaultFileTouchMutation):
    create_file_touch = CreateFileTouch.Field()


class UserMutation:
    update_user = UpdateUser.Field()
    update_user_profile = UpdateUserProfile.Field()
    follow_user = FollowUser.Field()
    unfollow_user = UnfollowUser.Field()


# Validators
class ValidatorMutation:
    create_validator = CreateValidator.Field()
    update_validator = UpdateValidator.Field()
    delete_validator = DeleteValidator.Field()


# Variables
VariableDefinitionMutation = VariableDefinitionNode.get_mutation_class()
ModuleVariableMutation = ModuleVariableNode.get_mutation_class()
TeamVariableMutation = TeamVariableNode.get_mutation_class()
HandVariableMutation = HandVariableNode.get_mutation_class()


# Vendors
VendorMutation = VendorNode.get_mutation_class()


# Widgets
WidgetMutation = WidgetNode.get_mutation_class()
WidgetStateMutation = WidgetStateNode.get_mutation_class()
WidgetEventStepMutation = WidgetEventStepNode.get_mutation_class()
WidgetEventMutation = WidgetEventNode.get_mutation_class()
WidgetPropMutation = WidgetPropNode.get_mutation_class()
WidgetConnectionMutation = WidgetConnectionNode.get_mutation_class()


# Modules
# All mutations added here to avoid gql NoneType errors
BaseModuleDefinitionMutation = ModuleDefinitionNode.get_mutation_class()


class SerializedModuleDefinition(ErySerializerMutationMixin, RelaySerializerMutation):
    class Meta(ErySerializerMutationMixin.Meta):
        serializer_class = ModuleDefinition.get_mutation_serializer()


class ModuleDefinitionMutation(BaseModuleDefinitionMutation):
    serialized_module_definition = SerializedModuleDefinition.Field()


ModuleDefinitionProcedureMutation = ModuleDefinitionProcedureNode.get_mutation_class()
ModuleDefinitionWidgetMutation = ModuleDefinitionWidgetNode.get_mutation_class()
WidgetChoiceMutation = WidgetChoiceNode.get_mutation_class()
WidgetChoiceTranslationMutation = WidgetChoiceTranslationNode.get_mutation_class()
ModuleEventMutation = ModuleEventNode.get_mutation_class()
ModuleEventStepMutation = ModuleEventStepNode.get_mutation_class()


# Stints
StintDefinitionMutation = StintDefinitionNode.get_mutation_class()


class StintMutation:
    start_stint = StartStint.Field()
    stop_stint = StopStint.Field()
    update_stint = UpdateStint.Field()
