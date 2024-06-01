"""
Test settings
"""

from .base import * #noqa

DEBUG = env.bool('DJANGO_DEBUG', default=True)
SECRET_KEY = env('DJANGO_SECRET_KEY', default='uFucK,w+$]peX2gV#Gou`(*>z_dWKb=+B.Y]X:L3ZK9*$)aW5)')

DATABASES = {
    'default': env.db('DATABASE_URL', default='postgres:///test_ery'),
}
DATABASES['default']['ATOMIC_REQUESTS'] = True

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