import json
from countries_plus.models import Country
from languages_plus.models import Language
from rest_framework import serializers

from ery_backend.frontends.models import Frontend

from .models import StintSpecificationVariable, StintSpecificationCountry, StintSpecificationAllowedLanguageFrontend


BaseStintSpecificationCountryBXMLSerializer = StintSpecificationCountry.create_bxml_serializer()


class StintSpecificationCountryBXMLSerializer(BaseStintSpecificationCountryBXMLSerializer):
    country = serializers.SlugRelatedField(many=False, slug_field='iso', queryset=Country.objects.get_queryset())


BaseStintSpecificationAllowedLanguageFrontendBXMLSerializer = (
    StintSpecificationAllowedLanguageFrontend.create_bxml_serializer()
)


class StintSpecificationAllowedLanguageFrontendBXMLSerializer(BaseStintSpecificationAllowedLanguageFrontendBXMLSerializer):
    language = serializers.SlugRelatedField(
        required=True, allow_null=False, slug_field='iso_639_1', queryset=Language.objects.get_queryset()
    )
    frontend = serializers.SlugRelatedField(
        required=True, allow_null=False, slug_field='name', queryset=Frontend.objects.get_queryset()
    )


BaseStintSpecificationVariableSerializer = StintSpecificationVariable.create_bxml_serializer()


class StintSpecificationVariableBXMLSerializer(BaseStintSpecificationVariableSerializer):
    def save(self, queue=None, **kwargs):
        # default_value validated before choices are created
        original_default_value = self.initial_data['default_value'] if 'default_value' in self.initial_data else None
        self.initial_data['default_value'] = None
        obj, _, _ = super().save(queue)
        if obj:  # Save may fail and be queued
            if original_default_value is not None:
                obj.default_value = json.loads(str(original_default_value))
                obj.save()
        # XXX: This shouldn't be so complicated
        return obj, [], []


# XXX: Address in #812
# class StintSpecificationRobotSerializer(ErySerializer):
#     class Meta:
#         model = StintSpecificationRobot
#         exclude = ('id', 'created', 'modified')

#     stint_specification = serializers.PrimaryKeyRelatedField(
#         many=False,
#         write_only=True,
#         queryset=StintSpecification.objects.get_queryset()
#     )
#     robot = serializers.SlugRelatedField(many=False, read_only=True, slug_field='name')


# XXX: Address in #812
# class StintSpecificationVariableSerializer(ErySerializer):
#     class Meta:
#         model = StintSpecificationVariable
#         exclude = ('id', 'created', 'modified')

#     IGNORE = ('variable_definition',)

#     stint_specification = serializers.PrimaryKeyRelatedField(
#         many=False,
#         write_only=True,
#         queryset=StintSpecification.objects.get_queryset()
#     )
#     variable_definition = serializers.SlugRelatedField(
#         many=False,
#         slug_field='name',
#         queryset=VariableDefinition.objects.get_queryset()
#     )
#     value = serializers.SerializerMethodField()

#     def get_value(self, obj):
#         if obj.variable_definition.data_type == obj.variable_definition.DATA_TYPE_CHOICES.dict:
#             return json.dumps(obj.value)
#         return obj.value

#     @classmethod
#     def _get_variable_definition(cls, parent, name):
#         stint_definition = parent.stint_definition
#         module_definitions = [sdmd.module_definition for sdmd in \
#                               stint_definition.stint_definition_module_definitions.select_related('module_definition').all()]
#         for module_definition in module_definitions:
#             variable_definition = module_definition.variabledefinition_set.filter(name=name).first()
#             if variable_definition:
#                 return variable_definition
#         return None

#     def nested_create(self, data):
#         """
#         Returns deserialized instance derived from data dictionary.

#         Args:
#             data (Dict): Deserialized to instantiate model instance.

#         Raises:
#             EryDeserializationError: Triggered if any exception occurs during deserialization. Adds information on the
#               ancestor of the class that triggered said error, allowing for back tracing during nested nested_creates.
#         """
#         # gets all child dependencies needed for initial creation
#         variable_definition_name = data['variable_definition']
#         stint_specification = data['stint_specification']
#         variable_definition = self._get_variable_definition(stint_specification, variable_definition_name)
#         model = self.Meta.model
#         try:
#             parent = model.objects.create(variable_definition=variable_definition, stint_specification=stint_specification)
#         # generalized exception is specified in handle_deserialization_exceptions
#         # pylint:disable=broad-except
#         except Exception as exc:
#             self.handle_deserialization_exceptions(data, exc)
#         return parent
