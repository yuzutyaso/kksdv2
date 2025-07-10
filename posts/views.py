# posts/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
import hashlib
from django.contrib import messages
from django.db import transaction # トランザクション処理のため

from .models import Post
from .forms import PostForm
from users.models import BannedIP # BannedIPモデルを使用

# IPアドレスを確実に取得するヘルパー関数
def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')

    if ip and ':' in ip and '.' in ip:
        try:
            ip = ip.rsplit(':', 1)[-1]
        except ValueError:
            pass
    return ip if ip else 'Unknown'


def post_list(request):
    posts = Post.objects.all()
    # ユーザー認証済みの場合、投稿フォームを渡す
    form = PostForm() if request.user.is_authenticated else None
    return render(request, 'posts/index.html', {'posts': posts, 'form': form})

@login_required # ログインが必須
def create_post(request):
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            title = form.cleaned_data['title']
            content = form.cleaned_data['content']
            author = request.user

            current_ip = get_client_ip(request)

            # --- BANされているIPかチェック ---
            if current_ip and current_ip != 'Unknown':
                try:
                    banned_ip_entry = BannedIP.objects.get(ip_address=current_ip)
                    if not banned_ip_entry.is_approved_by_admin:
                        messages.error(request, "あなたのIPアドレスからの投稿は制限されています。運営の承認が必要です。")
                        return redirect('posts:index')
                except BannedIP.DoesNotExist:
                    pass

            # --- 重複投稿チェック ---
            # 投稿内容のハッシュを生成（長文でも固定長で比較するため）
            # content_hash = hashlib.sha256(content.encode()).hexdigest() # 必要であればモデルにフィールド追加
            time_threshold = timezone.now() - timedelta(seconds=30) # 30秒以内に同じ内容の投稿を禁止
            
            recent_duplicate_posts = Post.objects.filter(
                author=author,
                content=content, # content_hash を使わない場合はcontentで直接比較
                created_at__gte=time_threshold
            ).exists()

            if recent_duplicate_posts:
                messages.error(request, "同じ内容の投稿は短時間に連続して行えません。")
                return redirect('posts:index') # またはフォームを再表示してエラーを表示

            # --- 投稿の保存 ---
            try:
                with transaction.atomic(): # トランザクションを確保
                    new_post = form.save(commit=False)
                    new_post.author = author
                    new_post.ip_address = current_ip # 取得したIPアドレスを保存
                    new_post.save()
                    messages.success(request, "投稿が作成されました。")
                    return redirect('posts:index')
            except Exception as e:
                messages.error(request, f"投稿の保存中にエラーが発生しました: {e}")
                return redirect('posts:index') # エラー時は一覧に戻す
        else:
            # フォームバリデーションエラー
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
            return redirect('posts:index') # エラー時は一覧に戻す

    # GETリクエストの場合は /posts/ にリダイレクト (直接 /posts/create にアクセスした場合)
    return redirect('posts:index')
