# commands/views.py
import re
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseBadRequest

from users.models import CustomUser, BannedIP # CustomUserとBannedIPをインポート
from posts.models import Post
from django.db import transaction

# コマンドのパーミッションマップ
# 実際の権限レベルと比較する際の基準として使用
COMMAND_PERMISSIONS = {
    'del': 'manager',
    'destroy': 'moderator',
    'clear': 'moderator',
    'NG': 'manager',
    'OK': 'manager',
    'prevent': 'summit',
    'permit': 'moderator',
    'restrict': 'moderator',
    'stop': 'summit',
    'prohibit': 'admin_op',
    'release': 'moderator',
    'speaker': 'manager', # 例: /speaker ID -> ユーザーの権限をspeakerに昇格
    'disspeaker': 'manager',
    'manager': 'moderator', # 例: /manager ID -> ユーザーの権限をmanagerに昇格 (マネージャー自身はモデレーター以上から付与可能)
    'dismanager': 'summit', # マネージャーを降格できるのはサミット以上
    'moderator': 'summit',
    'dismoderator': 'summit',
    'summit': 'admin_op',
    'dissummit': 'admin_op',
    'admin_op': None, # 運営の権限付与は管理者サイトからのみ、または特別な設定
    'disadmin_op': 'admin_op',
    'disself': 'blue_id', # 誰でも自分の権限を青IDにできる
    'kill': 'summit',
    'ban': 'summit',
    'revive': 'summit',
    'reduce': 'admin_op',
    'topic': 'manager',
    'add': 'moderator',
    'color': 'moderator',
    'instances': 'manager',
    'max': 'admin_op',
    'range': 'admin_op',
}

