import json
import os
import random

from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError

from countries_plus.models import Country

from ery_backend.base.exceptions import EryValidationError
from ery_backend.base.testcases import EryTestCase, random_dt_value
from ery_backend.datasets.factories import DatasetFactory
from ery_backend.datasets.models import Dataset
from ery_backend.modules.factories import ModuleDefinitionFactory
from ery_backend.robots.factories import RobotFactory
from ery_backend.stages.factories import StageDefinitionFactory
from ery_backend.stints.factories import StintDefinitionFactory, StintDefinitionModuleDefinitionFactory
from ery_backend.stints.models import StintDefinitionModuleDefinition

from ery_backend.syncs.factories import EraFactory
from ery_backend.users.factories import UserFactory
from ery_backend.variables.factories import VariableDefinitionFactory
from ery_backend.variables.models import VariableDefinition
from ..factories import (
    StintSpecificationFactory,
    StintSpecificationRobotFactory,
    StintSpecificationVariableFactory,
    StintModuleSpecificationFactory,
)
from ..models import StintSpecificationCountry, StintSpecificationRobot, StintSpecification


class TestStintSpecification(EryTestCase):
    def setUp(self):
        self.comment = 'Salutations with specifications!'
        self.stint_definition = StintDefinitionFactory()
        self.era = EraFactory()
        self.user = UserFactory()

        self.module_definition_1 = ModuleDefinitionFactory(start_era=self.era, start_stage=StageDefinitionFactory())
        StintDefinitionModuleDefinition.objects.create(
            stint_definition=self.stint_definition, module_definition=self.module_definition_1
        )
        self.backup_stint_specification = StintSpecificationFactory(stint_definition=self.stint_definition)
        self.stint_specification = StintSpecificationFactory(
            team_size=2,
            stint_definition=self.stint_definition,
            min_team_size=1,
            max_team_size=12,
            backup_stint_specification=self.backup_stint_specification,
            name='test-stintspecification',
            comment=self.comment,
            opt_in_code='231432123',
            min_earnings=24.15,
            max_earnings=24.16,
            immediate_payment_method=StintSpecification.PAYMENT_CHOICES.PHONE_RECHARGE,
            late_arrival=True,
        )

        ssc_link1 = StintSpecificationCountry(stint_specification=self.stint_specification, country=Country.objects.first())
        ssc_link1.save()
        ssc_link2 = StintSpecificationCountry(stint_specification=self.stint_specification, country=Country.objects.all()[1])
        ssc_link2.save()
        StintSpecificationVariableFactory(
            stint_specification=self.stint_specification, variable_definition__module_definition=self.module_definition_1
        )
        StintSpecificationVariableFactory(
            stint_specification=self.stint_specification, variable_definition__module_definition=self.module_definition_1
        )
        self.circular_stint_specification_1 = StintSpecificationFactory()
        self.circular_stint_specification_2 = StintSpecificationFactory()
        self.circular_stint_specification_3 = StintSpecificationFactory()
        self.circular_stint_specification_4 = StintSpecificationFactory()
        self.circular_stint_specification_5 = StintSpecificationFactory()
        self.circular_stint_specification_6 = StintSpecificationFactory()

    def test_exists(self):
        self.assertIsNotNone(self.stint_specification)

    def test_expected_attributes(self):
        self.stint_specification.refresh_from_db()
        self.assertEqual(self.stint_specification.name, 'test-stintspecification')
        self.assertEqual(self.stint_specification.comment, self.comment)
        self.assertEqual(self.stint_specification.team_size, 2)
        self.assertEqual(self.stint_specification.stint_definition, self.stint_definition)
        self.assertEqual(self.stint_specification.min_team_size, 1)
        self.assertEqual(self.stint_specification.max_team_size, 12)
        self.assertEqual(self.stint_specification.backup_stint_specification, self.backup_stint_specification)
        self.assertEqual(self.stint_specification.subject_countries.first(), Country.objects.first())
        self.assertEqual(self.stint_specification.opt_in_code, '231432123')
        self.assertEqual(self.stint_specification.min_earnings, 24.15)
        self.assertEqual(self.stint_specification.max_earnings, 24.16)
        self.assertEqual(self.stint_specification.immediate_payment_method, StintSpecification.PAYMENT_CHOICES.PHONE_RECHARGE)
        self.assertTrue(self.stint_specification.late_arrival)

    @staticmethod
    def test_teamsize_nullable():
        """
        Confirm min/max team size can be left blank
        """
        # both nullable
        StintSpecificationFactory(team_size=2, min_team_size=None, max_team_size=None)

        # single nullables
        StintSpecificationFactory(team_size=2, min_team_size=None, max_team_size=3)
        StintSpecificationFactory(team_size=2, min_team_size=1, max_team_size=None)

    def test_uniqueness_errors(self):
        """
        Opt_in must be unique on a case-insensitive level
        """
        StintSpecificationFactory(opt_in_code='orange')
        with self.assertRaises(IntegrityError):
            StintSpecificationFactory(opt_in_code='orange')
        with self.assertRaises(IntegrityError):
            StintSpecificationFactory(opt_in_code='OrAnGe')

    def test_validation_errors(self):
        """
        Confirm violation of team_size and earnings requirements trigger errors.
        """
        # min team_size exceeds team_size
        with self.assertRaises(ValidationError):
            StintSpecificationFactory(min_team_size=3, team_size=1)
        # max team_size less than team_size
        with self.assertRaises(ValidationError):
            StintSpecificationFactory(max_team_size=3, team_size=4)
        # min earnings exceed max
        with self.assertRaises(ValueError):
            StintSpecificationFactory(min_earnings=10, max_earnings=5)
        # min earnings less than combined min earnings across specifications
        ss = StintSpecificationFactory(min_earnings=10, max_earnings=15)
        for _ in range(2):
            StintModuleSpecificationFactory(stint_specification=ss, min_earnings=5, max_earnings=5)
        with self.assertRaises(ValueError):
            ss.min_earnings = 2
            ss.save()
        # max earnings less than combined max earnings across specifiations
        with self.assertRaises(ValueError):
            ss.max_earnings = 2
            ss.save()

    def test_circuluar_parent(self):
        # While Stint_Specification.save() should execute in the same way as StintSpecificationFactory(),
        # the latter is not picked up in coverage. The first is thus implemented here.
        #
        # pylint: disable=protected-access
        #
        self.assertTrue(self.circular_stint_specification_1._validate_not_circular())
        # Confirms 0 gen checking works
        self.circular_stint_specification_1.backup_stint_specification = self.circular_stint_specification_1
        self.assertFalse(self.circular_stint_specification_1._validate_not_circular())
        self.circular_stint_specification_3.backup_stint_specification = self.circular_stint_specification_2
        self.circular_stint_specification_3.save()
        # Confirms 1 gen checking works
        self.circular_stint_specification_2.backup_stint_specification = self.circular_stint_specification_3
        self.assertFalse(self.circular_stint_specification_2._validate_not_circular())
        self.circular_stint_specification_4.backup_stint_specification = self.circular_stint_specification_5
        self.circular_stint_specification_4.save()
        self.circular_stint_specification_5.backup_stint_specification = self.circular_stint_specification_6
        self.circular_stint_specification_5.save()
        self.circular_stint_specification_6.backup_stint_specification = self.circular_stint_specification_4
        # Confirms 1+ gen checking works
        self.assertFalse(self.circular_stint_specification_6._validate_not_circular())

    def test_save(self):
        """
        Confirms validation error on circular save
        """
        with self.assertRaises(ValidationError):
            self.circular_stint_specification_1.backup_stint_specification = self.circular_stint_specification_1
            self.circular_stint_specification_1.save()

    def test_duplicate(self):
        stint_specification_2 = self.stint_specification.duplicate()
        self.assertEqual(stint_specification_2.name, '{}_copy'.format(self.stint_specification.name))
        # Children should be the same
        self.assertEqual(stint_specification_2.stint_definition, self.stint_specification.stint_definition)
        # Sibling sets should be the same
        self.assertEqual(
            list(stint_specification_2.stint_specification_countries.values_list('country', flat=True)),
            list(self.stint_specification.stint_specification_countries.values_list('country', flat=True)),
        )

        # XXX: Address in issue #812
        # pylint:disable=consider-using-set-comprehension
        # self.assertEqual(set([obj.variable_definition for obj in stint_specification_2.variables.all()]),
        #                  set([obj.variable_definition for obj in self.stint_specification.variables.all()])
        # )

    def test_confirm_optin_uniqueness(self):
        """
        Confirm opt-in codes must have case insensitive uniqueness
        """
        StintSpecificationFactory(opt_in_code='Whatevs')
        with self.assertRaises(IntegrityError):
            StintSpecificationFactory(opt_in_code='whatEvs')

    def test_realize(self):
        stint = self.stint_specification.realize(self.user)
        self.assertIsNotNone(stint)
        self.assertEqual(stint.stint_specification, self.stint_specification)


