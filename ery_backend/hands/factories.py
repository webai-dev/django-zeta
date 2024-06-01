import datetime as dt
import pytz

import factory
import factory.fuzzy

from ery_backend.base.utils import get_default_language


class HandFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'hands.Hand'

    stint = factory.SubFactory('ery_backend.stints.factories.StintFactory')
    era = factory.SubFactory('ery_backend.syncs.factories.EraFactory')
    stage = factory.SubFactory('ery_backend.stages.factories.StageFactory')
    current_module = factory.SubFactory('ery_backend.modules.factories.ModuleFactory')
    last_seen = dt.datetime.now().replace(tzinfo=pytz.UTC)
    language = factory.LazyFunction(get_default_language)
