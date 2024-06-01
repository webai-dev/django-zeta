import graphene
from graphene import relay

import django_filters
from django.contrib.auth import get_user_model

from ery_backend.base.schema_utils import EryObjectType, EryFilterConnectionField
from ery_backend.users.utils import authenticated_user
from ery_backend.roles.schema import RoleAssignmentNodeMixin

from .models import NotificationContent, Notification


User = get_user_model()


# Notification Content
class NotificationContentNode(RoleAssignmentNodeMixin, EryObjectType):
    class Meta:
        model = NotificationContent


class NotificationContentQuery:
    notification_content = relay.Node.Field(NotificationContentNode)
    all_notification_contents = EryFilterConnectionField(NotificationContentNode)


# Notifications
class NotificationFilter(django_filters.FilterSet):
    class Meta:
        model = Notification
        fields = ("read",)

    # Order (before/after meta of additional args doesn't matter)
    date_lt = django_filters.DateTimeFilter(field_name="content__date", lookup_expr="lt")
    date_gt = django_filters.DateTimeFilter(field_name="content__date", lookup_expr="gt")


class NotificationNode(EryObjectType):
    class Meta:
        model = Notification
        filterset_class = NotificationFilter

    content = graphene.Field(NotificationContentNode)

    @classmethod
    def get_node(cls, info, node_id):
        user = authenticated_user(info.context)
        django_object = cls._meta.model.objects.get(pk=node_id)

        if django_object is None:
            return None

        if django_object.user != user:
            raise ValueError("not authorized")

        return django_object


class NotificationQuery:
    notification = relay.Node.Field(NotificationNode)
    # XXX: Does not actually work. Address in isue #750
    sent_notifications = EryFilterConnectionField(NotificationNode, filterset_class=NotificationFilter)
    received_notifications = EryFilterConnectionField(NotificationNode, filterset_class=NotificationFilter)
