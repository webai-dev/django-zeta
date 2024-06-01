from graphene import relay
import graphene

from ery_backend.base.schema import EryFilterConnectionField, EryMutationMixin
from ery_backend.roles.models import Role
from ery_backend.roles.utils import has_privilege, grant_role
from ery_backend.users.models import User
from ery_backend.users.utils import authenticated_user

from .models import Notification, NotificationContent, NotificationPriority
from .schema import NotificationContentNode, NotificationNode


class NotificationContentMutationInput:
    date = graphene.types.datetime.DateTime(required=True)
    message = graphene.String(required=True)
    priority = graphene.Enum.from_enum(NotificationPriority)(required=True)


class CreateNotificationContent(EryMutationMixin, relay.ClientIDMutation):
    notification_content = graphene.Field(NotificationContentNode, required=True)

    class Input(NotificationContentMutationInput):
        pass

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        user = authenticated_user(info.context)

        inputs["priority"] = inputs.pop("priority").upper()
        notification_content = NotificationContent()
        cls.add_all_attributes(notification_content, inputs)
        notification_content.save()

        ownership = Role.objects.get(name="owner")
        grant_role(ownership, notification_content, user)

        return CreateNotificationContent(notification_content=notification_content)


class UpdateNotificationContent(EryMutationMixin, relay.ClientIDMutation):
    notification_content = graphene.Field(NotificationContentNode, required=True)

    class Input(NotificationContentMutationInput):
        id = graphene.ID(required=True, description="GQL ID of the NotificationContent")

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        user = authenticated_user(info.context)

        notification_content_id = cls.gql_id_to_pk(inputs.pop("id"))
        notification_content = NotificationContent.objects.get(pk=notification_content_id)

        if not has_privilege(notification_content, user, "update"):
            raise ValueError("not authorized")

        inputs["priority"] = inputs.pop("priority").upper()
        cls.add_all_attributes(notification_content, inputs)
        notification_content.save()
        return UpdateNotificationContent(notification_content=notification_content)


class DeleteNotificationContent(EryMutationMixin, relay.ClientIDMutation):
    success = graphene.Boolean(required=True)

    class Input:
        id = graphene.ID(required=True, description="GQL ID of the NotificationContent")

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        user = authenticated_user(info.context)

        notification_content_id = cls.gql_id_to_pk(inputs.pop("id"))
        notification_content = NotificationContent.objects.get(pk=notification_content_id)

        if not has_privilege(notification_content, user, "delete"):
            raise ValueError("not authorized")

        notification_content.delete()
        return DeleteNotificationContent(success=True)


class NotificationMutationInput:
    notification_content = graphene.ID(required=True)
    users = graphene.List(graphene.ID)
    global_message = graphene.Boolean()


class CreateNotification(EryMutationMixin, relay.ClientIDMutation):
    notifications = EryFilterConnectionField(NotificationNode)

    class Input(NotificationMutationInput):
        pass

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        user = authenticated_user(info.context)

        cid = cls.gql_id_to_pk(inputs.pop("notification_content"))
        content = NotificationContent.objects.get(pk=cid)

        if not has_privilege(content, user, "update"):
            raise ValueError("not authorized")

        global_message = inputs.get("global_message", False)
        user_gql_ids = inputs.get("users", None)

        if not global_message and user_gql_ids is None:
            raise ValueError("must provide global_message=true or list of users")

        if global_message:
            recipients = User.objects.all()
        else:
            uids = [cls.gql_id_to_pk(gid) for gid in user_gql_ids]
            recipients = User.objects.filter(pk__in=uids)

        notifications = Notification.objects.bulk_create([Notification(content=content, user=user) for user in recipients])

        return CreateNotification(notifications=notifications)


class UpdateNotification(EryMutationMixin, relay.ClientIDMutation):
    notification = graphene.Field(NotificationNode, required=True)

    class Input:
        id = graphene.ID(required=True, description="GQL ID of the Notification")
        read = graphene.Boolean(required=True)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        user = authenticated_user(info.context)

        notification_id = cls.gql_id_to_pk(inputs.pop("id"))
        notification = Notification.objects.get(pk=notification_id)

        if user != notification.user:
            raise ValueError("not authorized")

        notification.read = inputs.pop("read")
        notification.save()
        return UpdateNotification(notification=notification)


class DeleteNotification(EryMutationMixin, relay.ClientIDMutation):
    success = graphene.Boolean(required=True)

    class Input:
        id = graphene.ID(required=True, description="GQL ID of the Notification")

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        user = authenticated_user(info.context)

        notification_id = cls.gql_id_to_pk(inputs.pop("id"))
        notification = Notification.objects.get(pk=notification_id)

        if user != notification.user:
            raise ValueError("not authorized")

        notification.delete()
        return DeleteNotification(success=True)
