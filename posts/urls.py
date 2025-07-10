# posts/urls.py
from django.urls import path
from . import views

app_name = 'posts'

urlpatterns = [
    path('', views.post_list, name='index'),
    path('create/', views.create_post, name='create_post'),
    # 他のビュー（詳細、編集、削除など）が必要であれば追加
]
