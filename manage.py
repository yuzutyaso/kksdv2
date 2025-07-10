#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    # ここでDJANGO_SETTINGS_MODULE環境変数を設定します。
    # 'config.settings' は、あなたのプロジェクトのsettings.pyファイルへのパスを指します。
    # もしあなたのプロジェクト名が 'myproject' のようなものであれば、
    # 'myproject.settings' となります。
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
