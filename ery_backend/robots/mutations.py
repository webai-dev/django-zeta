import graphene
from graphene import relay

from ery_backend.roles.utils import has_privilege
from ery_backend.base.schema import EryMutationMixin
from ery_backend.users.utils import authenticated_user

from ery_backend.modules.models import ModuleDefinition

from .models import Robot, RobotRule
from .schema import RobotNode, RobotRuleNode


class RobotInput:
    name = graphene.String()
    comment = graphene.String()


class CreateRobot(EryMutationMixin, relay.ClientIDMutation):
    robot = graphene.Field(RobotNode)

    class Input(RobotInput):
        module_definition = graphene.ID(required=True, description="GQL ID of the parent Module Definition")

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        user = authenticated_user(info.context)
        md_id = cls.gql_id_to_pk(inputs.pop('module_definition'))
        module_definition = ModuleDefinition.objects.get(pk=md_id)

        if not has_privilege(module_definition, user, 'update'):
            raise ValueError("not authorized")

        robot = Robot(module_definition=module_definition)
        cls.add_all_attributes(robot, inputs)
        robot.save()

        return CreateRobot(robot=robot)


class UpdateRobot(EryMutationMixin, relay.ClientIDMutation):
    robot = graphene.Field(RobotNode)

    class Input(RobotInput):
        id = graphene.ID(required=True, description="GQL ID of the Robot to update")

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        user = authenticated_user(info.context)
        robot_id = cls.gql_id_to_pk(inputs.pop('id'))
        robot = Robot.objects.get(pk=robot_id)

        if not has_privilege(robot, user, 'update'):
            raise ValueError("not authorized")

        cls.add_all_attributes(robot, inputs)
        robot.save()
        return UpdateRobot(robot=robot)


class DeleteRobot(EryMutationMixin, relay.ClientIDMutation):
    success = graphene.Boolean(required=True)

    class Input:
        id = graphene.ID(required=True, description="GQL ID of the Robot to delete")

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        user = authenticated_user(info.context)
        robot_id = cls.gql_id_to_pk(inputs.pop('id'))
        robot = Robot.objects.get(pk=robot_id)

        if not has_privilege(robot, user, 'delete'):
            raise ValueError("not authorized")

        robot.delete()
        return DeleteRobot(success=True)


class RobotRuleInput:
    widget = graphene.ID(description="GQL ID of the widget")
    rule_type = graphene.String()
    static_value = graphene.String()


class CreateRobotRule(EryMutationMixin, relay.ClientIDMutation):
    robot_rule = graphene.Field(RobotRuleNode)

    class Input(RobotRuleInput):
        robot = graphene.ID(required=True, description="GQL ID of the parent Robot")

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        user = authenticated_user(info.context)
        robot_id = cls.gql_id_to_pk(inputs.pop('robot'))
        robot = Robot.objects.get(pk=robot_id)
        module_definition = robot.module_definition

        if not has_privilege(module_definition, user, 'update'):
            raise ValueError("not authorized")

        robot_rule = RobotRule(robot=robot)
        cls.add_all_attributes(robot_rule, inputs)
        robot_rule.save()

        return CreateRobotRule(robot_rule=robot_rule)


class UpdateRobotRule(EryMutationMixin, relay.ClientIDMutation):
    robot_rule = graphene.Field(RobotRuleNode)

    class Input(RobotRuleInput):
        id = graphene.ID(required=True, description="GQL ID of the RobotRule to update")

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        user = authenticated_user(info.context)
        robot_rule_id = cls.gql_id_to_pk(inputs.pop('id'))
        robot_rule = RobotRule.objects.get(pk=robot_rule_id)

        if not has_privilege(robot_rule, user, 'update'):
            raise ValueError("not authorized")

        cls.add_all_attributes(robot_rule, inputs)
        robot_rule.save()
        return UpdateRobotRule(robot_rule=robot_rule)


class DeleteRobotRule(EryMutationMixin, relay.ClientIDMutation):
    success = graphene.Boolean(required=True)

    class Input:
        id = graphene.ID(required=True, description="GQL ID of the RobotRule to delete")

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        user = authenticated_user(info.context)
        robot_rule_id = cls.gql_id_to_pk(inputs.pop('id'))
        robot_rule = RobotRule.objects.get(pk=robot_rule_id)

        if not has_privilege(robot_rule, user, 'delete'):
            raise ValueError("not authorized")

        robot_rule.delete()
        return DeleteRobotRule(success=True)
