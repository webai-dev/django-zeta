import json
import logging

from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.functions import Lower
from django.db.utils import IntegrityError

from countries_plus.models import Country
from languages_plus.models import Language
from model_utils import Choices

from ery_backend.base.exceptions import EryValidationError
from ery_backend.base.models import EryNamedPrivileged, EryPrivileged
from ery_backend.frontends.models import Frontend
from ery_backend.modules.models import ModuleDefinitionModelMixin
from ery_backend.roles.utils import grant_ownership
from ery_backend.vendors.models import Vendor


logger = logging.getLogger(__name__)


class StintSpecificationCountry(EryPrivileged):
    """
    Intermediate model conntecting :class:`StintSpecification` and :class:`Country`.
    """

    class Meta(EryPrivileged.Meta):
        ordering = ('id',)

    parent_field = 'stint_specification'
    stint_specification = models.ForeignKey(
        'stint_specifications.StintSpecification',
        on_delete=models.CASCADE,
        related_name='stint_specification_countries',
        help_text="Linked :class:`StintSpecification` instance",
    )
    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        related_name='stint_specification_countries',
        help_text="Linked :class:`Country` instance.",
    )

    @staticmethod
    def get_bxml_serializer():
        from .serializers import StintSpecificationCountryBXMLSerializer

        return StintSpecificationCountryBXMLSerializer


class StintSpecificationAllowedLanguageFrontend(EryPrivileged):
    class Meta(EryPrivileged.Meta):
        unique_together = (("language", "frontend", "stint_specification"),)

    parent_field = 'stint_specification'
    stint_specification = models.ForeignKey(
        'stint_specifications.StintSpecification',
        on_delete=models.CASCADE,
        related_name='allowed_language_frontend_combinations',
    )
    language = models.ForeignKey(Language, on_delete=models.CASCADE)
    frontend = models.ForeignKey(Frontend, on_delete=models.CASCADE)

    @staticmethod
    def get_bxml_serializer():
        """
        Get serializer class.
        """
        from .serializers import StintSpecificationAllowedLanguageFrontendBXMLSerializer

        return StintSpecificationAllowedLanguageFrontendBXMLSerializer


