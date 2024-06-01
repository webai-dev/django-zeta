from languages_plus.models import Language
from rest_framework import serializers

from ery_backend.base.serializers import FileDependentSlugRelatedField
from ery_backend.frontends.models import Frontend
from ery_backend.keywords.models import Keyword
from ery_backend.stages.models import StageDefinition
from ery_backend.syncs.models import Era
from ery_backend.templates.models import Template
from ery_backend.themes.models import Theme
from .models import ModuleDefinition

# pylint:disable=unused-import
from .widget_serializers import (
    WidgetChoiceTranslationBXMLSerializer,
    ModuleDefinitionWidgetBXMLSerializer,
    ModuleDefinitionWidgetDuplicationSerializer,
    ModuleDefinitionWidgetMutationSerializer,
)


class ModuleDefinitionSerializerOverloads(serializers.ModelSerializer):
    start_era = FileDependentSlugRelatedField(
        slug_field='name', required=False, allow_null=True, queryset=Era.objects.get_queryset(), file_name='module_definition'
    )
    start_stage = FileDependentSlugRelatedField(
        slug_field='name',
        required=False,
        allow_null=True,
        queryset=StageDefinition.objects.get_queryset(),
        file_name='module_definition',
    )
    warden_stage = FileDependentSlugRelatedField(
        slug_field='name',
        required=False,
        allow_null=True,
        queryset=StageDefinition.objects.get_queryset(),
        file_name='module_definition',
    )
    primary_frontend = serializers.PrimaryKeyRelatedField(
        required=True, allow_null=False, queryset=Frontend.objects.get_queryset()
    )
    primary_language = serializers.PrimaryKeyRelatedField(
        required=True, allow_null=False, queryset=Language.objects.get_queryset()
    )
    default_template = serializers.PrimaryKeyRelatedField(
        required=True, allow_null=False, queryset=Template.objects.get_queryset()
    )
    default_theme = serializers.PrimaryKeyRelatedField(required=True, allow_null=False, queryset=Theme.objects.get_queryset())

    @staticmethod
    def _remove_defaults(data_set, defaults, attribute):
        delete_positions = list()
        counter = 0
        for data in data_set:
            target = data[attribute]
            if target in defaults:
                delete_positions.append(counter)
            counter += 1
        delete_positions.sort(reverse=True)
        for position in delete_positions:
            del data_set[position]
        return data_set

    @classmethod
    def _remove_default_actions(cls, actionset_data):
        """
        Removes default action information from serialized action_set.
        """
        if not cls.set_empty(actionset_data):
            try:
                actionset_data = cls._remove_defaults(
                    actionset_data, ['Default-Command-Next', 'Default-Command-Back', 'Default-Command-Quit'], 'name'
                )
            except KeyError:
                pass
        return actionset_data

    # XXX: Centralize these names
    @classmethod
    def _remove_default_commands(cls, commandset_data):
        """
        Removes default command information from serialized command_set.
        """
        if not cls.set_empty(commandset_data):
            try:
                commandset_data = cls._remove_defaults(commandset_data, ['next', 'back', 'quit', 'help'], 'name')
            except KeyError:
                pass
        return commandset_data

    @classmethod
    def _remove_start_era(cls, module_name, era_set):
        """
        Removes start era information from serialized era_set.
        """
        name = f'{module_name}-start'
        if not cls.set_empty(era_set):
            remove_data = None
            for era_data in era_set:
                if era_data['name'] == name:
                    remove_data = era_data
            if remove_data:
                print("REMOVING START ERA", name)
                era_set.remove(remove_data)
        return era_set

    def to_internal_value(self, data):
        """
        Direct conversion of serialized data to django instance. Collect errors to be reported together.

        Notes:
        - Overloads :py:meth:`rest_framework.serializers.BaseSerializer.to_internal_value`.

        Returns:
            :class:`~ery_backend.base.models.EryModel`
        """
        # Data may be invalid
        action_data = data.get('action_set')
        if action_data:
            self._remove_default_actions(action_data)

        command_data = data.get('command_set')
        if command_data:
            self._remove_default_commands(command_data)

        # XXX: Address in issue #817
        # era_data = data.get('era_set')
        # if era_data:
        #     self._remove_start_era(data.get('name'), era_data)
        return super().to_internal_value(data)


