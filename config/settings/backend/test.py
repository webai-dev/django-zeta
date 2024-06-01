from ..base import *  # noqa
import random
import string

DEBUG = False

INSTALLED_APPS = ['test_without_migrations',] + INSTALLED_APPS


CACHES['default']['KEY_PREFIX'] = ''.join(random.choices(string.ascii_letters, k=8))

SECRET_KEY = env('DJANGO_SECRET_KEY', default='INCASESOMETHINGGOESWRONGWITHENV')

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]
LOGIN_URL = 'http://landing.behavery.local:8001/'