class StintSpecification(EryNamedPrivileged):
    """
    Settings model for :class:`ery_backend.stints.models.StintDefinition`.

    Provides the following specifications:
        - The :class:`Language` to render the contents of each :class:`~ery_backend.modules.models.ModuleDefinition`.
        - The size of each :class:`~ery_backend.teams.models.Team`.
        - The number of :class:`~ery_backend.robots.models.Robot` objects, if any, to participate in associated \
          :class:`~ery_backend.stints.models.Stint` instances.

        - :class:`Country` instances a :class:`~ery_backend.users.models.User` must be associated with to participate in \
          associated :class:`~ery_backend.stints.models.Stint` instances.

    Attributes:
        parent_field: Static declaration of name of immediate ancestor from which privilege is inherited.

    Notes:
        * Through :class:`StintSpecificationVariable` objects, a :class:`StintSpecification` also specifies how to instantiate
          :class:`~ery_backend.variables.models.HandVariable`, :class:`~ery_backend.variables.models.TeamVariable`,
          :class:`~ery_backend.variables.models.ModuleVariable`, and :class:`~ery_backend.variables.models.StintVariable`
          objects for :class:`~ery_backend.stints.models.Stint` instances.
    """

    class Meta(EryNamedPrivileged.Meta):
        """
        Meta.
        """

        unique_together = (("name", "stint_definition"),)

    class SerializerMeta(EryNamedPrivileged.SerializerMeta):
        exclude = ('created', 'modified', 'opt_in_code', 'subject_countries')
        model_serializer_fields = (
            'stint_specification_countries',
            'allowed_language_frontend_combinations',
            'module_specifications',
        )

    WHERE_TO_RUN_CHOICES = Choices(('lab', 'Lab'), ('market', 'Marketplace'), ('simulation', 'Simulation'),)

    PAYMENT_CHOICES = Choices(('PHONE_RECHARGE', 'Phone Recharge'),)

    parent_field = 'stint_definition'

    stint_definition = models.ForeignKey(
        'stints.StintDefinition',
        related_name='specifications',
        on_delete=models.CASCADE,
        help_text="Connected :class:`~ery_backend.stints.models.StintDefintion`",
    )
    where_to_run = models.CharField(max_length=10, choices=WHERE_TO_RUN_CHOICES)
    vendor = models.ForeignKey(Vendor, on_delete=models.SET_NULL, blank=True, null=True)
    team_size = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Number of :class:`~ery_backend.hands.models.Hand` instances per" " :class:`~ery_backend.teams.models.Team`",
    )
    min_team_size = models.PositiveIntegerField(null=True, blank=True, help_text="DEFINE DURING IMPLEMENTATION")
    max_team_size = models.PositiveIntegerField(null=True, blank=True, help_text="DEFINE DURING IMPLEMENTATION")
    max_num_humans = models.PositiveIntegerField(null=True, blank=True, help_text="DEFINE DURING IMPLEMENTATION")
    min_earnings = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Minimum possible earnings per :class:`~ery_backend.hands.models.Hand` for"
        " :class:`~ery_backend.stints.models.Stint`",
    )
    max_earnings = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Maximum possible earnings per :class:`~ery_backend.hands.models.Hand` for"
        " :class:`~ery_backend.stints.models.Stint`",
    )

    backup_stint_specification = models.ForeignKey(
        'stint_specifications.StintSpecification',
        on_delete=models.SET_NULL,
        related_name='stints_backupstint',
        null=True,
        blank=True,
        help_text="Assigned to users who do not fit into a :class:`~ery_backend.teams.models.Team`"
        " in the primary :class:`StintSpecification`",
    )
    subject_countries = models.ManyToManyField(
        Country,
        through='StintSpecificationCountry',
        help_text=":class:`Country` instances used to limit :class:`~ery_backend.hands.models.User` participatation in"
        " associated :class:`~ery_backend.stints.models.Stint` instances",
    )
    late_arrival = models.BooleanField(
        default=False, help_text="Whether to accept new :class:`~ery_backend.hands.models.Hand` instances after start."
    )
    opt_in_code = models.CharField(
        max_length=32,
        unique=True,
        null=True,
        blank=True,
        help_text="Used to link :class:`~ery_backend.users.models.User` instances to the currently active associated"
        " :class:`~ery_backend.stints.models.Stint` instance",
    )
    immediate_payment_method = models.CharField(max_length=50, choices=PAYMENT_CHOICES, blank=True, null=True)
    dataset = models.ForeignKey(
        'datasets.Dataset',
        on_delete=models.SET_NULL,
        related_name='stint_specifications',
        null=True,
        blank=True,
        help_text="Specifies :class:`StintSpecificationVariable` values to override"
        " when starting a :class:`~ery_backend.stints.models.Stint`",
    )

    def get_default_language(self):
        allow_tuple = self.allowed_language_frontend_combinations.first()
        if allow_tuple:
            return allow_tuple.language
        return Language.objects.get(pk="en")

    def get_language_frontend_combination(self, user, frontend):
        # XXX: To be updated to be filtered by user and frontend
        # To be fixed according to issue #827
        return self.allowed_language_frontend_combinations.first()

    def _validate_not_circular(self, children=None):
        """
        Prevents circularity between backup stint_definition and default stint_definition.
        """
        if self.backup_stint_specification:
            if not children:
                children = [self]
            else:
                children.append(self)

            if self.backup_stint_specification in children:
                return False
            if not self.backup_stint_specification._validate_not_circular(children):  # pylint: disable=protected-access
                return False
        return True

    def _verify_stint_min_max(self):
        if self.min_earnings is not None and self.max_earnings is not None:
            if self.min_earnings > self.max_earnings:
                raise ValueError(
                    f"Minimum earnings: {self.min_earnings}, exceed maximum earnings: {self.max_earnings}, for"
                    f" {self.stint_definition}."
                )

    def verify_full_min_max(self):
        """
        Confirms :class:`StintModuleSpecification` level earnings combinations do not exceed bounds set by
        parental :class:`StintSpecification`.

        Returns:
            Tuple[bool, Dict[str: Union[bool, float]]]: Verification result and dictionary containing information needed for
            error reporting.
        """
        total_min_earnings = sum([specification.min_earnings for specification in self.module_specifications.all()])
        verified = True
        reason = None
        if self.min_earnings:
            if self.min_earnings < total_min_earnings:
                verified = False
                reason = 'min'
        total_max_earnings = sum([specification.max_earnings for specification in self.module_specifications.all()])
        if self.max_earnings:
            if self.max_earnings < total_max_earnings:
                verified = False
                reason = 'max'
        return (
            verified,
            {'reason': reason, 'total_min_earnings': total_min_earnings, 'total_max_earnings': total_max_earnings},
        )

    def _report_combined_earnings_violation(self, info):
        if info['reason'] == 'min':
            reason = 'minimum'
            total = info['total_min_earnings']
            stint_total = self.min_earnings
        else:
            reason = 'maximum'
            total = info['total_max_earnings']
            stint_total = self.max_earnings
        raise ValueError(
            f"Total {reason} earnings: {total}, combination of StintModuleSpecification"
            f" level minimum earnings, exceed minimum earnings: {stint_total}, declared at the"
            f" StintSpecification level for {self.stint_definition}."
        )

    def clean(self):
        """
        Prevents team size conflicts.

        Specifically:
            * Prevents specification of max_team_size attribute less than that of team_size/min_team_size attributes.
            * Prevents specification of min_team_size attribute greater than that of team_size.

        Raises:
            ValidationError: An error occuring if restrictions are violated.
        """

        super().clean()
        if self.opt_in_code:
            if (
                StintSpecification.objects.annotate(opt_in_code_lower=Lower('opt_in_code'))
                .filter(opt_in_code_lower=self.opt_in_code.lower())
                .exclude(id=self.id)
                .exists()
            ):
                raise IntegrityError(f'A version of opt_in_code {self.opt_in_code} has already been taken.')
        if self.max_team_size and self.max_team_size < self.team_size:
            raise ValidationError(
                {
                    'max_team_size': "Can not set value of max_team_size, {}, to a value less than team_size, {}, \
                 for Stint Specification: {}.".format(
                        self.max_team_size, self.team_size, self
                    )
                }
            )

        if self.min_team_size and self.min_team_size > self.team_size:
            raise ValidationError(
                {
                    'min_team_size': "Can not set value of min_team_size, {}, to a value greater than team_size, {}, \
                 for Stint Specification: {}.".format(
                        self.min_team_size, self.team_size, self
                    )
                }
            )

        self._verify_stint_min_max()
        combined_earnings_verified, info = self.verify_full_min_max()
        if not combined_earnings_verified:
            self._report_combined_earnings_violation(info)

    def post_save_clean(self):
        """
        Prevents circular references.

        Specifically, confirms backup :class:`StintSpecification` is not (in)directly connected to the current
        :class:`StintSpecification`.

        Raises:
            ValidationError: An error occuring if restrictions are violated.
        Notes:
            * Since circularity checks require that the current :class:`StintSpecification` have an id, they must be done
              post_save.
        """

        if not self._validate_not_circular():
            self.delete()
            raise ValidationError(
                {
                    'backup_stint_specification': 'Can not set specified backup_stint_specification of {},'
                    ' as it leads to a circular reference.'.format(self)
                }
            )

    def realize(self, user):
        """
        Create :class:`~ery_backend.stints.models.Stint` using parameters of current :class:`StintSpecification` instance.
        Send a signal to robot runner to create robot hands.

        Returns:
            :class:`~ery_backend.stints.models.Stint`

        Notes for discussion:
            - Hands can be assigned users/robots upon whatever join method we implement for experiment, which can select
              hand from available hands without user or robot.
        """
        stint = self.stint_definition.realize(self)
        grant_ownership(stint, user)

        return stint

    def get_dataset_variables(self):
        """
        Identify :class:`StintSpecificationVariable` values for matching
        :class:`~ery_backend.variables.models.VariableDefinition` objects using :class:`~ery_backend.datasets.models.Dataset`.

        Notes:
            - :class:`~ery_backend.variables.models.VariableDefinition` objects are matched to column headers by name.
            - A json serialized value is expected for a :class:`Dataset` cell when the matching :class:`VariableDefinition`
              object has a data_type of dictionary or list.
            - If more than one values row in the dataset, the last is used.

        Raises:
            - :class:`~ery_backend.base.exceptions.EryValidationError: Raise if no values rows in :class:`Dataset`.

        Returns:
            - Dict[Union[str, int]: Union[str, int, float, bool]]
        """
        from ery_backend.variables.models import VariableDefinition

        def _validate_row_count():
            if len(self.dataset.rows) < 1:
                raise EryValidationError(
                    f"{len(self.dataset.rows)} value rows found."
                    " There should be at one row (besides the header row), providing variable values)."
                )

        def _find_matches():
            names = self.dataset.headers
            matches = self.variables.filter(variable_definition__name__in=names).select_related('variable_definition')
            return matches.all()

        output = {}
        _validate_row_count()
        variables = _find_matches()
        values = self.dataset.rows[-1]
        for variable in variables:
            value = values.get(variable.variable_definition.name)
            if value is not None:
                if variable.variable_definition.data_type in (
                    VariableDefinition.DATA_TYPE_CHOICES.list,
                    VariableDefinition.DATA_TYPE_CHOICES.dict,
                ):
                    value = json.loads(value)
                key = variable.variable_definition.id
                output[key] = value
        return output

    # XXX: Address in issue #718
    # Integrate into stint.start such that stints get their specification var values directly from dataset when match
    # is found


