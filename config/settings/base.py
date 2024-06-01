import sys
import environ

ROOT_DIR = environ.Path(__file__) - 3  # (ery_backend/config/settings/base.py - 3 = ery_backend/)
APPS_DIR = ROOT_DIR.path('ery_backend')

TESTING = len(sys.argv) > 1 and sys.argv[1] == 'test'

env = environ.Env()

ERY_BABEL_HOSTPORT = env("ERY_BABEL_HOSTPORT", default="localhost:30000")
ERY_ENGINE_HOSTPORT = env("ERY_ENGINE_HOSTPORT", default="localhost:30001")
REDIS_LOCATION = '{0}/{1}'.format(env('REDIS_URL', default='redis://127.0.0.1:6379'), 0)

ASGI_APPLICATION = "config.routing.application"


# XXX: Address in issue #503
# CHANNELS_WS_PROTOCOLS = ["graphql-ws", ]
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [(REDIS_LOCATION[8:-7], 6379)],
        },
    },
}


# .env file, should load only in development environment
READ_DOT_ENV_FILE = env.bool('DJANGO_READ_DOT_ENV_FILE', default=False)

if READ_DOT_ENV_FILE:
    # Operating System Environment variables have precedence over variables defined in the .env file,
    # that is to say variables from the .env files will only be used if not defined
    # as environment variables.
    env_file = str(ROOT_DIR.path('.env'))
    print('Loading : {}'.format(env_file))
    env.read_env(env_file)
    print('The .env file has been loaded. See base.py for more information')

# APP CONFIGURATION
# ------------------------------------------------------------------------------
DJANGO_APPS = [
    # Default Django apps:
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Admin
    'django.contrib.admin',
]
THIRD_PARTY_APPS = [
    'graphene_django',
    'reversion',
    'rest_framework',
    'rest_framework_xml',
    'countries_plus',
    'languages_plus',
    'channels',
# XXX: social_django should be moved into web_runner's settings only, but needed here for now to make sure that migrations are
# made for the package.
    'social_django', 
]

LOCAL_APPS = [
    'ery_backend.actions.apps.ActionsConfig',
    'ery_backend.assets.apps.AssetsConfig',
    'ery_backend.base.apps.BaseConfig',
    'ery_backend.comments.apps.CommentsConfig',
    'ery_backend.datasets.apps.DatasetsConfig',
    'ery_backend.commands.apps.CommandsConfig',
    'ery_backend.conditions.apps.ConditionsConfig',
    'ery_backend.folders.apps.FoldersConfig',
    'ery_backend.forms.apps.FormsConfig',
    'ery_backend.frontends.apps.FrontendsConfig',
    'ery_backend.hands.apps.HandsConfig',
    'ery_backend.inputs.apps.InputsConfig',
    'ery_backend.keywords.apps.KeywordsConfig',
    'ery_backend.labs.apps.LabsConfig',
    'ery_backend.logs.apps.EryLogsConfig',
    'ery_backend.modules.apps.ModulesConfig',
    'ery_backend.news.apps.NewsConfig',
    'ery_backend.notifications.apps.NotificationsConfig',
    'ery_backend.procedures.apps.ProceduresConfig',
    'ery_backend.robots.apps.RobotsConfig',
    'ery_backend.roles.apps.RolesConfig',
    'ery_backend.stages.apps.StagesConfig',
    'ery_backend.stint_specifications.apps.StintSpecificationsConfig',
    'ery_backend.stints.apps.StintsConfig',
    'ery_backend.syncs.apps.SyncsConfig',
    'ery_backend.teams.apps.TeamsConfig',
    'ery_backend.templates.apps.EryTemplatesConfig',
    'ery_backend.themes.apps.ThemesConfig',
    'ery_backend.users.apps.UsersConfig',
    'ery_backend.validators.apps.ValidatorsConfig',
    'ery_backend.vendors.apps.VendorsConfig',
    'ery_backend.variables.apps.VariablesConfig',
    'ery_backend.wardens.apps.WardensConfig',
    'ery_backend.widgets.apps.WidgetsConfig',
]

# See: https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# MIDDLEWARE CONFIGURATION
# ------------------------------------------------------------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'graphql_jwt.middleware.JSONWebTokenMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# MIGRATIONS CONFIGURATION
# ------------------------------------------------------------------------------
MIGRATION_MODULES = {
    'sites': 'ery_backend.contrib.sites.migrations'
}

