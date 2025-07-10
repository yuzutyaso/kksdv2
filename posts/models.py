# posts/models.py
from django.db import models
from users.models import CustomUser # カスタムユーザーモデルをインポート

class Post(models.Model):
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='posts', verbose_name='投稿者')
    title = models.CharField(
        max_length=100,
        blank=True,  # フォームや管理画面で空を許可
        null=True,   # データベースでNULLを許可
        verbose_name='タイトル'
    )
    content = models.TextField(verbose_name='内容') # デフォルトで必須
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='投稿日時')
    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        verbose_name='IPアドレス',
        protocol='IPv4' # 必要に応じて 'both' に変更
    )

    def __str__(self):
        display_title = self.title if self.title else "(タイトルなし)"
        return f"No.{self.id}: {display_title} by {self.author.username}"

    class Meta:
        ordering = ['-created_at'] # 新しい投稿が上に来るように