class StintSpecificationRobot(EryPrivileged):
    """
    Specifies number of Robot instances associated to a :class:`StintSpecification`
    """

    # XXX: You need to do a custom clean for robot/stint_spec unique together, because the first is M2M.
    # See post_save clean.

    parent_field = 'stint_specification'
    # Make Below many to many such that a single stint spec can have different proportions of robots for various behaviors
    robots = models.ManyToManyField('robots.Robot', blank=False, related_name='stint_specification_robots')
    stint_specification = models.ForeignKey(
        'stint_specifications.StintSpecification',
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name='stint_specification_robots',
    )
    number = models.PositiveIntegerField(
        null=True, blank=True, help_text="Specifies the number of robots to include per stint specification."
    )
    robots_per_human = models.PositiveIntegerField(
        null=True, blank=True, help_text="Specifies the number of robots per human to include per stint specification."
    )

    def post_save_clean(self):
        for robot in self.robots.all():
            stint_specification_robots = StintSpecificationRobot.objects.filter(
                stint_specification=self.stint_specification, robots__in=[robot]
            ).count()
            if stint_specification_robots >= 2:
                self.delete()
                raise IntegrityError("StintSpecificationRobot already exists")


class StintSpecificationVariable(EryPrivileged):
    """
    Intermediate model conntecting :class:`StintSpecification` and :class:`~ery_backend.variables.models.VariableDefinition`.

    Used to specify the following:
        * WHAT DOES SET_TO_EVERY_NTH DO?
        * The value to use for setting the corresponding variable through
          :py:meth:`~ery_backend.variables.models.VariableDefinition.realize`.
    """

    class Meta(EryPrivileged.Meta):
        # XXX: Address in issue #815
        # unique_together = (('stint_specification', 'variable_definition'),)
        pass

    parent_field = "stint_specification"

    stint_specification = models.ForeignKey(
        'stint_specifications.StintSpecification',
        on_delete=models.CASCADE,
        related_name="variables",
        help_text="Connected :class:`StintSpecification`",
    )
    variable_definition = models.ForeignKey(
        'variables.VariableDefinition',
        on_delete=models.CASCADE,
        help_text="Connected :class:`~ery_backend.variables.models.VariableDefinition`",
    )

    set_to_every_nth = models.PositiveIntegerField(default=1, help_text='WHAT IS THIS FOR?')  # XXX
    value = JSONField(
        null=True,
        blank=True,
        help_text='Used to set value attribute of specified variable during initialization of its definition.',
    )

    @staticmethod
    def get_bxml_serializer():
        from .serializers import StintSpecificationVariableBXMLSerializer

        return StintSpecificationVariableBXMLSerializer

    def set_value(self, value):
        from google.cloud.datastore.entity import Entity

        if isinstance(value, Entity):
            value = dict(value)
        self.value = self.variable_definition.cast(value)
        self.save()

    def clean(self):
        """
        Confirm value data_type matches corresponding :class:`~ery_backend.variables.models.VariableDefinition` data_type.

        Raises:
            TypeError: Raise if requirements are violated.
        """
        if self.value:
            self.value = self.variable_definition.cast(self.value)
        super().clean()


