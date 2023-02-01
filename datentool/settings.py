"""
Django settings for datentool project.

Generated by 'django-admin startproject' using Django 3.2.4.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.2/ref/settings/
"""

from pathlib import Path
import os
import sys
from datetime import timedelta
import json

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

DB_NAME = os.environ.get('DB_NAME', 'datentool')
DB_USER = os.environ.get('DB_USER', 'postgres')
DB_PASS = os.environ.get('DB_PASS', '')
DB_PORT = os.environ.get('DB_PORT', 5432)
DB_HOST = os.environ.get('DB_HOST', 'localhost')
SECRET_KEY = os.environ.get('SECRET_KEY')
ENCRYPT_KEY = os.environ.get('ENCRYPT_KEY')

TIME_ZONE = os.environ.get('TIME_ZONE', 'Europe/Berlin')

OSRM_ROUTING = {
    'CAR': {
        'alias': 'car',
        'host': os.environ.get('MODE_CAR_HOST', 'localhost'),
        'service_port': os.environ.get('MODE_CAR_SERVICE_PORT', 8001),
        'routing_port': os.environ.get('MODE_CAR_ROUTING_PORT', 5001),
    },
    'BIKE': {
        'alias': 'bicycle',
        'host': os.environ.get('MODE_BIKE_HOST', 'localhost'),
        'service_port': os.environ.get('MODE_BIKE_SERVICE_PORT', 8002),
        'routing_port': os.environ.get('MODE_BIKE_ROUTING_PORT', 5002),
    },
    'WALK': {
        'alias': 'foot',
        'host': os.environ.get('MODE_WALK_HOST', 'localhost'),
        'service_port': os.environ.get('MODE_WALK_SERVICE_PORT', 8003),
        'routing_port': os.environ.get('MODE_WALK_ROUTING_PORT', 5003),
    },
}

BASE_PBF = 'germany-latest.osm.pbf'
PBF_URL = f'http://download.geofabrik.de/europe/{BASE_PBF}'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

hosts = os.environ.get('ALLOWED_HOSTS')
if hosts:
    hosts = hosts.split(',')
    CSRF_TRUSTED_ORIGINS = [f'https://{h}' for h in hosts]
    ALLOWED_HOSTS = hosts

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',
    'datentool_backend',
    'daphne',
    'rest_framework',
    'rest_framework_simplejwt',
    'drf_spectacular',
    'django_cleanup.apps.CleanupConfig',
    'django_filters',
    'django_q'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.locale.LocaleMiddleware',
]

REST_FRAMEWORK = {
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend'
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': (
        'djangorestframework_camel_case.render.CamelCaseJSONRenderer',
        'djangorestframework_camel_case.render.CamelCaseBrowsableAPIRenderer',
    ),
    'DEFAULT_PARSER_CLASSES': (
        'djangorestframework_camel_case.parser.CamelCaseJSONParser',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}


SPECTACULAR_SETTINGS = {
    'TITLE': 'Datentool Project API',
    'DESCRIPTION': 'Bule Datentool',
    'VERSION': '1.0.0',
    'COMPONENT_SPLIT_REQUEST': True,
    # OTHER SETTINGS
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True
}

ROOT_URLCONF = 'datentool.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'datentool', 'templates'),
            #os.path.join(BASE_DIR, 'angular-frontend', 'src')
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'debug': True,
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'datentool.wsgi.application'
ASGI_APPLICATION = 'datentool.asgi.application'

REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = os.environ.get('REDIS_PORT', 6379)

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.pubsub.RedisPubSubChannelLayer',
        'CONFIG': {
            "hosts": [f'redis://{REDIS_HOST}:{REDIS_PORT}'],
        },
    },
}

# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': DB_NAME,
        'USER': DB_USER,
        'PASSWORD': DB_PASS,
        'HOST': DB_HOST,
        'PORT': DB_PORT,
        'OPTIONS': {
            'sslmode': 'prefer',
        },
    },
    'spatialite': {
        'ENGINE': 'django.contrib.gis.db.backends.spatialite',
        'NAME': BASE_DIR / 'db_spatial.sqlite3',
    },
    'sqlite': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    },
}
# GDAL configuration
if os.name == 'nt':
    lib_path = os.path.join(sys.exec_prefix, 'Library')
    if (os.path.exists(os.path.join(lib_path, 'share', 'gdal'))
            and os.path.exists(os.path.join(lib_path, 'share', 'proj')) ):
        os.environ['GDAL_DATA'] = os.path.join(lib_path, 'share', 'gdal')
        os.environ['PROJ_LIB'] = os.path.join(lib_path, 'share', 'proj')
    else:
        # preset for GDAL installation via OSGeo4W as recommended by Django, see
        # https://docs.djangoproject.com/en/3.2/ref/contrib/gis/install/#windows
        osgeo4w_directories = [r'C:\OSGeo4W64', r'C:\OSGeo4W']
        for OSGEO4W_ROOT in osgeo4w_directories:
            if os.path.exists(OSGEO4W_ROOT):
                break
        else:
            raise IOError(f'OSGeo4W not installed in {osgeo4w_directories}')
        os.environ['GDAL_DATA'] = os.path.join(OSGEO4W_ROOT, 'share', 'gdal')
        os.environ['PROJ_LIB'] = os.path.join(OSGEO4W_ROOT, 'share', 'proj')
        os.environ['PATH'] = ';'.join([os.environ['PATH'],
                                       os.path.join(OSGEO4W_ROOT, 'bin')])

