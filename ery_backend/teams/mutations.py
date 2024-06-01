from graphene import relay
import graphene

from ery_backend.base.schema import EryMutationMixin
from ery_backend.hands.models import Hand

from .models import Team
from .schema import TeamNodeEdge


class AddTeamMembership(EryMutationMixin, relay.ClientIDMutation):
    success = graphene.Boolean()
    team_edge = graphene.Field(TeamNodeEdge)

    class Input:
        id = graphene.ID(required=True)
        subject_id = graphene.ID(required=True)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        gql_id = inputs.pop("id")
        tid = cls.gql_id_to_pk(gql_id)
        gql_id = inputs.pop("subject_id")
        sid = cls.gql_id_to_pk(gql_id)

        team = Team.objects.get(pk=tid)
        hand = Hand.objects.get(pk=sid)

        team.hands.add(hand)
        team.save()

        return AddTeamMembership(success=True, team_edge=TeamNodeEdge(node=team))


class DeleteTeamMembership(EryMutationMixin, relay.ClientIDMutation):
    success = graphene.Boolean()

    class Input:
        id = graphene.ID(required=True)
        subject_id = graphene.ID(required=True)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        gql_id = inputs.pop("id")
        tid = cls.gql_id_to_pk(gql_id)
        gql_id = inputs.pop("subject_id")
        sid = cls.gql_id_to_pk(gql_id)

        team = Team.objects.get(pk=tid)
        hand = Hand.objects.get(pk=sid)

        team.hands.remove(hand)
        team.save()

        return AddTeamMembership(success=True)
