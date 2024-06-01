import graphene

from ery_backend.base.schema_utils import EryObjectType
from ery_backend.folders.schema import FileNodeMixin

from .models import ImageAsset, DatasetAsset


class ImageAssetNode(FileNodeMixin, EryObjectType):
    class Meta:
        model = ImageAsset

    url = graphene.Field(graphene.String)

    def resolve_url(self, info):
        return f'assets/{self.gql_id}'


ImageAssetNodeEdge = ImageAssetNode._meta.connection.Edge
ImageAssetQuery = ImageAssetNode.get_query_class()


class DatasetAssetNode(EryObjectType):
    class Meta:
        model = DatasetAsset

    url = graphene.Field(graphene.String)

    def resolve_url(self, info):
        return f'assets/{self.gql_id}'


DatasetAssetQuery = DatasetAssetNode.get_query_class()
