from ery_backend.base.schema_utils import EryObjectType
from ery_backend.roles.schema import RoleAssignmentNodeMixin

from .models import (
    HandVariable,
    ModuleVariable,
    TeamVariable,
    VariableDefinition,
    VariableChoiceItem,
    VariableChoiceItemTranslation,
)


class VariableChoiceItemTranslationNode(RoleAssignmentNodeMixin, EryObjectType):
    class Meta:
        model = VariableChoiceItemTranslation


class VariableChoiceItemNode(RoleAssignmentNodeMixin, EryObjectType):
    class Meta:
        model = VariableChoiceItem


class VariableDefinitionNode(RoleAssignmentNodeMixin, EryObjectType):
    class Meta:
        model = VariableDefinition


VariableDefinitionQuery = VariableDefinitionNode.get_query_class()


class ModuleVariableNode(RoleAssignmentNodeMixin, EryObjectType):
    class Meta:
        model = ModuleVariable


ModuleVariableQuery = ModuleVariableNode.get_query_class()


class TeamVariableNode(RoleAssignmentNodeMixin, EryObjectType):
    class Meta:
        model = TeamVariable


TeamVariableQuery = TeamVariableNode.get_query_class()


class HandVariableNode(RoleAssignmentNodeMixin, EryObjectType):
    class Meta:
        model = HandVariable


HandVariableQuery = HandVariableNode.get_query_class()
