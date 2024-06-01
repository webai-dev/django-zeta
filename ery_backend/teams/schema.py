from graphene import relay

from ery_backend.roles.schema import RoleAssignmentNodeMixin
from ery_backend.base.schema_utils import EryObjectType, EryFilterConnectionField

from .models import Team


class TeamNode(RoleAssignmentNodeMixin, EryObjectType):
    class Meta:
        model = Team


class TeamQuery:
    team = relay.Node.Field(TeamNode)
    all_teams = EryFilterConnectionField(TeamNode)


TeamNodeEdge = TeamNode._meta.connection.Edge
