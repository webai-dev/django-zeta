from enum import Enum

import django
from django.db import models
from django.conf import settings

from ery_backend.base.models import EryPrivileged


class NotificationPriority(Enum):
    """Enumerate possible :class:`~Notification.priority` values"""

    LOW = "low"
    MED = "medium"
    HIGH = "high"


class NotificationContent(EryPrivileged):
    """
    Notification content contains system messages that can be sent to users
    """

    message = models.CharField(max_length=512, null=False)
    date = models.DateTimeField(null=False, default=django.utils.timezone.now)
    # length of longest option
    priority = models.CharField(max_length=6, null=False, choices=([(tag.name, tag.value) for tag in NotificationPriority]))

    def __str__(self):
        return f"NotificationContent (date={self.date.isoformat()}, priority={self.priority}): {self.message}"


class Notification(EryPrivileged):
    """
    Notifications are text strings that may be delivered to individual users or globally.  They allow us to update users about
    changes to the system.
    """

    class Meta(EryPrivileged.Meta):
        unique_together = ("content", "user")

    content = models.ForeignKey(NotificationContent, on_delete=models.CASCADE, null=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=False)
    read = models.BooleanField(default=False, null=False)
    # max_length attained by researching recommended upper limit of urls
    url = models.URLField(max_length=2000, null=True, blank=True)

    def __str__(self):
        return f"Notification (user={self.user.username}, read={self.read}): {self.content.message}"
