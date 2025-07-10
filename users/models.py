# users/models.py
import os
import hashlib
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

class CustomUser(AbstractUser):
    PERMISSION_CHOICES = [
        ('blue_id', '青ID'),
        ('speaker', 'スピーカー'),
        ('manager', 'マネージャー'),
        ('moderator', 'モデレーター'),
        ('summit', 'サミット'),
        ('admin_op', '運営'), # 'admin' はDjangoの予約語と被るので別の名前に
    ]
    permission_level = models.CharField(
        max_length=20,
        choices=PERMISSION_CHOICES,
        default='blue_id',
        verbose_name='権限レベル'
    )
    id_color = models.CharField(
        max_length=20,
        default='blue',
        verbose_name='ID表示色'
    )
    display_hash = models.CharField(max_length=7, blank=True, null=True, unique=True, verbose_name='表示ハッシュ')

    def __str__(self):
        return self.username

    # 権限チェック用のヘルパーメソッド
    def has_permission(self, required_level):
        level_map = {
            'blue_id': 0,
            'speaker': 1,
            'manager': 2,
            'moderator': 3,
            'summit': 4,
            'admin_op': 5,
        }
        user_level = level_map.get(self.permission_level, 0)
        req_level = level_map.get(required_level, 0)
        return user_level >= req_level

    # ユーザーが保存される際に、権限レベルに応じてid_colorを設定
    def save(self, *args, **kwargs):
        color_map = {
            'blue_id': 'blue',
            'speaker': 'darkorange',
            'manager': 'red',
            'moderator': 'purple',
            'summit': 'darkcyan',
            'admin_op': 'red',
        }
        self.id_color = color_map.get(self.permission_level, 'blue')
        super().save(*args, **kwargs)

# ユーザーが保存された後にdisplay_hashを生成するシグナル
@receiver(post_save, sender=CustomUser)
def create_user_display_hash(sender, instance, created, **kwargs):
    if created and not instance.display_hash:
        # ユーザーのIDとタイムスタンプなどを組み合わせたユニークな文字列からハッシュを生成
        # パスワードは絶対に使わないこと！
        unique_string = f"{instance.id}-{instance.username}-{instance.date_joined.timestamp()}-{os.urandom(16).hex()}"
        instance.display_hash = hashlib.sha256(unique_string.encode()).hexdigest()[:7]
        instance.save(update_fields=['display_hash'])


class BannedIP(models.Model):
    ip_address = models.GenericIPAddressField(
        unique=True,
        verbose_name='BAN対象IPアドレス',
        protocol='IPv4'
    )
    is_approved_by_admin = models.BooleanField(
        default=False,
        verbose_name='運営承認済み (解除可否)' # FalseならBAN状態、Trueなら承認済みで解除可
    )
    banned_at = models.DateTimeField(auto_now_add=True, verbose_name='BAN日時')
    reason = models.TextField(blank=True, verbose_name='BAN理由')

    def __str__(self):
        status = "承認済み (投稿可能)" if self.is_approved_by_admin else "BAN中 (投稿不可)"
        return f"{self.ip_address} ({status})"

    class Meta:
        verbose_name = 'BANされたIPアドレス'
        verbose_name_plural = 'BANされたIPアドレス'
