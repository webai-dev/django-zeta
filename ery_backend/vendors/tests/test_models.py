from ery_backend.assets.factories import ImageAssetFactory
from ery_backend.base.testcases import EryTestCase

from ..factories import VendorFactory
from ..models import Vendor


class TestVendor(EryTestCase):
    def setUp(self):
        self.icon = ImageAssetFactory()
        self.vendor = VendorFactory(
            background_color='#c2b84c',
            short_name='crocs',
            icon=self.icon,
            homepage_url='dontwearcrocs.ery.sh',
            theme_color='#242329',
            name='dontwearcrocs',
            comment='Unless you\'re rich?',
        )

    def test_exists(self):
        self.assertIsNotNone(self.vendor)

    def test_expected_attributes(self):
        self.vendor.refresh_from_db()
        self.assertEqual(self.vendor.name, 'dontwearcrocs')
        self.assertEqual(self.vendor.comment, 'Unless you\'re rich?')
        self.assertEqual('#c2b84c', self.vendor.background_color)
        self.assertEqual('crocs', self.vendor.short_name)
        self.assertEqual(self.icon, self.vendor.icon)
        self.assertEqual('dontwearcrocs.ery.sh', self.vendor.homepage_url)
        self.assertEqual('#242329', self.vendor.theme_color)

    def test_duplicate(self):
        duplicate = self.vendor.duplicate()
        self.assertEqual(duplicate.name, f'{self.vendor.name}_copy')
        self.assertEqual(duplicate.comment, self.vendor.comment)
        self.assertEqual(duplicate.background_color, self.vendor.background_color)
        self.assertEqual(duplicate.short_name, self.vendor.short_name)
        self.assertEqual(duplicate.icon, self.vendor.icon)
        self.assertEqual(duplicate.homepage_url, self.vendor.homepage_url)
        self.assertEqual(duplicate.theme_color, self.vendor.theme_color)

    def test_get_vendor_by_request(self):
        from django.http import HttpRequest

        request = HttpRequest()
        request.META['HTTP_HOST'] = 'dontwearcrocs.ery.sh'
        self.assertEqual(Vendor.get_vendor_by_request(request), self.vendor)

        # With port
        request.META['HTTP_HOST'] = 'dontwearcrocs.ery.sh:8000'
        self.assertEqual(Vendor.get_vendor_by_request(request), self.vendor)

        # Confirm doesn't match everything
        request.META['HTTP_HOST'] = 'www.dontwearcrocs.ery.sh'
        with self.assertRaises(Vendor.DoesNotExist):
            Vendor.get_vendor_by_request(request)

        request.META['HTTP_HOST'] = 'dontwearcrocs.com'
        self.assertIsNone(Vendor.get_vendor_by_request(request))
