from ..base import *  # noqa
import os

PRIMARY_SITE = "localhost"

DEBUG = env.bool('DJANGO_DEBUG', default=True)
SILKY_PYTHON_PROFILER = True
SILKY_PYTHON_PROFILER_BINARY = True
SILKY_PYTHON_PROFILER_RESULT_PATH = 'profs'

INSTALLED_APPS += [
#    'debug_toolbar',
    'corsheaders',
    'django_extensions',
    'silk',
]
MIDDLEWARE = [
    'silk.middleware.SilkyMiddleware',
    'corsheaders.middleware.CorsMiddleware',
#    'debug_toolbar.middleware.DebugToolbarMiddleware',
] + MIDDLEWARE

AUTHENTICATION_BACKENDS = ['ery_backend.frontends.web_views.Auth0'] + AUTHENTICATION_BACKENDS

INTERNAL_IPS = ['127.0.0.1', '10.0.2.2', ]
if os.environ.get('USE_DOCKER') == 'yes':
    import socket
    ip = socket.gethostbyname(socket.gethostname())
    INTERNAL_IPS += [ip[:-1] + '1']

SECRET_KEY = env('DJANGO_SECRET_KEY', default='uFucK,w+$]peX2gV#Gou`(*>z_dWKb=+B.Y]X:L3ZK9*$)aW5)')

CORS_ORIGIN_ALLOW_ALL = True
CORS_ALLOW_CREDENTIALS = True

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'debug_file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': '/tmp/debug.log'
        },
        'info_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/tmp/info.log'
        }
    },
    'loggers': {
        'ery_backend.roles.utils': {
            'handlers': ['debug_file'],
            'level': 'DEBUG',
            'propogate': True,
        },
        'ery_backend.base.testcases': {
            'handlers': ['info_file'],
            'level': 'INFO',
            'propogate': True,
        }
    }
}

# Authentication
JWT_SECRET = 'I3IadGN29m'
ALLOWED_HOSTS=['*']

ROOT_URLCONF = 'config.web_runner_urls'
RUNNER_URL = 'http://runner.behavery.local:8080'

LOGIN_URL = '/login/auth0'
LOGIN_REDIRECT_URL = '/'

SOCIAL_AUTH_AUTH0_DOMAIN = 'ery.auth0.com'
SOCIAL_AUTH_AUTH0_KEY = 'TkyjDyLQe9zyCLTXgCkhqjSnC0e4RPij'
SOCIAL_AUTH_AUTH0_SECRET = 'E80E3hnpOZNOEKTMSB90dwp5WF2hcEwY7h2K29W1blfRhYL5R4-86U0WAKgD1dZl'
SOCIAL_AUTH_TRAILING_SLASH = False  # Remove trailing slash from routes
SOCIAL_AUTH_AUTH0_SCOPE = ['openid', 'profile', 'email']
SOCIAL_AUTH_POSTGRES_JSONFIELD = True
