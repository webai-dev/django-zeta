import re

from django.db import models

from ery_backend.base.cache import ery_cache
from ery_backend.base.mixins import PrivilegedMixin
from ery_backend.base.models import EryNamedSlugged


@ery_cache
def get_regex_ery_sh_domain():
    return re.compile(r"^(.*).ery.sh(:\d+)?$")


regex_ery_sh_domain = get_regex_ery_sh_domain()


class Vendor(EryNamedSlugged, PrivilegedMixin):
    background_color = models.CharField(max_length=7, default="#ffffff")
    short_name = models.CharField(max_length=12, blank=True, null=True)
    icon = models.ForeignKey('assets.ImageAsset', on_delete=models.SET_NULL, blank=True, null=True)
    homepage_url = models.CharField(max_length=255, blank=True, null=True)
    theme_color = models.CharField(max_length=7, default="#000000")

    @classmethod
    def get_vendor_by_request(cls, request):
        matching = re.search(regex_ery_sh_domain, request.META["HTTP_HOST"])

        if not matching:
            return None

        vendor_name = matching.group(1)
        return cls.objects.get(name=vendor_name)
