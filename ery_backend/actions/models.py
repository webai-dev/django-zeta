"""Contains models for defining actions that may be triggered by hands in stints."""
from django.core.exceptions import ValidationError
from django.db import models

from model_utils import Choices

from ery_backend.base.models import EryPrivileged
from ery_backend.modules.models import ModuleDefinitionNamedModel
from ery_backend.scripts import engine_client

from ery_backend.variables.models import VariableDefinition

from .exceptions import EryActionError


class Action(ModuleDefinitionNamedModel):
    """
    Container for process(es) to be run during a :class:`~ery_backend.stints.models.Stint`.

    The specific process run by an :class:`Action` are declared in its :class:`ActionStep` objects.
    """

    class SerializerMeta(ModuleDefinitionNamedModel.SerializerMeta):
        model_serializer_fields = ('steps',)

    parent_field = 'module_definition'

    # XXX: Address in issue #677
    # def _is_circular(self, actions=None):
    # """Confirm no direct, or indirect, circular relationship exists between any ActionStep and this Action."""
    # if not actions:
    #     actions = [self]
    # else:
    #     if self in actions:  # Current Action is already part of chain of ActionSteps, indicating circularity
    #         return True
    #     actions.append(self)
    # # Follow each child ActionStep chain for circularity
    # for actionstep in self.steps.all():
    #     if actionstep.subaction:
    #         result = actionstep.subaction._is_circular(actions)  # pylint: disable=protected-access
    #         if result:
    #             return result
    # return False
    # return False

    # Inheriting docstring
    def duplicate(self, name=None):
        """
        Creates a duplicate of current instance, as well as all of its children.

        Args:
            - name: If specified, the new name that will be used instead of the original. \
              Otherwise, {original_name}_copy is used.

        Returns:
            :class:`Action`: A duplicated instance, with option of modifying attributes.

        Notes:
          - Expands :py:meth:`ery_backend.base.models.NamedMixin.duplicate` in order to handle
            :class:`ActionStep` set, which is ignored in the default nested_create.
        """
        if not name:
            name = '{}_copy'.format(self.name)
        return super().duplicate(name)

    def run(self, hand):
        """
        Execute all :class:`ActionStep` objects (in order).

        Args:
            hand (:class:`~ery_backend.hands.models.Hand`): Provides context for all :class:`ActionStep` objects.
        """
        socket_message_args = []
        action_start_message = "action: {}, started on hand with id: {}".format(self.name, hand.id)
        hand.stint.log(action_start_message, system_only=True)
        for action_step in self.steps.all():
            start_message = "actionstep: {}, started for action: {}, on hand with id: {}".format(
                action_step.action_type, self.name, hand.id
            )
            hand.stint.log(start_message, system_only=True)
            socket_message_args += action_step.run(hand)
            end_message = "actionstep: {}, completed for action: {}, on hand with id: {}".format(
                action_step.action_type, self.name, hand.id
            )
            hand.stint.log(end_message, system_only=True)

        action_end_message = "action: {}, completed on hand with id: {}".format(self.name, hand.id)
        hand.stint.log(action_end_message, system_only=True)
        return socket_message_args


