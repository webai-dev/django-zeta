from ery_backend.base.testcases import EryTestCase

from ..factories import VendorFactory
from ..models import Vendor


class TestVendorBXMLSerializer(EryTestCase):
    def setUp(self):

        self.vendor = VendorFactory()
        self.vendor_serializer_data = Vendor.get_bxml_serializer()(self.vendor).data

    def test_expected_attributes(self):
        self.assertEqual(self.vendor_serializer_data['name'], self.vendor.name)
        self.assertEqual(self.vendor_serializer_data['background_color'], self.vendor.background_color)
        self.assertEqual(self.vendor_serializer_data['short_name'], self.vendor.short_name)
        self.assertEqual(self.vendor_serializer_data['icon'], self.vendor.icon.slug)
        self.assertEqual(self.vendor_serializer_data['homepage_url'], self.vendor.homepage_url)
        self.assertEqual(self.vendor_serializer_data['theme_color'], self.vendor.theme_color)
