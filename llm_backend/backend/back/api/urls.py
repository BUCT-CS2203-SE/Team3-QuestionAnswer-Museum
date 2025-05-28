from django.urls import path
from . import views

# API路由配置
urlpatterns = [
    # 设置用户名的接口，用于初始化用户会话并获取历史记录
    path('set_username/', views.set_username, name='set_username'),
    # 聊天接口，用于处理用户消息并返回AI回复
    path('chat/', views.chat, name='chat'),
] 