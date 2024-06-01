from test_plus.test import TestCase

from ..factories import ValidatorFactory
from ..models import Validator


class TestValidatorBXMLSerializer(TestCase):
    def setUp(self):
        self.validator = ValidatorFactory(regex=None)
        self.validator_2 = ValidatorFactory(code=None)
        self.validator_serializer = Validator.get_bxml_serializer()(self.validator)
        self.validator_serializer_2 = Validator.get_bxml_serializer()(self.validator_2)

    def test_exists(self):
        self.assertIsNotNone(self.validator)

    def test_expected_attributes(self):
        self.assertEqual(self.validator_serializer.data['name'], self.validator.name)
        self.assertEqual(self.validator_serializer.data['comment'], self.validator.comment)
        self.assertEqual(self.validator_serializer.data['code'], self.validator.code)
        self.assertEqual(self.validator_serializer_2.data['regex'], self.validator_2.regex)
