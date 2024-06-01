import logging

from django.contrib.auth import login

from ery_backend.hands.models import Hand
from ery_backend.users.models import User

logger = logging.getLogger(__name__)


def get_or_create_user(secret, player_id):
    username = f'__lab__:{secret}:{player_id}'
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        user = User.objects.create(username=username, profile={'player_id': player_id, 'secret': secret})
        logger.info("Created User idenified by secret: %s, and player_id: %s.", secret, player_id)

    return user


def join(request, lab, as_player):
    """
    Join :class:`~ery_backend.labs.models.Lab` instance's current
    :class:`~ery_backend.stints.models.Stint`.

    Args:
        request (:class:`django.http.request.HttpRequest`): HttpRequest.
        lab (:class:`~ery_backend.labs.models.Lab`): Provides :class:`~ery_backend.stints.models.Stint`
          instance to join.
        as_player (int): Identifies :class:`~ery_backend.labs.models.Lab` specific
          :class:`~ery_backend.users.models.User` instance.

    Returns:
        :class:`~ery_backend.hands.models.Hand`: Associated with logged in
          :class:`~ery_backend.users.models.User`.
    """
    username = f'__lab__:{lab.secret}:{as_player}'
    user = User.objects.get(username=username)
    user.backend = 'django.contrib.auth.backends.ModelBackend'
    user.save()
    login(request, user)
    hand = Hand.objects.get(user=user, stint=lab.current_stint)
    return hand
