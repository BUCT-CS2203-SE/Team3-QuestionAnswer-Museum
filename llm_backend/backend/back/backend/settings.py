"""
Django项目配置文件
"""
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 安全密钥
SECRET_KEY = 'django-insecure-luq$fl*ttq^v8l7s%&l$0y)$p6f_6jm#0e^rrk=y#^u8xzia)o'

# 调试模式
DEBUG = True

# 允许的主机
ALLOWED_HOSTS = []

# 已安装的应用列表
INSTALLED_APPS = [
    'django.contrib.admin',      # 管理后台
    'django.contrib.auth',       # 认证系统
    'django.contrib.contenttypes', # 内容类型
    'django.contrib.sessions',   # 会话框架
    'django.contrib.messages',   # 消息框架
    'django.contrib.staticfiles', # 静态文件
    'api',                      # 我们的API应用
    'corsheaders',              # 跨域支持
]

# 中间件配置
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # 跨域中间件
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',  # 会话中间件
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# 会话配置
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 86400  # 会话cookie过期时间（秒）
SESSION_COOKIE_NAME = 'sessionid'  # 会话cookie名称
SESSION_COOKIE_DOMAIN = None  # 会话cookie域名
SESSION_COOKIE_SECURE = False  # 是否使用HTTPS
SESSION_COOKIE_HTTPONLY = True  # 是否只允许HTTP访问
SESSION_SAVE_EVERY_REQUEST = True  # 每次请求都保存会话
SESSION_COOKIE_SAMESITE = 'Lax'  # 防止CSRF攻击

# 根URL配置
ROOT_URLCONF = 'backend.urls'

# 模板配置
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# WSGI应用配置
WSGI_APPLICATION = 'backend.wsgi.application'

# 数据库配置
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# 密码验证配置
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

# 国际化配置
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# 静态文件配置
STATIC_URL = 'static/'

# 默认主键字段类型
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# 跨域配置
CORS_ALLOW_ALL_ORIGINS = True  # 允许所有来源的跨域请求
CORS_ALLOW_CREDENTIALS = True  # 允许携带认证信息
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # 前端开发服务器
    "http://127.0.0.1:3000",
  
]
CORS_ALLOWED_METHODS = [
    'GET',
    'POST',
    'PUT',
    'PATCH',
    'DELETE',
    'OPTIONS'
]
CORS_ALLOWED_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'cookie',  # 允许cookie
]
