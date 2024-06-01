from languages_plus.models import Language
from rest_framework import serializers

from ery_backend.frontends.models import Frontend

from .models import CommandTemplateBlockTranslation


class CommandTemplateBlockTranslationSerializerOverloads(serializers.ModelSerializer):
    language = serializers.SlugRelatedField(
        required=True, allow_null=False, queryset=Language.objects.get_queryset(), slug_field='iso_639_1'
    )
    frontend = serializers.SlugRelatedField(
        required=True, allow_null=False, queryset=Frontend.objects.get_queryset(), slug_field='name'
    )


BaseCommandTemplateBlockTranslationBXMLSerializer = CommandTemplateBlockTranslation.create_bxml_serializer()


class CommandTemplateBlockTranslationBXMLSerializer(
    CommandTemplateBlockTranslationSerializerOverloads, BaseCommandTemplateBlockTranslationBXMLSerializer
):
    pass


class CommandTemplateBlockTranslationIDSerializer(
    CommandTemplateBlockTranslationSerializerOverloads, BaseCommandTemplateBlockTranslationBXMLSerializer
):
    pass
