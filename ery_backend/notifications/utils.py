from .models import Notification, NotificationContent, NotificationPriority


def create_user_notification(user, msg, url=None, priority=NotificationPriority.MED.value):
    """
    Convenience method for creating a :class:`~ery_backend.notifications.models.Notification`
    to be sent to a :class:`~ery_backend.users.models.User`.

    Args:
        - user (:class:`~ery_backend.users.models.User`): Target of
          :class:`~ery_backend.notifications.models.Notification`.
        - msg (str): Message tied to :class:`~ery_backend.notifications.models.Notification`.
        - url (Optional[str]): Link to connected web page.
    """
    content = NotificationContent.objects.create(message=msg, priority=priority)
    notification = Notification.objects.create(user=user, content=content, url=url)
    return notification


def create_group_notification(users, msg, url=None, priority=NotificationPriority.MED.value):
    """
    Convenience method for creating a :class:`~ery_backend.notifications.models.Notification`
    to be sent to a group of :class:`~ery_backend.users.models.User` instances.

    Args:
        - user (:class:`~ery_backend.users.models.User`): Target of
          :class:`~ery_backend.notifications.models.Notification`.
        - msg (str): Message tied to :class:`~ery_backend.notifications.models.Notification`.
        - url (Optional[str]): Link to connected web page.
    """

    def _generate_type_error(arg, arg_types, arg_value):
        message = f'\'{arg}\' must be one of the following types: {arg_types}, not: {type(arg_value)}'
        raise TypeError(message)

    if not isinstance(users, list):
        _generate_type_error('users', (list,), users)

    if not isinstance(msg, (str)):
        _generate_type_error('msg', (str,), msg)

    if url:
        if not isinstance(url, (str,)):
            _generate_type_error('link', (str,), url)

    content = NotificationContent.objects.create(message=msg, priority=priority)

    return [Notification.objects.create(user=user, content=content, url=url) for user in users]
