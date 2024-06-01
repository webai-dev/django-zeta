from rest_framework import serializers

from ery_backend.keywords.models import Keyword
from .models import StintDefinition


BaseStintDefinitionBXMLSerializer = StintDefinition.create_bxml_serializer()


class StintDefinitionBXMLSerializer(BaseStintDefinitionBXMLSerializer):
    keywords = serializers.SlugRelatedField(
        slug_field='name', many=True, required=False, allow_null=True, queryset=Keyword.objects.get_queryset()
    )


# XXX: Address in issue #820
# class SimpleStintDefinitionSerializer(ErySerializer):
#     """
#     Note: The "Simple" in name refers to serialization flow in which the children of the serialized
#         class are recorded via reference (i.e., slug), instead of with a nested serializer
#     """
#     class Meta:
#         model = StintDefinition
#         fields = ('stint_definition_module_definitions', 'name', 'comment')

#     ATTRIBUTE_MAP = {'stint_definition_module_definitions': {
#         'many': True,
#         'model_cls': StintDefinitionModuleDefinition,
#         'simple_serialization': True
#     }}
#     INSTRUCTION_KWARGS = {
#         'stint_definition_module_definitions': {'instruction': 'create', 'replace_kwargs': {'stint_definition': '..'}}
#     }
#     stint_definition_module_definitions = SimpleStintDefinitionModuleDefinitionSerializer(many=True, allow_null=True)