class TestStintSpecificationRobot(EryTestCase):
    def setUp(self):
        self.stint_specification_robot = StintSpecificationRobotFactory()

    def test_exists(self):
        self.assertIsNotNone(self.stint_specification_robot)

    # def test_duplicate(self):
    #     stint_specification_2 = self.stint_specification_robot.stint_specification.duplicate()
    #     stint_specification_robot_2 = stint_specification_2.stint_specification_robots.first()
    #     self.assertEqual(stint_specification_robot_2.robot, self.stint_specification_robot.robot)
    #     self.assertEqual(stint_specification_robot_2.number, self.stint_specification_robot.number)

    def test_create(self):
        # Create with matching stint sprcification but not robot
        stint_specification_robot_2 = StintSpecificationRobot(stint_specification=StintSpecificationFactory())
        stint_specification_robot_2.save()
        stint_specification_robot_2.robots.add(self.stint_specification_robot.robots.first())
        stint_specification_robot_2.save()

        # Create with matching robot but not stint specification
        stint_specification_robot_3 = StintSpecificationRobot(
            stint_specification=self.stint_specification_robot.stint_specification
        )
        stint_specification_robot_3.save()
        stint_specification_robot_3.robots.add(RobotFactory())
        stint_specification_robot_3.save()

        self.assertEqual(StintSpecificationRobot.objects.all().count(), 3)

    def test_unique_together(self):
        with self.assertRaises(IntegrityError):
            stint_specification_robot = StintSpecificationRobot(
                stint_specification=self.stint_specification_robot.stint_specification
            )
            stint_specification_robot.save()
            stint_specification_robot.robots.add(self.stint_specification_robot.robots.first())
            stint_specification_robot.save()


