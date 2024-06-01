#!/usr/bin/env python
"""ery.RobotRunner is simulating humans using incoming requests over Pub/Sub."""

import logging
import json
import os
import time
import traceback

import environ
import django
from django.conf import settings
import google.api_core.exceptions
from google.cloud import pubsub
from google.cloud import error_reporting  # pylint: disable=no-name-in-module
from opencensus.trace import tracer as tracer_module  # pylint: disable=import-error

env = environ.Env()
django.setup()

logger = logging.getLogger(__name__)
deployment = getattr(settings, "DEPLOYMENT", "staging")
project_name = getattr(settings, "PROJECT_NAME", "eryservices-176219")


class RobotRunner:
    def __init__(self, *args, **kwargs):
        self.publisher = pubsub.PublisherClient()
        self.subscriber = pubsub.SubscriberClient()
        self.tracer = tracer_module.Tracer()

        self.robot_topic = f'projects/{project_name}/topics/{deployment}-robot'
        self.robot_subscription = f'projects/{project_name}/subscriptions/{deployment}-robot'
        self.init_pubsub()

    def init_pubsub(self):
        """
        Initilize Google Pub/Sub communication.

        Create topics and subscription if non-existing.
        """
        logger.debug("Setting up robot_runner Pub/Sub client")
        try:
            self.publisher.create_topic(self.robot_topic)
        except google.api_core.exceptions.AlreadyExists:
            pass
        try:
            self.subscriber.create_subscription(self.robot_subscription, self.robot_topic)
            logger.debug("Subscription created: topic %s -- subscription %s", self.robot_topic, self.robot_subscription)
        except google.api_core.exceptions.NotFound:
            logger.warning("Could not find subscription '%s'. Retrying...", self.robot_subscription)
            time.sleep(1)
        except google.api_core.exceptions.AlreadyExists:
            pass

    @staticmethod
    def stint_start(stint_id):
        from ery_backend.stints import models as stint_models
        from ery_backend.robots import models as robot_models
        from ery_backend.hands.models import Hand

        current_stint = stint_models.Stint.objects.get(id=stint_id)
        stint_definition = current_stint.get_privilege_ancestor()
        first_module_definition = stint_definition.stint_definition_module_definitions.first().module_definition

        # Assuming for now there is only one robot per Module Definition for now
        current_robot = robot_models.Robot.objects.get(module_definition=first_module_definition)

        # Create Hands for each Robot
        # There will be a robot for each module definition inside of a stint_specification
        for stint_specification_robot in current_stint.stint_specification.stint_specification_robots.all():
            if stint_specification_robot.number:
                robot_hands = stint_specification_robot.number

            elif stint_specification_robot.robots_per_human:
                human_hands = Hand.objects.filter(stint=current_stint, robot__isnull=True)
                num_humans = human_hands.count()

                robot_hands = stint_specification_robot.robots_per_human * num_humans

            for _ in range(robot_hands):
                robot_hand = Hand(stint=current_stint, robot=current_robot)
                robot_hand.save()

    def stint_start_init_walk(self, stint_id):
        """
        Initiate robot hands when stint starts by publishing to ROBOT_TOPIC.
        This will initiate various robots to be consumed by the robot runner.
        """
        from ery_backend.stints import models as stint_models

        stint = stint_models.Stint.objects.get(id=stint_id)
        robot_hands = stint.hands.filter(robot__isnull=False)

        for robot_hand in robot_hands:
            robot_topic = os.environ.get('ROBOT_TOPIC')
            pub = pubsub.PublisherClient()
            try:
                pub.create_topic(robot_topic)
            except google.api_core.exceptions.AlreadyExists:
                pass

            message = json.dumps({'action': 'WALK_ROBOT', 'stint_definition_id': robot_hand.id}).encode()
            logger.info("Send WALK_ROBOT for %s StintSpecification", self.id)
            future = pub.publish(robot_topic, message)

            try:
                future.result()
            except:  # pylint: disable=bare-except
                logger.warning("STINT_START_INIT_WALK failed to send WALK_ROBOT signal")

            logger.info("Sent WALK_ROBOT for %s", robot_hand.id)

        return f"stint start {stint_id}"

    # XXX: Fix this
    # def walk_robot(self, hand_id):
    #     # Todo: abstract out get_sms_widgets to work for not SMS items
    #     from ery_backend.hands.models import Hand
    #     from ery_backend.robots.models import Robot, RobotRule
    #     from ery_backend.frontends.sms_utils import get_sms_widgets

    #     try:
    #         hand = Hand.objects.get(id=hand_id)
    #     except:
    #         logger.info(f"Hand:{hand_id} not found.")

    #     try:
    #         robot = Robot.objects.get(id=hand.robot.id)
    #     except:
    #         logger.info(f"Robot :{hand.robot.id} not found.")

    #     stage_template = hand.stage.stage_definition.stagetemplate_set.get(frontend=hand.frontend)
    #     widgets = hand.stage.get_sms_widgets()
    #     message = robot.robot_rules.filter()
    #     try:
    #         for widget_wrapper in widgets:
    #             if isinstance(widget_wrapper, ModuleDefinitionWidget) and widget_wrapper.variable_definition:
    #                 widget_wrapper.validate(message)  # may raise EryValueError and EryTypeError
    #         for widget_wrapper in widget:
    #             if isinstance(widget_wrapper, ModuleDefinitionWidget):
    #                 widget_wrapper.trigger_events(ModuleEvent.EVENT_CHOICES.onClick, hand, value=message)
    #                 widget_wrapper.widget.trigger_events(WidgetEvent.EVENT_CHOICES.onClick, hand)
    #     except (EryValueError, EryTypeError) as exc:
    #         error_message = f"'{message}' is not a valid response."

    #     w.trigger_events  # in eventholder mixin, use onChange for event

    #     # Frontend and Language comes from the Hand (code coming soon)
    #     # Widgets handle movements through stages (submodule)
    #     # Get stage template:
    #     #

    #     # widgets = hand.current_module_definition.widgets
    #     # for widget in widgets:
    #     #     widget.trigger()

    def incoming_callback(self, incoming):
        """
        Handler for callback for the 'incoming_sms' PubSub topic.

        Args:
            incoming (~google.cloud.pubsub_v1.subscriber.message.Message): The incoming PubSub message.

        Basic Control Flow:
            StintSpec.start() -> Trigger the init_robot function -> Trigger flow function (walk through survey)
        """
        incoming_data = json.loads(incoming.data)
        action = incoming_data.get('action', 'default')

        if action == 'default':
            logger.warning('Action not received')

        elif str(action) == 'STINT_START':
            stint_id = incoming_data.pop('stint_id')
            try:
                self.stint_start(stint_id=stint_id)
            except Exception as e:
                incoming.ack()
                logger.error("Robot runner error: %s", e)
                traceback.print_exc()
                raise e

        # XXX; Not sure what these are supposed to do
        # elif 'STINT_START_INIT_ROBOT':
        # self.stint_start(stint_id=incoming_data.pop('stint_id'))
        # XXX: Not sure what these are supposed to do
        # elif 'WALK_ROBOT':
        # self.walk_robot(hand_id=incoming_data.pop('hand_id'))
        else:
            logger.info('Invalid Action')

        logger.info('Acknowledge: %s', incoming)
        incoming.ack()

    def run(self):
        """Await new messages in loop"""
        logger.info("Running ery.RobotRunner")

        logger.debug("Setting up robot_subscription")
        self.subscriber.subscribe(self.robot_subscription, callback=self.incoming_callback)

        logger.debug("Listening...")
        logger.info("Subscription: %s", self.robot_subscription)
        logger.info("Topic: %s", self.robot_topic)
        while True:
            time.sleep(60)

        logger.info("Shutting down ery.RobotRunner")


if __name__ == '__main__':
    try:
        r = RobotRunner()
        r.run()
    except Exception as e:  # pylint: disable=broad-except
        if settings.USE_ERROR_REPORTING:
            error_reporter = error_reporting.Client()
            error_reporter.report_exception()
        else:
            print(e)
