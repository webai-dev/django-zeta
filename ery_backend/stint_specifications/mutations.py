from graphene_django.rest_framework.mutation import RelaySerializerMutation
from graphene import relay
import graphene

from ery_backend.base.schema import EryMutationMixin, ErySerializerMutationMixin
from ery_backend.roles.utils import has_privilege
from ery_backend.stint_specifications.models import StintSpecification
from ery_backend.stints.schema import StintNode
from ery_backend.users.utils import authenticated_user

from .schema import StintSpecificationNode


BaseStintSpecificationMutation = StintSpecificationNode.get_mutation_class()


class RealizeStintSpecification(EryMutationMixin, relay.ClientIDMutation):
    stint = graphene.Field(StintNode)

    class Input:
        id = graphene.ID(required=True, description="GQL ID of the StintSpecification being realized")

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        user = authenticated_user(info.context)
        stint_specification_id = cls.gql_id_to_pk(inputs.pop('id'))
        stint_specification = StintSpecification.objects.get(pk=stint_specification_id)

        if not has_privilege(stint_specification, user, 'realize'):
            raise ValueError("not authorized")

        stint = stint_specification.realize(user)
        return RealizeStintSpecification(stint=stint)


class SerializedStintSpecification(ErySerializerMutationMixin, RelaySerializerMutation):
    class Meta(ErySerializerMutationMixin.Meta):
        serializer_class = StintSpecification.get_mutation_serializer()
