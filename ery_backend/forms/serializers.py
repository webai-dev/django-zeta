from languages_plus.models import Language
from rest_framework import serializers

from ery_backend.forms.models import FormFieldChoiceTranslation


BaseFormFieldChoiceTranslationBXMLSerializer = FormFieldChoiceTranslation.create_bxml_serializer()


class FormFieldChoiceTranslationBXMLSerializer(BaseFormFieldChoiceTranslationBXMLSerializer):
    language = serializers.SlugRelatedField(
        slug_field='iso_639_1', required=True, allow_null=False, queryset=Language.objects.get_queryset()
    )

    def to_internal_value(self, data):
        # Content may contain JSX tags
        original_caption = data.get('caption')
        if original_caption:
            data['caption'] = str(original_caption)
        return super().to_internal_value(data)
