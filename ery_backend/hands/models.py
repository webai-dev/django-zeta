import datetime as dt
import logging

from django.db import models
from django.core.exceptions import ValidationError

from languages_plus.models import Language
from model_utils import Choices
import pytz

from ery_backend.base.mixins import LogMixin
from ery_backend.stints.models import StintModel
from ery_backend.stint_specifications.models import StintModuleSpecification

logger = logging.getLogger(__name__)


class Hand(LogMixin, StintModel):
    """
    Represents the worker (:class:`~ery_backend.hands.models.User` or :class:`~ery_backend.hands.models.Robot`) participating
    in a given :class:`~ery_backend.stints.models.Stint`.

    Attributes:
        - STATUS_CHOICES (Tuple): Specify the possible states of :class:`Hand`.
    Notes:
        - Can belong to many teams through :class:`TeamHand`.
    """

    class Meta(StintModel.Meta):
        unique_together = (('user', 'stint'),)

    STATUS_CHOICES = Choices(
        ('active', "Active"), ('timedout', "Timed Out"), ('quit', "Quit"), ('finished', "Finished"), ('cancelled', "Cancelled")
    )
    # assigned during StintSpecification.realize
    stint = models.ForeignKey(
        'stints.Stint', on_delete=models.CASCADE, null=True, blank=True, help_text="Parental instance", related_name='hands'
    )
    # users, robots, teams, eras, modules, and stages should never be deleted during runtime,
    # when hands exist, so on_delete should not matter
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, null=True, blank=True, related_name='human_hands')
    robot = models.ForeignKey('robots.Robot', on_delete=models.CASCADE, null=True, blank=True, related_name='robot_hands')
    current_team = models.ForeignKey(
        'teams.Team',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='current_hands',
        help_text="Current grouping (with other :class:`Hand` instances) in :class:`~ery_backend.stints.models.Stint`",
    )
    current_module = models.ForeignKey(
        'modules.Module',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='current_hands',
        help_text="Used in multi :class:`~ery_backend.modules.models.Module` :class:`~ery_backend.stints.models.Stint` to"
        " proceed from one :class:~ery_backend.modules.models.Module` to the next.",
    )
    current_payoff = models.FloatField(default=0)
    # current_breadcrumb should be replaced via stage.delete, even though attribute is nullable
    current_breadcrumb = models.OneToOneField(
        'stages.StageBreadcrumb',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='current_hand',
        help_text="Last traversed instance",
    )
    # triggers changes to team via set_era
    # assigned during StintDefinition.realize
    era = models.ForeignKey(
        'syncs.Era',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='hands',
        help_text="Used to synchronize progression through :class:`~ery_backend.stints.models.Stint` with other :class:`Hand`"
        " instances",
    )
    # assigned during StintDefinition.realize
    stage = models.ForeignKey(
        'stages.Stage',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='hands',
        help_text="Current position in :class:`~ery_backend.stints.models.Stint`",
    )
    last_seen = models.DateTimeField(null=True, blank=True, help_text="Used for inactivity timeouts")
    status = models.CharField(
        max_length=24, choices=STATUS_CHOICES, null=True, blank=True, help_text="Indicates current state of :class:`Hand`"
    )
    frontend = models.ForeignKey(
        'frontends.Frontend', on_delete=models.CASCADE, default=3, help_text="Current client frontend", related_name='hands'
    )
    language = models.ForeignKey(Language, on_delete=models.PROTECT, default='en')

    def __str__(self):
        if self.robot is not None:
            return f"{self.stint}-Hand-{self.robot}"
        return f"{self.stint}-Hand-{self.user}"

    @property
    def name(self):
        return "Hand: {}".format(self.stint.stint_specification.name)

    @property
    def current_module_definition(self):
        """
        Convenience method for obtaining currently connected :class:`~ery_backend.modules.models.ModuleDefinition`.

        Returns:
            :class:`~ery_backend.modules.models.ModuleDefinition`: Parent of :class:`Hand` instance's current_module.

        """
        return self.current_module.stint_definition_module_definition.module_definition

    @property
    def stint_definition(self):
        """
        Convenience method for obtaining connected :class:`~ery_backend.stints.models.StintDefinition`.

        Returns:
            :class:`~ery_backend.stints.models.StintDefinition`: Parent of :class:`Hand` instance's stint.
        """
        return self.stint.stint_specification.stint_definition

    def clean(self):
        """
        Default django method, with additional enforcement of prohibited attribute combinations.

        Raises:
            :class:`ValidationError`: Raised via prohibited attribute combinations.
        """
        super().clean()
        if self.user and self.robot:
            raise ValidationError(
                {'user': "Can not specify both user ({}) and robot ({}) to Hand".format(self.user, self.robot)}
            )

    def _log_attribute_change(self, attribute, value):
        message = (
            f"Set {attribute}: {value}, for hand: {self.id}, of stint: {self.stint.id},"
            f" with definition name: {self.stint.stint_specification.stint_definition.name}"
        )
        self.stint.log(message, system_only=True)

    def set_era(self, era):
        """
        Change :class:`~ery_backend.syncs.models.Era` attribute and log details.

        Args:
            era (:class:`~ery_backend.syncs.models.Era`): New attribute value.

        Notes:
            - If :class:`Hand` belongs to a larger body (:class:`Team`/:class:`~ery_backend.stints.models.Stint`), \
              is the last member of that group to change to a new :class:`~ery_backend.syncs.models.Era`, and changes to a \
              new :class:`~ery_backend.syncs.models.Era` shared by all :class:`Hand` instances in said group, the \
              :class:`~ery_backend.syncs.models.Era` of the larger group will also change.
        """
        self.era = era
        self.save()
        self._log_attribute_change('Era', era)
        if self.current_team is not None:
            self.current_team.synchronize(era)

    # XXX: Address in issue #505
    def set_status(self, status):
        """
        Change status attribute.

        Args:
            status (str): New attribute value.

        Raises:
            ValueError: If designated status is not present in :py:meth:`Hand.STATUS_CHOICES`.
        """
        from ery_backend.stints.models import Stint

        if status not in Hand.STATUS_CHOICES:
            raise ValueError(f"'{status}' is not present in STATUS_CHOICES.")
        self.status = status
        self.save()
        if status != self.STATUS_CHOICES.active:
            # XXX: Must be reimplemented
            # self.pay()
            statuses = list(self.stint.hands.order_by('status').distinct('status').values_list('status', flat=True))
            if (
                self.STATUS_CHOICES.active not in statuses
                and self.stint.status != Stint.STATUS_CHOICES.cancelled
                and not self.stint.stint_specification.late_arrival
            ):
                self.stint.set_status(Stint.STATUS_CHOICES.cancelled)

    # XXX: Address in issue #505
    def set_stage(self, stage=None, stage_definition=None):
        """
        Change :class:`~ery_backend.stages.models.Stage` attribute and log details.

        Args:
            stage_definition: (:class:~ery_backend.stages.models.StageDefinition`): Used to instantiate \
               :class:`~ery_backend.stages.models.Stage` to be set as new attribute value.
            stage: (:class:~ery_backend.stages.models.Stage`): New attribute value.

        Notes:
            - If intended :class:`~ery_backend.stages.models.Stage` instance's \
              :class:`~ery_backend.stages.models.StageDefinition` has end_stage=True, and the parental \
              :class:`~ery_backend.stints.models.Stint` has a following :class:`~ery_backend.modules.models.Module`, the \
              start :class:`~ery_backend.stages.models.Stage` of said :class:`~ery_backend.modules.models.Module` will be
              used as a replacement.
        """
        if stage_definition is None:
            next_stage_definition = stage.stage_definition
        else:
            next_stage_definition = stage_definition

        current_module_definition = self.current_module_definition
        if next_stage_definition.end_stage:
            next_module = self.get_next_module()
            if next_module:
                next_stage_definition = next_module.module_definition.start_stage
            else:
                self.set_status(Hand.STATUS_CHOICES.finished)
        if not stage:
            stage = next_stage_definition.realize()

        new_module_definition = current_module_definition != next_stage_definition.module_definition
        if new_module_definition:
            self.set_module(
                self.stint.modules.get(
                    stint_definition_module_definition__module_definition=next_stage_definition.module_definition
                )
            )

        if not stage.preaction_started and stage.stage_definition.pre_action:
            stage.run_preaction(self)
        old_stage = self.stage
        self.stage = stage
        self.save()

        self._log_attribute_change('Stage', self.stage)

        changed = [next_stage_definition.module_definition, stage] if new_module_definition else None
        if not changed:
            if not old_stage or old_stage != stage:
                changed = stage
        return stage, changed

    def set_module(self, module):
        """
        Change :class:`~ery_backend.modules.models.Module` attribute and log details.

        Args:
            module (:class:~ery_backend.module.models.Module`): New attribute value.
            index (int): Update (using order in :class:`~ery_backend.stints.models.StintDefinitionModuleDefinition` set)
              position of current :class:`~ery_backend.modules.models.Module`.
        """
        previous_module = self.current_module
        self.current_module = module
        self.save()

        changed = previous_module != module
        self._log_attribute_change('Current Module', module)

        return module, changed

    def create_breadcrumb(self, stage):
        """
        Add new :class:`~ery_backend.stages.models.StageBreadCrumb` instance, while updating references on pre-existing
        instance belonging to :class:`Hand`.

        Args:
            hand (:class:`Hand`): Instance owning new :class:`~ery_backend.stages.models.StageBreadCrumb`.
            stage (:class:`Stage`): Data for new :class:`~ery_backend.stages.models.StageBreadCrumb`.
        """
        from ery_backend.stages.models import StageBreadcrumb, StageDefinition

        last_crumb = None
        if self.current_breadcrumb:
            last_crumb = self.current_breadcrumb
        new_crumb = StageBreadcrumb.objects.create(hand=self, stage=stage)
        if new_crumb.stage.stage_definition.breadcrumb_type in [
            StageDefinition.BREADCRUMB_TYPE_CHOICES.back,
            StageDefinition.BREADCRUMB_TYPE_CHOICES.all,
        ]:
            new_crumb.previous_breadcrumb = last_crumb
            new_crumb.save()
        if last_crumb and last_crumb.stage.stage_definition.breadcrumb_type == StageDefinition.BREADCRUMB_TYPE_CHOICES.all:
            last_crumb.next_breadcrumb = new_crumb
            last_crumb.save()
        return new_crumb

    def set_breadcrumb(self, breadcrumb):
        """"
        Change :class:`~ery_backend.stages.models.StageBreadcrumb` attribute and log details.

        Args:
            breadcrumb (:class:`~ery_backend.stage.models.StageBreadcrumb`).
        """
        self.current_breadcrumb = breadcrumb
        self.save()
        self._log_attribute_change('Current Breadcrumb', breadcrumb)

    def get_variable(self, variable_definition):
        """
        Get :class:`~ery_backend.variables.models.HandVariable` using :class:`Hand` and
        :class:`~ery_backend.variables.models.VariableDefinition`.

        Notes:
            - If :class:`~ery_backend.variables.models.VariableDefinition` does not have scope 'hand', will return None.
        """
        from ery_backend.variables.models import HandVariable

        return HandVariable.objects.get(hand=self, variable_definition=variable_definition)

    def _get_order_set(self):
        stint_definition = self.current_module.stint_definition_module_definition.stint_definition
        return stint_definition.stint_definition_module_definitions.values_list("order", flat=True)

    def _get_current_order(self):
        return self.current_module.stint_definition_module_definition.order

    def get_current_index(self):
        """Index of this :class:`Hand`s :class:`~ery_backend.modules.models.Module`"""
        order = self._get_current_order()
        return list(self._get_order_set()).index(order)

    def get_next_module(self):
        """
        Get next :class:`~ery_backend.modules.models.Module` (if exists).

        Notes:
            - If the current :class:`~ery_backend.modules.models.Module` is the last in the parent :class:`Stint`
              instance's set, nothing is returned.

        Returns:
            Tuple(:class:`~ery_backend.modules.models.Module`, int): Next object in set (if available).

            int: Index (using order in :class:`~ery_backend.stints.models.StintDefinitionModuleDefinition` set)
            position of current :class:`~ery_backend.modules.models.Module`.
        """
        current_order = self._get_current_order()
        next_order_q = self._get_order_set().filter(order__gt=current_order).order_by("order")
        if next_order_q:
            next_order = next_order_q.first()
            return self.stint.modules.get(stint_definition_module_definition__order=next_order)
        return None

    def opt_out(self):
        """
        Sets :class:`Hand` status to 'quit'.

        Used by EryRunner on reception of text message with opt-out code.
        """
        self.set_status(Hand.STATUS_CHOICES.quit)

    def update_last_seen(self):
        """
        Sets last_seen attribute to current time in UTC.
        """
        self.last_seen = dt.datetime.now(pytz.UTC)
        self.save()

    def get_payoff(self, module=None):
        """
        Get sum of all payoff :class:`~ery_backend.variables.models.VariableMixin` variables belonging to
        :class:`~ery_backend.hands.models.Hand`.

        Args:
            module Optional[(:class:`~ery_backend.modules.models.Module`): If specified constrains \
              :class:`~ery_backend.variables.models.VariableMixin` variables to given \
              :class:`~ery_backend.modules.models.Module`.

        Returns:
            float: Amount to be paid.
        """
        full_pay_q = self.variables.filter(variable_definition__is_payoff=True).values_list('value', flat=True)
        if module:
            full_pay_q = full_pay_q.filter(module=module)
            full_pay = sum(full_pay_q)
            module_definition = module.stint_definition_module_definition.module_definition
            stint_specification = self.stint.stint_specification
            stint_module_specification_q = StintModuleSpecification.objects.filter(
                stint_specification=stint_specification, module_definition=module_definition
            )
            if stint_module_specification_q:
                stint_module_specification = stint_module_specification_q.first()
                # pylint:disable=no-else-return
                if stint_module_specification.min_earnings is not None and full_pay < stint_module_specification.min_earnings:
                    return stint_module_specification.min_earnings
                elif (
                    stint_module_specification.max_earnings is not None and full_pay > stint_module_specification.max_earnings
                ):
                    return stint_module_specification.max_earnings
        else:
            full_pay = sum(full_pay_q)
            # pylint:disable=no-else-return
            if (
                self.stint.stint_specification.min_earnings is not None
                and full_pay < self.stint.stint_specification.min_earnings
            ):
                return self.stint.stint_specification.min_earnings
            elif (
                self.stint.stint_specification.max_earnings is not None
                and full_pay > self.stint.stint_specification.max_earnings
            ):
                return self.stint.stint_specification.max_earnings
        return full_pay

    def _update_payoff(self, amount):
        self.current_payoff += amount
        self.save()

    def back(self):
        """
        Initiates back action using the current :class:`~ery_backend.stages.models.StageBreacrumb`.
        """
        from ery_backend.stages.models import StageDefinition

        socket_message_args = []  # Used to generate external web socket messages

        crumb_choices = StageDefinition.BREADCRUMB_TYPE_CHOICES
        if self.stage.stage_definition.breadcrumb_type in (crumb_choices.back, crumb_choices.all):
            previous_breadcrumb = self.current_breadcrumb.previous_breadcrumb
            if previous_breadcrumb:
                changed = self.set_stage(previous_breadcrumb.stage)[1]
                if changed:
                    socket_message_args.append(changed)
                self.set_breadcrumb(previous_breadcrumb)

        return socket_message_args

    def submit(self):
        """
        Initiates submit action for the current :class:`~ery_backend.stages.models.Stage`.
        """
        from ery_backend.stages.models import StageDefinition

        socket_message_args = []  # Used to generate external web socket messages

        stage_definition = self.stage.stage_definition
        if stage_definition.redirect_on_submit:
            if (
                stage_definition.breadcrumb_type == StageDefinition.BREADCRUMB_TYPE_CHOICES.all
                and self.current_breadcrumb.next_breadcrumb
            ):
                changed = self.set_stage(self.current_breadcrumb.next_breadcrumb.stage)[1]
                if changed:
                    socket_message_args.append(changed)
                self.set_breadcrumb(self.current_breadcrumb.next_breadcrumb)
            else:
                changed = self.set_stage(stage_definition=stage_definition.get_redirect_stage(self))[1]
                if changed:
                    socket_message_args.append(changed)
                new_breadcrumb = self.create_breadcrumb(self.stage)
                self.set_breadcrumb(new_breadcrumb)
        return socket_message_args

    def pay(self, action_step=None):
        """
        Distribute money to :class:`~ery_backend.hands.models.Hand` instances.

        Args:
            - action_step (:class:`~ery_backend.actions.models.ActionStep`): Instance executing current method.
        """
        from ery_backend.scripts.ledger_client import send_payment

        # XXX: Address in issue #505
        payoff = self.get_payoff()
        message = f"Distributed ${payoff} from {self.stint.started_by} to {self.user}"

        if action_step:
            message += f" during action_step with id: {action_step.id}."
        else:
            message += f" through stint: {self.stint}."
        send_payment(payoff, self, action_step)
        self._update_payoff(payoff)
        for hand_variable in self.variables.filter(variable_definition__is_payoff=True).all():
            hand_variable.reset_payoff()
        self.stint.log(message, system_only=True)

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
        super().log(
            message,
            {'stint': self.stint, 'module': self.current_module, 'team': self.current_team, 'hand': self},
            logger,
            log_type,
            system_only,
        )
