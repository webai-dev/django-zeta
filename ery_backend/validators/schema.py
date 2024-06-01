from graphene import relay

from ery_backend.base.schema import VersionMixin
from ery_backend.base.schema_utils import EryObjectType, EryFilterConnectionField
from ery_backend.folders.schema import FileNodeMixin

from .models import Validator


class ValidatorNode(FileNodeMixin, VersionMixin, EryObjectType):
    class Meta:
        model = Validator


class ValidatorQuery:
    validator = relay.Node.Field(ValidatorNode)
    all_validators = EryFilterConnectionField(ValidatorNode)
