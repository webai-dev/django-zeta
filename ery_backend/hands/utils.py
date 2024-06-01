import datetime as dt

import pytz

from ery_backend.hands.models import Hand
from ery_backend.stints.models import Stint
from ery_backend.stint_specifications.models import StintModuleSpecification


def update_timeouts():
    """
    Updates status of :class:`~ery_backend.hands.models.Hand` and :class:`~ery_backend.stint.models.Stint` objects.

    Notes:
        - Only monitors :class:`~ery_backend.hands.models.Hand` objects in :class:`~ery_backend.stints.models.Stint` instances
          with a status of 'running'.
    """
    now = dt.datetime.now(pytz.UTC)
    for stint in Stint.objects.filter(status=Stint.STATUS_CHOICES.running).all():
        for hand in stint.hands.filter(status=Hand.STATUS_CHOICES.active).all():
            now = dt.datetime.now(pytz.UTC)
            stint_module_specification = StintModuleSpecification.objects.get(
                module_definition=hand.current_module.stint_definition_module_definition.module_definition,
                stint_specification=hand.stint.stint_specification,
            )
            if now - hand.last_seen >= dt.timedelta(seconds=stint_module_specification.hand_timeout):
                hand.status = Hand.STATUS_CHOICES.timedout
                hand.save()
                if stint_module_specification.stop_on_quit and stint.status == Stint.STATUS_CHOICES.running:
                    stint.set_status(Stint.STATUS_CHOICES.cancelled)
                    stint.save()
