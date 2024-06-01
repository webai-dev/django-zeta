import datetime
import random

import graphene
import pytz

from ery_backend.base.testcases import GQLTestCase
from ery_backend.mutations import NotificationContentMutation, NotificationMutation
from ery_backend.roles.utils import grant_role
from ery_backend.users.factories import UserFactory
from ery_backend.users.schema import ViewerQuery

from ..factories import NotificationContentFactory, NotificationFactory
from ..models import NotificationContent, Notification
from ..schema import NotificationContentQuery, NotificationQuery


class TestQuery(NotificationContentQuery, NotificationQuery, ViewerQuery, graphene.ObjectType):
    pass


class TestMutation(NotificationContentMutation, NotificationMutation, graphene.ObjectType):
    pass


class TestReadNotificationContent(GQLTestCase):
    node_name = "NotificationContentNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_read_requires_login(self):
        """
        User must be logged in to use the NotificationContentQuery
        """
        notification_content = NotificationContentFactory()
        td = {"gqlId": notification_content.gql_id}

        query = """query Read($gqlId: ID!){ notificationContent(id: $gqlId){
            date message priority
            }}"""

        result = self.gql_client.execute(query, variable_values=td)
        self.assert_query_was_unauthorized(result)

        query = """{allNotificationContents {edges {node { date message priority }}}}"""

        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

    def test_read_filters_by_privilege(self):
        """
        allNotificationContents filters by privilege
        """
        # Permission Setup
        notification_contents = [NotificationContentFactory(), NotificationContentFactory(), NotificationContentFactory()]

        for notification_content in notification_contents:
            grant_role(self.viewer["role"], notification_content, self.viewer["user"])

        for notification_content in notification_contents[1:]:
            grant_role(self.editor["role"], notification_content, self.editor["user"])

        grant_role(self.owner["role"], notification_contents[2], self.owner["user"])

        # Query
        query = """{allNotificationContents {edges {node { date message priority }}}}"""

        # Viewer
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allNotificationContents"]["edges"]), 3)

        # Editor
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allNotificationContents"]["edges"]), 2)

        # Viewer
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allNotificationContents"]["edges"]), 1)


