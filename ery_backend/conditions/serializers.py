from rest_framework import serializers

from .models import Condition


class ConditionSerializerOverloads(serializers.ModelSerializer):
    operator = serializers.CharField(required=False, allow_null=True, default=None)
    relation = serializers.CharField(required=False, allow_null=True, default=None)


BaseConditionBXMLSerializer = Condition.create_bxml_serializer()


class ConditionBXMLSerializer(ConditionSerializerOverloads, BaseConditionBXMLSerializer):
    pass


BaseConditionDuplicationSerializer = Condition.create_duplication_serializer()


class ConditionDuplicationSerializer(ConditionSerializerOverloads, BaseConditionDuplicationSerializer):
    pass
