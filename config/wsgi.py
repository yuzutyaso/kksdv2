# config/wsgi.py

import os

from django.core.wsgi import get_wsgi_application

# ここでDJANGO_SETTINGS_MODULE環境変数を設定します。
# 'config.settings' は、あなたのプロジェクトのsettings.pyファイルへのパスを指します。
# もしあなたのプロジェクト名が 'myproject' のようなものであれば、
# 'myproject.settings' となります。今回は 'config' としています。
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Django WSGIアプリケーションを取得します。
# Gunicornはこの 'application' オブジェクトを呼び出してリクエストを処理します。
application = get_wsgi_application()
