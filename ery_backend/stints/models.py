# pylint: disable=too-many-lines
import datetime as dt
import json
import logging
import pytz

from django.db import models
from django.contrib.postgres.fields import JSONField
from django.conf import settings
import google
from google.cloud import pubsub

from model_utils import Choices

from ery_backend.base.cache import ery_cache
from ery_backend.base.exceptions import EryValidationError
from ery_backend.base.mixins import LogMixin, RenderMixin
from ery_backend.base.models import EryFile, EryPrivileged
from ery_backend.datasets.models import Dataset
from ery_backend.datastore.entities import RunEntity, WriteEntity, TeamEntity, HandEntity
from ery_backend.datastore.ery_client import get_datastore_client


logger = logging.getLogger(__name__)


class StintDefinition(EryFile):
    """
    Describe how to instantiate :class:`Stint` objects, which group together tasks (in the form of :class:`Module` objects)
    """

    class SerializerMeta(EryFile.SerializerMeta):
        model_serializer_fields = (
            'stint_definition_module_definitions',
            'specifications',
            'stint_definition_variable_definitions',
        )
        exclude = ('module_definitions',)

    # Required through API
    module_definitions = models.ManyToManyField(
        'modules.ModuleDefinition',
        through='stints.StintDefinitionModuleDefinition',
        help_text="Connected set of :class:`~ery_backend.modules.models.ModuleDefinition` children",
    )
    cover_image = models.ForeignKey('assets.ImageAsset', on_delete=models.SET_NULL, null=True, blank=True)

    @property
    def ready(self):
        """
        Confirms whether :class:`StintDefinition` is approved for instantiating :class:`Stint`.

        Approval is based on having at least one :class:`~ery_backend.modules.models.ModuleDefinition` child with a start_stage
        and start_era.

        Returns:
            bool: Whether :class:`StintDefinition` can be be used to launch :class:`Stint`.
        """
        return self.module_definitions.exclude(start_stage=None).exclude(start_era=None).exists()

    @staticmethod
    def get_bxml_serializer():
        """
        Get serializer class.
        """
        from .serializers import StintDefinitionBXMLSerializer

        return StintDefinitionBXMLSerializer

    # XXX: Address in issue #820
    # @staticmethod
    # def _get_simple_serializer():
    #     from .serializers import SimpleStintDefinitionSerializer
    #     return SimpleStintDefinitionSerializer

    def simple_serialize(self):
        """
        Get serializer data, substituting fully serialized children for slugged references.

        Returns:
            str: Serialized data.
        """
        return self._get_simple_serializer()(self).data

    @staticmethod
    def import_instance_from_xml(xml, name=None, simple=False):
        """
        Import data from xml file into :class:`StintDefinition` instance.

        Args:
            name (Optional[str]): Replacement name for duplicated instance.

        Notes:
            - Takes full bxml file for xml argument.
            - Default replacement name is {original_name}_copy.

        Returns:
            :class:`StintDefinition`: Duplicated instance.
        """
        model_serializer = StintDefinition.get_bxml_serializer()
        stream = xml.read()
        decoded_data = model_serializer.xml_decode(stream)
        replace_kwargs = {'name': name} if name else {}
        decoded_data.update(replace_kwargs)
        # XXX: Address in issue #820
        # if simple:
        #     stint_definition = SimpleStintDefinitionSerializer.nested_create(modified_data)
        # else:
        stint_definition = model_serializer(data=decoded_data).validate_and_save()
        return stint_definition

    def get_module_widgets(self, frontend):
        """
        Generate queryset containing all :class:`ery_backend.modules.models.ModuleWidget` instances connected to
        :class:`~ery_backend.stints.models.StintDefinition`.

        Returns:
            :class:`django.db.models.query.Queryset`
        """
        from ery_backend.modules.models import ModuleDefinitionWidget

        return ModuleDefinitionWidget.objects.filter(
            id__in=self.module_definitions.values_list('module_widgets__id', flat=True), widget__frontend=frontend
        )

    # XXX: Cache this
    def get_template_widgets(self, frontend):
        """
        Generate queryset containing all :class:`ery_backend.templates.models.TemplateWidget` instances connected to
        :class:`~ery_backend.stints.models.StintDefinition`.

        Returns:
            :class:`django.db.models.query.Queryset`
        """
        from ery_backend.templates.models import Template, TemplateWidget

        template_widget_ids = set()

        template_ids = set(self.module_definitions.values_list('stage_definitions__stage_templates__template__id', flat=True))
        for template in Template.objects.filter(id__in=template_ids).filter(frontend=frontend):
            template_widget_ids = template_widget_ids.union(template.get_ancestoral_template_widget_ids())

        return TemplateWidget.objects.filter(id__in=template_widget_ids)

    # XXX: Cache this
    def get_widgets(self, frontend):
        """
        Generate queryset containing all :class:`ery_backend.widgets.models.Widget` instances connected to
        :class:`~ery_backend.stints.models.StintDefinition`.

        Returns:
            :class:`django.db.models.query.Queryset`
        """
        from ery_backend.widgets.models import Widget, WidgetConnection

        form_widget_ids = self.module_definitions.values_list('forms__items__field__widget__id', flat=True).union(
            self.module_definitions.values_list('forms__items__button_list__buttons__widget__id', flat=True)
        )
        module_widget_ids = self.module_definitions.values_list('module_widgets__widget__id', flat=True)
        template_widget_ids = self.get_template_widgets(frontend).values_list('widget__id', flat=True)

        widget_ids = set(module_widget_ids).union(set(template_widget_ids)).union(set(form_widget_ids))

        widget_dependency_ids = set(
            WidgetConnection.objects.filter(originator__id__in=widget_ids).values_list('target__id', flat=True)
        )

        while not widget_dependency_ids.issubset(widget_ids):
            widget_ids.update(widget_dependency_ids)
            widget_dependency_ids = set(
                WidgetConnection.objects.filter(originator__id__in=widget_dependency_ids).values_list('target__id', flat=True)
            )

        return Widget.objects.filter(id__in=widget_ids, frontend=frontend)

    def realize(self, stint_specification):
        """
        Generates a :class:`Stint` for deployment.

        Args:
            stint_specification: Provides configuration information for creation of :class:`Stint`.

        Specifically:
            - The :class:`Stint` instance's configuration is obtained from the current :class:`StintDefinition` instance's \
              connected :class:`~ery_backend.stint_specifications.models.StintSpecification`.

        Returns:
            :class:`Stint`
        """
        if not self.ready:
            raise EryValidationError(
                f'Initializing Stint from StintDefinition: {self.name}, requires StintDefinition to have at'
                ' least one connected ModuleDefinition with a start_stage and start_era.'
            )
        stint = Stint.objects.create(stint_specification=stint_specification)

        return stint

    @ery_cache
    def render_web(self, language, vendor, is_marketplace):
        """
        Generate ES5 code for given instance.

        Args:
            - language (:class:`Language`)

        Returns:
            str
        """
        from ery_backend.frontends.renderers import ReactStintRenderer

        return ReactStintRenderer(self, language, vendor, is_marketplace).render()


