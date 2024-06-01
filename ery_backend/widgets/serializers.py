from rest_framework import serializers

from ery_backend.widgets.models import WidgetEvent

BaseWidgetEventBXMLSerializer = WidgetEvent.create_bxml_serializer()
BaseWidgetEventDuplicationSerializer = WidgetEvent.create_bxml_serializer()


class WidgetEventSerializerOverloads(serializers.ModelSerializer):
    name = serializers.CharField(required=True, allow_null=True, allow_blank=True)


class WidgetEventBXMLSerializer(WidgetEventSerializerOverloads, BaseWidgetEventBXMLSerializer):
    pass


class WidgetEventDuplicationSerializer(WidgetEventSerializerOverloads, BaseWidgetEventDuplicationSerializer):
    pass