class StintModuleSpecification(ModuleDefinitionModelMixin, EryPrivileged):
    """
    Holds timeout and payment related specifications for a :class:`~ery_backend.modules.models.Module` in a
    :class:`~ery_backend.stints.models.Stint`.

    Notes:
        - A :class:`StintModuleSpecification` only applies to :class:`~ery_backend.modules.models.Module` instances created \
          via its parental :class:`StintSpecification`.
    """

    parent_field = 'stint_specification'
    stint_specification = models.ForeignKey(
        'stint_specifications.StintSpecification',
        on_delete=models.CASCADE,
        related_name='module_specifications',
        help_text="Parental :class:`StintSpecification`",
    )
    hand_timeout = models.PositiveIntegerField(
        default=0, help_text="Number of seconds before status of :class:`~ery_backend.hands.models.Hand` is set to 'quit'."
    )
    hand_warn_timeout = models.PositiveIntegerField(
        default=0,
        help_text="Number of seconds before warning :class:`~ery_backend.users.models.User` about"
        " :class:`~ery_backend.hands.models.Hand` timeout",
    )
    stop_on_quit = models.BooleanField(
        default=True,
        help_text="Determines whether :class:`~ery_backend.stints.models.Stint` status should be set to"
        " 'canceled' if :class:`~ery_backend.hands.models.Hand` instance quits or times out.",
    )
    min_earnings = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Minimum possible earnings per :class:`~ery_backend.hands.models.Hand` for"
        " :class:`~ery_backend.modules.models.Module`",
    )
    max_earnings = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Maximum possible earnings per :class:`~ery_backend.hands.models.Hand` for"
        " :class:`~ery_backend.modules.models.Module`",
    )
    timeout_earnings = models.FloatField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Amount earned on timeout during" " :class:`~ery_backend.modules.model.Module`",
    )

    def _verify_inner_min_max(self):
        if self.min_earnings > self.max_earnings:
            raise ValueError(
                f"Minimum earnings: {self.min_earnings}, exceed maximum earnings: {self.max_earnings}, for "
                f" {self.module_definition}."
            )

    def _report_post_save_violation(self, info):
        if info['reason'] == 'min':
            reason = 'minimum'
            total = info['total_min_earnings']
            stint_total = self.stint_specification.min_earnings
        else:
            reason = 'maximum'
            total = info['total_max_earnings']
            stint_total = self.stint_specification.max_earnings
        raise ValueError(
            f"Total {reason} earnings: {total}, combination of StintModuleSpecification"
            f" level minimum earnings, exceed minimum earnings: {stint_total}, declared at the"
            f" StintSpecification level for {self.stint_specification.stint_definition}."
        )

    def clean(self):
        """
        Confirms earnings configuration rules are not violates.

        Specifically:
            - Minimum earnings may not exceed maximum earnings.

        Raises:
            ValueError: Raised if requirements are violated.
        """
        self._verify_inner_min_max()
        self.stint_specification.clean()

    def post_save_clean(self):
        """
        Clean functionality performed after save.

        Notes:
            - Conventional reason for use: Since queryset checks require current :class:`StintModuleSpecification` have an id,
              they must be done post save.

        Raises:
            :class:`~ery_backend.base.exceptions.ValueError`: Raised if :class:`StintModuleSpecification` level earnings
            combinations exceed bounds set by parental :class:`StintSpecification`.
        """
        verified, info = self.stint_specification.verify_full_min_max()
        if not verified:
            self.delete()
            self._report_post_save_violation(info)
