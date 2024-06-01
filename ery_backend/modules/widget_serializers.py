from languages_plus.models import Language
from rest_framework import serializers

from ery_backend.widgets.models import Widget

# pylint:disable=unused-import
from .models import ModuleDefinitionWidget, WidgetChoice, ModuleEvent, ModuleEventStep, WidgetChoiceTranslation


BaseWidgetChoiceTranslationBXMLSerializer = WidgetChoiceTranslation.create_bxml_serializer()


class WidgetChoiceTranslationBXMLSerializer(BaseWidgetChoiceTranslationBXMLSerializer):
    language = serializers.SlugRelatedField(
        slug_field='iso_639_1', required=True, allow_null=False, queryset=Language.objects.get_queryset()
    )

    def to_internal_value(self, data):
        # Content may contain JSX tags
        original_caption = data.get('caption')
        if original_caption:
            data['caption'] = str(original_caption)
        return super().to_internal_value(data)


class ModuleEventSerializerOverloads(serializers.ModelSerializer):
    # rest-framework-xml exports name as null field when it is actually a blank string
    name = serializers.CharField(required=True, allow_null=True, allow_blank=True)


BaseModuleEventBXMLSerializer = ModuleEvent.create_bxml_serializer()


class ModuleEventBXMLSerializer(ModuleEventSerializerOverloads, BaseModuleEventBXMLSerializer):
    pass


BaseModuleEventDuplicationSerializer = ModuleEvent.create_duplication_serializer()


class ModuleEventDuplicationSerializer(ModuleEventSerializerOverloads, BaseModuleEventDuplicationSerializer):
    pass


BaseModuleDefinitionWidgetBXMLSerializer = ModuleDefinitionWidget.create_bxml_serializer()
# XXX: Question
# XXX: Due to default
class ModuleDefinitionWidgetBXMLSerializer(BaseModuleDefinitionWidgetBXMLSerializer):
    widget = serializers.SlugRelatedField(
        slug_field='slug', queryset=Widget.objects.get_queryset(), required=True, allow_null=False
    )


BaseModuleDefinitionWidgetDuplicationSerializer = ModuleDefinitionWidget.create_duplication_serializer()


class ModuleDefinitionWidgetDuplicationSerializer(BaseModuleDefinitionWidgetDuplicationSerializer):
    widget = serializers.PrimaryKeyRelatedField(queryset=Widget.objects.get_queryset(), required=True, allow_null=False)


BaseModuleDefinitionWidgetMutationSerializer = ModuleDefinitionWidget.create_mutation_serializer()


class ModuleDefinitionWidgetMutationSerializer(BaseModuleDefinitionWidgetMutationSerializer):
    widget = serializers.PrimaryKeyRelatedField(queryset=Widget.objects.get_queryset(), required=True, allow_null=False)
