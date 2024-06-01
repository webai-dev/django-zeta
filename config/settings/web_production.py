from .production import *  # noqa

import environ
env = environ.Env()

PRIMARY_SITE = env('PRIMARY_SITE', default="stg.behavery.com")

CORS_ORIGIN_WHITELIST = (
    f'https://about.{PRIMARY_SITE}',
)

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
] + MIDDLEWARE

CORS_ALLOW_CREDENTIALS = True

ALLOWED_HOSTS = ['*']

INSTALLED_APPS += [
    'gunicorn',
    'health_check',
    'health_check.db',
    'health_check.cache',
    'corsheaders',
]
