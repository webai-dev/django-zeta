import graphene


class EryInterface(graphene.Interface):
    id = graphene.GlobalID()
    created = graphene.DateTime()
    modified = graphene.DateTime()


class EryNamedInterface(EryInterface):
    name = graphene.String(required=True)
    comment = graphene.String()


class EryNamedSluggedInterface(EryNamedInterface):
    slug = graphene.String(required=True)
