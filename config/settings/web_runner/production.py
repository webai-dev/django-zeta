from ..web_production import *  # noqa

AUTHENTICATION_BACKENDS = ['ery_backend.frontends.web_views.Auth0'] + AUTHENTICATION_BACKENDS

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'INFO',
        }
    }
}

STATIC_URL = '//storage.googleapis.com/ery_web_runner_static/'

ROOT_URLCONF = 'config.web_runner_urls'
RUNNER_URL = 'https://stintery.com'

LOGIN_URL = '/login/auth0'
LOGIN_REDIRECT_URL = '/'

SOCIAL_AUTH_AUTH0_DOMAIN = 'ery.auth0.com'
SOCIAL_AUTH_AUTH0_KEY = env('AUTH0_CLIENT_ID')
SOCIAL_AUTH_AUTH0_SECRET = env('AUTH0_SECRET')
SOCIAL_AUTH_TRAILING_SLASH = False  # Remove trailing slash from routes
SOCIAL_AUTH_AUTH0_SCOPE = ['openid', 'profile', 'email']
SOCIAL_AUTH_POSTGRES_JSONFIELD = True

