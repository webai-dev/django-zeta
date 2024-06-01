from graphene import relay
import graphene
from graphql_relay import from_global_id

from ery_backend.assets.models import ImageAsset
from ery_backend.base.schema import EryMutationMixin
from ery_backend.modules.models import ModuleDefinition
from ery_backend.procedures.models import Procedure
from ery_backend.roles.utils import has_privilege
from ery_backend.stints.models import StintDefinition
from ery_backend.templates.models import Template
from ery_backend.users.utils import authenticated_user
from ery_backend.widgets.models import Widget
from .models import FileComment, FileStar
from .schema import FileCommentNode, FileStarNode


class FileCommentMutationInput:
    comment = graphene.String()


class FileStarMutationInput:
    pass


class CreateFileComment(EryMutationMixin, relay.ClientIDMutation):
    user_comment_edge = graphene.Field(FileCommentNode._meta.connection.Edge, required=True)

    class Input(FileCommentMutationInput):
        on = graphene.ID(required=True, description="GQL ID of the comment's object")
        comment = graphene.String(required=True, description="Comment text")

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        user = authenticated_user(info.context)

        global_id = inputs.pop("on")

        try:
            node_type, node_pk = from_global_id(global_id)
        except:
            raise ValueError('Invalid GQL ID in request: {on: >"%s"<}' % global_id)

        comment = FileComment(user=user, comment=inputs.pop("comment"))

        if node_type == "ImageAssetNode":
            obj = ImageAsset.objects.get(pk=node_pk)
            comment.reference_type = "image_asset"
            comment.image_asset = obj
        elif node_type == "ProcedureNode":
            obj = Procedure.objects.get(pk=node_pk)
            comment.reference_type = "procedure"
            comment.procedure = obj
        elif node_type == "ModuleDefinitionNode":
            obj = ModuleDefinition.objects.get(pk=node_pk)
            comment.reference_type = "module_definition"
            comment.module_definition = obj
        elif node_type == "StintDefinitionNode":
            obj = StintDefinition.objects.get(pk=node_pk)
            comment.reference_type = "stint_definition"
            comment.stint_definition = obj
        elif node_type == "TemplateNode":
            obj = Template.objects.get(pk=node_pk)
            comment.reference_type = "template"
            comment.template = obj
        elif node_type == "WidgetNode":
            comment.reference_type = "widget"
            obj = Widget.objects.get(pk=node_pk)
            comment.widget = obj
        else:
            raise ValueError(f"Invalid node type: {node_type}")

        if not has_privilege(obj, user, "comment"):
            raise ValueError("not authorized")

        comment.save()
        comment_edge = FileCommentNode._meta.connection.Edge(comment)

        return CreateFileComment(user_comment_edge=comment_edge)


class UpdateFileComment(EryMutationMixin, relay.ClientIDMutation):
    user_comment = graphene.Field(FileCommentNode, required=True)

    class Input(FileCommentMutationInput):
        id = graphene.ID(required=True, description="GQL ID of the FileComment")
        comment = graphene.String(description="Updated comment text")

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        user = authenticated_user(info.context)

        user_comment_id = cls.gql_id_to_pk(inputs.pop("id"))
        user_comment = FileComment.objects.get(pk=user_comment_id)

        if not has_privilege(user_comment, user, "update"):
            raise ValueError("not authorized")

        cls.add_all_attributes(user_comment, inputs)
        user_comment.save()
        return UpdateFileComment(user_comment=user_comment)


class DeleteFileComment(EryMutationMixin, relay.ClientIDMutation):
    success = graphene.Boolean(required=True)

    class Input:
        id = graphene.ID(required=True, description="GQL ID of the FileComment")

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        user = authenticated_user(info.context)

        user_comment_id = cls.gql_id_to_pk(inputs.pop("id"))
        user_comment = FileComment.objects.get(pk=user_comment_id)

        if not has_privilege(user_comment, user, "delete"):
            raise ValueError("not authorized")

        user_comment.delete()
        return DeleteFileComment(success=True)


class CreateFileStar(EryMutationMixin, relay.ClientIDMutation):
    file_star = graphene.Field(FileStarNode, required=True)

    class Input(FileStarMutationInput):
        on = graphene.ID(required=True, description="GQL id of the object to be starred")

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        user = authenticated_user(info.context)

        global_id = inputs.pop("on")

        try:
            node_type, node_pk = from_global_id(global_id)
        except:
            raise ValueError('Invalid GQL ID in request: {on: >"%s"<}' % global_id)

        star = FileStar(user=user)

        if node_type == "ImageAssetNode":
            obj = ImageAsset.objects.get(pk=node_pk)
            star.reference_type = "image_asset"
            star.image_asset = obj
        elif node_type == "ProcedureNode":
            obj = Procedure.objects.get(pk=node_pk)
            star.reference_type = "procedure"
            star.procedure = obj
        elif node_type == "ModuleDefinitionNode":
            obj = ModuleDefinition.objects.get(pk=node_pk)
            star.reference_type = "module_definition"
            star.module_definition = obj
        elif node_type == "StintDefinitionNode":
            obj = StintDefinition.objects.get(pk=node_pk)
            star.reference_type = "stint_definition"
            star.stint_definition = obj
        elif node_type == "TemplateNode":
            obj = Template.objects.get(pk=node_pk)
            star.reference_type = "template"
            star.template = obj
        elif node_type == "WidgetNode":
            obj = Widget.objects.get(pk=node_pk)
            star.reference_type = "widget"
            star.widget = obj
        else:
            raise ValueError(f"Invalid node type: {node_type}")

        if not has_privilege(obj, user, "star"):
            raise ValueError("not authorized")

        star.save()

        return CreateFileStar(file_star=star)


class DeleteFileStar(EryMutationMixin, relay.ClientIDMutation):
    success = graphene.Boolean(required=True)

    class Input:
        id = graphene.ID(required=True, description="GQL ID of the FileStar")

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        user = authenticated_user(info.context)

        star_id = cls.gql_id_to_pk(inputs.pop("id"))
        star = FileStar.objects.get(pk=star_id)

        if not has_privilege(star, user, "delete"):
            raise ValueError("not authorized")

        star.delete()
        return DeleteFileStar(success=True)