# DEBUG
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = env.bool('DJANGO_DEBUG', False)

# FIXTURE CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-FIXTURE_DIRS
FIXTURE_DIRS = (
    str(ROOT_DIR.path('fixtures')),
)

# EMAIL CONFIGURATION
# ------------------------------------------------------------------------------
EMAIL_BACKEND = env('DJANGO_EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')

# MANAGER CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#admins
ADMINS = [
    ("""Alexander Funcke""", 'funcke@zd.ee'),
]

# See: https://docs.djangoproject.com/en/dev/ref/settings/#managers
MANAGERS = ADMINS

# DATABASE CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DATABASE_NAME', default='ery'),
    },
}
if 'DATABASE_HOST' in env: DATABASES['default']['HOST'] = env('DATABASE_HOST')
if 'DATABASE_PORT' in env: DATABASES['default']['PORT'] = env('DATABASE_PORT')
if 'DATABASE_USER' in env: DATABASES['default']['USER'] = env('DATABASE_USER')
if 'DATABASE_PASSWORD' in env: DATABASES['default']['PASSWORD'] = env('DATABASE_PASSWORD')

TIME_ZONE = 'UTC'
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

USE_I18N = True
USE_L10N = True
USE_TZ = True

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.jinja2.Jinja2',
        'DIRS': [
            f"{ROOT_DIR.path('templates')}/react-spa",
        ],
        'OPTIONS': {
            'extensions': ['jinja2.ext.do']
        }
    },
    # Keep DjangoTemplate for admin interface
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [f"{ROOT_DIR.path('templates')}"],
        'OPTIONS': {
            'debug': DEBUG,
            'loaders': [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ],
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# See: http://django-crispy-forms.readthedocs.io/en/latest/install.html#template-packs
CRISPY_TEMPLATE_PACK = 'bootstrap4'

# STATIC FILE CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = str(ROOT_DIR('staticfiles'))

# See: https://docs.djangoproject.com/en/dev/ref/settings/#static-url
STATIC_URL = '/static/'

# See: https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#std:setting-STATICFILES_DIRS
STATICFILES_DIRS = [
    str(ROOT_DIR.path('static')),
]

# See: https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#staticfiles-finders
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

# MEDIA CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = str(APPS_DIR('media'))

# See: https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = '/media/'

# URL Configuration
# ------------------------------------------------------------------------------
ROOT_URLCONF = 'config.urls'

# See: https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
WSGI_APPLICATION = 'config.wsgi.application'

# PASSWORD STORAGE SETTINGS
# ------------------------------------------------------------------------------
# See https://docs.djangoproject.com/en/dev/topics/auth/passwords/#using-argon2-with-django
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
    'django.contrib.auth.hashers.BCryptPasswordHasher',
]

# PASSWORD VALIDATION
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-password-validators
# ------------------------------------------------------------------------------

AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# AUTHENTICATION CONFIGURATION
# ------------------------------------------------------------------------------
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'ery_backend.users.backends.JSONWebTokenBackend',
]

AUTH_USER_MODEL = 'users.User'

# Graphene
GRAPHENE = {
    'SCHEMA': 'ery_backend.schema.schema',
    'SCHEMA_OUTPUT': 'data/schema.json',
    'MIDDLEWARE': (
        'graphql_jwt.middleware.JSONWebTokenMiddleware',
        'graphene_django.debug.DjangoDebugMiddleware'
    )
}

REST_FRAMEWORK = {
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework_xml.parsers.XMLParser',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework_xml.renderers.XMLRenderer',
    ),
}

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_LOCATION,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Also use Redis for session handling
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

AUTH0_DOMAIN = "ery.auth0.com"

# JWT
GRAPHQL_JWT = {
    'JWT_ALGORITHM': "RS256",
    'JWT_AUTH_HEADER_PREFIX': "Bearer",
    'JWT_AUDIENCE': env("AUTH0_GRAPHQL_URL", default="http://localhost:8000/graphql/"),
    'JWT_ISSUER': "https://{}/".format(AUTH0_DOMAIN),
    'JWT_DECODE_HANDLER': 'ery_backend.users.utils.jwt_decode',
}

DEFAULT_LANGUAGE = 'en'
ALLOWED_HOSTS = ['127.0.0.1', 'localhost', 'behavery.local', 'stintery.com', 'stg.stintery.com']

# GCP
PROJECT_NAME = "eryservices-176219"
