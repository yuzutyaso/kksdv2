# config/urls.py
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView # favicon対応

urlpatterns = [
    path('admin/', admin.site.urls),
    path('posts/', include('posts.urls')), # postsアプリのURL
    path('users/', include('users.urls')), # usersアプリのURL
    path('commands/', include('commands.urls')), # commandsアプリのURL
    path('', RedirectView.as_view(url='/posts/', permanent=True)), # トップページを/posts/にリダイレクト
]
