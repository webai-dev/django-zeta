from languages_plus.models import Language
from rest_framework import serializers

from ery_backend.frontends.models import Frontend
from .models import StageTemplateBlockTranslation


class StageTemplateBlockTranslationSerializerOverloads(serializers.ModelSerializer):
    language = serializers.SlugRelatedField(
        slug_field='iso_639_1', required=True, allow_null=False, queryset=Language.objects.get_queryset()
    )
    frontend = serializers.SlugRelatedField(
        slug_field='name', required=True, allow_null=False, queryset=Frontend.objects.get_queryset()
    )


BaseStageTemplateBlockTranslationBXMLSerializer = StageTemplateBlockTranslation.create_bxml_serializer()


class StageTemplateBlockTranslationBXMLSerializer(
    StageTemplateBlockTranslationSerializerOverloads, BaseStageTemplateBlockTranslationBXMLSerializer
):
    def to_internal_value(self, data):
        # Content may contain JSX tags
        original_content = data.get('content')
        if original_content:
            data['content'] = str(original_content)
        return super().to_internal_value(data)


BaseStageTemplateBlockTranslationDuplicationSerializer = StageTemplateBlockTranslation.create_duplication_serializer()


class StageTemplateBlockTranslationDuplicationSerializer(
    StageTemplateBlockTranslationSerializerOverloads, BaseStageTemplateBlockTranslationDuplicationSerializer
):
    pass


BaseStageTemplateBlockTranslationMutationSerializer = StageTemplateBlockTranslation.create_mutation_serializer()


class StageTemplateBlockTranslationMutationSerializer(
    StageTemplateBlockTranslationSerializerOverloads, BaseStageTemplateBlockTranslationMutationSerializer
):
    pass
