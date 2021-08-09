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

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = [
    'datentool.ggr-planung.de'
]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'datentool_backend',
    'rest_framework',
    'rest_framework_simplejwt',
    'django_cleanup.apps.CleanupConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
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
        'djangorestframework_camel_case.parser.CamelCaseFormParser',
        'djangorestframework_camel_case.parser.CamelCaseMultiPartParser',
        'djangorestframework_camel_case.parser.CamelCaseJSONParser',
    ),
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'ROTATE_REFRESH_TOKENS':  True,
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
            'sslmode': 'require',
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
    # preset for GDAL installation via OSGeo4W as recommended by Django, see
    # https://docs.djangoproject.com/en/3.2/ref/contrib/gis/install/#windows
    OSGEO4W_ROOT = 'C:\OSGeo4W64'
    os.environ['GDAL_DATA'] = os.path.join(OSGEO4W_ROOT, 'share','gdal')
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
    SPATIALITE_LIBRARY_PATH = 'mod_spatialite.so'
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

# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

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