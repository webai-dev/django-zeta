import graphene
from graphene import relay
from graphql_relay.node.node import from_global_id, to_global_id

from ery_backend.base.schema import EryMutationMixin
from ery_backend.users.models import User
from ery_backend.users.utils import authenticated_user

from .models import Role, RoleAssignment
from .schema import RoleNode, RoleAssignmentNodeEdge
from .utils import grant_role, has_privilege, revoke_role, get_role_objs


class InputRole:
    name = graphene.String()
    comment = graphene.String()


class CreateRole(EryMutationMixin, relay.ClientIDMutation):
    role = graphene.Field(RoleNode)

    class Input(InputRole):
        pass

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        user = authenticated_user(info.context)
        ownership = Role.objects.get(name="owner")

        role = Role()
        cls.add_all_attributes(role, inputs)
        role.save()
        grant_role(ownership, role, user)

        return CreateRole(role=role)


class UpdateRole(EryMutationMixin, relay.ClientIDMutation):
    role = graphene.Field(RoleNode)

    class Input(InputRole):
        id = graphene.ID(description="GQL ID of the Role", required=True)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        user = authenticated_user(info.context)
        role_id = cls.gql_id_to_pk(inputs.pop("id"))
        role = Role.objects.get(pk=role_id)

        if role is None:
            raise ValueError("role not found")

        if not has_privilege(role, user, "update"):
            raise ValueError("not authorized")

        cls.add_all_attributes(role, inputs)
        role.save()

        return UpdateRole(role=role)


class DeleteRole(EryMutationMixin, relay.ClientIDMutation):
    success = graphene.Boolean()

    class Input:
        id = graphene.ID(description="GQL ID of the Role", required=True)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        user = authenticated_user(info.context)
        role_id = cls.gql_id_to_pk(inputs["id"])
        role = Role.objects.get(pk=role_id)

        if role is None:
            raise ValueError("role not found")

        if not has_privilege(role, user, "delete"):
            raise ValueError("not authorized")

        role.delete()
        return DeleteRole(success=True)


class GrantRole(EryMutationMixin, relay.ClientIDMutation):
    success = graphene.Boolean()
    role_assignment_edge = graphene.Field(RoleAssignmentNodeEdge)

    class Input:
        id = graphene.ID(description="GQL ID of the Role", required=True)
        owner = graphene.ID(description="GQL ID of the user to assign role to ", required=True)
        obj = graphene.ID(description="GQL ID of the object to assign role on", required=True)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        user = authenticated_user(info.context)
        role_id = cls.gql_id_to_pk(inputs["id"])
        role = Role.objects.get(pk=role_id)
        owner_id = cls.gql_id_to_pk(inputs["owner"])
        owner = User.objects.get(pk=owner_id)
        obj_raw_name, obj_id = from_global_id(inputs["obj"])
        obj_name = obj_raw_name.replace('Node', '')

        try:
            obj = get_role_objs()[obj_name].objects.get(pk=obj_id)
        except KeyError:
            raise ValueError(f"Object: {obj_name}(id: {obj_id}) cannot be assigned roles")

        if obj is None:
            raise ValueError("obj not found")
        if not has_privilege(obj, user, 'grant'):
            raise ValueError("not authorized")

        if role is None:
            raise ValueError("role not found")

        if owner is None:
            raise ValueError("viewer not found")

        if has_privilege(role, user, 'grant'):
            role_assignment = grant_role(role, obj, user=owner)
            role_assignment_edge = RoleAssignmentNodeEdge(node=role_assignment)
        else:
            raise ValueError("not authorized")

        return GrantRole(success=True, role_assignment_edge=role_assignment_edge)


class RevokeRole(EryMutationMixin, relay.ClientIDMutation):
    success = graphene.Boolean()
    role_assignment_id = graphene.ID()

    class Input:
        id = graphene.ID(description="GQL ID of the Role", required=True)
        owner = graphene.ID(description="GQL ID of the user to revoke role from ", required=True)
        obj = graphene.ID(description="GQL ID of the object to revoke role on", required=True)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        role_assignment = None
        user = authenticated_user(info.context)
        role_id = cls.gql_id_to_pk(inputs["id"])
        role = Role.objects.get(pk=role_id)
        owner_id = cls.gql_id_to_pk(inputs["owner"])
        owner = User.objects.get(pk=owner_id)
        obj_raw_name, obj_id = from_global_id(inputs["obj"])
        obj_name = obj_raw_name.replace('Node', '')
        try:
            obj = get_role_objs()[obj_name].objects.get(pk=obj_id)
        except KeyError:
            raise ValueError(f"Object: {obj_name}(id: {obj_id}) cannot be assigned roles")

        if obj is None:
            raise ValueError("obj not found")
        if not has_privilege(obj, user, 'revoke'):
            raise ValueError("not authorized")

        if role is None:
            raise ValueError("role not found")

        if owner is None:
            raise ValueError("viewer not found")

        if has_privilege(role, user, 'revoke'):
            role_assignment = RoleAssignment.objects.filter(
                role=role, user=owner, object_id=obj.id, content_type=obj.get_content_type()
            ).first()
            revoke_role(role, obj, user=owner)
        else:
            raise ValueError("not authorized")

        return RevokeRole(success=True, role_assignment_id=to_global_id("RoleAssignmentNode", role_assignment.pk))
