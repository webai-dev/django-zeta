from unittest import mock

from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError

from ery_backend.base.testcases import EryTestCase, create_test_hands
from ery_backend.keywords.factories import KeywordFactory
from ery_backend.modules.factories import ModuleDefinitionFactory, ModuleDefinitionProcedureFactory

from ..factories import ProcedureFactory, ProcedureArgumentFactory
from ..models import Procedure


class TestProcedure(EryTestCase):
    def setUp(self):
        self.procedure = ProcedureFactory(name='test_procedure', comment='eval erythang', code='rm -Rf *',)

    def test_exists(self):
        self.assertIsNotNone(self.procedure)

    def test_expected_attributes(self):
        self.assertEqual(self.procedure.name, 'test_procedure')
        self.assertEqual(self.procedure.comment, 'eval erythang')
        self.assertEqual(self.procedure.code, 'rm -Rf *')

    def test_arg_ordering(self):
        """
        Confirm args are ordered as expected.
        """
        arg_3 = ProcedureArgumentFactory(procedure=self.procedure, order=3)
        arg_2 = ProcedureArgumentFactory(procedure=self.procedure, order=2)
        arg_1 = ProcedureArgumentFactory(procedure=self.procedure, order=1)

        function = self.procedure.generate_js_function(target='engine')
        # extra space due to lack of optional args
        self.assertEqual(
            function, f"function ({arg_1.name}, {arg_2.name}, {arg_3.name})" f"{{  return {self.procedure.code} }};"
        )

    def test_duplicate(self):
        for _ in range(3):
            keyword = KeywordFactory()
            self.procedure.keywords.add(keyword)
        ProcedureArgumentFactory(procedure=self.procedure)
        ProcedureArgumentFactory(procedure=self.procedure, default=3)
        procedure_copy = self.procedure.duplicate()
        self.assertEqual(f'{self.procedure.name}_copy', procedure_copy.name)
        self.assertEqual(self.procedure.code, procedure_copy.code)
        self.assertEqual(procedure_copy.arguments.count(), 2)
        self.assertTrue(procedure_copy.arguments.filter(default=3).exists())
        self.assertEqual(procedure_copy.keywords.count(), 3)

    def test_import(self):
        xml = open('ery_backend/procedures/tests/data/procedure-0.bxml', 'rb')
        procedure = Procedure.import_instance_from_xml(xml)
        self.assertEqual(procedure.name, 'duplicate_procedure')
        self.assertEqual(procedure.arguments.count(), 2)
        self.assertTrue(procedure.arguments.filter(default=2).exists())

    def test_expected_naming_errors(self):
        """
        Confirm Procedure cannot violate js naming conventions.
        """
        # reserved words
        with self.assertRaises(ValidationError):
            ProcedureFactory(name='choices')
        with self.assertRaises(ValidationError):
            ProcedureFactory(name='var')
        with self.assertRaises(ValidationError):
            ProcedureFactory(name='in')
        with self.assertRaises(ValidationError):
            ProcedureFactory(name='for')

        # punctuation
        # valid
        ProcedureFactory(name='$hasdollarsign')
        ProcedureFactory(name='has_underscore')
        # invalid
        with self.assertRaises(ValidationError):
            ProcedureFactory(name='incorrect.punctuation')
        with self.assertRaises(ValidationError):
            ProcedureFactory(name='unnecessary-punct-u-ation')

        # numbers
        # valid
        ProcedureFactory(name='endswith2')
        # invalid
        with self.assertRaises(ValidationError):
            ProcedureFactory(name='3time2time1timebop')

        # spaces
        with self.assertRaises(ValidationError):
            ProcedureFactory(name='has spaces')


class TestAgnosticEvaluation(EryTestCase):
    """
    Verify methods shared between procedures to be evaluated client or server side.
    """

    def test_generate_js_function(self):
        procedure = ProcedureFactory(
            name='rand_int', comment="Return a random integer between 1 and 100", code='Math.floor(Math.random()*100) + 1',
        )
        returned_function = procedure.generate_js_function()
        # extra space comes from lack of prepended code
        expected_function = f'function (){{  return {procedure.code} }};'
        self.assertEqual(returned_function, expected_function)


class TestServerSideEvaluation(EryTestCase):
    @classmethod
    def setUpClass(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)
        cls.hand = create_test_hands(n=1, signal_pubsub=False).first()

    @mock.patch('ery_backend.scripts.engine_client.evaluate_without_side_effects')
    def test_server_side_evaluate(self, mock_evaluate):
        """
        Confirm engine_client's evaluate called as expected
        """
        procedure = ProcedureFactory(
            name='rand_int', comment="Return a random integer between 1 and 100", code='Math.floor(Math.random()*100) + 1;',
        )
        procedure.evaluate(self.hand)
        mock_evaluate.assert_called_with(procedure.js_name, procedure.code, self.hand)


