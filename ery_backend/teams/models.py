import logging

from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.postgres.fields import JSONField

from ery_backend.base.mixins import LogMixin
from ery_backend.base.models import EryModel
from ery_backend.modules.models import ModuleDefinitionNamedModel
from ery_backend.stints.models import StintModel

logger = logging.getLogger(__name__)


class TeamHand(EryModel):
    """
    Intermediate model used for ordering many to many relationship.
    """

    class Meta(EryModel.Meta):
        ordering = ('id',)

    team = models.ForeignKey('teams.Team', on_delete=models.CASCADE)
    hand = models.ForeignKey('hands.Hand', on_delete=models.CASCADE)


class Team(LogMixin, StintModel):
    """
    Group :class:`Hand` instances in a given :class:`~ery_backend.stints.models.Stint`.

    Notes:
        TeamVariables are descendants of Teams.
    """

    # assigned during StintSpecification.realize
    stint = models.ForeignKey(
        'stints.Stint', on_delete=models.CASCADE, null=True, blank=True, help_text="Parental instance", related_name='teams'
    )
    name = models.CharField(max_length=256, help_text="Name of model instance")
    # required through API
    hands = models.ManyToManyField('hands.Hand', through='teams.TeamHand', related_name='teams', help_text="Grouped children")
    # assigned during StintDefinition.realize, and updated automatically when all hands in set share a new era.
    # an era or team should never be deleted during runtime, when teams exist, so on_delete should not matter
    era = models.ForeignKey(
        'syncs.Era',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Used to synchronize current :class:`Team` instances with other instances",
    )
    team_network_definition = models.ForeignKey(
        'teams.TeamNetworkDefinition',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Social network used to render instance during :class:`~ery_backend.stints.models.Stint`",
    )

    def set_era(self, era):
        """
        Change era attribute and logs details.

        Notes:
            - Should only be run via :py:meth:`Team.synchronize`.
        """
        self.era = era
        message = "setEra: {} for team: {}, of stint: {}, with definition name: {}".format(
            era, self.id, self.stint.id, self.stint.stint_specification.stint_definition.name
        )
        self.stint.log(message, system_only=True)
        self.save()

    def synchronize(self, era):
        """
        Sets new era if all member :class:`Hand` instances are of said :class:`~ery_backend.syncs.models.Era`.
        """
        if self.hands.filter(era=era).count() == self.hands.count():
            self.set_era(era)

    def get_variable(self, variable_definition):
        """
        Get :class:`~ery_backend.variables.models.TeamVariable` using :class:`Team` and
        :class:`~ery_backend.variables.models.VariableDefinition`.

        Notes:
            - If :class:`~ery_backend.variables.models.VariableDefinition` does not have scope 'team', will return None.

        Returns:
            :class:`~ery_backend.variables.models.TeamVariable`: Matching instance given :class:`Team` and
            :class:`~ery_backend.variables.models.VariableDefinition`.
        """
        from ery_backend.variables.models import TeamVariable

        return TeamVariable.objects.get(team=self, variable_definition=variable_definition)

    # pylint:disable=redefined-outer-name
    def log(self, message, creation_kwargs=None, my_logger=logger, log_type=None, system_only=False):
        """
        Create log via Django logger and :class:`~ery_backend.logs.models.Log` instance.

        Args:
            message (Optional[str]): Text to be logged.
            log_type (Optional[str]): Django log level.
            system_only (Optional[bool]): Whether to create a :class:`~ery_backend.logs.models.Log` instance.

        Notes:
            - A :class:`~ery_backend.logs.models.Log` instance is only created for system_only=False cases.
        """
        super().log(message, {'stint': self.stint, 'team': self}, my_logger, log_type, system_only)


class TeamNetworkDefinition(ModuleDefinitionNamedModel):
    """
    Defines either a static definition, or a method to generate, a :class:`~ery_backend.teams.models.TeamNetwork`.
    XXX: Yet to be implemeneted. Once properly implemented, make parameters explicit fields rather than a JSONField.
    XXX: Address in issue #524
    """

    parent_field = 'module_definition'
    GENERATION_METHOD_CHOICES = (
        ('connected_newman_watts_strogatz_graph', "Connected Newman-Watts-Strogatz"),
        ('neighborhood_graph', "Random with neighborhoods of size"),
    )

    K_ERROR_MESSAGE = "k: an integer representing a node's nearest neighbors in a ring topology)"
    P_ERROR_MESSAGE = "p: a float representing the probability per edge of adding an additional edge"

    static_network = models.TextField(null=True, blank=True)  # graph markup language
    generation_method = models.CharField(max_length=100, choices=GENERATION_METHOD_CHOICES, null=True, blank=True)
    parameters = JSONField(null=True, blank=True)

    @staticmethod
    def parameter_is_num(value):
        """
        Checks if value is the equivalent of a positive number.

        Args:
            value (Union[int, float]): Converted value.

        Returns:
            bool
        """
        if not isinstance(value, (int, float)):
            return False
        return True

    @classmethod
    def parameter_is_whole(cls, value):
        """
        Check if value is the equivalent of a positive integer.

        Args:
            value (Union[int, float]): Converted value.

        Returns:
            bool
        """
        if cls.parameter_is_num(value):
            return value % 1 == 0
        return False

    def _validate_parameter(self, validate_method, value, error_message):
        """
        Executes validation_method on given parameter during clean, and raises exception upon failure.
        """
        target_error = False
        if value is None:
            target_error = True
        elif not validate_method(value):
            target_error = True
        if target_error:
            raise ValidationError(
                {
                    'parameters': "connected_newman_watts_strogatz_graph requires parameter "
                    "{} for TeamNetwork Definition: {}. Got: {}".format(error_message, self, value)
                }
            )

    def clean(self):
        """
        Default django method, with additional enforcement of required attribute combinations.

        Raises:
            :class:`ValidationError`: If instances violates required attribute combination(s).
        """
        super().clean()
        if self.static_network and self.generation_method:
            raise ValidationError(
                {
                    'generation_method': "static_network and generation_method cannot both have values for "
                    "Team Network: {}".format(self)
                }
            )
        if not self.static_network and not self.generation_method:
            raise ValidationError(
                {
                    'generation_method': "Either static_network or a generation_method is required for "
                    "Team Network: {}".format(self)
                }
            )

        if self.generation_method == 'connected_newman_watts_strogatz_graph':
            if not self.parameters:
                raise ValidationError(
                    {
                        'parameters': "connected_newman_watts_strogatz_graph requires parameters {} and "
                        "{} for Team Network: {}".format(self.K_ERROR_MESSAGE, self.P_ERROR_MESSAGE, self)
                    }
                )
            self._validate_parameter(self.parameter_is_whole, self.parameters.get('k'), self.K_ERROR_MESSAGE)
            self._validate_parameter(self.parameter_is_num, self.parameters.get('p'), self.P_ERROR_MESSAGE)


class TeamNetwork(StintModel):
    """
    A TeamNetwork uses GML (https://networkx.github.io/documentation/networkx-2.3/reference/readwrite/gml.html)
    to specify the graph that describes the relationships in a given :class:`~ery_backend.teams.models.Team`.

    Note:
        A :class:`~ery_backend.hands.models.Hand` can be member in multiple :class:`~ery_backend.teams.models.Team`,
        hence a Hand can be a node in multiple :class:`~ery_backend.teams.models.TeamNetwork` too.

    XXX: Address in issue #524
    """

    network = models.TextField()  # graph markup language
