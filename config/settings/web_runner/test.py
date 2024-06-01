import random
import string

from ..base import *  # noqa

DEBUG = False

ROOT_URLCONF = 'config.web_runner_urls'
INSTALLED_APPS = ['test_without_migrations',] + INSTALLED_APPS

AUTHENTICATION_BACKENDS = ['ery_backend.frontends.web_views.Auth0'] + AUTHENTICATION_BACKENDS

CACHES['default']['KEY_PREFIX'] = ''.join(random.choices(string.ascii_letters, k=8))

SECRET_KEY = env('DJANGO_SECRET_KEY', default='INCASESOMETHINGGOESWRONGWITHENV')

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]
LOGIN_URL = '/login/auth0'
LOGIN_REDIRECT_URL = '/'

JWT_SECRET = 'I3IadGN29m'
