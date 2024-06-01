from ..base import *  # noqa

ERY_BABEL_HOSTPORT = "localhost:30000"
ERY_ENGINE_HOSTPORT = "localhost:30001"

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
        },
    },
}

DEBUG = env.bool('DJANGO_DEBUG', default=True)

SECRET_KEY = env('DJANGO_SECRET_KEY', default='uFucK,w+$]peX2gV#Gou`(*>z_dWKb=+B.Y]X:L3ZK9*$)aW5)')

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
