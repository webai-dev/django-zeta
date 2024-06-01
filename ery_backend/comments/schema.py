from graphene import relay

from ery_backend.base.schema import PrivilegedNodeMixin
from ery_backend.base.schema_utils import EryObjectType

from .models import FileStar, FileComment


# XXX: Address in issue #578
class FileCommentNode(PrivilegedNodeMixin, EryObjectType):
    class Meta:
        model = FileComment
        filter_privilege = False


class FileCommentQuery:
    file_comment = relay.Node.Field(FileCommentNode)


class FileStarNode(PrivilegedNodeMixin, EryObjectType):
    class Meta:
        model = FileStar


FileStarQuery = FileStarNode.get_query_class()
