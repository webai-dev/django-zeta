from django.db import models

from ery_backend.base.models import EryModel


class Warden(EryModel):
    """
    Serve as :class:`~ery_backend.models.stints.Stint` administrators, which monitor :class:`Hand` progression.

    Notes:
        - Can have a :class:`~ery_backend.models.stints.Stint` attribute (automatically accessible if \
          :class:`Warden` assigned to :class:`~ery_backend.models.stints.Stint` via :py:attr:`Stint.warden`)
    """

    # users should never be deleted during a stint, when wardens are used, so on_delete should not matter
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    last_seen = models.DateTimeField(null=True, blank=True)  # used for timing out users and stints
