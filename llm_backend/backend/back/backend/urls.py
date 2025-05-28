"""
Django项目的主路由配置文件
"""
from django.contrib import admin
from django.urls import path, include

# URL路由配置
urlpatterns = [
    # Django管理后台路由
    path('admin/', admin.site.urls),
    # API路由，所有API都以/api/开头
    path('api/', include('api.urls')),
]
