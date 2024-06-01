import graphene

from ery_backend.base.schema import PrivilegedNodeMixin, VersionMixin
from ery_backend.base.schema_utils import EryObjectType, EryFilterConnectionField
from ery_backend.folders.schema import FileNodeMixin
from ery_backend.hands.schema import HandNode
from ery_backend.teams.schema import TeamNode

# This import loads the 'related_name' variables from HandVariable
# pylint: disable=unused-import
from ery_backend.variables.schema import HandVariableNode

from .models import StintDefinition, Stint


class StintDefinitionNode(FileNodeMixin, VersionMixin, EryObjectType):
    class Meta:
        model = StintDefinition

    ready = graphene.Boolean()


StintDefinitionQuery = StintDefinitionNode.get_query_class()


class StintNode(PrivilegedNodeMixin, EryObjectType):
    class Meta:
        model = Stint

    hands = EryFilterConnectionField(HandNode)
    teams = EryFilterConnectionField(TeamNode)


StintQuery = StintNode.get_query_class()
