from django.db import models
from django.core.exceptions import ValidationError

from languages_plus.models import Language

from ery_backend.base.mixins import JavascriptNamedMixin, ReactNamedMixin
from ery_backend.base.models import EryFile, EryNamedPrivileged
from ery_backend.base.utils import get_default_language
from ery_backend.stints.models import StintModel, StintDefinitionModuleDefinitionMixin

# pylint:disable=unused-import
from .widgets import ModuleDefinitionWidget, WidgetChoice, WidgetChoiceTranslation, ModuleEvent, ModuleEventStep


class ModuleDefinition(ReactNamedMixin, EryFile):
    """
    ModuleDefinitions describe how to instantiate Modules, which can be combined
    modularly to make a stint.
    """

    class SerializerMeta(EryFile.SerializerMeta):
        model_serializer_fields = (
            'action_set',
            'command_set',
            'condition_set',
            'era_set',
            'forms',
            'moduledefinitionprocedure_set',
            'module_widgets',
            'robots',
            'stage_definitions',
            'variabledefinition_set',
        )

    primary_frontend = models.ForeignKey(
        'frontends.Frontend', on_delete=models.PROTECT, help_text="Language for the primary implementation of the module."
    )
    primary_language = models.ForeignKey(
        Language,
        default=get_default_language(pk=True),
        on_delete=models.SET_DEFAULT,
        help_text="Language for the primary implementation of the module.",
    )
    # XXX: Issue 757: Actually should be a default template and default theme per Frontend
    default_template = models.ForeignKey(
        'templates.Template',
        on_delete=models.PROTECT,
        default=5,  # from fixtures/templates.json
        help_text='Template used for stage definitions not choosing an explicit template',
    )
    default_theme = models.ForeignKey(
        'themes.Theme',
        on_delete=models.PROTECT,
        default=8,  # DefaultTheme-GGGlqICG
        help_text='Theme used for stage definitions not choosing an explicit theme',
    )
    start_era = models.ForeignKey("syncs.Era", on_delete=models.SET_NULL, null=True, blank=True)
    start_stage = models.ForeignKey(
        "stages.StageDefinition", on_delete=models.SET_NULL, null=True, blank=True, related_name='stints_start_stage'
    )
    warden_stage = models.ForeignKey(
        "stages.StageDefinition", on_delete=models.SET_NULL, null=True, blank=True, related_name='stints_warden_stage'
    )
    mxgraph_xml = models.TextField(null=True, blank=True)
    min_team_size = models.PositiveIntegerField(default=0)
    max_team_size = models.PositiveIntegerField(default=0)
    version = models.PositiveIntegerField(default=0)

    @staticmethod
    def get_bxml_serializer():
        from .serializers import ModuleDefinitionBXMLSerializer

        return ModuleDefinitionBXMLSerializer

    @staticmethod
    def get_duplication_serializer():
        from .serializers import ModuleDefinitionDuplicationSerializer

        return ModuleDefinitionDuplicationSerializer

    @staticmethod
    def get_mutation_serializer():
        from .serializers import ModuleDefinitionMutationSerializer

        return ModuleDefinitionMutationSerializer

    def get_widgets(self, frontend=None):
        from ery_backend.widgets.models import Widget, WidgetConnection

        widget_ids = set(self.module_widgets.filter(widget__frontend=frontend).values_list('widget', flat=True))
        connected_widget_ids = set(self.module_widgets.values_list('widget__connections__target', flat=True))
        widget_ids.update(connected_widget_ids)
        for connected_widget_id in connected_widget_ids:
            widget_ids.update(Widget.get_nested_connected_widget_ids(connected_widget_id))
        return Widget.objects.filter(id__in=widget_ids)

    def _assign_start_era(self):
        from ..syncs.models import Era

        era_name = '{}-start'.format(self.name)
        self.start_era = Era.objects.get_or_create(
            module_definition=self, name=era_name, comment='Initial era for {}'.format(self.name)
        )[0]

    def clean(self):
        super().clean()
        if self.max_team_size < self.min_team_size:
            raise ValidationError(
                {
                    'max_team_size': "Can not set value of max_team_size, {}, to a value less than min_team_size, {}, \
                 for Stint Part: {}.".format(
                        self.max_team_size, self.min_team_size, self
                    )
                }
            )

    def touch(self):
        self.version += 1
        super().touch()

    def post_save_clean(self):
        """
        Reason for use: Starting era (child of self) cannot be created before self.
        """
        # XXX: Address in issue #817
        # if not self.start_era:
        #     self._assign_start_era()
        #     self.save()

    def has_stage(self, name):
        """
        Verifies whether child :class:`~ery_backend.stages.models.Stage` exists.

        Args:
            name (str): Used to search for :class:`~ery_bcakend.stages.models.Stage`.

        Returns:
            bool
        """
        return self.stage_definitions.filter(name=name).exists()

    def create_random_robot(self, name, comment=None):
        # import here to avoid circular dependency
        from ery_backend.robots.models import Robot, RobotRule

        robot = Robot.objects.create(name=name, comment=comment)
        for rule_module_definition_widget in self.module_definition_widgets.all():
            RobotRule.objects.create(
                module_definition_widget=rule_module_definition_widget, rule_type='random', static_value=None
            )
        return robot

    def _invalidate_related_tags(self, history):
        for stint_definition_module_definition in self.stint_definition_module_definitions.all():
            stint_definition_module_definition.invalidate_tags(history)


