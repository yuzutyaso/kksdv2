# delete_all_posts.py
import os
import django
from django.conf import settings
from django.db import connection

# Django環境をセットアップ
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from posts.models import Post

if __name__ == '__main__':
    try:
        # 全ての投稿を削除
        num_deleted, _ = Post.objects.all().delete()
        print(f"{num_deleted}件の投稿を削除しました。")

        # PostgreSQLのシーケンスをリセットして投稿番号をリセット
        # 注意: これはテーブルのデータを完全に削除し、IDシーケンスをリセットします。
        # 本番環境での使用は慎重に。
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE posts_post RESTART IDENTITY;")
        print("投稿番号をリセットしました。")

    except Exception as e:
        print(f"投稿の削除中にエラーが発生しました: {e}")