# Address in issue #402
# pylint:disable=abstract-method
# pylint:disable=too-many-public-methods
class Stint(RenderMixin, LogMixin, EryPrivileged):
    """
    Group together tasks (in the form of :class:`Module` objects).

    Attributes:
        - STATUS_CHOICES (Tuple): Specify the possible states of a :class:`Stint`.
    Notes:
        - Each instance is accessible via behavery/stint_id.
        - A :class:`Stint` instance's :class:`~ery_backend.wardens.models.Warden` serves as the administrator used to monitor
          each :class:`Hand` instance's progression through said :class:`Stint`.
        - A :class:`Stint` instance must have at least one :class:`Module`.
    """

    STATUS_CHOICES = Choices(
        ('starting', "Starting"),
        ('running', "Running"),
        ('finished', "Finished"),
        ('cancelled', "Cancelled"),
        ('panicked', "Panicked"),
    )

    # Since stint is a runtime model, none of its attributes should be deleted while it is in use, making on_delete irrelevant
    stint_specification = models.ForeignKey(
        'stint_specifications.StintSpecification',
        on_delete=models.CASCADE,
        help_text="Parental instance",
        related_name='stints',
    )
    started_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text=":class:`User` who initiates via :py:meth:`Stint.start`",
        related_name='started_stints',
    )
    stopped_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        help_text=":class:`User` who cancels via :py:meth:`Stint.stop`",
        related_name='stopped_stints',
    )
    # Required through API
    warden = models.OneToOneField(
        'wardens.Warden', on_delete=models.CASCADE, null=True, blank=True, help_text="Serves as administrator"
    )
    lab = models.ForeignKey(
        'labs.Lab',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Endpoint for :class:`Stint`",
        related_name='stints',
    )
    status = models.CharField(
        max_length=24,
        choices=STATUS_CHOICES,
        blank=True,
        null=True,
        help_text="Indicates the state of the current :class:`Stint`",
    )

    started = models.DateTimeField(null=True, blank=True)
    ended = models.DateTimeField(null=True, blank=True)

    comment = models.TextField(null=True, blank=True)

    layout = JSONField(default=list, null=True, blank=True)

    @property
    def render_name(self):
        return self.stint_specification.stint_definition.name

    @property
    def ready(self):
        """
        # XXX: Addressed in issue #510. This will be changed after min/max team_size.

        Indicates :class:`Stint` has at least one full :class:`~ery_backend.teams.models.Team` of
          :class:`~ery_backend.hands.models.Hand` instances.
        """
        if self.hands.count() >= self.stint_specification.team_size:
            return True
        return False

    def get_context(self, hand=None, team=None, target='engine'):
        """
        Gather :class:`Stint` instance related information (based on context from :class:`~ery_backend.hands.models.Hand` or
        :class:`~ery_backend.teams.models.Team`) for processing in EryEngine.

        Args:
            - hand (Optional[:class:`~ery_backend.hands.models.Hand`]): Used if :class:`~ery_backend.teams.models.Team`
              not present.
            - team (Optional[:class:`~ery_backend.teams.models.Team`])
            - target (Optional[str]): Whether to include ids with variables.

        Notes:
            - In the case that there are two different variables whose definitions have the same name, a prefix is used to
              keep both and establish a default order of prioritization for which value to use.

        Returns:
            dict
        """
        from ..variables.models import ModuleVariable, TeamVariable, HandVariable

        context = {
            "stint": self.stint_specification.stint_definition.slug,
            "module": hand.current_module_definition.slug,
            "era": hand.era.slug,
            "nteams": self.teams.count(),
            "language": hand.language.iso_639_1,
        }

        context['variables'] = {}

        def _get_value(data, target):
            # Include id and value for engine. Just value otherwise.
            if target == 'engine':
                return data['variable_definition__id'], data['value']
            return data['value']

        for data in ModuleVariable.objects.filter(module=hand.current_module).values(
            'variable_definition__name', 'variable_definition__id', 'value'
        ):
            context['variables'][f'module.{data["variable_definition__name"]}'] = _get_value(data, target)
            context['variables'][data["variable_definition__name"]] = _get_value(data, target)

        for hand_team in hand.teams.all():
            team_name = hand_team.name.replace("-", "_")
            context['variables'][team_name] = {}
            for data in TeamVariable.objects.filter(team=hand_team, module=hand.current_module).values(
                'variable_definition__name', 'variable_definition__id', 'value'
            ):
                context['variables'][team_name][data["variable_definition__name"]] = _get_value(data, target)

                if hand_team == hand.current_team:
                    context['variables'][data['variable_definition__name']] = _get_value(data, target)

        if hand:
            for data in HandVariable.objects.filter(hand=hand, module=hand.current_module).values(
                'variable_definition__name', 'variable_definition__id', 'value'
            ):
                context['variables'][data['variable_definition__name']] = _get_value(data, target)

        return context

    # pylint:disable=redefined-outer-name
    def log(self, message, creation_kwargs=None, logger=logger, log_type=None, system_only=False):
        """
        Create log via Django logger and :class:`~ery_backend.logs.models.Log` instance.

        Args:
            message (Optional[str]): Text to be logged.
            log_type (Optional[str]): Django log level.
            system_only (Optional[bool]): Whether to create a :class:`~ery_backend.logs.models.Log` instance.

        Notes:
            - A :class:`~ery_backend.logs.models.Log` instance is only created for system_only=False cases.
        """
        super().log(message, {'stint': self}, logger, log_type, system_only)

    @staticmethod
    def get_variable(variable_definition, hand=None, team=None):
        """
        Get :class:`~ery_backend.variables.models.HandVariable`, :class:`~ery_backend.variables.models.TeamVariable`,
        :class:`~ery_backend.variables.models.ModuleVariable`, or :class:`~ery_backend.variables.models.StintVariable`.

        Args:
            variable_definition (:class:`~ery_backend.variables.models.VariableDefinition`): Used to obtain returned model
              instance.
            hand (Optional[:class:`~ery_backend.hands.models.Hand`]): Used to obtain returned model instance.
            team (Optional[:class:`~ery_backend.teams.models.Team`]): Used to obtain returned model instance.
        Notes:
            - Type of model obtained depends on the scope of the :class:`~ery_backend.variables.models.VariableDefinition`.

        Returns:
            :class:`~ery_backend.variables.models.HandVariable`: If :class:`~ery_backend.variables.models.VariableDefinition`
              instance's scope is 'hand'.
            :class:`~ery_backend.variables.models.TeamVariable`: If :class:`~ery_backend.variables.models.VariableDefinition`
              instance's scope is 'team'.
            :class:`~ery_backend.variables.models.ModuleVariable`: If :class:`~ery_backend.variables.models.VariableDefinition`
              instance's scope is 'module'.
            :class:`~ery_backend.variables.models.StintVariable`: If :class:`~ery_backend.variables.models.VariableDefinition`
              instance's scope is 'stint'.
        """
        from ..variables.models import VariableDefinition, ModuleVariable

        if variable_definition.scope == VariableDefinition.SCOPE_CHOICES.hand and hand is None:
            raise EryValidationError(
                'Hand required in get_variable for stint with variable_definition: {}'
                ' with scope: \'{}\''.format(variable_definition, variable_definition.scope)
            )
        if variable_definition.scope == VariableDefinition.SCOPE_CHOICES.team and (hand is None and team is None):
            raise EryValidationError(
                'Hand or Team required in get_variable for stint with variable_definition: {},'
                ' with scope: {}'.format(variable_definition, variable_definition.scope)
            )

        if VariableDefinition.SCOPE_CHOICES.hand in variable_definition.scope:
            variable = hand.get_variable(variable_definition)
        elif VariableDefinition.SCOPE_CHOICES.team in variable_definition.scope:
            if not team:
                team = hand.current_team
            variable = team.get_variable(variable_definition)
        elif VariableDefinition.SCOPE_CHOICES.module in variable_definition.scope:
            variable = ModuleVariable.objects.get(module=hand.current_module, variable_definition=variable_definition)
        else:
            raise NotImplementedError(f"get_variable is unprepared for scope {variable_definition.scope}")

        return variable

    def set_variable(self, variable_definition, value, hand=None, team=None):
        """
        Sets value of :class:`~ery_backend.variables.models.HandVariable`, :class:`~ery_backend.variables.models.TeamVariable`,
        :class:`~ery_backend.variables.models.ModuleVariable`, or :class:`~ery_backend.variables.models.StintVariable` and logs
        details.

        Args:
            variable_definition (:class:`~ery_backend.variables.models.VariableDefinition`): Used to locate variable instance.
            value (Union[str, int, float, bool, list, dict]): Value to set for variable instance.
            hand: (:class:`~ery_backend.variables.models.VariableDefinition`): Used to locate variable instance.
        """
        variable = self.get_variable(variable_definition, hand, team)
        if value not in [None, '']:
            new_value = variable_definition.cast(value)
        else:
            new_value = None
        old_value = variable.value

        changed = old_value != new_value
        if changed:
            variable.value = new_value
            variable.save()

        self.log(
            'set_variable for: {}, of type: {}, = {}'.format(variable_definition.name, variable.__class__, value),
            system_only=True,
        )
        return variable, changed

    def get_start_module(self):
        from ery_backend.modules.models import Module

        sdmds = self.stint_specification.stint_definition.stint_definition_module_definitions
        return Module.objects.get(stint=self, stint_definition_module_definition=sdmds.first())

    @staticmethod
    def _create_hand_variables(hand):
        from ery_backend.variables.models import VariableDefinition

        modules = hand.stint.modules
        modules.prefetch_related('stint_definition_module_definition__module_definition')
        for module in modules.all():
            variable_definitions = module.module_definition.variabledefinition_set.filter(
                scope=VariableDefinition.SCOPE_CHOICES.hand
            ).all()
            for variable_definition in variable_definitions:
                variable_definition.realize(module, hands=[hand])

    def start_hand(self, hand):
        from ery_backend.hands.models import Hand

        module = self.get_start_module()

        hand.set_module(module)
        hand.set_era(module.module_definition.start_era)
        hand.set_stage(stage_definition=module.module_definition.start_stage)
        hand.set_status(Hand.STATUS_CHOICES.active)
        breadcrumb = hand.create_breadcrumb(hand.stage)
        hand.set_breadcrumb(breadcrumb)

    def join_user(self, user, frontend):
        """
        Args:
            - user (:class:`~ery_backend.users.models.User`): Joining user.
            - frontend (:class:`~ery_backend.frontends.models.Frontend`): Intended frontend.

        Notes:
            - Should only be used if :class:`~ery_backend.stints.models.Stint` allows
              late_arrival (i.e., instance.late_arrival == True).
        """
        from ery_backend.hands.models import Hand
        from ery_backend.teams.models import TeamHand

        language_frontend_combination = self.stint_specification.get_language_frontend_combination(user, frontend)

        if not language_frontend_combination:
            return None

        hand = Hand.objects.create(user=user, stint=self, frontend=frontend, language=language_frontend_combination.language)
        team = self.teams.first()
        hand.current_team = team
        TeamHand.objects.create(team=team, hand=hand)

        self.start_hand(hand)
        self._create_hand_variables(hand)

        return hand

    def reset_hand(self, hand, frontend):
        """
        Args:
            - hand (:class:`~ery_backend.hands.models.hand`): Re-joining hand.
            - frontend (:class:`~ery_backend.frontends.models.Frontend`): Intended frontend.

        Notes:
            - Should only be used if :class:`~ery_backend.stints.models.Stint` allows
              late_arrival (i.e., instance.late_arrival == True).
        """
        hand.variables.all().delete()

        self.start_hand(hand)
        self._create_hand_variables(hand)

    def signal_create_robot_hands(self):
        deployment = getattr(settings, "DEPLOYMENT", "staging")
        project_name = getattr(settings, "PROJECT_NAME", "eryservices-176219")

        # XXX: Centralize this too
        robot_topic = f'projects/{project_name}/topics/{deployment}-robot'
        # XXX: Move this so that it isn't initialized per realize
        pub = pubsub.PublisherClient()
        try:
            pub.create_topic(robot_topic)
        except google.api_core.exceptions.AlreadyExists:
            pass

        message = json.dumps({'action': 'STINT_START', 'stint_id': self.id}).encode()
        logger.info("Send STINT_START for %s Stint", self.id)
        future = pub.publish(robot_topic, message)
        logger.info("Sent STINT_START for %s", self.id)
        return future

    def start(self, started_by, signal_pubsub=True):
        """
        Initialize a pre-created :class:`Stint` for use by :class:`~ery_backend.hands.models.Hand` objects.

        Args:
            - started_by (:class:`~ery_backend.users.models.User`)
            - signal_pubsub (bool): Whether to send a signal to the Robot Runner using Google Pubsub during stint.start.
        """
        from ery_backend.teams.models import Team, TeamHand
        from ery_backend.wardens.models import Warden

        if self.status is not None:
            raise EryValidationError(f"{self} already started by {self.started_by} at {self.started}.")

        self.set_status(self.STATUS_CHOICES.starting)
        self.started_by = started_by
        team_number = 0
        hands_assigned = 0
        teams = []
        team = Team.objects.create(stint=self, name=f"team-{team_number}")
        teams.append(team)

        # create and allocate teams
        for hand in self.hands.all():
            # Start a new team if the current one is full
            if not self.stint_specification.late_arrival:
                if hands_assigned >= self.stint_specification.team_size:
                    team_number += 1
                    hands_assigned = 0
                    team = Team.objects.create(stint=self, name=f"team-{team_number}")
                    teams.append(team)

            # Assign the hand to the team
            hand.current_team = team
            hand.save()
            TeamHand.objects.create(team=team, hand=hand)
            hands_assigned += 1

        sdvds = self.stint_specification.stint_definition.stint_definition_variable_definitions
        exclude_sdvds = []  # used to make sure only one variable is allocated per stint_definition_variable_definition

        # Store stint-specified variable values by VariableDefinition id for cached variable realization
        values = dict(self.stint_specification.variables.values_list('variable_definition__id', 'value'))

        if self.stint_specification.dataset is not None:
            values.update(self.stint_specification.get_dataset_variables())

        sdmds = self.stint_specification.stint_definition.stint_definition_module_definitions
        start_module_definition = sdmds.first().module_definition

        for sdmd in sdmds.select_related('module_definition').all():
            module_definition = sdmd.module_definition
            module_sdvds = sdvds.filter(variable_definitions__module_definition__id=module_definition.id).exclude(
                id__in=exclude_sdvds
            )
            exclude_sdvds += list(module_sdvds.exclude(id__in=exclude_sdvds).values_list('id', flat=True))

            sdmd.realize(self, stint_definition_variable_definitions=module_sdvds.all(), values=values)

        # set team
        # XXX: Address in issue #510. Currently ignores max/min size.

        # Add robot hands here
        if signal_pubsub:
            future = self.signal_create_robot_hands()
            signal_error = future.exception()
            if signal_error:
                raise signal_error

        for hand in self.hands.all():
            self.start_hand(hand)

        self.set_status(Stint.STATUS_CHOICES.running)
        self.started = dt.datetime.now(pytz.UTC)

        self.save()

    # XXX: Address in issue #505
    def stop(self, stopped_by=None):
        """
        Cancels the status of the :class:`Stint` and all of its child
        :class:`~ery_backend.hands.models.Hand` instances.

        Args:
            stopped_by (Optional[:class:`~ery_backend.users.models.User`]): Absence indicates :class:`Stint`
              was stopped automatically.
        """
        from ery_backend.hands.models import Hand

        if self.status is None:
            raise EryValidationError(f"{self} has not been started, and cannot be stopped.")

        stop_time = dt.datetime.now(pytz.UTC)
        formatted_stop_time = stop_time.strftime('%Y-%m-%d %H:%M')
        cancel_hand = self.status in [
            self.STATUS_CHOICES.panicked,
            self.STATUS_CHOICES.cancelled,
            self.STATUS_CHOICES.finished,
        ]
        if cancel_hand:
            for hand in self.hands.filter(status=Hand.STATUS_CHOICES.active):
                hand.set_status(Hand.STATUS_CHOICES.cancelled)
        self.stopped_by = stopped_by
        self.ended = stop_time
        self.save()
        message = f'Stint with StintDefinition: {self.stint_specification.stint_definition.name},' f' stopped'
        if stopped_by:
            message += f' by User: {stopped_by.username}'
        message += f' at {formatted_stop_time}.'
        self.log(message, system_only=True)

    @property
    def active(self):
        """
        Describes whether the current :class:`Stint` is running.

        Returns:
            bool
        """
        return self.status == self.STATUS_CHOICES.running

    def set_status(self, status, actor=None):
        """
        Changes status of :class:`Stint`.

        Args:
            status (str): Intended state change.
            actor (Optional[:class:`~ery_backend.users.models.User`]): Absence indicates :class:`Stint`
              status changed automatically.

        Raises:
            ValueError: Raised if status is not in :class:`Stint` model's STATUS_CHOICES.
        """
        from ery_backend.hands.models import Hand

        if status in self.STATUS_CHOICES:
            self.status = status
            self.save()
            self.refresh_from_db()  # prevents misreading of stint status in hand.set_status
            if status in (self.STATUS_CHOICES.finished, self.STATUS_CHOICES.cancelled, self.STATUS_CHOICES.panicked):
                self.stop(actor)
            elif status == self.STATUS_CHOICES.running:
                for hand in self.hands.all():
                    hand.set_status(Hand.STATUS_CHOICES.active)

        else:
            raise ValueError(f"'{status}' is not a valid status choice for {self}.")

    def render(self, hand):
        """
        Generate an ES5 based view for the given model instance.

        Args:
            - hand (:class:`~ery_backend.hands.models.Hand`): Provides context (i.e., desired
              :class:`ery_backend.frontends.models.Frontend`, :class:`Language`, and :class:`Variable`
              needed for content creation.

        Returns:
            str: ES5 javascript which includes :class:`ery_backend.users.models.User` based content and the react module
            code needed to render said content in the form of ES6 components.

        """
        # XXX: Address in issue #505
        if hand.frontend.name == 'Web':
            return self.render_web(hand.language)
        raise EryValidationError('No render method exists for StageDefinition given {hand.frontend} ')

    def render_web(self, language):
        """
        Generate ES5 code for given instance.

        Args:
            - language (:class:`Language`)

        Returns:
            str
        """
        return self.stint_specification.stint_definition.render_web(
            language,
            self.stint_specification.vendor,
            self.stint_specification.where_to_run == self.stint_specification.WHERE_TO_RUN_CHOICES.market,
        )

    # XXX: Needs testing in issue #679
    def save_output_data(self, action_step, hand):
        entities = []

        variable_definitions = action_step.get_to_save(self)

        def get_variables_by_scope(scope):
            from ery_backend.variables.models import VariableDefinition, HandVariable, TeamVariable, ModuleVariable

            qs_filter_kwargs = {'module': hand.current_module}

            if scope == VariableDefinition.SCOPE_CHOICES.module:
                variable_cls = ModuleVariable
            if scope == VariableDefinition.SCOPE_CHOICES.team:
                variable_cls = TeamVariable
                qs_filter_kwargs['team'] = hand.current_team
            if scope == VariableDefinition.SCOPE_CHOICES.hand:
                variable_cls = HandVariable
                qs_filter_kwargs['hand'] = hand
            variable_definition_ids = variable_definitions.values_list('id', flat=True)
            qs_filter_kwargs["variable_definition__id__in"] = variable_definition_ids
            variable_qs = variable_cls.objects.filter(**qs_filter_kwargs).prefetch_related('variable_definition')
            return dict(variable_qs.values_list('variable_definition__name', 'value'))

        # XXX: Remove try/except in issue #680
        # try:
        run = RunEntity.from_django(self)
        write = WriteEntity.from_django(action_step, get_variables_by_scope('module'), hand, run.key)
        entities.append(run)
        entities.append(write)

        for team in hand.teams.all():
            te = TeamEntity.from_django(team, get_variables_by_scope('team'), write.key, hand)
            entities.append(te)
        he = HandEntity.from_django(hand, get_variables_by_scope('hand'), write.key)
        entities.append(he)

        ery_datastore_client = get_datastore_client()
        with ery_datastore_client.transaction():
            ery_datastore_client.put_multi(entities)
        # except Exception as e:  #pylint:disable=broad-except
        #     print(e)

    # XXX: Cache this
    # XXX: Integration with StintDefVarDef
    # XXX: Test this
    # XXX: What if two modules have the same variable name for any scope?
    # XXX: Variable naming prioritization?
    def variable_names(self, output_only=True):
        from ery_backend.variables.models import VariableDefinition

        output_kwargs = {'is_output_data': True} if output_only else {'is_output_data__in': [True, False]}
        module_definition_ids = self.stint_specification.stint_definition.module_definitions.values_list('id', flat=True)
        hand_variable_definitions = VariableDefinition.objects.filter(
            module_definition__id__in=module_definition_ids, scope=VariableDefinition.SCOPE_CHOICES.hand, **output_kwargs
        )
        team_variable_definitions = VariableDefinition.objects.filter(
            module_definition__id__in=module_definition_ids, scope=VariableDefinition.SCOPE_CHOICES.team, **output_kwargs
        )
        module_variable_definitions = VariableDefinition.objects.filter(
            module_definition__id__in=module_definition_ids, scope=VariableDefinition.SCOPE_CHOICES.module, **output_kwargs
        )

        hand_variable_names = list(hand_variable_definitions.values_list('name', flat=True))
        team_variable_names = list(team_variable_definitions.values_list('name', flat=True))
        module_variable_names = list(module_variable_definitions.values_list('name', flat=True))

        return hand_variable_names + team_variable_names + module_variable_names

    def to_dataset(self, name=None, save=True):
        """ Produce a dataset of the stint'svariable as they are stored in datastore"""
        data = []
        ery_datastore_client = get_datastore_client()
        run_key = ery_datastore_client.key("Run", self.pk)
        entity = ery_datastore_client.get(run_key)
        if entity:
            run = RunEntity.from_entity(entity)
            write_query = ery_datastore_client.query(kind="Write", ancestor=run_key)
            writes = [WriteEntity.from_entity(w) for w in write_query.fetch()]
            for write in writes:
                team_query = ery_datastore_client.query(kind="Team", ancestor=write.key)
                teams = [TeamEntity.from_entity(t) for t in team_query.fetch()]
                hand_query = ery_datastore_client.query(kind="Hand", ancestor=write.key)
                hands = [HandEntity.from_entity(h) for h in hand_query.fetch()]
                for hand in hands:
                    has_team = False
                    for team in teams:
                        if "members" in team and hand["pk"] in team["members"]:
                            data.append({**run.csv_data, **write.csv_data, **team.csv_data, **hand.csv_data})
                            has_team = True
                        if not has_team:
                            data.append({**run.csv_data, **write.csv_data, **hand.csv_data})
        ds = Dataset(name=name)
        if save:
            ds.save()
        ds.set_datastore(data)

        return ds

    def to_pandas(self):
        return self.to_dataset(save=False).to_pandas()

    def to_csv(self):
        return self.to_dataset(save=False).to_pandas().to_csv()


