import json

from django.core.exceptions import ValidationError
from languages_plus.models import Language
from rest_framework import serializers

from .models import VariableDefinition, VariableChoiceItemTranslation


class VariableChoiceItemTranslationSerializerOverloads(serializers.ModelSerializer):
    language = serializers.SlugRelatedField(
        slug_field='iso_639_1', required=True, allow_null=False, queryset=Language.objects.get_queryset()
    )


BaseVariableChoiceItemTranslationBXMLSerializer = VariableChoiceItemTranslation.create_bxml_serializer()


class VariableChoiceItemTranslationBXMLSerializer(
    VariableChoiceItemTranslationSerializerOverloads, BaseVariableChoiceItemTranslationBXMLSerializer
):
    pass


BaseVariableChoiceItemTranslationDuplicationSerializer = VariableChoiceItemTranslation.create_duplication_serializer()


class VariableChoiceItemTranslationDuplicationSerializer(
    VariableChoiceItemTranslationSerializerOverloads, BaseVariableChoiceItemTranslationDuplicationSerializer
):
    pass


class VariableDefinitionSerializerOverloads:
    @staticmethod
    def get_default_value(obj):
        return json.dumps(obj.default_value)

    def save(self, **kwargs):
        # default_value validated before choices are created
        original_default_value = self.initial_data['default_value'] if 'default_value' in self.initial_data else None
        self.initial_data['default_value'] = None
        obj = super().save()
        if obj:  # Save may fail and be queued
            if original_default_value is not None:
                if self.initial_data['data_type'] in VariableDefinition.DATA_TYPE_CHOICES.bool:
                    obj.default_value = str(original_default_value).lower() in ['true', '1']
                else:
                    try:
                        obj.default_value = json.loads(str(original_default_value))
                    except json.decoder.JSONDecodeError as exc:
                        raise ValidationError({self.__class__.__name__: exc})
                obj.save()
        return obj


BaseVariableDefinitionDuplicationSerializer = VariableDefinition.create_duplication_serializer()


class VariableDefinitionDuplicationSerializer(
    VariableDefinitionSerializerOverloads, BaseVariableDefinitionDuplicationSerializer
):
    default_value = serializers.SerializerMethodField()


BaseVariableDefinitionBXMLSerializer = VariableDefinition.create_bxml_serializer()


class VariableDefinitionBXMLSerializer(VariableDefinitionSerializerOverloads, BaseVariableDefinitionBXMLSerializer):
    default_value = serializers.SerializerMethodField()
