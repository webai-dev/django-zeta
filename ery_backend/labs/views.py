from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.shortcuts import redirect
from django.views.decorators.cache import never_cache

from .models import Lab
from .utils import join


@never_cache
def play_most_recent(request, lab_secret, as_player):
    """
    Join/continue :class:`~ery_backend.labs.models.Lab` instance's current
    :class:`~ery_backend.stints.models.Stint`.

    Args:
        request (:class:`django.http.request.HttpRequest`): HttpRequest.
        lab_secret (str): Identifies :class:`~ery_backend.labs.models.Lab` instance.
        as_player (int): Identifies :class:`~ery_backend.labs.models.Lab` specific
          :class:`~ery_backend.users.models.User` instance.

    Returns:
        :class:`django.http.response.HttpResponse`): Stage related content.

    Raises:
        :class:`Http404`: If :class:`~ery_backend.labs.models.Lab` does not exist or have current
          :class:`~ery_backend.stints.models.Stint`.

    Notes:
        - Content is returned through :py:meth:render_web.
    """
    try:
        lab = Lab.objects.get(secret=lab_secret)
    except ObjectDoesNotExist:
        raise Http404("Lab does not exist")
    else:
        if not lab.current_stint:
            raise Http404("Stint does not exist")

        join(request, lab, as_player)
        return redirect('render_stint', lab.current_stint.gql_id)
