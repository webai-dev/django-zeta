from languages_plus.models import Language
from rest_framework import serializers

from ery_backend.frontends.models import Frontend

from .models import Template, TemplateBlockTranslation


BaseTemplateBlockTranslationBXMLSerializer = TemplateBlockTranslation.create_bxml_serializer()


class TemplateBlockTranslationBXMLSerializer(BaseTemplateBlockTranslationBXMLSerializer):
    language = serializers.SlugRelatedField(
        slug_field='iso_639_1', required=True, allow_null=False, queryset=Language.objects.get_queryset()
    )

    def to_internal_value(self, data):
        # Content may contain JSX tags
        original_content = data.get('content')
        if original_content:
            data['content'] = str(original_content)
        return super().to_internal_value(data)


BaseTemplateBXMLSerializer = Template.create_bxml_serializer()


class TemplateBXMLSerializer(BaseTemplateBXMLSerializer):
    primary_language = serializers.SlugRelatedField(
        slug_field='iso_639_1', required=True, allow_null=False, queryset=Language.objects.get_queryset()
    )
    frontend = serializers.SlugRelatedField(
        slug_field='name', required=True, allow_null=False, queryset=Frontend.objects.get_queryset()
    )