class ActionStep(EryPrivileged):
    """
    Executes one process via run method.

    Specifically:
      - Process is specified via "action_type" for each \
        :class:`~ery_backend.hands.models.Hand` or :class:`~ery_backend.teams.models.Team` \
        in specified scope.
      -  Process is only run if its associated \
        :class:`~ery_backend.conditions.models.Condition` evaluates as true.

    Available Process:
        -  Instantiate a Variable (i.e., :class:`~ery_backend.variables.models.HandVariable`, \
          :class:`~ery_backend.variables.models.TeamVariable`, \
          :class:`~ery_backend.variables.models.ModuleVariable`, \
          :class:`~ery_backend.variables.models.StintVariable`).
        -  Transition :class:`~ery_backend.syncs.models.Era`.
        -  Transition :class:`~ery_backend.stages.models.Stage`.
        -  Log a message.
        -  Execute a block of JavaScript code.
        -  Save :class:`~ery_backend.modules.models.Module` related output data.
        -  Execute another :class:`Action`.
    """

    class Meta(EryPrivileged.Meta):
        ordering = ('order',)

    # Defines which Hands/Teams should run
    FOR_EACH_CHOICES = Choices(
        ('current_hand_only', "Current Hand Only"),
        ('hand_in_neighborhood', "Hand in Neighborhood"),  # Neighborhood meaning Social Network
        ('hand_in_team', "Hand in Team"),
        ('hand_in_stint', "Hand in Stint"),
        ('team_in_stint', "Team in Stint"),
    )

    ACTION_TYPE_CHOICES = Choices(
        ('set_variable', "Set Variable"),
        ('set_era', "Set Era"),
        ('run_code', "Run Code"),
        ('log', "Log"),
        ('save_data', "Save Data"),
        ('subaction', "Subaction"),
        ('pay_users', "Pay Users"),
        ('quit', 'Quit'),
    )

    parent_field = 'action'
    action = models.ForeignKey('actions.Action', on_delete=models.CASCADE, related_name='steps')
    order = models.IntegerField(default=0)
    condition = models.ForeignKey(
        'conditions.Condition', on_delete=models.SET_NULL, null=True, blank=True, related_name='conditional_steps'
    )
    invert_condition = models.BooleanField(default=False)
    for_each = models.CharField(max_length=50, choices=FOR_EACH_CHOICES, default='current_hand_only')
    action_type = models.CharField(max_length=50, choices=ACTION_TYPE_CHOICES)
    to_save = models.ManyToManyField('variables.VariableDefinition', blank=True, related_name='saved_via')
    variable_definition = models.ForeignKey(
        'variables.VariableDefinition', on_delete=models.CASCADE, null=True, blank=True, related_name='setting_action_steps'
    )
    value = models.CharField(max_length=4096, null=True, blank=True)  # For set_variable
    code = models.TextField(null=True, blank=True)  # For run_code
    era = models.ForeignKey(
        'syncs.Era', on_delete=models.CASCADE, null=True, blank=True, related_name='setting_action_steps'
    )  # For set_era
    log_message = models.CharField(max_length=512, null=True, blank=True)  # For log
    subaction = models.ForeignKey(
        'actions.Action', on_delete=models.CASCADE, null=True, blank=True, related_name='super_actions'
    )  # For subaction

    def __str__(self):
        return f"{self.action}-Step:{self.order}"

    def _interpret_value(self, hand):
        """
        Uses EryEngine to evaluate Javascript code present in value attribute.
        """
        return engine_client.evaluate_without_side_effects(str(self), self.value, hand)

    # pylint:disable=too-many-branches
    def clean(self):
        """
        Default django method, with additional enforcement of required attribute combinations.

        Raises:
            :class:`~ery_backend.base.exceptions.ValidationError`: Raised if attribute combinations are violated.
        """
        super().clean()
        if self.action_type == ActionStep.ACTION_TYPE_CHOICES.run_code and not self.code:
            raise ValidationError(
                {
                    'code': "If action_type == '{}', code is required for {}".format(
                        ActionStep.ACTION_TYPE_CHOICES.run_code, self
                    )
                }
            )

        # XXX: Address in issue #813
        # if self.action_type == ActionStep.ACTION_TYPE_CHOICES.set_era and not self.era:
        #     raise ValidationError(
        #         {
        #             'era': "If action_type == '{}', an era is required for {}".format(
        #                 ActionStep.ACTION_TYPE_CHOICES.set_era, self
        #             )
        #         }
        #     )

        if self.action_type == ActionStep.ACTION_TYPE_CHOICES.log and not self.log_message:
            raise ValidationError(
                {
                    'log_message': "If action_type == '{}', a log message is required for {}".format(
                        ActionStep.ACTION_TYPE_CHOICES.log, self
                    )
                }
            )

        # XXX: Address in issue #813
        # if self.action_type == ActionStep.ACTION_TYPE_CHOICES.subaction and not self.subaction:
        #     raise ValidationError(
        #         {
        #             'subaction': "If action_type == '{}', a subaction is required for {}".format(
        #                 ActionStep.ACTION_TYPE_CHOICES.subaction, self
        #             )
        #         }
        #     )

        if self.action_type == ActionStep.ACTION_TYPE_CHOICES.set_variable:
            #     if not self.variable_definition:
            #         raise ValidationError(
            #             {
            #                 'variable_definition': "If action_type == '{}', a variable_definition is required for {}".format(
            #                     ActionStep.ACTION_TYPE_CHOICES.set_variable, self
            #                 )
            #             }
            #         )
            if self.value is None:
                raise ValidationError(
                    {
                        'value': "If action_type == '{}', a value is required for {}".format(
                            ActionStep.ACTION_TYPE_CHOICES.set_variable, self
                        )
                    }
                )

        if self.action_type == ActionStep.ACTION_TYPE_CHOICES.quit:
            if not self.for_each == ActionStep.FOR_EACH_CHOICES.current_hand_only:
                raise ValidationError(
                    {
                        'action_type': f"If action_type == '{self.action_type}', for_each must be"
                        f" '{self.FOR_EACH_CHOICES.current_hand_only}'. "
                    }
                )
        if self.action_type == ActionStep.ACTION_TYPE_CHOICES.pay_users:
            if self.for_each != ActionStep.FOR_EACH_CHOICES.hand_in_stint:
                raise ValidationError(
                    {
                        'for_each': f"If action_type == '{ActionStep.ACTION_TYPE_CHOICES.pay_users}', for_each must be ' \
                    {ActionStep.FOR_EACH_CHOICES.hand_in_stint}'"
                    }
                )

        # XXX: Address in issue #677
        # if self.action == self.subaction:
        #     raise ValidationError({
        #         'subaction': "Cannot create current action step. It uses the same action and subaction, "
        #                      "leading to a circular reference for {}.".format(self)
        #     })

    # XXX: Address in issue #677
    # def post_save_clean(self):
    #     """
    #     Clean functionality performed after save.

    #     Notes:
    #         - Conventional reason for use: Since circularity checks require current ActionStep have an id,
    #            they must be done post save.

    #     Raises:
    #         :class:`~ery_backend.base.exceptions.ValidationError`: Raised if attribute combinations are violated.

    #     """
    #     if self.subaction:
    # result = self.subaction._is_circular()  # pylint: disable=protected-access
    # if result:
    #     self.delete()
    #     raise ValidationError(
    #         {'subaction': "Cannot create current action step. Adding the current action step would cause "
    #                       "a circular reference, where the subaction: Action {}, id: {} (the current action "
    #                       "step's subaction) eventually contains an actionstep referencing itself as the "
    #                       "subaction.".format(self, self.id)
    #         }
    #     )

    def _run_part_conditionally(self, hand=None, team=None):
        """
        Run :class:`ActionStep` given true evaluation of corresponding :class:`~ery_backend.conditions.models.Condition`.

        Note:
            - An :class:`ActionStep` may return a list of messages to forward over websocket for the
              web :class:`~ery_backend.frontends.models.Frontend`. As such, an empty list is returned
              if the :class:`ActionStep` is not run.
        """
        do_run = self.condition.evaluate(hand, team) if self.condition is not None else True

        if self.invert_condition:
            do_run = not do_run

        # XXX: Properly test all of these changes in issue #688
        return self._run_part(hand, team) if do_run else []

    # pylint:disable=too-many-branches
    def _run_part(self, hand=None, team=None):
        """
        Execute predefined action_type if Condition satisfied.
        """
        from ery_backend.stints.models import Stint

        socket_message_args = []
        try:
            if self.action_type == ActionStep.ACTION_TYPE_CHOICES.log:
                from ..logs.models import Log

                hand.stint.log(self.log_message, Log.LOG_TYPE_CHOICES.info)
            elif self.action_type == ActionStep.ACTION_TYPE_CHOICES.set_variable:
                value = self._interpret_value(hand)  # separated due to issues with mocking
                variable, changed = hand.stint.set_variable(self.variable_definition, value, hand, team)
                if changed:
                    socket_message_args.append(variable)
            elif self.action_type == ActionStep.ACTION_TYPE_CHOICES.set_era:
                hand.set_era(self.era)
            elif self.action_type == ActionStep.ACTION_TYPE_CHOICES.subaction:
                socket_message_args += self.subaction.run(hand=hand)
            elif self.action_type == ActionStep.ACTION_TYPE_CHOICES.save_data:
                hand.stint.save_output_data(self, hand)
            elif self.action_type == ActionStep.ACTION_TYPE_CHOICES.quit:
                from ery_backend.base.utils import opt_out

                opt_out(hand)
            elif self.action_type == ActionStep.ACTION_TYPE_CHOICES.pay_users:
                hand.pay(self)
            elif self.action_type == ActionStep.ACTION_TYPE_CHOICES.run_code:
                actor = hand if hand else team
                engine_client.evaluate(f'run_code_on_{actor}', hand, self.code)
            return socket_message_args
        except Exception as e:
            hand.stint.set_status(Stint.STATUS_CHOICES.panicked)
            raise EryActionError(self, e, hand)

    def run(self, hand):
        """
        Use predefined for_each to execute :class:`ActionStep` at specific scope.

        Args:
            hand (:class:`~ery_backend.hands.models.Hand`): Provides context for :class:`ActionStep` objects.
        """
        socket_message_args = []
        if self.for_each == ActionStep.FOR_EACH_CHOICES.current_hand_only:
            socket_message_args += self._run_part_conditionally(hand)
        # XXX: Add socket_message_args flow for more than just hand
        elif self.for_each == ActionStep.FOR_EACH_CHOICES.hand_in_neighborhood:
            pass
        elif self.for_each == ActionStep.FOR_EACH_CHOICES.hand_in_team:
            team_members = hand.current_team.hands.all()
            for team_hand in team_members:
                self._run_part_conditionally(team_hand)
        elif self.for_each == ActionStep.FOR_EACH_CHOICES.hand_in_stint:
            for stint_hand in hand.stint.hands.all():
                self._run_part_conditionally(stint_hand)
        elif self.for_each == ActionStep.FOR_EACH_CHOICES.team_in_stint:
            for team in hand.stint.teams.all():
                self._run_part_conditionally(team)

        return socket_message_args

    def get_to_save(self, stint):
        """
        Return the :class:`~ery_backend.variables.models.VariableDefinition` object(s)
        that should be saved to Google Datastore.

        Returns:
            :class:`django.db.models.query.Queryset`: set of
            :class:`~ery_backend.variables.models.VariableDefinition` objects.
        """
        if self.to_save.exists():
            return self.to_save

        module_definitions = stint.stint_specification.stint_definition.module_definitions
        return VariableDefinition.objects.filter(module_definition__in=module_definitions.all()).filter(is_output_data=True)