class TestStintSpecificationVariable(EryTestCase):
    def setUp(self):
        self.variable_definition = VariableDefinitionFactory(data_type=VariableDefinition.DATA_TYPE_CHOICES.str)
        self.stint_specification = StintSpecificationFactory()
        self.stint_specification_variable = StintSpecificationVariableFactory(
            stint_specification=self.stint_specification,
            set_to_every_nth=3,
            value='something significant',
            variable_definition=self.variable_definition,
        )

    def test_exists(self):
        self.assertIsNotNone(self.stint_specification_variable)

    def test_expected_attributes(self):
        self.assertEqual(self.stint_specification_variable.stint_specification, self.stint_specification)
        self.assertEqual(self.stint_specification_variable.set_to_every_nth, 3)
        self.assertEqual(self.stint_specification_variable.value, 'something significant')
        self.assertEqual(self.stint_specification_variable.variable_definition, self.variable_definition)


class TestStintModuleSpecification(EryTestCase):
    def setUp(self):
        ss = StintSpecificationFactory(min_earnings=3, max_earnings=7)
        self.stint_module_specification = StintModuleSpecificationFactory(
            hand_timeout=120,
            hand_warn_timeout=60,
            stop_on_quit=False,
            min_earnings=0.14,
            max_earnings=5.5,
            timeout_earnings=1.25,
            stint_specification=ss,
        )

    def test_exists(self):
        self.assertIsNotNone(self.stint_module_specification)

    def test_expected_attributes(self):
        self.assertEqual(self.stint_module_specification.hand_timeout, 120)
        self.assertEqual(self.stint_module_specification.hand_warn_timeout, 60)
        self.assertFalse(self.stint_module_specification.stop_on_quit)
        self.assertEqual(self.stint_module_specification.min_earnings, 0.14)
        self.assertEqual(self.stint_module_specification.max_earnings, 5.5)
        self.assertEqual(self.stint_module_specification.timeout_earnings, 1.25)

    def test_expected_errors(self):
        """
        Confirm min/max earning conflicts trigger expected errors.
        """
        # min > max
        with self.assertRaises(ValueError):
            StintModuleSpecificationFactory(min_earnings=20, max_earnings=10)

        # min exceeds stint_specification level min
        stint_specification = StintSpecificationFactory(min_earnings=10, max_earnings=15)
        with self.assertRaises(ValueError):
            StintModuleSpecificationFactory(min_earnings=20, max_earnings=20, stint_specification=stint_specification)

        # max exceeds stint_specification level max
        with self.assertRaises(ValueError):
            StintModuleSpecificationFactory(min_earnings=10, max_earnings=20, stint_specification=stint_specification)

        # min, along with other mins, exceeds stint_specification level min
        with self.assertRaises(ValueError):
            for _ in range(3):
                StintModuleSpecificationFactory(min_earnings=5, max_earnings=5, stint_specification=stint_specification)
        # max, along with other maxs, exceeds stint_specification level max
        stint_specification.module_specifications.all().delete()
        with self.assertRaises(ValueError):
            for _ in range(3):
                StintModuleSpecificationFactory(min_earnings=1, max_earnings=10, stint_specification=stint_specification)


