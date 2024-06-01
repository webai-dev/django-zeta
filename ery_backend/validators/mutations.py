from graphene import relay
import graphene

from ery_backend.base.schema import EryMutationMixin
from ery_backend import roles
from ery_backend.users.utils import authenticated_user
from ery_backend.validators.models import Validator
from ery_backend.validators.schema import ValidatorNode


class InputValidator:
    name = graphene.String()
    comment = graphene.String()
    code = graphene.String()
    regex = graphene.String()
    nullable = graphene.Boolean()


class CreateValidator(EryMutationMixin, relay.ClientIDMutation):
    validator = graphene.Field(ValidatorNode)

    class Input(InputValidator):
        pass

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        authenticated_user(info.context)

        validator = Validator()
        cls.add_all_attributes(validator, inputs)
        validator.save()

        return CreateValidator(validator=validator)


class UpdateValidator(EryMutationMixin, relay.ClientIDMutation):
    validator = graphene.Field(ValidatorNode)

    class Input(InputValidator):
        id = graphene.ID(description="GQL ID of the Validator", required=True)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        user = authenticated_user(info.context)
        validator_id = cls.gql_id_to_pk(inputs.pop("id"))
        validator = Validator.objects.get(pk=validator_id)

        if validator is None:
            raise ValueError("Validator not found")

        if not roles.utils.has_privilege(validator, user, "update"):
            raise ValueError("not authorized")

        cls.add_all_attributes(validator, inputs)
        validator.save()

        return UpdateValidator(validator=validator)


class DeleteValidator(EryMutationMixin, relay.ClientIDMutation):
    success = graphene.Boolean()

    class Input:
        id = graphene.ID(description="GQL ID of the Validator", required=True)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        user = authenticated_user(info.context)
        validator_id = cls.gql_id_to_pk(inputs.pop("id"))
        validator = Validator.objects.get(pk=validator_id)

        if validator is None:
            raise ValueError("Validator not found")

        if not roles.utils.has_privilege(validator, user, "delete"):
            raise ValueError("not authorized")

        validator.soft_delete()

        return DeleteValidator(success=True)
