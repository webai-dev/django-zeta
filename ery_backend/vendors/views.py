from django.http import Http404
from django.shortcuts import render

from ery_backend.stints.views import redirect_to_market_stint
from ery_backend.vendors.models import Vendor


def render_vendor_manifest(request):
    try:
        vendor = Vendor.get_vendor_by_request(request)
    except Vendor.DoesNotExist:
        raise Http404

    return render(request, 'manifest.json', context={"vendor": vendor,})


def render_vendor_marketplace(request, vendor_gql_id):
    return redirect_to_market_stint(request)
