"""
Test settings
"""

from .base import * #noqa

DEPLOYMENT = "local"

SECRET_KEY = env('DJANGO_SECRET_KEY', default='uFucK,w+$]peX2gV#Gou`(*>z_dWKb=+B.Y]X:L3ZK9*$)aW5)')


# DEBUG
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = env.bool('DJANGO_DEBUG', True)


USE_ERROR_REPORTING = False
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