class ModuleDefinitionModelMixin(models.Model):
    """Adds ModuleDefinition as the parent model"""

    class Meta:
        abstract = True

    module_definition = models.ForeignKey(
        'modules.ModuleDefinition',
        on_delete=models.CASCADE,
        help_text="Parent :class:`~ery_backend.modules.models.ModuleDefinition`",
    )


class ModuleDefinitionNamedModel(EryNamedPrivileged, ModuleDefinitionModelMixin):
    """
    Adds all methods and kwarg dictionaries from EryModel model, Module model and following fields:
        1. Name
        2. Comment

    Adds get_privilege_ancestor method to 1st gen descendants of Module
    """

    class Meta(EryNamedPrivileged.Meta):
        abstract = True
        unique_together = (('name', 'module_definition'),)


class ModuleDefinitionProcedure(JavascriptNamedMixin, ModuleDefinitionNamedModel):
    """
    Name used by a :class:`~ery_backend.procedures.models.Procedure` for a given :class:`ModuleDefinition`.
    """

    parent_field = 'module_definition'

    procedure = models.ForeignKey('procedures.Procedure', on_delete=models.CASCADE)
    module_definition = models.ForeignKey('modules.ModuleDefinition', on_delete=models.CASCADE)


class Module(StintDefinitionModuleDefinitionMixin, StintModel):
    """
    Modules represent the independent tasks run alone or combinatorily in a stint.

    Modules have their own scope of variable (ModuleVariable)

    Children: ModuleVariable
    """

    # Override attribute from StintModel to add related_name
    stint = models.ForeignKey('stints.Stint', on_delete=models.CASCADE, related_name='modules')

    def __str__(self):
        return f"{self.stint}-Module:{self.stint_definition_module_definition.module_definition.name}"

    @property
    def module_definition(self):
        return self.stint_definition_module_definition.module_definition

    def make_variables(self, teams=None, hands=None, stint_definition_variable_definitions=None, values=None):
        """
        Realize :class:`~ery_backend.variables.models.VariableDefinition` instances.

        Args:
            - teams (Optional[List[:class:`~ery_backend.teams.models.Team`]]): Used to determine scope and owner of variable.
            - hands (Optional[List[:class:`~ery_backend.hands.models.Hand`]]): Used to determine scope and owner of variable.
            - stint_definition_variable_definitions (:class:`django.models.QuerySet`):
              :class:`~ery_backend.stints.models.StintDefinitionVariableDefinition` instances linked to variables during
              :class:`ery_backend.modules.models.Module` creation.
            - values (List[int: Union[int, float, str, Dict, List]]): Ids of
              :class:`~ery_backend.variables.models.VariableDefinition` instances that receive
              :class:`~ery_backend.users.models.User` specified values when realized.

        """
        # Linked through stint_def_var_def instead
        if stint_definition_variable_definitions:
            exclude_variable_definitions = stint_definition_variable_definitions.values_list(
                'variable_definitions__id', flat=True
            )
        else:
            exclude_variable_definitions = None
        for variable_definition in self.stint_definition_module_definition.module_definition.variabledefinition_set.all():
            if exclude_variable_definitions and variable_definition.pk in exclude_variable_definitions:
                continue
            # Stint_specifications allowing late_arrival do not always start with hands present
            if variable_definition.scope == variable_definition.SCOPE_CHOICES.hand and not hands:
                continue
            value = values[variable_definition.id] if values and variable_definition.id in values else None
            variable_definition.realize(self, teams, hands, value=value)

        if stint_definition_variable_definitions:
            for stint_definition_variable_definition in stint_definition_variable_definitions.all():
                variable_definition = stint_definition_variable_definition.variable_definitions.get(
                    module_definition=self.module_definition
                )
                value = values[variable_definition.id] if values and variable_definition.id in values else None
                variable_definition.realize(
                    self, teams, hands, stint_definition_variable_definition=stint_definition_variable_definition, value=value
                )
