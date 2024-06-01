from graphene import relay
import graphene
from graphql_relay.node.node import from_global_id

from ery_backend.assets.models import ImageAsset
from ery_backend.base.schema import EryMutationMixin
from ery_backend.modules.models import ModuleDefinition
from ery_backend.procedures.models import Procedure
from ery_backend.roles.utils import grant_ownership, has_privilege
from ery_backend.stints.models import StintDefinition
from ery_backend.templates.models import Template
from ery_backend.users.models import User, UserRelation
from ery_backend.widgets.models import Widget


from .models import FileTouch
from .schema import FileTouchNode, UserNode
from .utils import authenticated_user


DefaultFileTouchMutation = FileTouchNode.get_mutation_class()


class CreateFileTouch(EryMutationMixin, relay.ClientIDMutation):
    file_touch = graphene.Field(FileTouchNode, required=True)

    class Input:
        on = graphene.ID(required=True, description="GQL ID of file to be touched")

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        user = authenticated_user(info.context)

        global_id = inputs.pop("on")

        # try:
        node_type, node_pk = from_global_id(global_id)
        # except:
        # raise ValueError('Invalid GQL ID in request: {on: >"%s"<}' % global_id)

        if node_type == "ImageAssetNode":
            obj = ImageAsset.objects.get(pk=node_pk)
            file_touch, _ = FileTouch.objects.get_or_create(user=user, image_asset=obj)
        elif node_type == "ProcedureNode":
            obj = Procedure.objects.get(pk=node_pk)
            file_touch, _ = FileTouch.objects.get_or_create(user=user, procedure=obj)
        elif node_type == "ModuleDefinitionNode":
            obj = ModuleDefinition.objects.get(pk=node_pk)
            file_touch, _ = FileTouch.objects.get_or_create(user=user, module_definition=obj)
        elif node_type == "StintDefinitionNode":
            obj = StintDefinition.objects.get(pk=node_pk)
            file_touch, _ = FileTouch.objects.get_or_create(user=user, stint_definition=obj)
        elif node_type == "TemplateNode":
            obj = Template.objects.get(pk=node_pk)
            file_touch, _ = FileTouch.objects.get_or_create(user=user, template=obj)
        elif node_type == "WidgetNode":
            obj = Widget.objects.get(pk=node_pk)
            file_touch, _ = FileTouch.objects.get_or_create(user=user, widget=obj)
        else:
            raise ValueError(f"Invalid node type: {node_type}")

        if not has_privilege(obj, user, "read"):
            raise ValueError("not authorized")

        file_touch.save()
        grant_ownership(file_touch, user)

        return CreateFileTouch(file_touch=file_touch)


class UserInput:
    privacy = graphene.String()
    profile = graphene.types.json.JSONString()
    experience = graphene.types.json.JSONString()


class UpdateUser(EryMutationMixin, relay.ClientIDMutation):
    user = graphene.Field(UserNode)

    class Input(UserInput):
        pass

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        user = authenticated_user(info.context)

        cls.add_all_attributes(user, inputs)
        user.save()

        return UpdateUser(user=user)


class UpdateUserProfile(EryMutationMixin, relay.ClientIDMutation):
    user = graphene.Field(UserNode)

    class Input:
        field_name = graphene.String()
        value = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        user = authenticated_user(info.context)

        field_name = inputs['field_name']
        value = inputs['value']

        if user.profile['edit']:
            user.profile['edit'][field_name] = value
        else:
            user.profile['edit'] = {field_name: value}

        user.save()
        return UpdateUserProfile(user=user)


class FollowUser(EryMutationMixin, relay.ClientIDMutation):
    user = graphene.Field(UserNode)

    class Input:
        id = graphene.ID(required=True, description="GQL ID of the user who will be followed by me")

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        me = authenticated_user(info.context)

        tdid = cls.gql_id_to_pk(inputs.pop("id"))
        user = User.objects.get(pk=tdid)

        UserRelation.objects.get_or_create(from_user=me, to_user=user)

        return UpdateUser(user=me)


class UnfollowUser(EryMutationMixin, relay.ClientIDMutation):
    user = graphene.Field(UserNode)

    class Input:
        id = graphene.ID(required=True, description="GQL ID of the user who will be followed by me")

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        me = authenticated_user(info.context)

        tdid = cls.gql_id_to_pk(inputs.pop("id"))
        user = User.objects.get(pk=tdid)

        UserRelation.objects.filter(from_user=me, to_user=user).delete()

        return UpdateUser(user=me)
