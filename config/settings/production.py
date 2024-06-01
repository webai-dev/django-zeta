import environ

from .base import *  # noqa

DEPLOYMENT = "production"

env = environ.Env()

ERY_BABEL_HOSTPORT = "ery-babel:30000"
ERY_ENGINE_HOSTPORT = "ery-engine:30001"

SECRET_KEY = env('DJANGO_SECRET_KEY')
