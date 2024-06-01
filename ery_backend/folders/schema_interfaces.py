import graphene

from ery_backend.base.schema_interfaces import EryNamedSluggedInterface
from ery_backend.base.schema_utils import EryFilterConnectionField


class EryFileInterface(EryNamedSluggedInterface):
    published = graphene.Boolean()
    state = graphene.String()
    role_assignments = EryFilterConnectionField('ery_backend.roles.schema.RoleAssignmentNode')
    links = EryFilterConnectionField('ery_backend.folders.schema.LinkNode')
    comments = EryFilterConnectionField('ery_backend.comments.schema.FileCommentNode')
    stars = EryFilterConnectionField('ery_backend.comments.schema.FileStarNode')
    keywords = EryFilterConnectionField('ery_backend.keywords.schema.KeywordNode')
    touches = EryFilterConnectionField('ery_backend.users.schema.FileTouchNode')
