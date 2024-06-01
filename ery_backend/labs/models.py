# As of 2018-09-12, pylint claims variable hand is undefined.
# pylint:disable=undefined-variable
from uuid import uuid4

from django.db import models

from ery_backend.base.exceptions import EryValueError
from ery_backend.base.mixins import PrivilegedMixin
from ery_backend.base.models import EryNamedSlugged

from .utils import get_or_create_user


class Lab(EryNamedSlugged, PrivilegedMixin):
    """
    Environment for monitoring :class:`~ery_backend.stints.models.Stint` as an administrator.

    Notes:

        - Labs are accessed via behavery/lab/id. Any authenticated user accessing the lab is \
          thrown into whatever was started in that lab, so long as a spot for said :class:`~ery_backend.users.models.User` \
          already exists or an empty spot is available.

        - The :class:`~ery_backend.stints.models.Stint` hosted in a :class:`Lab` can be started, stopped, and changed manually
          by the :class:`Lab` instance's administrator.
    """

    # Since lab is a runtime model, its attributes should never be deleted while in use, so on_delete is irrelevant
    current_stint = models.ForeignKey(
        'stints.Stint',
        related_name='lab_currentstint',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Instance intended for execution",
    )
    secret = models.CharField(max_length=36, unique=True, help_text="User facing unique identifier")

    def _set_secret(self):
        secret = str(uuid4())
        if not Lab.objects.filter(secret=secret).exists():
            self.secret = secret
        else:
            self._set_secret()

    def set_stint(self, stint_specification_id, user):
        """
        Assigns a :class:`~ery_backend.stints.models.Stint` from
        :class:`~ery_backend.stint_specifications.models.StintSpecification`.

        Args:
            stint_specification_slug (str): Used to get :class:`ery_backend.stint_specifications.models.StintSpecification`.
        """
        from ..stint_specifications.models import StintSpecification

        stint_specification = StintSpecification.objects.get(id=stint_specification_id)
        self.current_stint = stint_specification.realize(user)

        message = (
            f'Stint with StintDefinition: {self.current_stint.stint_specification.stint_definition.name},'
            f' set by User: {user.username} to Lab: {self.name}'
        )

        self.current_stint.log(message, system_only=True)
        self.current_stint.lab = self
        self.current_stint.save()
        self.save()

    # XXX: Address in issue #104
    def start(self, hand_n, started_by, signal_pubsub=True):
        """
        Initializes a new :class:`Stint` with specified set of :class:`~ery_backend.hands.models.Hand` objects.

        Args:
            stint_specification_slug (str): Used to get :class:`ery_backend.stint_specifications.models.StintSpecification`.
            hand_n: Number of :class:`~ery_backend.hands.models.Hand` objects to assign to
              :class:`~ery_backend.stints.models.Stint`.
            started_by (:class:`ery_backend.users.models.User`): Recorded initiator of generated
              :class:`~ery_backend.stints.models.Stint`.
            signal_pubsub (bool): Whether to send a signal to the Robot Runner using Google Pubsub during stint.start.
        """
        from ery_backend.hands.models import Hand

        for n in range(1, hand_n + 1):  # hand_n should start at 1 in naming
            user = get_or_create_user(self.secret, n)
            Hand.objects.create(
                user=user, stint=self.current_stint, language=self.current_stint.stint_specification.get_default_language()
            )
        hands = self.current_stint.hands
        stintdef_name = self.current_stint.stint_specification.stint_definition.name
        username = started_by.username
        hand_names = [hand.user.username for hand in hands.all()]
        message = f'Stint with StintDefinition: {stintdef_name} started by User: {username}, with hands: {hand_names}'

        self.current_stint.start(started_by, signal_pubsub)
        self.save()
        self.current_stint.log(message, system_only=True)

    def stop(self, stopped_by):
        """
        Removes current :class:`~ery_backend.stints.models.Stint` instance from current :class:`Lab` instance.

        Sets status of current :class:`~ery_backend.stints.models.Stint` to 'cancelled' before removing.

        Args:
            stopped_by (:class:`ery_backend.users.models.User`): Recorded initator of removal of associated
              :class:`~ery_backend.stints.models.Stint`.
        """
        from ery_backend.stints.models import Stint

        stintdef_name = self.current_stint.stint_specification.stint_definition.name
        username = stopped_by.username
        hand_names = [hand.user.username for hand in self.current_stint.hands.all() if hand.user]
        robot_names = [hand.robot for hand in self.current_stint.hands.all() if hand.robot]
        message = (
            f'Current stint with StintDefinition: {stintdef_name} '
            f'stopped by User: {username}, with hands: {hand_names} and robots: {robot_names}'
        )

        self.current_stint.set_status(Stint.STATUS_CHOICES.cancelled)
        self.current_stint.log(message, system_only=True)
        self.current_stint = None
        self.save()

    def change(self, stint_id):
        """
        Changes current :class:`Lab` instance's current :class:`~ery_backend.stints.models.Stint`.

        Args:
            stint_id (int): Used to retrieve target :class:`~ery_backend.stints.models.Stint` instance.

        Raises:
            :class:`~ery_backend.base.exceptions.EryValueError` if stint_id lookup yields a :class:`Stint` that does not have
            attribute 'lab' set to the current :class:`Lab` instance.

        Notes:
            - If :class:`Lab` has a current :class:`~ery_backend.stints.models.Stint`, it is cancelled after the new \
              :class:`~ery_backend.stints.models.Stint` is assigned.
        """
        from ery_backend.stints.models import Stint

        stint_to_cancel = self.current_stint
        registered_stint_ids = self.stints.values_list('id', flat=True)
        if stint_id in registered_stint_ids:
            self.current_stint = self.stints.get(id=stint_id)
            self.save()
        else:
            raise EryValueError(f'Stint with id: {stint_id}, does not belong to lab: {self},')
        if stint_to_cancel and stint_to_cancel.status == Stint.STATUS_CHOICES.running:
            stint_to_cancel.set_status(Stint.STATUS_CHOICES.cancelled)

    def clean(self):
        """
        Confirms secret exists for current :class:`Lab` instance.
        """
        if not self.secret:
            self._set_secret()
        super().clean()

    def save(self, *args, **kwargs):
        """
        Confirms clean method run before default django save.
        """
        # XXX: Address in issue #505 to confirm secret is set
        self.clean()
        super().save(*args, **kwargs)