@login_required # コマンドはログインユーザーのみ実行可能
def process_command(request):
    if request.method == 'POST':
        command_text = request.POST.get('command_text', '').strip()
        if not command_text.startswith('/'):
            messages.error(request, "コマンドは'/'で始まる必要があります。")
            return redirect('posts:index')

        # コマンドと引数を解析
        parts = command_text[1:].split(' ', 1) # /を外し、最初のスペースで分割
        command_name = parts[0].lower()
        args_str = parts[1] if len(parts) > 1 else ''
        args = args_str.split(' ') if args_str else [] # 引数をスペースで分割

        required_permission = COMMAND_PERMISSIONS.get(command_name)

        if required_permission is None:
            # 運営の昇格/降格コマンドなど、ウェブUIで直接実行すべきでないもの
            if command_name in ['admin_op', 'disadmin_op']:
                messages.error(request, f"コマンド '{command_name}' はウェブUIからは実行できません。管理者サイトを使用してください。")
            else:
                messages.error(request, f"不明なコマンドです: {command_name}")
            return redirect('posts:index')

        # 権限チェック
        if not request.user.has_permission(required_permission):
            messages.error(request, f"コマンド '{command_name}' の実行には {required_permission} 以上の権限が必要です。")
            return redirect('posts:index')

        # --- 各コマンドの処理 ---
        try:
            with transaction.atomic(): # コマンド処理をトランザクションで囲む
                if command_name == 'del':
                    if not args:
                        messages.error(request, "/del には投稿番号が必要です。")
                    else:
                        deleted_count = 0
                        for post_id_str in args:
                            try:
                                post_id = int(post_id_str)
                                post_to_delete = get_object_or_404(Post, id=post_id)
                                post_to_delete.delete()
                                deleted_count += 1
                            except ValueError:
                                messages.warning(request, f"無効な投稿番号: {post_id_str} はスキップされました。")
                            except Exception: # Post.DoesNotExist を含む
                                messages.warning(request, f"投稿番号 {post_id_str} は見つかりませんでした。")
                        if deleted_count > 0:
                            messages.success(request, f"{deleted_count}件の投稿を削除しました。")
                        else:
                            messages.info(request, "削除対象の投稿は見つかりませんでした。")

                elif command_name == 'destroy':
                    if not args:
                        messages.error(request, "/destroy には条件となる文字または 'color' 指定が必要です。")
                        return redirect('posts:index')

                    condition = args[0]
                    deleted_count = 0
                    if condition.lower() == 'color':
                        if len(args) < 2:
                            messages.error(request, "/destroy color には色指定が必要です。")
                            return redirect('posts:index')
                        target_color = args[1].lower()
                        # 色と権限レベルのマッピングを逆引き
                        target_permission_level = None
                        for level, color in request.user.color_map.items(): # CustomUserモデルにcolor_mapを持たせるか、ここに定義
                             if color == target_color:
                                 target_permission_level = level
                                 break
                        if target_permission_level:
                            # 該当権限のユーザーの投稿を一括削除
                            posts_to_delete = Post.objects.filter(author__permission_level=target_permission_level)
                            deleted_count, _ = posts_to_delete.delete()
                            messages.success(request, f"{target_color} ID ({target_permission_level}) の投稿を {deleted_count} 件削除しました。")
                        else:
                            messages.error(request, f"不明な色指定: {target_color}")

                    else: # 特定の文字やIDを含む投稿を削除
                        posts_to_delete = Post.objects.filter(Q(title__icontains=condition) | Q(content__icontains=condition) | Q(id__icontains=condition))
                        deleted_count, _ = posts_to_delete.delete()
                        messages.success(request, f"'{condition}' を含む投稿を {deleted_count} 件削除しました。")

                elif command_name == 'clear':
                    deleted_count, _ = Post.objects.all().delete()
                    # 投稿番号をリセット (PostgreSQLの場合)
                    with transaction.atomic():
                        from django.db import connection
                        with connection.cursor() as cursor:
                            cursor.execute("TRUNCATE TABLE posts_post RESTART IDENTITY;")
                    messages.success(request, f"全ての投稿 ({deleted_count}件) を削除し、投稿番号をリセットしました。")

                elif command_name in ['NG', 'OK']:
                    if not args:
                        messages.error(request, f"/{command_name} には禁止/許可する言葉が必要です。")
                        return redirect('posts:index')
                    # NGWord モデルを別途作成し、ここで追加/削除ロジックを実装
                    # 例: NGWord.objects.create(word=args_str) / NGWord.objects.filter(word=args_str).delete()
                    messages.info(request, f"NGWordコマンド '{command_name}' は現在実装中です。")

                elif command_name in ['prevent', 'permit', 'restrict', 'stop', 'prohibit', 'release']:
                    if command_name == 'prevent':
                        # 青IDの投稿を解除されるまで禁止
                        messages.info(request, "青IDの投稿を禁止しました。(実装が必要です)")
                    elif command_name == 'permit':
                        messages.info(request, "/prevent を解除しました。(実装が必要です)")
                    # 他の規制コマンドも同様にユーザーのステータスを更新するロジックを実装
                    # CustomUser モデルに is_prevented, restricted_until などのフィールドを追加し、
                    # それを更新する。投稿時にこれらのフィールドをチェックする。
                    messages.info(request, f"規制コマンド '{command_name}' は現在実装中です。")

                elif command_name in ['speaker', 'manager', 'moderator', 'summit', 'admin_op']:
                    if not args:
                        messages.error(request, f"/{command_name} にはユーザーIDが必要です。")
                        return redirect('posts:index')
                    target_username = args[0]
                    try:
                        target_user = CustomUser.objects.get(username=target_username)
                        target_user.permission_level = command_name # 例: 'speaker'
                        target_user.save()
                        messages.success(request, f"{target_username} の権限を {command_name} に昇格しました。")
                    except CustomUser.DoesNotExist:
                        messages.error(request, f"ユーザー '{target_username}' が見つかりませんでした。")

                elif command_name.startswith('dis'): # 降格コマンド
                    if not args:
                        messages.error(request, f"/{command_name} にはユーザーIDが必要です。")
                        return redirect('posts:index')
                    target_username = args[0]
                    target_level = command_name[3:] # 'dis' を除いた部分 (例: 'speaker')
                    if target_level not in CustomUser.PERMISSION_CHOICES: # 権限レベルの有効性チェック
                         messages.error(request, f"不正な権限降格指定: {target_level}")
                         return redirect('posts:index')
                    try:
                        target_user = CustomUser.objects.get(username=target_username)
                        # 降格できる権限のロジックをここに追加
                        # 例: モデレーターはマネージャーをスピーカーに降格できるが、サミットにはできないなど
                        # ここではシンプルに指定レベルより一つ低いレベルに降格する例 (要調整)
                        # CustomUser.PERMISSION_CHOICES の順序を利用
                        current_level_idx = [level for level, _ in CustomUser.PERMISSION_CHOICES].index(target_user.permission_level)
                        target_level_idx = [level for level, _ in CustomUser.PERMISSION_CHOICES].index(target_level)

                        if current_level_idx > target_level_idx: # 現在のレベルが降格対象より高ければ
                            if target_level == 'speaker': # スピーカーは青IDに降格
                                target_user.permission_level = 'blue_id'
                            else: # それ以外の降格は、単純に指定レベルに降格
                                target_user.permission_level = target_level # スピーカー, マネージャーなど
                            target_user.save()
                            messages.success(request, f"{target_username} の権限を {target_level} に降格しました。")
                        else:
                            messages.error(request, f"{target_username} の権限を {target_level} に降格できません。")

                    except CustomUser.DoesNotExist:
                        messages.error(request, f"ユーザー '{target_username}' が見つかりませんでした。")
                    except ValueError:
                        messages.error(request, "降格処理に失敗しました。")


                elif command_name == 'disself':
                    request.user.permission_level = 'blue_id'
                    request.user.save()
                    messages.success(request, "あなたの権限を青IDに降格しました。")
                    return redirect('users:logout') # 権限降格後、再ログインを促す

                elif command_name == 'kill':
                    if not args:
                        messages.error(request, "/kill にはユーザーIDが必要です。")
                        return redirect('posts:index')
                    target_username = args[0]
                    try:
                        target_user = CustomUser.objects.get(username=target_username)
                        target_user.is_active = False # アカウントを非アクティブにする
                        target_user.save()
                        messages.success(request, f"ユーザー '{target_username}' を使用不可能にしました。")
                    except CustomUser.DoesNotExist:
                        messages.error(request, f"ユーザー '{target_username}' が見つかりませんでした。")

                elif command_name == 'ban':
                    if not args:
                        messages.error(request, "/ban にはIPアドレスまたは投稿番号が必要です。")
                        return redirect('posts:index')
                    target_identifier = args[0]
                    try:
                        # IPアドレスとしてBANを試みる
                        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", target_identifier): # IPv4の簡単な正規表現
                            BannedIP.objects.get_or_create(ip_address=target_identifier, defaults={'is_approved_by_admin': False, 'reason': f"コマンドによるBAN by {request.user.username}"})
                            messages.success(request, f"IPアドレス '{target_identifier}' をBANしました。")
                        else:
                            # 投稿番号として処理
                            post_id = int(target_identifier)
                            post = get_object_or_404(Post, id=post_id)
                            if post.ip_address:
                                BannedIP.objects.get_or_create(ip_address=post.ip_address, defaults={'is_approved_by_admin': False, 'reason': f"投稿番号 {post_id} からのBAN by {request.user.username}"})
                                messages.success(request, f"投稿番号 {post_id} のIPアドレス '{post.ip_address}' をBANしました。")
                            else:
                                messages.error(request, f"投稿番号 {post_id} にIPアドレス情報がありません。")
                    except ValueError:
                        messages.error(request, "無効なIPアドレスまたは投稿番号です。")
                    except Exception as e:
                        messages.error(request, f"BAN処理中にエラーが発生しました: {e}")

                elif command_name == 'revive':
                    # killされたユーザーをアクティブにする
                    CustomUser.objects.filter(is_active=False).update(is_active=True)
                    # BANされたIPの is_approved_by_admin を全てTrueにするか、エントリを削除するか
                    BannedIP.objects.update(is_approved_by_admin=True) # 全て承認済みに変更（投稿可能に）
                    messages.success(request, "/kill および /ban の効果を全て解除しました。")

                elif command_name == 'reduce':
                    # 権限全体の2%削除 (複雑なロジックのため、ここではダミーメッセージ)
                    messages.info(request, "/reduce コマンドは現在実装中です。(複雑なロジックが必要)")

                elif command_name == 'topic':
                    if not args_str:
                        messages.error(request, "/topic には話題の内容が必要です。")
                        return redirect('posts:index')
                    # topicをどこかに保存し、表示するロジックが必要
                    messages.success(request, f"トピックを '{args_str}' に変更しました。(実装が必要です)")

                elif command_name == 'add':
                    if len(args) < 2:
                        messages.error(request, "/add にはIDと後ろにつけたい文字が必要です。")
                        return redirect('posts:index')
                    target_username = args[0]
                    suffix = args_str.split(' ', 1)[1] # ID以降の全てを文字とする
                    try:
                        target_user = CustomUser.objects.get(username=target_username)
                        # CustomUserモデルに 'suffix' フィールドなどを追加し、ここに保存
                        # 例: target_user.display_suffix = suffix; target_user.save()
                        messages.success(request, f"ユーザー '{target_username}' に '{suffix}' を追加しました。(実装が必要です)")
                    except CustomUser.DoesNotExist:
                        messages.error(request, f"ユーザー '{target_username}' が見つかりませんでした。")

                elif command_name == 'color':
                    if len(args) < 2:
                        messages.error(request, "/color にはカラーコードとIDが必要です。")
                        return redirect('posts:index')
                    color_code = args[0]
                    target_username = args[1]
                    if not re.match(r'^#[0-9a-fA-F]{6}$', color_code):
                        messages.error(request, "無効なカラーコードです。#FFFFFF の形式で入力してください。")
                        return redirect('posts:index')
                    try:
                        target_user = CustomUser.objects.get(username=target_username)
                        target_user.id_color = color_code
                        target_user.save()
                        messages.success(request, f"ユーザー '{target_username}' の名前の色を {color_code} に変更しました。")
                    except CustomUser.DoesNotExist:
                        messages.error(request, f"ユーザー '{target_username}' が見つかりませんでした。")

                elif command_name in ['instances', 'max', 'range']:
                    messages.info(request, f"コマンド '{command_name}' は現在実装中です。(要件に応じて実装)")

                else:
                    messages.error(request, f"不明なコマンドです: {command_name}")

        except Exception as e:
            messages.error(request, f"コマンド実行中に予期せぬエラーが発生しました: {e}")

    return redirect('posts:index')
