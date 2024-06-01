"""
WSGI config for the ery_backend project.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

Usually you will have the standard Django WSGI application here, but it also
might make sense to replace the whole Django WSGI application with a custom one
that later delegates to the Django one. For example, you could introduce WSGI
middleware here, or combine a Django application with an application of another
framework.

"""
import os
import sys

from django.core.wsgi import get_wsgi_application

# This allows easy placement of apps within the interior
# ery_backend directory.
app_path = os.path.dirname(os.path.abspath(__file__)).replace('/config', '')
sys.path.append(os.path.join(app_path, 'ery_backend'))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.backend.production")

application = get_wsgi_application()
