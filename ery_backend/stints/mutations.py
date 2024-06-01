import graphene
from graphene import relay

from ery_backend.base.schema import EryMutationMixin
from ery_backend.roles.utils import has_privilege
from ery_backend.users.utils import authenticated_user

# This import loads the 'related_name' variables from HandVariable
# pylint: disable=unused-import
from ery_backend.variables.schema import HandVariableNode

from .models import StintDefinition, Stint
from .schema import StintNode


class StintInput:
    comment = graphene.String()
    layout = graphene.types.json.JSONString()


class UpdateStint(EryMutationMixin, relay.ClientIDMutation):
    stint = graphene.Field(StintNode)

    class Input(StintInput):
        id = graphene.ID(description="GQL ID of the stint to update", required=True)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        gql_id = inputs.pop("id")
        tid = cls.gql_id_to_pk(gql_id)

        stint = Stint.objects.get(pk=tid)

        cls.add_all_attributes(stint, inputs)
        stint.save()

        return UpdateStint(stint=stint)


class StartStint(EryMutationMixin, relay.ClientIDMutation):
    success = graphene.Boolean()

    class Input:
        id = graphene.ID(required=True, descriptions="GQL ID of the Stint to start")
        signal_pubsub = graphene.Boolean(
            description="Whether to send a signal to the Robot Runner using Google Pubsub during stint.start",
            default_value=True,
        )

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        user = authenticated_user(info.context)
        stint_id = cls.gql_id_to_pk(inputs.pop('id'))
        signal_pubsub = inputs.pop('signal_pubsub')
        stint = Stint.objects.get(pk=stint_id)

        if not has_privilege(stint, user, 'start'):
            raise ValueError("not authorized")

        stint.start(started_by=user, signal_pubsub=signal_pubsub)
        return StartStint(success=True)


class StopStint(EryMutationMixin, relay.ClientIDMutation):
    success = graphene.Boolean()

    class Input:
        id = graphene.ID(required=True, description="GQL ID of the Stint to start")

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        user = authenticated_user(info.context)
        stint_id = cls.gql_id_to_pk(inputs.pop('id'))
        stint = Stint.objects.get(pk=stint_id)

        if not has_privilege(stint, user, 'stop'):
            raise ValueError("not authorized")

        stint.set_status(Stint.STATUS_CHOICES.cancelled, actor=user)
        return StopStint(success=True)
