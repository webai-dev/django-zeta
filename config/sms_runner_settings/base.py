"""
Django settings for ery_backend project.

For more information on this file, see
https://docs.djangoproject.com/en/dev/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/dev/ref/settings/
"""
import environ

ROOT_DIR = environ.Path(__file__) - 3  # (ery_backend/config/settings/base.py - 3 = ery_backend/)
APPS_DIR = ROOT_DIR.path('ery_backend')

# Load operating system environment variables and then prepare to use them
env = environ.Env()

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

DEFAULT_LANGUAGE = 'en'

# APP CONFIGURATION
# ------------------------------------------------------------------------------
DJANGO_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sites',
]
THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_xml',
    'countries_plus',
    'languages_plus',
    'channels',
]

# Apps specific for this project go here.
LOCAL_APPS = [
    'ery_backend.actions.apps.ActionsConfig',
    'ery_backend.assets.apps.AssetsConfig',
    'ery_backend.base.apps.BaseConfig',
    'ery_backend.commands.apps.CommandsConfig',
    'ery_backend.conditions.apps.ConditionsConfig',
    'ery_backend.folders.apps.FoldersConfig',
    'ery_backend.frontends.apps.FrontendsConfig',
    'ery_backend.hands.apps.HandsConfig',
    'ery_backend.inputs.apps.InputsConfig',
    'ery_backend.labs.apps.LabsConfig',
    'ery_backend.logs.apps.EryLogsConfig',
    'ery_backend.modules.apps.ModulesConfig',
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
    'ery_backend.variables.apps.VariablesConfig',
    'ery_backend.wardens.apps.WardensConfig',
    'ery_backend.widgets.apps.WidgetsConfig',
]

# See: https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# DEBUG
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = env.bool('DJANGO_DEBUG', False)

# DATABASE CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {
    'default': env.db('DATABASE_URL', default='postgres:///ery'),
}
DATABASES['default']['ATOMIC_REQUESTS'] = True


# GENERAL CONFIGURATION
# ------------------------------------------------------------------------------
# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'UTC'

# See: https://docs.djangoproject.com/en/dev/ref/settings/#language-code
LANGUAGE_CODE = 'en-us'

# See: https://docs.djangoproject.com/en/dev/ref/settings/#site-id
SITE_ID = 1

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-i18n
USE_I18N = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-l10n
USE_L10N = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-tz
USE_TZ = True

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
]

AUTH_USER_MODEL = 'users.User'

# SLUGLIFIER
AUTOSLUG_SLUGIFY_FUNCTION = 'slugify.slugify'

REST_FRAMEWORK = {
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework_xml.parsers.XMLParser',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework_xml.renderers.XMLRenderer',
    ),
}

# CACHING
# ------------------------------------------------------------------------------

REDIS_LOCATION = '{0}/{1}'.format(env('REDIS_URL', default='redis://127.0.0.1:6379'), 0)
# Heroku URL does not pass the DB number, so we parse it in
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_LOCATION,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}


# CHANNELS
ASGI_APPLICATION = "config.routing.application"

# GCP
PROJECT_NAME = "eryservices-176219"