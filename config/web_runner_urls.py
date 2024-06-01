from django.conf import settings
from django.conf.urls import include
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import path, re_path
from django.views import defaults as default_views
from django.views.decorators.csrf import csrf_exempt

from ery_backend.labs.views import play_most_recent
from ery_backend.stints.views import redirect_to_market_stint, render_stint
from ery_backend.vendors.models import Vendor

from .urls import csrf_view


def render_manifest(request):
    return render(request, 'manifest.json', content_type='application/json', context={'vendor': Vendor.get_vendor_by_request(request)})


def render_service_woker(request):
    return render(request, 'sw.js', content_type='application/javascript', context={'vendor': Vendor.get_vendor_by_request(request)})


urlpatterns = [
    path('', redirect_to_market_stint),
    path('', include('social_django.urls')),
    path('admin/', admin.site.urls),
    path('manifest.json', render_manifest),
    path('sw.js', render_service_woker),
    path('csrf/', csrf_exempt(csrf_view)),  # CSRF
    path('healthz', lambda request: HttpResponse("OK")),  # Health check
    re_path(r'^stints/(?P<stint_gql_id>\S+)[/]?', render_stint, name='render_stint'),
    re_path(r'^started_by/(?P<started_by_gql_id>\S+)[/]?', redirect_to_market_stint),
    re_path(r'^labs/(?P<lab_secret>\S+)/(?P<as_player>\d+)[/]?', play_most_recent),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if "health_check" in settings.INSTALLED_APPS:
    urlpatterns += [path('healthz', include('health_check.urls'))]

if settings.DEBUG:
    urlpatterns += [
        path('400/', default_views.bad_request, kwargs={'exception': Exception('Bad Request!')}),
        path('403/', default_views.permission_denied, kwargs={'exception': Exception('Permission Denied')}),
        path('404/', default_views.page_not_found, kwargs={'exception': Exception('Page not Found')}),
        path('500/', default_views.server_error),
        path('silk/', include('silk.urls', namespace='silk')),
    ]

    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns += [path('__debug__/', include(debug_toolbar.urls))]
