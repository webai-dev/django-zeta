import unittest

from django.core.exceptions import ValidationError

from ery_backend.base.exceptions import EryValueError
from ery_backend.base.testcases import EryTestCase
from ery_backend.keywords.factories import KeywordFactory
from ery_backend.variables.factories import ModuleVariableFactory, VariableDefinitionFactory
from ery_backend.variables.models import VariableDefinition
from ..factories import ValidatorFactory
from ..models import Validator


class TestValidator(EryTestCase):
    def setUp(self):
        self.message = 'Is there any objective validity in our subjective philosophy?!?'
        self.regex_message = 'r[TheLimitDoesNotCompute]*'
        self.validator = ValidatorFactory(name='test-validator', comment=self.message, code='01000011101', regex=None,)
        self.validator_2 = ValidatorFactory(regex=self.regex_message, code=None,)
        self.validator_3 = ValidatorFactory(code=None, nullable=True)

    def test_exists(self):
        self.assertIsNotNone(self.validator)

    def test_expected_attributes(self):
        self.assertEqual(self.validator.name, 'test-validator')
        self.assertEqual(self.validator.comment, self.message)
        self.assertEqual(self.validator.code, '01000011101')
        self.assertEqual(self.validator_2.regex, self.regex_message)
        self.assertIsNotNone(self.validator.slug)
        self.assertTrue(self.validator_3.nullable)

    def test_initialization_errors(self):
        """
        Confirm only one of code/regex must be present.
        """
        with self.assertRaises(ValidationError):
            ValidatorFactory(code=None, regex=None)
        with self.assertRaises(ValidationError):
            ValidatorFactory(code='code', regex='r[ITit]+[GOESgoes]+[ONAND]{500, 5000}')

    def test_duplicate(self):
        preload_keywords = [KeywordFactory() for _ in range(3)]
        for keyword in preload_keywords:
            self.validator.keywords.add(keyword)
        validator_2 = self.validator.duplicate()
        self.assertIsNotNone(validator_2)
        self.assertEqual('{}_copy'.format(self.validator.name), validator_2.name)
        # Expected keywords
        for keyword in preload_keywords:
            self.assertIn(keyword, validator_2.keywords.all())

    def test_regex_validation(self):
        """
        Confirm regex validation works for values.
        """
        self.validator.code = None
        self.validator.regex = 'man says something'
        self.validator.save()
        variable_definition = VariableDefinitionFactory(
            validator=self.validator, data_type=VariableDefinition.DATA_TYPE_CHOICES.str
        )
        value = 'If a man says something and no one is around to hear it, is he still wrong?'
        variable = ModuleVariableFactory(variable_definition=variable_definition, value=value)
        variable.variable_definition.validator.validate(variable.value, variable)

        value = 'If a boy says something and no one is around to hear it, then good.'
        variable.value = value
        with self.assertRaises(EryValueError):
            variable.variable_definition.validator.validate(variable.value, variable)

    @unittest.skip("Address in issue #465")
    def test_nullable_validation(self):
        """
        Confirm nullable on non-nullable validator causes error.
        """
        validator = ValidatorFactory(nullable=False, code='1==1', regex=None)
        with self.assertRaises(EryValueError):
            VariableDefinitionFactory(validator=validator, default_value=None)

    def test_import(self):
        xml = open('ery_backend/validators/tests/data/module_definition-vd-1.bxml', 'rb')
        validator = Validator.import_instance_from_xml(xml, name='instance_new')

        self.assertIsNotNone(validator)
        self.assertEqual(validator.name, 'instance_new')
