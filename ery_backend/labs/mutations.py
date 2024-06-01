from graphene import relay
import graphene

from ery_backend.base.schema import EryMutationMixin
from ery_backend.stint_specifications.models import StintSpecification
from ery_backend.users.utils import authenticated_user
from ery_backend import roles

from .models import Lab
from .schema import LabNode


DefaultLabMutation = LabNode.get_mutation_class()


class SetLabStint(EryMutationMixin, relay.ClientIDMutation):
    success = graphene.Boolean(required=True)

    class Input:
        id = graphene.ID(description="GQL ID of the Lab recieving Stint", required=True)
        stint_specification_id = graphene.ID(
            description="Id of the StintSpecification used for Stint realization", required=True
        )

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        user = authenticated_user(info.context)
        lab_id = cls.gql_id_to_pk(inputs.pop("id"))
        stint_specification_id = cls.gql_id_to_pk(inputs.pop("stint_specification_id"))
        lab = Lab.objects.get(pk=lab_id)
        stint_specification = StintSpecification.objects.get(id=stint_specification_id)
        for model in [lab, stint_specification]:
            if not roles.utils.has_privilege(model, user, "start"):
                raise ValueError("not authorized")

        lab.set_stint(stint_specification_id, user)

        return SetLabStint(success=True)


class StartLabStint(EryMutationMixin, relay.ClientIDMutation):
    success = graphene.Boolean(required=True)

    class Input:
        id = graphene.ID(description="GQL ID of the Lab recieving Stint", required=True)
        hand_n = graphene.Int(description="Number of Hands added to Stint at start", required=True)
        signal_pubsub = graphene.Boolean(
            description="Whether to send a signal to the Robot Runner using Google Pubsub during stint.start",
            default_value=True,
        )

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        user = authenticated_user(info.context)
        lab_id = cls.gql_id_to_pk(inputs.pop("id"))
        signal_pubsub = inputs.pop("signal_pubsub")
        lab = Lab.objects.get(pk=lab_id)
        hand_n = inputs.pop("hand_n")
        if not roles.utils.has_privilege(lab, user, "start"):
            raise ValueError("not authorized")

        lab.start(hand_n, user, signal_pubsub)

        return StartLabStint(success=True)


class StopLabStint(EryMutationMixin, relay.ClientIDMutation):
    success = graphene.Boolean(required=True)

    class Input:
        id = graphene.ID(description="GQL ID of the Lab to act on", required=True)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        user = authenticated_user(info.context)
        lab_id = cls.gql_id_to_pk(inputs.pop("id"))
        lab = Lab.objects.get(pk=lab_id)
        if not roles.utils.has_privilege(lab, user, "stop"):
            raise ValueError("not authorized")

        lab.stop(user)

        return StopLabStint(success=True)


class ChangeLabStint(EryMutationMixin, relay.ClientIDMutation):
    success = graphene.Boolean(required=True)

    class Input:
        id = graphene.ID(description="GQL ID of the Lab to act on", required=True)
        stint_id = graphene.ID(description="GQL ID of the Stint to change to", required=True)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        user = authenticated_user(info.context)
        lab_id = cls.gql_id_to_pk(inputs.pop("id"))
        lab = Lab.objects.get(pk=lab_id)
        if not roles.utils.has_privilege(lab, user, "change"):
            raise ValueError("not authorized")

        stint_id = cls.gql_id_to_pk(inputs.pop("stint_id"))
        lab.change(stint_id)

        return ChangeLabStint(success=True)
