from django.http import HttpRequest

from ery_backend.base.testcases import EryTestCase

from ..factories import VendorFactory
from ..views import render_vendor_manifest


class TestManifestRender(EryTestCase):
    def test_manifest(self):
        vendor = VendorFactory()
        request = HttpRequest()
        request.META['HTTP_HOST'] = vendor.homepage_url
        response = render_vendor_manifest(request)
        self.assertIsNotNone(response.content)