BaseModuleDefinitionBXMLSerializer = ModuleDefinition.create_bxml_serializer()


class ModuleDefinitionBXMLSerializer(ModuleDefinitionSerializerOverloads, BaseModuleDefinitionBXMLSerializer):
    primary_frontend = serializers.SlugRelatedField(
        slug_field='name', required=True, allow_null=False, queryset=Frontend.objects.get_queryset()
    )
    primary_language = serializers.SlugRelatedField(
        slug_field='iso_639_1', required=True, allow_null=False, queryset=Language.objects.get_queryset()
    )
    keywords = serializers.SlugRelatedField(
        slug_field='name', required=False, allow_null=True, queryset=Keyword.objects.get_queryset(), many=True
    )
    default_template = serializers.SlugRelatedField(
        slug_field='slug', required=True, allow_null=False, queryset=Template.objects.get_queryset()
    )
    default_theme = serializers.SlugRelatedField(
        slug_field='slug', required=True, allow_null=False, queryset=Theme.objects.get_queryset()
    )


BaseModuleDefinitionDuplicationSerializer = ModuleDefinition.create_duplication_serializer()


class ModuleDefinitionDuplicationSerializer(ModuleDefinitionSerializerOverloads, BaseModuleDefinitionDuplicationSerializer):
    pass


BaseModuleDefinitionMutationSerializer = ModuleDefinition.create_mutation_serializer()


class ModuleDefinitionMutationSerializer(ModuleDefinitionSerializerOverloads, BaseModuleDefinitionMutationSerializer):
    pass


# XXX: Address in #817
# class ModuleDefinitionSerializer(ErySerializer):
#     class Meta:
#         model = ModuleDefinition
#         exclude = ('id', 'created', 'modified', 'slug')

#     @staticmethod
#     def _remove_defaults(data_set, defaults, attribute):
#         delete_positions = list()
#         counter = 0
#         for data in data_set:
#             target = data[attribute]
#             if target in defaults:
#                 delete_positions.append(counter)
#             counter += 1
#         delete_positions.sort(reverse=True)
#         for position in delete_positions:
#             del data_set[position]
#         return data_set

#     @classmethod
#     def _remove_default_actions(cls, actionset_data):
#         """
#         Removes default action information from serialized action_set.
#         """
#         if not cls.set_empty(actionset_data):
#             actionset_data = cls._remove_defaults(actionset_data, ['Default-Command-Next', 'Default-Command-Back',
#                                                                    'Default-Command-Quit'], 'name')
#         return actionset_data

#     @classmethod
#     def _remove_default_conditions(cls, conditionset_data):
#         """
#         Removes default condition information from serialized condition_set.
#         """
#         if not cls.set_empty(conditionset_data):
#             conditionset_data = cls._remove_defaults(conditionset_data, ['unnecessary_action_condition'], 'name')
#         return conditionset_data

#     @classmethod
#     def _remove_default_commands(cls, data_set):
#         """
#         Removes default command information from serialized command_set.
#         """
#         if not cls.set_empty(data_set['command_set']['data']):
#             commandset_data = cls._remove_defaults(data_set['command_set']['data'], ['next', 'back', 'help', 'quit'], 'name')
#             data_set['command_set']['data'] = commandset_data
#         return data_set

#     @classmethod
#     def _remove_start_era(cls, module, data_set):
#         """
#         Removes start era information from serialized era_set.
#         """
#         name = f'{module.name}-start'
#         era_set = data_set['era_set']['data']
#         if not cls.set_empty(era_set):
#             remove_data = None
#             for era_data in era_set:
#                 if era_data['name'] == name:
#                     remove_data = era_data
#             data_set['era_set']['data'] = [era_data for era_data in era_set if era_data != remove_data]
#         return data_set
