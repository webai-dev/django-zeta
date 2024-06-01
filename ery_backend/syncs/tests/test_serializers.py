from ery_backend.base.testcases import EryTestCase
from ..factories import EraFactory
from ..models import Era


class TestEraBXMLSerializer(EryTestCase):
    def setUp(self):
        self.era = EraFactory()
        self.era_serializer = Era.get_bxml_serializer()(self.era)

    def test_exists(self):
        self.assertIsNotNone(self.era_serializer)

    def test_expected_attributes(self):
        self.assertEqual(self.era_serializer.data['action'], self.era.action.name)
        self.assertEqual(self.era_serializer.data['comment'], self.era.comment)
        self.assertEqual(self.era_serializer.data['name'], self.era.name)
