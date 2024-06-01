from datetime import date

import factory
import factory.fuzzy

from ery_backend.users.factories import UserFactory

from .models import Notification, NotificationContent, NotificationPriority


class NotificationContentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = NotificationContent

    date = date.today()
    message = factory.fuzzy.FuzzyText(length=100)
    priority = factory.fuzzy.FuzzyChoice([tag.name for tag in NotificationPriority])


class NotificationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Notification

    user = factory.SubFactory(UserFactory)
    content = factory.SubFactory(NotificationContentFactory)
    read = factory.fuzzy.FuzzyChoice([True, False])