class TestProcedureArgument(EryTestCase):
    def setUp(self):
        self.procedure = ProcedureFactory(name='add_stuff')
        self.procedure_arg = ProcedureArgumentFactory(procedure=self.procedure, name='a_val', comment='First value to add')

    def test_exists(self):
        self.assertIsNotNone(self.procedure_arg)

    def test_expected_attributes(self):
        self.assertEqual(self.procedure_arg.procedure, self.procedure)
        self.assertEqual(self.procedure_arg.name, 'a_val')
        self.assertEqual(self.procedure_arg.comment, 'First value to add')

    def test_naming_restrictions(self):
        """
        Confirm argument required to have a valid js-argument name.
        """
        # _ should work
        ProcedureArgumentFactory(name='semi_necessary_punctuation')
        # punctation in name that isn't _
        with self.assertRaises(ValidationError):
            ProcedureArgumentFactory(name='unnecessary_punct-u-ation')
        # space in name
        with self.assertRaises(ValidationError):
            ProcedureArgumentFactory(name='thats not my name')

    def test_uniqueness_requirements(self):
        # order enforcement
        ProcedureArgumentFactory(procedure=self.procedure, order=3)
        with self.assertRaises(IntegrityError):
            ProcedureArgumentFactory(procedure=self.procedure, order=3)

        # name enforcement
        ProcedureArgumentFactory(procedure=self.procedure, name='dontcopyme')
        with self.assertRaises(IntegrityError):
            ProcedureArgumentFactory(procedure=self.procedure, name='dontcopyme')


class TestOptionalProcedureArgument(EryTestCase):
    def setUp(self):
        self.procedure = ProcedureFactory(name='add_more_stuff')
        self.procedure_argument = ProcedureArgumentFactory(
            order=2, procedure=self.procedure, name='make_professional', default=3
        )

    def confirm_single_match(self, procedure, procedure_argument, value):
        expected_function = (
            f'function ({procedure_argument.name})'
            f'{{ if (typeof {self.procedure_argument.name} === \'undefined\'){{'
            f' {procedure_argument.name} = {value}}};\n return {procedure.code} }};'
        )
        returned_function = procedure.generate_js_function()
        self.assertEqual(expected_function, returned_function)

    def test_generation(self):
        """
        Confirm inclusion in function definition.
        """
        self.confirm_single_match(self.procedure, self.procedure_argument, 3)

    def test_generation_types(self):
        """
        Confirm proper type interpretation from retrieval of database default to use of default in function generation.
        """

        # strs
        self.procedure_argument.default = "'im a string'"
        self.procedure_argument.save()
        self.confirm_single_match(self.procedure, self.procedure_argument, self.procedure_argument.default)

        self.procedure_argument.default = '"im a string'
        self.procedure_argument.save()
        self.confirm_single_match(self.procedure, self.procedure_argument, self.procedure_argument.default)

        # bools
        self.procedure_argument.default = True
        self.procedure_argument.save()
        self.confirm_single_match(self.procedure, self.procedure_argument, 'true')

        self.procedure_argument.default = False
        self.procedure_argument.save()
        self.confirm_single_match(self.procedure, self.procedure_argument, 'false')

    def test_ordering(self):
        """
        Confirm optional args generated after positional args.
        """
        required_procedure_argument = ProcedureArgumentFactory(
            order=1, procedure=self.procedure, name='passive_aggressiveness'
        )

        expected_function = (
            f'function ({required_procedure_argument.name},'
            f' {self.procedure_argument.name})'
            f'{{ if (typeof {self.procedure_argument.name} === \'undefined\'){{'
            f' {self.procedure_argument.name} = {self.procedure_argument.default}}};\n'
            f' return {self.procedure.code} }};'
        )

        returned_function = self.procedure.generate_js_function()
        self.assertEqual(expected_function, returned_function)


class TestModuleDefinitionProcedure(EryTestCase):
    def setUp(self):
        self.procedure = ProcedureFactory()
        self.module_definition = ModuleDefinitionFactory()
        self.module_definition_procedure = ModuleDefinitionProcedureFactory(
            name='test_pa', procedure=self.procedure, module_definition=self.module_definition
        )

    def test_exists(self):
        self.assertIsNotNone(self.module_definition_procedure)

    def test_expected_attributes(self):
        self.module_definition_procedure.refresh_from_db()
        self.assertEqual(self.module_definition_procedure.procedure, self.procedure)
        self.assertEqual(self.module_definition_procedure.name, 'test_pa')
        self.assertEqual(self.module_definition_procedure.module_definition, self.module_definition)
