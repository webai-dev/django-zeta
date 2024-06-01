from django.conf import settings
from django.conf.urls import include
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponse
from django.middleware.csrf import get_token
from django.shortcuts import redirect
from django.urls import path
from django.views import defaults as default_views
from django.views.decorators.csrf import csrf_exempt

from graphene_django.views import GraphQLView

from ery_backend.base.middleware import DataLoaderMiddleware
from ery_backend.schema import schema
from ery_backend.stints.views import render_datastore_csv, test_stint_view
from ery_backend.users.utils import authenticated_user


def csrf_view(request):
    authenticated_user(request)
    response = HttpResponse('')
    response.set_cookie(key='csrftoken', value=get_token(request), samesite='Strict')
    return response


_graphql_view = GraphQLView.as_view(graphiql=True, schema=schema, middleware=[DataLoaderMiddleware()])

if settings.DEBUG and 'silk' in settings.INSTALLED_APPS:
    from silk.profiling.profiler import silk_profile

    @silk_profile()
    def profiled_graphql_view(*args, **kwargs):
        return _graphql_view(*args, **kwargs)

    graphql_view = profiled_graphql_view
else:
    graphql_view = _graphql_view

urlpatterns = [
    path('', lambda request: redirect('graphql/', permanent=True)),
    path('admin/', admin.site.urls),  # XXX: move me to settings.DEBUG
    path('csrf/', csrf_exempt(csrf_view)),
    path('graphql/', csrf_exempt(graphql_view) if settings.DEBUG else graphql_view),
    path('healthz', lambda request: HttpResponse("OK")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if "health_check" in settings.INSTALLED_APPS:
    urlpatterns += [path('healthz', include('health_check.urls'))]

if settings.DEBUG:
    urlpatterns += [
        path('assets/', include('ery_backend.assets.urls')),
        path('datasets/', include('ery_backend.datasets.urls')),
        path('stints/<stint_gql_id>/data', render_datastore_csv),

        path('export/', include('ery_backend.base.export_urls')),
        path('import/', include('ery_backend.base.import_urls')),

        path('stints/<stint_gql_id>/test_cover_view', test_stint_view),

        path('400/', default_views.bad_request, kwargs={'exception': Exception('Bad Request!')}),
        path('403/', default_views.permission_denied, kwargs={'exception': Exception('Permission Denied')}),
        path('404/', default_views.page_not_found, kwargs={'exception': Exception('Page not Found')}),
        path('500/', default_views.server_error),
    ]

    if 'silk' in settings.INSTALLED_APPS:
        urlpatterns += [path('silk/', include('silk.urls', namespace='silk')),]

    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns += [path('__debug__/', include(debug_toolbar.urls)),]
