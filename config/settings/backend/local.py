from ..base import *  # noqa
import os

PRIMARY_SITE = "localhost"
DEPLOYMENT = 'local'

DEBUG = env.bool('DJANGO_DEBUG', default=True)
SILKY_PYTHON_PROFILER = True
SILKY_PYTHON_PROFILER_BINARY = True
SILKY_PYTHON_PROFILER_RESULT_PATH = 'profs'

INSTALLED_APPS = (
    ['test_without_migrations'] 
    + INSTALLED_APPS 
    + [
        # 'debug_toolbar', 'graphiql_debug_toolbar',
        'corsheaders', 'django_extensions', 'sslserver', 'silk'
    ]
)

MIDDLEWARE = [
    'silk.middleware.SilkyMiddleware',
    'corsheaders.middleware.CorsMiddleware',
#    'graphiql_debug_toolbar.middleware.DebugToolbarMiddleware'
] + MIDDLEWARE

INTERNAL_IPS = ['127.0.0.1', '10.0.2.2', ]
if os.environ.get('USE_DOCKER') == 'yes':
    import socket
    ip = socket.gethostbyname(socket.gethostname())
    INTERNAL_IPS += [ip[:-1] + '1']

SECRET_KEY = env('DJANGO_SECRET_KEY', default='uFucK,w+$]peX2gV#Gou`(*>z_dWKb=+B.Y]X:L3ZK9*$)aW5)')

CORS_ORIGIN_ALLOW_ALL = True
CORS_ALLOW_CREDENTIALS = True

# XXX: Still used?
if not os.environ.get('IS_DEV_IMAGE') == 'yes':
    CELERY_ALWAYS_EAGER = True

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
ALLOWED_HOSTS = ['*']

LOGIN_URL = 'http://landing.behavery.local:8001/login'
RUNNER_URL = 'http://runner.behavery.local:8080'
