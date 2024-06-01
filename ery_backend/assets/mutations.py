from graphene import relay
import graphene

from ery_backend.base.schema import EryMutationMixin
from ery_backend.roles.utils import grant_ownership
from ery_backend.users.utils import authenticated_user

from .models import ImageAsset
from .schema import ImageAssetNodeEdge


class UploadImageAsset(EryMutationMixin, relay.ClientIDMutation):
    image_asset_edge = graphene.Field(ImageAssetNodeEdge)

    class Input:
        pass

    success = graphene.Boolean()
    image_asset_url = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        user = authenticated_user(info.context)

        files = info.context.FILES
        if files:
            image_file = files['file']
            image_asset = ImageAsset.objects.create_file(image_file.read())
            image_asset_edge = ImageAssetNodeEdge(node=image_asset)
            url = f'assets/{image_asset.gql_id}'
            grant_ownership(image_asset, user)

        return UploadImageAsset(success=True, image_asset_url=url, image_asset_edge=image_asset_edge)
