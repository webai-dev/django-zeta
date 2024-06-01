import graphene
from graphene import relay

from ery_backend.base.schema import EryMutationMixin
from ery_backend.roles.utils import grant_ownership, has_privilege
from ery_backend.users.utils import authenticated_user

from .models import Folder, Link
from .schema import FolderEdge, FolderNode, LinkEdge, LinkNode


class InputFolder:
    name = graphene.String()
    comment = graphene.String()


class CreateFolder(EryMutationMixin, relay.ClientIDMutation):
    folder_edge = graphene.Field(FolderEdge)
    link_edge = graphene.Field(LinkEdge)

    class Input(InputFolder):
        parent_folder = graphene.ID(required=True)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        user = authenticated_user(info.context)
        parent_folder = Folder.objects.get(pk=cls.gql_id_to_pk(inputs.pop("parent_folder")))
        folder = Folder()
        cls.add_all_attributes(folder, inputs)
        folder.save()
        link = Link.objects.create(
            parent_folder=parent_folder, folder=folder, reference_type=Link.FILE_AND_FOLDER_CHOICES.folder
        )

        grant_ownership(folder, user=user)

        link_edge = LinkEdge(node=link) if link else None

        folder_edge = FolderEdge(node=folder)

        return CreateFolder(folder_edge=folder_edge, link_edge=link_edge)


UpdateFolder = FolderNode.get_update_mutation_class(InputFolder)


class DuplicateFolder(EryMutationMixin, relay.ClientIDMutation):
    folder_edge = graphene.Field(FolderEdge)

    class Input(InputFolder):
        id = graphene.ID(description="GQL ID of the Folder", required=True)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        user = authenticated_user(info.context)
        folder_id = cls.gql_id_to_pk(inputs.pop("id"))
        folder = Folder.objects.get(pk=folder_id)

        if folder is None:
            raise ValueError("folder not found")

        if not has_privilege(folder, user, "read"):
            raise ValueError("not authorized")

        folder.id = None
        folder.save()

        folder_edge = FolderEdge(node=folder)

        return DuplicateFolder(folder_edge=folder_edge)


DeleteFolder = FolderNode.get_delete_mutation_class(InputFolder)


class DuplicateLink(EryMutationMixin, relay.ClientIDMutation):
    link_edge = graphene.Field(LinkEdge)

    class Input:
        id = graphene.ID(description="GQL ID of the Link", required=True)
        parent_folder = graphene.ID()
        folder = graphene.ID()
        stint_definition = graphene.ID()
        module_definition = graphene.ID()
        procedure = graphene.ID()
        image_asset = graphene.ID()
        widget = graphene.ID()
        template = graphene.ID()
        theme = graphene.ID()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        user = authenticated_user(info.context)
        link_id = cls.gql_id_to_pk(inputs.pop("id"))
        link = Link.objects.get(pk=link_id)

        if link is None:
            raise ValueError("link not found")

        if not has_privilege(link, user, "read"):
            raise ValueError("not authorized")

        field, obj = link.get_referenced_field_and_obj()
        new_obj = obj.duplicate(name=f"{obj.name}_copy")
        setattr(link, field, new_obj)

        link.id = None
        link.save()

        link_edge = LinkEdge(node=link)

        return DuplicateLink(link_edge=link_edge)


BaseLinkMutation = LinkNode.get_mutation_class()
