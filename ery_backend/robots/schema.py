from graphene import relay

from ery_backend.base.schema import PrivilegedNodeMixin
from ery_backend.base.schema_utils import EryObjectType, EryFilterConnectionField

from .models import Robot, RobotRule


class RobotNode(PrivilegedNodeMixin, EryObjectType):
    class Meta:
        model = Robot


class RobotQuery:
    robot = relay.Node.Field(RobotNode)
    all_robots = EryFilterConnectionField(RobotNode)


class RobotRuleNode(PrivilegedNodeMixin, EryObjectType):
    class Meta:
        model = RobotRule


class RobotRuleQuery:
    robot_rule = relay.Node.Field(RobotRuleNode)
    all_robot_rules = EryFilterConnectionField(RobotRuleNode)
