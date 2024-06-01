from ery_backend.base.schema_utils import EryObjectType
from ery_backend.roles.schema import RoleAssignmentNodeMixin

from .models import (
    StintSpecification,
    StintSpecificationAllowedLanguageFrontend,
    StintSpecificationRobot,
    StintSpecificationVariable,
    StintSpecificationCountry,
    StintModuleSpecification,
)


class StintSpecificationNode(RoleAssignmentNodeMixin, EryObjectType):
    class Meta:
        model = StintSpecification


StintSpecificationQuery = StintSpecificationNode.get_query_class()


class StintSpecificationAllowedLanguageFrontendNode(RoleAssignmentNodeMixin, EryObjectType):
    class Meta:
        model = StintSpecificationAllowedLanguageFrontend


StintSpecificationAllowedLanguageFrontendQuery = StintSpecificationAllowedLanguageFrontendNode.get_query_class()


class StintSpecificationRobotNode(RoleAssignmentNodeMixin, EryObjectType):
    class Meta:
        model = StintSpecificationRobot


StintSpecificationRobotQuery = StintSpecificationRobotNode.get_query_class()


class StintSpecificationVariableNode(RoleAssignmentNodeMixin, EryObjectType):
    class Meta:
        model = StintSpecificationVariable


StintSpecificationVariableQuery = StintSpecificationVariableNode.get_query_class()


# XXX: Test this
class StintSpecificationCountryNode(RoleAssignmentNodeMixin, EryObjectType):
    class Meta:
        model = StintSpecificationCountry


StintSpecificationCountryQuery = StintSpecificationCountryNode.get_query_class()


# XXX: Test this
class StintModuleSpecificationNode(RoleAssignmentNodeMixin, EryObjectType):
    class Meta:
        model = StintModuleSpecification


StintModuleSpecificationQuery = StintModuleSpecificationNode.get_query_class()
