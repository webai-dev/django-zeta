#!/usr/bin/env python
"""ery.Runner is handling incoming requests over Pub/Sub."""

import os

project_name = "eryservices-176219"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.sms_runner.local")

# pylint: disable=wrong-import-position
# try:
#    import googleclouddebugger
#    googleclouddebugger.enable(
#        module=project_name,
#        version=version,
#    )
# except ImportError:
#    pass

import time
import json
import logging
import environ

import django
from django.core.cache import cache

import google.api_core.exceptions
from google.cloud import pubsub
from google.cloud import error_reporting  # pylint: disable=no-name-in-module


from ery_backend.base.exceptions import EryValueError, EryTypeError

# XXX: Fix this
# from ery_backend.base.utils import get_widgets

env = environ.Env()
django.setup()

logger = logging.getLogger(__name__)
deployment = env("DEPLOYMENT", default="local")
error_reporter = error_reporting.Client()


class Runner:
    incoming_topic_name = f'projects/{project_name}/topics/{deployment}-incoming_sms'
    outgoing_topic_name = f'projects/{project_name}/topics/{deployment}-outgoing_sms'
    incoming_subscription_name = f'projects/{project_name}/subscriptions/{deployment}-runner-incoming_sms'

    def __init__(self, *args, **kwargs):
        self.publisher = pubsub.PublisherClient()
        self.subscriber = pubsub.SubscriberClient()

        self.init_pubsub()

    def init_pubsub(self):
        """
        Initilize Google Pub/Sub communication.

        Create topics and subscription if non-existing.
        """
        logger.debug("Setting up Pub/Sub client")
        try:
            self.publisher.create_topic(self.incoming_topic_name)
        except google.api_core.exceptions.AlreadyExists:
            pass
        try:
            self.publisher.create_topic(self.outgoing_topic_name)
        except google.api_core.exceptions.AlreadyExists:
            pass
        try:
            self.subscriber.create_subscription(self.incoming_subscription_name, self.incoming_topic_name)
        except google.api_core.exceptions.NotFound:
            logger.warning("Could not find subscription '%s'. Retrying...", self.incoming_subscription_name)
            time.sleep(1)
        except google.api_core.exceptions.AlreadyExists:
            pass

    def send_sms(self, to, message):
        """
        Put a Send SMS request onto the outgoing SMS topic.

        Note:
            - A long message string will be be split up into multiple SMS.

        Args:
            to (string): The number to send the SMS to, e.g. "+13477818303".
            message (string): The message to be sent via SMS.
        """
        logger.info("Sending message '%s'.", message)
        outgoing_message = json.dumps({"ID": "1", "To": to, "Message": message})
        future = self.publisher.publish(self.outgoing_topic_name, outgoing_message.encode())
        future.result()
        logger.info("Message '%s', sent.", outgoing_message)

    # pylint: disable=too-many-nested-blocks, too-many-branches
    def incoming_callback(self, incoming):
        """
        Hander for callback for the 'incoming_sms' PubSub topic.

        Args:
            incoming (~google.cloud.pubsub_v1.subscriber.message.Message): The incoming PubSub message.
        """
        from ery_backend.commands.utils import get_command
        from ery_backend.frontends.sms_views import render_sms
        from ery_backend.frontends.sms_utils import is_opt_in, opt_in, get_or_create_sms_stage
        from ery_backend.modules.models import ModuleEvent, ModuleDefinitionWidget

        reply = None
        error_message = None
        sms_stage = None

        incoming_data = json.loads(incoming.data)
        msg_id = incoming_data["ID"]
        message = incoming_data["Message"]
        phone_number = incoming_data["From"]

        l = cache.lock(f"sms-runner-lock-{phone_number}")
        if not l.acquire(blocking=False):
            logger.info("Blocking, ignoring: '%s'", incoming.data)
            incoming.nack()
            time.sleep(1)
            return

        last_id = cache.get(f"incoming-counter-{phone_number}")

        if last_id:
            if msg_id < last_id + 1:
                logger.info("Already handled, expected: %s, ignoring: '%s'", last_id + 1, incoming.data)
                l.release()
                incoming.ack()
                return
            if msg_id > last_id + 1:
                logger.info("Premature message, expected: %s, postponed: '%s'", last_id + 1, incoming.data)
                l.release()
                incoming.nack()
                time.sleep(1)
                return
        else:
            logger.info("No cached incoming-counter, resetting to: %s", msg_id)

        cache.set(f"incoming-counter-{phone_number}", msg_id)

        try:
            logger.info("Handling incoming: '%s'", incoming.data)
            from ery_backend.frontends.sms_utils import get_sms_hand

            reply = None
            hand = get_sms_hand(incoming_data, phone_number)
            opted_in = False
            if not hand:
                if is_opt_in(message):
                    hand = opt_in(message, phone_number)
                    opted_in = True
            if hand:
                sms_stage = get_or_create_sms_stage(hand)
                command = get_command(message, hand.stage.stage_definition.module_definition)
                if command:
                    if command.action is not None:
                        command.action.run(hand)
                    command_template = command.command_templates.filter(template__frontend__name='SMS')
                    if command_template.exists():
                        reply = command_template.first().render(language=hand.stint.stint_specification.language, hand=hand)
                else:
                    if not opted_in:
                        # XXX: Fix this
                        # sms_widgets = get_widgets(hand, 'SMS')
                        sms_widgets = []
                        if sms_widgets:
                            try:
                                for widget_wrapper in sms_widgets:
                                    if (
                                        isinstance(widget_wrapper, ModuleDefinitionWidget)
                                        and widget_wrapper.variable_definition
                                    ):
                                        widget_wrapper.validate(message)  # may raise EryValueError and EryTypeError
                                for widget_wrapper in sms_widgets:
                                    if isinstance(widget_wrapper, ModuleDefinitionWidget):
                                        widget_wrapper.trigger_events(ModuleEvent.EVENT_CHOICES.onReply, hand, value=message)
                                    widget_wrapper.widget.trigger_events(ModuleEvent.EVENT_CHOICES.onReply, hand)
                            except (EryValueError, EryTypeError) as exc:
                                error_message = f"'{message}' is not a valid response."
                if not reply and hand:
                    reply = render_sms(hand)
            if error_message:
                self.send_sms(phone_number, error_message)

            # Need to pick it up again as an action could have changed the stage
            if hand:
                sms_stage = get_or_create_sms_stage(hand)
            if sms_stage is None or sms_stage.stage.stage_definition.end_stage or sms_stage.send == 0:
                if reply is not None:
                    self.send_sms(phone_number, reply)
                    if sms_stage:
                        sms_stage.send += 1
                        sms_stage.save()
                else:
                    self.send_sms(phone_number, "Opt-in code '{}' is not in use.".format(message))

            incoming.ack()
        except json.decoder.JSONDecodeError:
            logger.error("Could not decode JSON: '%s'", incoming.data)
            incoming.ack()
        except Exception as exc:  # pylint: disable=broad-except
            import traceback

            incoming.ack()
            traceback.print_exc()
            logger.error("Incoming sms error: %s", exc)
            raise exc
        finally:
            l.release()

    def run(self):
        """Await new messages in loop on the 'incoming_sms' topic."""
        logger.info("Running ery.Runner ...")

        logger.debug("Setting up incoming_sms subscription")
        self.subscriber.subscribe(self.incoming_subscription_name, callback=self.incoming_callback)

        while True:  # Subscribe does not block, block here.
            time.sleep(60)

        logger.info("Shutting down ery.Runner")


if __name__ == '__main__':
    try:
        r = Runner()
        r.run()
    except Exception:  # pylint: disable=broad-except
        error_reporter.report_exception()
