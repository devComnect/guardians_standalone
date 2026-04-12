import os
from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost').split(',')

DJANGO_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'crispy_forms',
    'crispy_bootstrap5',
    'nested_admin',
    # 'debug_toolbar',    #pausado para tentar otimizar perfomance
    # 'django_auth_ldap',        # Ativar quando AD disponível
    # 'mozilla_django_oidc',     # Alternativa Azure AD/OIDC
]

LOCAL_APPS = [
    'apps.core',
    'apps.accounts',
    'apps.profiles',
    'apps.challenges',
    'apps.minigames',
    'apps.rankings',
    'apps.store',
    'apps.feedback',
    'apps.missions.apps.MissionsConfig',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', 
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    #'debug_toolbar.middleware.DebugToolbarMiddleware',   #pausado para perfomance
]

ROOT_URLCONF = 'comnect_guardians.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.profiles.context_processors.notifications',          
            ],
        },
    },
]

WSGI_APPLICATION = 'comnect_guardians.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME':     config('DB_NAME',     default='comnect_guardians'),
        'USER':     config('DB_USER',     default='cg_user'),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST':     config('DB_HOST',     default='127.0.0.1'),
        'PORT':     config('DB_PORT',     default='5432'),
    }
}

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    # 'django_auth_ldap.backend.LDAPBackend',  # Ativar quando AD disponível
]

LOGIN_URL          = '/accounts/login/'
LOGIN_REDIRECT_URL = '/home/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'pt-br'
TIME_ZONE     = 'America/Sao_Paulo'
USE_I18N      = True
USE_TZ        = True

STATIC_URL  = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL  = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

INTERNAL_IPS = ['127.0.0.1']

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SESSION_COOKIE_AGE = 28800
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.server': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

JAZZMIN_SETTINGS = {
    "site_title": "Portal Admin",
    "site_header": "Portal Admin",
    "site_brand": "⚡ Portal",
    "welcome_sign": "Bem-vindo ao painel de administração",
    "search_model": ["profiles.Player", "auth.User"],
    "topmenu_links": [
        {"name": "Portal", "url": "/", "new_window": True},
    ],
    "show_sidebar": True,
    "navigation_expanded": True,
    "icons": {
        "auth.User":                        "fas fa-users",
        "profiles.Player":                  "fas fa-user-circle",
        "profiles.EventoPontos":            "fas fa-gavel",
        "profiles.Achievement":             "fas fa-trophy",
        "profiles.PlayerAchievement":       "fas fa-medal",
        "profiles.BattlePassConfig":        "fas fa-scroll",
        "profiles.SystemLog":               "fas fa-history",
        "minigames.Quiz":                   "fas fa-question-circle",
        "minigames.QuizAttempt":            "fas fa-redo",
        "minigames.DecriptarAttempt":       "fas fa-redo",
        "minigames.CodigoAttempt":          "fas fa-redo",
        "minigames.PatrolAttempt":          "fas fa-redo",
        "minigames.PasswordAttempt":        "fas fa-redo",
        "core.AdminPost":                   "fas fa-bullhorn",
        "feedback.Feedback":                "fas fa-comment-alt",
        "rankings.Season":                  "fas fa-calendar-alt",
        "store.Item":                       "fas fa-store",
        "missions.MissionTemplate":         "fas fa-tasks",
    },
    "order_with_respect_to": [
        "profiles.Player",
        "profiles.EventoPontos",
        "profiles",
        "core",
        "minigames",
        "feedback",
        "rankings",
        "missions",
        "store",
        "auth",
    ],
    "custom_links": {
        "profiles": [
            {
                "name": "Tabela de Níveis",
                "url": "admin:profiles_player_level_progression",
                "icon": "fas fa-chart-line",
            }
        ]
    },
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": True,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-dark",
    "accent": "accent-info",
    "navbar": "navbar-dark",
    "no_navbar_border": True,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-info",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": True,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "darkly",
    "default_theme_mode": "dark",
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success",
    },
}