import graphene

from ery_backend.base.schema import PrivilegedNodeMixin
from ery_backend.base.schema_utils import EryObjectType

from .models import Hand


class HandNode(PrivilegedNodeMixin, EryObjectType):
    class Meta:
        model = Hand

    # Used to access the property name
    name = graphene.String()


HandQuery = HandNode.get_query_class()