class TestCreateNotificationContent(GQLTestCase):
    node_name = "NotificationContentNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_create_produces_result(self):
        """
        Logged in user can create a NotificationContent
        """
        day = datetime.datetime.now().replace(tzinfo=pytz.UTC)
        td = {"date": day.isoformat(), "message": "create produces result", "priority": "LOW"}

        mutation = """mutation CreateNotificationContent($date: DateTime!, $message: String!,
                                                         $priority: NotificationPriority!){
            createNotificationContent(input: {
                date: $date,
                message: $message,
                priority: $priority })
            { notificationContent
            { date message priority }}}"""

        response = self.gql_client.execute(
            mutation, variable_values=td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(response)

        # May be off in microseconds
        self.assertAlmostEqual(response["data"]["createNotificationContent"]["notificationContent"]["date"], td["date"])

        self.assertEqual(response["data"]["createNotificationContent"]["notificationContent"]["message"], td["message"])

        self.assertEqual(response["data"]["createNotificationContent"]["notificationContent"]["priority"], td["priority"])


class TestUpdateNotificationContent(GQLTestCase):
    node_name = "NotificationContentNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_update_requires_privileges(self):
        """Unprivileged users cannot update NotificationContents"""
        notification_content = NotificationContentFactory()

        grant_role(self.viewer["role"], notification_content, self.viewer["user"])

        day = datetime.datetime(2018, 8, 25, tzinfo=pytz.UTC)
        td = {
            "gqlId": notification_content.gql_id,
            "date": day.isoformat(),
            "message": "update_requires_privilege",
            "priority": "MED",
        }

        mutation = """mutation UpdateNotificationContent(
            $gqlId: ID!, $date: DateTime!, $message: String!, $priority: NotificationPriority!){
            updateNotificationContent(input: {
                id: $gqlId,
                date: $date,
                message: $message,
                priority: $priority })
            { notificationContent
            { date message priority }}}"""

        result = self.gql_client.execute(
            mutation, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

        notification_content.refresh_from_db()

        self.assertNotEqual(getattr(notification_content, "date"), day)
        self.assertNotEqual(getattr(notification_content, "message"), td["message"])

    def test_update_produces_result(self):
        """UpdateNotificationContent alters the database"""
        notification_content = NotificationContentFactory()

        grant_role(self.editor["role"], notification_content, self.editor["user"])

        day = datetime.datetime(2018, 8, 25, tzinfo=pytz.UTC)
        td = {
            "gqlId": notification_content.gql_id,
            "date": day.isoformat(),
            "message": "update_produces_result",
            "priority": "HIGH",
        }

        mutation = """mutation UpdateNotificationContent(
            $gqlId: ID!, $date: DateTime!, $message: String!, $priority: NotificationPriority!){
            updateNotificationContent(input: {
                id: $gqlId,
                date: $date,
                message: $message,
                priority: $priority })
            { notificationContent
            { date message priority }}}"""

        result = self.gql_client.execute(
            mutation, variable_values=td, context_value=self.gql_client.get_context(user=self.editor["user"])
        )
        self.fail_on_errors(result)

        notification_content.refresh_from_db()

        self.assertEqual(getattr(notification_content, "date"), day)
        self.assertEqual(getattr(notification_content, "message"), td["message"])
        self.assertEqual(getattr(notification_content, "priority"), td["priority"])


class TestDeleteNotificationContent(GQLTestCase):
    node_name = "NotificationContentNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_delete_requires_privileges(self):
        """Unprivileged user cannot delete NotificationContent"""
        notification_content = NotificationContentFactory()
        notification_content_id = notification_content.pk
        td = {"gqlId": notification_content.gql_id}

        grant_role(self.viewer["role"], notification_content, self.viewer["user"])

        mutation = """mutation DeleteNotificationContent($gqlId: ID!){
            deleteNotificationContent(input: {id: $gqlId}){success}}"""

        result = self.gql_client.execute(mutation, variable_values=td)
        self.assert_query_was_unauthorized(result)

        result = self.gql_client.execute(
            mutation, variable_values=td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

        # Prove it's still in the database
        NotificationContent.objects.get(pk=notification_content_id)

    def test_delete_produces_result(self):
        """DeleteNotificationContent deletes the record"""

        notification_content = NotificationContentFactory()
        notification_content_id = notification_content.pk
        td = {"gqlId": notification_content.gql_id}

        grant_role(self.owner["role"], notification_content, self.owner["user"])

        mutation = """mutation DeleteNotificationContent($gqlId: ID!){
            deleteNotificationContent(input: {id: $gqlId}){success}}"""

        result = self.gql_client.execute(
            mutation, variable_values=td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.assertTrue(result["data"]["deleteNotificationContent"]["success"])
        self.assertRaises(NotificationContent.DoesNotExist, NotificationContent.objects.get, **{"pk": notification_content_id})


class TestReadNotification(GQLTestCase):
    node_name = "NotificationNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_read_requires_login(self):
        """
        User must be logged in to use the NotificationQuery
        """
        notification = NotificationFactory()
        td = {"gqlId": notification.gql_id}

        query = """query Read($gqlId: ID!){ notification(id: $gqlId){
            read
            }}"""

        result = self.gql_client.execute(query, variable_values=td)
        self.assert_query_was_unauthorized(result)

        query = """{sentNotifications {edges {node { read }}}}"""

        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

    def test_read_filters_by_privilege(self):
        """
        sentNotifications filters by privilege
        """
        # Permission Setup
        notifications = [NotificationFactory(), NotificationFactory(), NotificationFactory()]

        for notification in notifications:
            grant_role(self.viewer["role"], notification, self.viewer["user"])

        for notification in notifications[1:]:
            grant_role(self.editor["role"], notification, self.editor["user"])

        grant_role(self.owner["role"], notification, self.owner["user"])

        # Query
        query = """{sentNotifications {edges {node { read }}}}"""

        # Viewer
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["sentNotifications"]["edges"]), 3)

        # Editor
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["sentNotifications"]["edges"]), 2)

        # Viewer
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["sentNotifications"]["edges"]), 1)

    # XXX: Address in issue # 575
    # def test_read_all_allows_notification_user_access(self):
    #     """
    #     notification.user should be able to run receivedNotifications and get the notification and content.message, distinct
    #     from the Roles privilege model
    #     """
    #     notification = NotificationFactory()
    #     NotificationFactory() # User should only see their own notifications
    #     user = notification.user

    #     query = """{receivedNotifications {edges {node { read content { date message }}}}}"""
    #     result = self.gql_client.execute(
    #         query, context_value=self.gql_client.get_context(user=user))
    #     self.fail_on_errors(result)

    #     self.assertEqual(len(result["data"]["receivedNotifications"]["edges"]), 1)

    #     data = result["data"]["receivedNotifications"]["edges"][0]["node"]
    #     self.assertEqual(data["read"], notification.read)
    #     self.assertEqual(data["content"]["message"], notification.content.message)

    def test_user_reads_own_notifications(self):
        """notification.user can read their own notifications, but not others (distinct from the Role privilege model)"""

        user_notice = NotificationFactory()
        user = user_notice.user

        td = {"gqlId": user_notice.gql_id}

        query = """query Notification($gqlId: ID!){notification(id: $gqlId) { id read content { date message }}}"""
        result = self.gql_client.execute(query, variable_values=td, context_value=self.gql_client.get_context(user=user))
        self.fail_on_errors(result)
        self.assertEqual(result["data"]["notification"]["content"]["message"], user_notice.content.message)

        other_notice = NotificationFactory()
        td = {"gqlId": other_notice.gql_id}
        result = self.gql_client.execute(query, variable_values=td, context_value=self.gql_client.get_context(user=user))
        self.assert_query_was_unauthorized(result)

    def test_filter_unread_messages(self):
        """receivedNotifications can filter on Notification.read status"""

        query = """{receivedNotifications(read: false) {edges {node { id content { id message date priority }}}}}"""

        user = UserFactory()

        for _ in range(random.randint(1, 5)):
            notification = NotificationFactory(user=user, read=True)
            grant_role(self.viewer['role'], notification, user)

        unread_notices = [NotificationFactory(user=user, read=False) for _ in range(random.randint(1, 5))]
        for notice in unread_notices:
            grant_role(self.viewer['role'], notice, user)

        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=user))
        self.fail_on_errors(result)

        self.assertEqual(len(result["data"]["receivedNotifications"]["edges"]), len(unread_notices))

    def test_filter_message_dates(self):
        """receivedNotifications can filter on dates"""

        before = datetime.datetime(2018, 8, 15, tzinfo=pytz.UTC)
        split = datetime.datetime(2018, 8, 20, tzinfo=pytz.UTC).isoformat()
        user = UserFactory()

        td = {"date": split}

        query = """query Notifications($date: DateTime!){receivedNotifications(dateGt: $date)
                    {edges {node { content { date message}}}}}"""

        old_content = NotificationContentFactory(date=before)
        new_content = NotificationContentFactory(date=datetime.datetime(year=2020, month=1, day=1, tzinfo=pytz.UTC))
        old_notice = NotificationFactory(user=user, content=old_content)
        new_notice = NotificationFactory(user=user, content=new_content)
        grant_role(self.owner['role'], old_notice, user)
        grant_role(self.owner['role'], new_notice, user)

        result = self.gql_client.execute(query, variable_values=td, context_value=self.gql_client.get_context(user=user))
        self.fail_on_errors(result)

        self.assertEqual(len(result["data"]["receivedNotifications"]["edges"]), 1)
        self.assertEqual(
            result["data"]["receivedNotifications"]["edges"][0]["node"]["content"]["message"], new_notice.content.message
        )

        query = """query AllNotifications($date: DateTime!){receivedNotifications(dateLt: $date)
                    {edges {node { content { date message}}}}}"""

        result = self.gql_client.execute(query, variable_values=td, context_value=self.gql_client.get_context(user=user))
        self.fail_on_errors(result)

        self.assertEqual(len(result["data"]["receivedNotifications"]["edges"]), 1)
        self.assertEqual(
            result["data"]["receivedNotifications"]["edges"][0]["node"]["content"]["message"], old_notice.content.message
        )