class StintModel(EryPrivileged):
    """
    Adds Stint model with parental infomation.

    Args:
        parent_field (str): Name of parental attribute.
    """

    class Meta(EryPrivileged.Meta):
        abstract = True

    parent_field = "stint"
    stint = models.ForeignKey('stints.Stint', on_delete=models.CASCADE, help_text="Parental instance")


class StintDefinitionModuleDefinition(EryPrivileged):
    """
    Custom intermediate model class for stint and module_definition.
    """

    class Meta(EryPrivileged.Meta):
        ordering = ("order",)

    class SerializerMeta(EryPrivileged.SerializerMeta):
        model_serializer_fields = ('module_definition',)

    parent_field = 'stint_definition'
    stint_definition = models.ForeignKey(
        'stints.StintDefinition', on_delete=models.CASCADE, related_name='stint_definition_module_definitions'
    )
    module_definition = models.ForeignKey(
        'modules.ModuleDefinition', on_delete=models.CASCADE, related_name='stint_definition_module_definitions'
    )
    order = models.IntegerField(default=0)

    # XXX: Address in issue #820
    # @staticmethod
    # def get_simple_serializer():
    #     """
    #     Get simple serializer class.
    #     """
    #     from .serializers import SimpleStintDefinitionModuleDefinitionSerializer
    #     return SimpleStintDefinitionModuleDefinitionSerializer

    def realize(self, stint, stint_definition_variable_definitions=None, values=None):
        """
        Make the :class:`~ery_backend.modules.models.Module` and associated variables.

        Args:
            - stint (:class:~ery_backend.stints.models.Stint`): Parent of created :class:`~ery_backend.modules.models.Module`.
            - stint_definition_variable_definitions (List[:class:`StintDefinitionVariableDefinition`]): Each element contains
              a :class:`~ery_backend.variables.models.VariableDefinition` belonging to the current instance's
              :class:`~ery_backend.modules.models.ModuleDefintion`. Linked to variables during
              :class:`ery_backend.modules.models.Module` creation.
            - values (List[int: Union[int, float, str, Dict, List]]): Ids of
              :class:`~ery_backend.variables.models.VariableDefinition` instances that recieve
              :class:`~ery_backend.users.models.User` specified values when realized.

        Return:
            :class:`~ery_backend.modules.models.Module`
        """
        from ery_backend.modules.models import Module

        module = Module.objects.create(stint=stint, stint_definition_module_definition=self)
        module.make_variables(
            teams=module.stint.teams.all(),
            hands=module.stint.hands.all(),
            stint_definition_variable_definitions=stint_definition_variable_definitions,
            values=values,
        )
        return module

    def _invalidate_related_tags(self, history):
        self.stint_definition.invalidate_tags(history)


