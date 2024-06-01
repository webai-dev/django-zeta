from countries_plus.models import Country

from ery_backend.base.testcases import EryTestCase

from ..factories import StintSpecificationFactory, StintSpecificationVariableFactory
from ..models import StintSpecificationCountry, StintSpecification


class TestStintSpecificationBXMLSerializer(EryTestCase):
    def setUp(self):
        self.backup_stint_specification = StintSpecificationFactory()
        self.stint_specification = StintSpecificationFactory(backup_stint_specification=self.backup_stint_specification)
        self.country = Country.objects.first()
        ss_link = StintSpecificationCountry(stint_specification=self.stint_specification, country=self.country)
        ss_link.save()
        self.ssv = StintSpecificationVariableFactory(stint_specification=self.stint_specification)
        self.stint_specification_serializer = StintSpecification.get_bxml_serializer()(self.stint_specification)

    def test_exists(self):
        self.assertIsNotNone(self.stint_specification_serializer)

    def test_expected_attributes(self):
        self.assertEqual(self.stint_specification_serializer.data['comment'], self.stint_specification.comment)
        self.assertEqual(self.stint_specification_serializer.data['name'], self.stint_specification.name)
        self.assertEqual(self.stint_specification_serializer.data['team_size'], self.stint_specification.team_size)
        self.assertEqual(self.stint_specification_serializer.data['min_team_size'], self.stint_specification.min_team_size)
        self.assertEqual(self.stint_specification_serializer.data['max_team_size'], self.stint_specification.max_team_size)
        # XXX: Address in issue #812
        # self.assertIsNotNone(self.stint_specification_serializer.data['variables'])
        self.assertIsNotNone(self.stint_specification_serializer.data['stint_specification_countries'])
        self.assertEqual(
            self.stint_specification_serializer.data['backup_stint_specification'], self.backup_stint_specification.name
        )


# XXX: Address in issue #812
# class TestStintSpecificationRobotSerializer(EryTestCase):
#     def setUp(self):
#         self.stint_specification_robot = StintSpecificationRobotFactory()
#         self.stint_specification_robot_serializer = StintSpecificationRobotSerializer(
#             self.stint_specification_robot)

#     def test_exist(self):
#         self.assertIsNotNone(self.stint_specification_robot_serializer)

#     def test_expected_attributes(self):
#         self.assertEqual(self.stint_specification_robot_serializer.data['number'], self.stint_specification_robot.number)


# XXX: Address in issue #812
# class TestStintSpecificationVariableSerializer(EryTestCase):
#     def setUp(self):
#         self.stint_specification_variable = StintSpecificationVariableFactory()
#         self.stint_specification_variable_serializer =
#             StintSpecificationVariableSerializer(self.stint_specification_variable)
#     def test_exists(self):
#         self.assertIsNotNone(self.stint_specification_variable_serializer)

#     def test_expected_attributes(self):
#         self.assertEqual(
#           self.stint_specification_variable_serializer.data['variable_definition'],
#           self.stint_specification_variable.variable_definition.name
#         )
#         self.assertEqual(
#           self.stint_specification_variable_serializer.data['set_to_every_nth'],
#           self.stint_specification_variable.set_to_every_nth
#         )
#         serialized_value = self.stint_specification_variable_serializer.data['value']
#         if self.stint_specification_variable.variable_definition.data_type == VariableDefinition.DATA_TYPE_CHOICES.dict:
#             serialized_value = json.loads(serialized_value)
#         self.assertEqual(serialized_value, self.stint_specification_variable.value)