class TestCreateNotification(GQLTestCase):
    node_name = "NotificationNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_create_requires_privilege(self):
        """
        Notifications can't be sent without privileges
        """
        content = NotificationContentFactory()
        recipient = UserFactory()

        cid = content.gql_id
        uid = recipient.gql_id

        td = {"notificationContent": cid, "users": [uid]}

        mutation = """mutation CreateNotification($notificationContent: ID!, $users: [ID]){
            createNotification(input: {
                notificationContent: $notificationContent,
                users: $users })
            {notifications { edges { node { content { message } user { username } }}}}}"""

        result = self.gql_client.execute(
            mutation, variable_values=td, context_value=self.gql_client.get_context(user=self.no_roles["user"])
        )
        self.assert_query_was_unauthorized(result)

    def test_create_produces_result(self):
        """
        Logged in user can create (send) a Notification
        """
        content = NotificationContentFactory()
        grant_role(self.owner["role"], content, self.owner["user"])
        recipients = [UserFactory() for _ in range(random.randint(1, 5))]
        excluded = [UserFactory() for _ in range(random.randint(1, 5))]

        cid = content.gql_id
        uids = [recipient.gql_id for recipient in recipients]

        td = {"notificationContent": cid, "users": uids}

        mutation = """mutation CreateNotification($notificationContent: ID!, $users: [ID]){
            createNotification(input: {
                notificationContent: $notificationContent,
                users: $users })
            {notifications { edges { node { content { message } user { username } }}}}}"""

        result = self.gql_client.execute(
            mutation, variable_values=td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        for recipient in recipients:
            notification = Notification.objects.get(user=recipient, content=content)
            self.assertIs(notification.read, False)

        for user in excluded:
            self.assertRaises(Notification.DoesNotExist, Notification.objects.get, **{"user": user, "content": content})

    def test_create_can_be_global(self):
        """
        A notification can be sent globally, without requiring manual list of user ids
        """
        content = NotificationContentFactory()
        grant_role(self.owner["role"], content, self.owner["user"])
        cid = content.gql_id

        recipients = [UserFactory() for _ in range(random.randint(1, 10))]

        td = {"notificationContent": cid, "globalMessage": True}

        mutation = """mutation CreateNotification($notificationContent: ID!, $globalMessage: Boolean){
            createNotification(input: {
                notificationContent: $notificationContent,
                globalMessage: $globalMessage })
            {notifications { edges { node { content { message } user { username } }}}}}"""

        result = self.gql_client.execute(
            mutation, variable_values=td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        for recipient in recipients:
            notification = Notification.objects.get(user=recipient, content=content)
            self.assertIs(notification.read, False)


class TestUpdateNotification(GQLTestCase):
    node_name = "NotificationNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_update_only_by_user(self):
        """
        Users can only affect their own notification "read" status, regardless of other privileges.
        """

        notification = NotificationFactory()
        grant_role(self.owner["role"], notification, self.owner["user"])
        grant_role(self.owner["role"], notification.content, self.owner["user"])

        td = {"gqlId": notification.gql_id, "read": not notification.read}

        mutation = """mutation UpdateNotification(
            $gqlId: ID!, $read: Boolean!){
            updateNotification(input: {
                id: $gqlId,
                read: $read })
            { notification
            { read }}}"""

        result = self.gql_client.execute(
            mutation, variable_values=td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.assert_query_was_unauthorized(result)

        notification.refresh_from_db()
        self.assertNotEqual(getattr(notification, "read"), td["read"])

    def test_update_produces_result(self):
        """UpdateNotification alters the database"""
        notification = NotificationFactory()
        user = notification.user

        td = {"gqlId": notification.gql_id, "read": not notification.read}

        mutation = """mutation UpdateNotification(
            $gqlId: ID!, $read: Boolean!){
            updateNotification(input: {
                id: $gqlId,
                read: $read })
            { notification
            { read }}}"""

        result = self.gql_client.execute(mutation, variable_values=td, context_value=self.gql_client.get_context(user=user))
        self.fail_on_errors(result)

        notification.refresh_from_db()
        self.assertEqual(getattr(notification, "read"), td["read"])


class TestDeleteNotification(GQLTestCase):
    node_name = "NotificationNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_delete_requires_privileges(self):
        """Only the notification.user can delete the notification, regardless of Role privileges"""
        notification = NotificationFactory()
        notification_id = notification.pk
        td = {"gqlId": notification.gql_id}

        grant_role(self.owner["role"], notification, self.owner["user"])

        mutation = """mutation DeleteNotification($gqlId: ID!){
            deleteNotification(input: {id: $gqlId}){success}}"""

        result = self.gql_client.execute(mutation, variable_values=td)
        self.assert_query_was_unauthorized(result)

        result = self.gql_client.execute(
            mutation, variable_values=td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.assert_query_was_unauthorized(result)

        # Prove it's still in the database
        Notification.objects.get(pk=notification_id)

    def test_delete_produces_result(self):
        """DeleteNotification deletes the record"""

        notification = NotificationFactory()
        notification_id = notification.pk
        td = {"gqlId": notification.gql_id}

        user = notification.user

        mutation = """mutation DeleteNotification($gqlId: ID!){
            deleteNotification(input: {id: $gqlId}){success}}"""

        result = self.gql_client.execute(mutation, variable_values=td, context_value=self.gql_client.get_context(user=user))
        self.fail_on_errors(result)

        self.assertTrue(result["data"]["deleteNotification"]["success"])
        self.assertRaises(Notification.DoesNotExist, Notification.objects.get, **{"pk": notification_id})