elif sys.platform == 'linux':
    lib_path = os.path.join(sys.exec_prefix, 'lib')
    # Linux
    GDAL_LIBRARY_PATH = os.path.join(lib_path, 'libgdal.so')

    GEOS_LIBRARY_PATH = os.path.join(lib_path, 'libgeos_c.so')
    if not os.path.exists(GEOS_LIBRARY_PATH):
        GEOS_LIBRARY_PATH = os.path.join(lib_path, 'x86_64-linux-gnu',
                                         'libgeos_c.so')

    PROJ4_LIBRARY_PATH = os.path.join(sys.exec_prefix,
                                     'lib', 'libproj.so')
    if not os.path.exists(PROJ4_LIBRARY_PATH):
        PROJ4_LIBRARY_PATH = os.path.join(lib_path, 'x86_64-linux-gnu',
                                          'libproj.so')

elif sys.platform == 'darwin':
    # Max OS
    GDAL_LIBRARY_PATH = os.path.join(sys.exec_prefix,
                                     'lib', 'libgdal.dylib')
    GEOS_LIBRARY_PATH = os.path.join(sys.exec_prefix,
                                     'lib', 'libgeos_c.dylib')
    PROJ4_LIBRARY_PATH = os.path.join(sys.exec_prefix,
                                     'lib', 'libproj.dylib')

if sys.platform == 'linux':
    SPATIALITE_LIBRARY_PATH = '/usr/lib/x86_64-linux-gnu/mod_spatialite.so'
else:
    SPATIALITE_LIBRARY_PATH = 'mod_spatialite'

# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = 'de-de'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

FRONTEND_APP_DIR = os.path.join(BASE_DIR, 'angular-frontend')
FRONTEND_DIST = 'dist/angular-frontend'

STATICFILES_DIRS = [
    os.path.join(FRONTEND_APP_DIR),
    os.path.join(BASE_DIR, 'datentool', 'static'),
]

#FIXTURE_DIRS = [
    #os.path.join(BASE_DIR, 'datentool_backend', 'fixtures'),
#]

PUBLIC_DIR = os.path.join(BASE_DIR, 'public')

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(PUBLIC_DIR, 'static')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(PUBLIC_DIR, 'media')

DATA_ROOT = os.path.join(BASE_DIR, 'datentool_backend', 'data')

# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# maximum number of persisted log entries per room
MAX_N_LOGS = 2000

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
        },
        'web_socket': {
            'level': 'DEBUG',
            'class': 'datentool.loggers.WebSocketHandler',
        },
        'persist': {
            'level': 'DEBUG',
            'class': 'datentool_backend.logging.loggers.PersistLogHandler',
        },
    },
    'loggers': {
        'areas': {
            'handlers': ['web_socket', 'console', 'persist'],
            'level': 'INFO',
            'propagate': False,
        },
        'population': {
            'handlers': ['web_socket', 'console', 'persist'],
            'level': 'INFO',
            'propagate': False,
        },
        'infrastructure': {
            'handlers': ['web_socket', 'console', 'persist'],
            'level': 'INFO',
            'propagate': False,
        },
        'routing': {
            'handlers': ['web_socket', 'console', 'persist'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

Q_CLUSTER = {
    'name': 'datentool',
    'workers': 2,
    'recycle': 500,
    'timeout': 848000,
    'retry': 848001,
    'compress': True,
    'save_limit': 250,
    'queue_limit': 500,
    'cpu_affinity': 1,
    'ack_failures': True,
    'max_attempts': 1,
    'attempt_count': 1,
    'label': 'Django Q',
    'redis': {
        'host': REDIS_HOST,
        'port': REDIS_PORT,
        'db': 0, }
}

USE_DJANGO_Q = True

def load_stats_json():
    fn = os.path.join(FRONTEND_APP_DIR,
                      *FRONTEND_DIST.split('/'),
                      'stats.json')
    if not os.path.exists(fn):
        return
    with open(fn, 'r') as file:
        chunks = json.loads(file.read())['assetsByChunkName'] or {}
        chunk_paths = {k: (f'{FRONTEND_DIST}/{fn[0]}')
                       for k, fn in chunks.items()}
        return chunk_paths

ANGULAR_RESOURCES = load_stats_json() or {}

LOCALE = 'de_DE.utf8'

STEPSIZE = 100000

ROUTING_ALGORITHM = 'ch'