class StintDefinitionModuleDefinitionMixin(models.Model):
    """
    Adds :class:`StintDefinitionModuleDefinition` relationship.
    """

    class Meta:
        abstract = True

    stint_definition_module_definition = models.ForeignKey(
        'stints.StintDefinitionModuleDefinition',
        on_delete=models.CASCADE,
        help_text="Links to parental instance realized to create current instance in order to track order of presentation.",
    )


class StintDefinitionVariableDefinition(EryPrivileged):
    """
    Link :class:`~ery_backend.variables.VariableDefinition` instances to indicate that they
    are equivalent.
    """

    parent_field = 'stint_definition'

    variable_definitions = models.ManyToManyField(
        "variables.VariableDefinition", related_name="stint_definition_variable_definitions",
    )

    stint_definition = models.ForeignKey(
        "stints.StintDefinition", related_name="stint_definition_variable_definitions", on_delete=models.CASCADE
    )

    # XXX: Address in issue #813
    def clean(self):
        """
        Link :class:`~ery_backend.variables.VariableDefinition` instances that:
            - belong to :class:`~ery_backend.stints.StintDefinition`
            - have identical scope
            - are not part of the same :class:`~ery_backend.models.ModuleDefinition`
        """
        # vds = self.variable_definitions.all()

        # if not vds:
        #     return

        # vd1 = vds[0]
        # used_module_defs = set()
        # accepted_module_defs = set(
        #     self.stint_definition.stint_definition_module_definitions.values_list('module_definition__id', flat=True)
        # )

        # for vd in vds:
        #     if vd.data_type != vd1.data_type:
        #         raise ValueError("Data type mismatch on %s" % vd)

        #     if vd.scope != vd1.scope:
        #         raise ValueError("Scope type mismatch on %s" % vd)

        #     if vd.module_definition.pk not in accepted_module_defs:
        #         raise ValueError("%s does not belong to %s" % (vd, self.stint_definition))

        #     if vd.module_definition.pk in used_module_defs:
        #         raise ValueError("Cannot use multiple VariableDefinitions from %s" % (vd.module_definition))

        #     used_module_defs.add(vd.module_definition.pk)