class TestDatasetLink(EryTestCase):
    """
    Confirm linking of Dataset works as expected.
    """

    def setUp(self):
        self.stint_specification = StintSpecificationFactory()
        module_definition = ModuleDefinitionFactory()
        StintDefinitionModuleDefinitionFactory(
            stint_definition=self.stint_specification.stint_definition, module_definition=module_definition
        )
        self.vds = [
            VariableDefinitionFactory(
                name='testvd1', scope=VariableDefinition.SCOPE_CHOICES.hand, module_definition=module_definition
            ),
            VariableDefinitionFactory(
                name='testvd2', scope=VariableDefinition.SCOPE_CHOICES.team, module_definition=module_definition
            ),
            VariableDefinitionFactory(
                name='testvd3', scope=VariableDefinition.SCOPE_CHOICES.module, module_definition=module_definition
            ),
        ]
        # 4th/5th vds are extras to ensure no unexpected behavior
        self.vds += [VariableDefinitionFactory(module_definition=module_definition) for _ in range(2)]

    def test_dataset_connected(self):
        """ Confirm dataset can be connected"""
        dataset = DatasetFactory()
        self.stint_specification.dataset = dataset
        self.stint_specification.save()

        stint_specification = StintSpecification.objects.get(id=self.stint_specification.id)
        self.assertIsNotNone(stint_specification.dataset)

    def test_required_rows(self):
        """Complain if there aren't at least two rows (one for header and one for values)"""
        empty_dataset_address = f'{os.getcwd()}/ery_backend/datasets/tests/data/empty_dataset.csv'
        with self.assertRaises(EryValidationError):
            Dataset.objects.create_dataset_from_file('EmptyDataset', open(empty_dataset_address, 'rb').read())
        one_row_dataset_address = f'{os.getcwd()}/ery_backend/datasets/tests/data/one_row_dataset.csv'
        one_row_dataset = Dataset.objects.create_dataset_from_file('OneRowDataset', open(one_row_dataset_address, 'rb').read())
        self.stint_specification.dataset = one_row_dataset
        with self.assertRaises(EryValidationError):
            self.stint_specification.get_dataset_variables()
        dataset_headers = ['a', 'b', 'c', 'd']
        # one values row required
        one_values_data = [{header: str(random.randint(1, 10)) for header in dataset_headers}]
        one_values_dataset = DatasetFactory(to_dataset=one_values_data)
        self.stint_specification.dataset = one_values_dataset
        self.stint_specification.get_dataset_variables()
        # multiple values rows acceptable
        mutli_values_data = [
            {header: str(random.randint(1, 10)) for header in dataset_headers} for _ in range(random.randint(3, 10))
        ]
        multi_values_dataset = DatasetFactory(to_dataset=mutli_values_data)
        self.stint_specification.dataset = multi_values_dataset
        self.stint_specification.get_dataset_variables()

    def test_matching_variables(self):
        """Confirm matching variables between dataset and stint_spec are correctly located"""
        dataset_headers = ['testvd1', 'testvd2', 'testvd3', 'testvd4']
        data_types = VariableDefinition.DATA_TYPE_CHOICES
        rows = []
        for _ in range(2):
            full_data = {}
            for i in range(4):
                data_type = self.vds[i].data_type
                value = random_dt_value(data_type)
                key = dataset_headers[i]
                value = json.dumps(value) if data_type in (data_types.dict, data_types.list) else str(value)
                full_data[key] = value
            rows.append(full_data)
        dataset = DatasetFactory(to_dataset=rows)
        self.stint_specification.dataset = dataset

        # One matching variable
        StintSpecificationVariableFactory(variable_definition=self.vds[0], stint_specification=self.stint_specification)
        variable_values = self.stint_specification.get_dataset_variables()
        vd1_is_json = self.vds[0].data_type in (data_types.dict, data_types.list)
        vd1_expected = json.loads(rows[-1]['testvd1']) if vd1_is_json else rows[-1]['testvd1']
        vd1_actual = variable_values[self.vds[0].id]
        self.assertEqual(vd1_expected, vd1_actual)

        # Multiple variables
        StintSpecificationVariableFactory(variable_definition=self.vds[1], stint_specification=self.stint_specification)
        StintSpecificationVariableFactory(variable_definition=self.vds[2], stint_specification=self.stint_specification)
        variable_values = self.stint_specification.get_dataset_variables()
        vd1_is_json = self.vds[0].data_type in (data_types.dict, data_types.list)
        vd1_expected = json.loads(rows[-1]['testvd1']) if vd1_is_json else rows[-1]['testvd1']
        vd1_actual = variable_values[self.vds[0].id]
        self.assertEqual(vd1_expected, vd1_actual)
        vd2_is_json = self.vds[1].data_type in (data_types.dict, data_types.list)
        vd2_expected = json.loads(rows[-1]['testvd2']) if vd2_is_json else rows[-1]['testvd2']
        vd2_actual = variable_values[self.vds[1].id]
        self.assertEqual(vd2_expected, vd2_actual)
        vd3_is_json = self.vds[2].data_type in (data_types.dict, data_types.list)
        vd3_expected = json.loads(rows[-1]['testvd3']) if vd3_is_json else rows[-1]['testvd3']
        vd3_actual = variable_values[self.vds[2].id]
        self.assertEqual(vd3_expected, vd3_actual)
