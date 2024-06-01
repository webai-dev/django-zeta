from ..production import *  # noqa

from google.cloud import logging

logging_client = logging.Client(project='ery_sms_runner')
logging_client._use_grpc = False


LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': env('DJANGO_LOG_LEVEL', default='DEBUG'),
        },
    },
}

