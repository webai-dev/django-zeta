from ery_backend.base.schema import PrivilegedNodeMixin, VersionMixin
from ery_backend.base.schema_utils import EryObjectType

from .models import Command, CommandTemplate, CommandTemplateBlock, CommandTemplateBlockTranslation


class CommandNode(PrivilegedNodeMixin, VersionMixin, EryObjectType):
    class Meta:
        model = Command


CommandQuery = CommandNode.get_query_class()


class CommandTemplateNode(PrivilegedNodeMixin, VersionMixin, EryObjectType):
    class Meta:
        model = CommandTemplate


CommandTemplateQuery = CommandTemplateNode.get_query_class()


class CommandTemplateBlockNode(PrivilegedNodeMixin, VersionMixin, EryObjectType):
    class Meta:
        model = CommandTemplateBlock


CommandTemplateBlockQuery = CommandTemplateBlockNode.get_query_class()


class CommandTemplateBlockTranslationNode(PrivilegedNodeMixin, VersionMixin, EryObjectType):
    class Meta:
        model = CommandTemplateBlockTranslation


CommandTemplateBlockTranslationQuery = CommandTemplateBlockTranslationNode.get_query_class()
