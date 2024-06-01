from ery_backend.base.testcases import EryTestCase
from ..factories import FormFactory


class TestFormBXMLSerializer(EryTestCase):
    def setUp(self):
        self.form = FormFactory()
        self.form_serializer = self.form.get_bxml_serializer()(instance=self.form)

    def test_exists(self):
        self.assertIsNotNone(self.form_serializer)

    def test_expected_attributes(self):
        self.assertEqual(self.form_serializer.data['comment'], self.form.comment)
        self.assertEqual(self.form_serializer.data['name'], self.form.name)
