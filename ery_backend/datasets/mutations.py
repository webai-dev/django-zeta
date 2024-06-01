from graphene import relay
import graphene
from graphql_relay.node.node import from_global_id

from ery_backend.base.schema import EryMutationMixin
from ery_backend.folders.models import Folder
from ery_backend.roles.utils import grant_ownership
from ery_backend.users.utils import authenticated_user

from .models import Dataset
from .schema import DatasetNode


class UploadDataset(EryMutationMixin, relay.ClientIDMutation):
    dataset_edge = graphene.Field(DatasetNode._meta.connection.Edge)
    success = graphene.Boolean()

    class Input:
        folder = graphene.ID(required=False)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        user = authenticated_user(info.context)

        # only process if exactly one file attached
        if len(info.context.FILES) == 1:
            name, f = next(info.context.FILES.items())
            dataset = Dataset.objects.create_dataset_from_file(name=name, file_data=f.read())
            dataset_edge = DatasetNode._meta.connection.Edge(node=dataset)
            grant_ownership(dataset, user)

            if 'folder' in inputs:
                _, folder_id = from_global_id(inputs['folder'])
                dataset.create_link(Folder.objects.get(pk=folder_id))

            return UploadDataset(success=True, dataset_edge=dataset_edge)
        return UploadDataset(success=False)
