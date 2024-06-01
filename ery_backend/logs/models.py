import logging

from django.db import models

from model_utils import Choices

from ery_backend.base.models import EryPrivileged


logger = logging.getLogger(__name__)


class Log(EryPrivileged):
    """
    Save information about stints during runtime. Information saved in logs should be concerned about
    the stint itself, as opposed to user data gathered for payment, progression, or analysis, which should
    be saved in Variables.

    Notes: As in python's logger, users can assign log types representing severity of message.
    """

    parent_field = "stint"

    LOG_TYPE_CHOICES = Choices(
        ('debug', 'Info not needed for regular operation, but useful in development.'),
        ('info', 'Info that\'s helpful during regular operation.'),
        ('warning', 'Info that could be problematic, but is non-urgent.'),
        ('error', 'Info that is important and likely requires prompt attention.'),
        ('critical', 'I don\'t find myself using this in practice, but if you need one higher than error, here it is'),
    )

    stint = models.ForeignKey('stints.Stint', on_delete=models.CASCADE, related_name='logs')
    era = models.ForeignKey('syncs.Era', on_delete=models.SET_NULL, null=True, blank=True, help_text="Relevant instance")
    hand = models.ForeignKey('hands.Hand', on_delete=models.SET_NULL, null=True, blank=True, help_text="Relevant instance")
    # Length is (reasonable) subset of 512 standard
    log_type = models.CharField(max_length=64, choices=LOG_TYPE_CHOICES, default=LOG_TYPE_CHOICES.info)
    message = models.TextField()
    module = models.ForeignKey(
        'modules.Module', on_delete=models.SET_NULL, null=True, blank=True, help_text="Relevant instance"
    )
    team = models.ForeignKey('teams.Team', on_delete=models.SET_NULL, null=True, blank=True, help_text="Relevant instance")
