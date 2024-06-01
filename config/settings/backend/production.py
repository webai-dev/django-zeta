from ..web_production import *  # noqa

from google.cloud import logging

logging_client = logging.Client(project='ery_backend')
logging_client._use_grpc = False

DEBUG = True
LOGGING = {
    'version': 1,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'stackdriver': {
            'class': 'google.cloud.logging.handlers.CloudLoggingHandler',
            'client': logging_client,
        }
    },
    'loggers': {
        'django': {
            'handlers': ['stackdriver', 'console'],
            'level': 'INFO',
            'name': "ery_backend",
        },
        'django.request': {
            'handlers': ['stackdriver'],
            'level': 'INFO',
            'name': "ery_backend_request",
        }
    }
}

STATIC_URL = '//storage.googleapis.com/ery_backend_static/'

LOGIN_URL = 'https://about.behavery.com/login'
RUNNER_URL = 'https://stintery.com'

# Web socket security (see ery_backend.frontends.renderers)
USE_WSS = True
