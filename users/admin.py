# users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, BannedIP

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('permission_level', 'id_color', 'display_hash')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('permission_level', 'id_color', 'display_hash')}),
    )
    list_display = ('username', 'email', 'permission_level', 'id_color', 'display_hash', 'is_staff')
    list_filter = ('permission_level', 'is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('username', 'email')
    ordering = ('username',)

@admin.register(BannedIP)
class BannedIPAdmin(admin.ModelAdmin):
    list_display = ('ip_address', 'is_approved_by_admin', 'banned_at', 'reason')
    list_filter = ('is_approved_by_admin', 'banned_at')
    search_fields = ('ip_address', 'reason')
    actions = ['approve_ban_ip', 'reject_ban_ip']

    def approve_ban_ip(self, request, queryset):
        if not request.user.has_permission('admin_op'):
            self.message_user(request, "BAN承認には運営権限が必要です。", level='error')
            return
        updated = queryset.update(is_approved_by_admin=True)
        self.message_user(request, f"{updated}件のIPアドレスのBANを承認しました。(投稿可能になりました)")
    approve_ban_ip.short_description = "選択したIPのBANを承認する (投稿可能にする)"

    def reject_ban_ip(self, request, queryset):
        if not request.user.has_permission('admin_op'):
            self.message_user(request, "BAN解除には運営権限が必要です。", level='error')
            return
        updated = queryset.update(is_approved_by_admin=False)
        self.message_user(request, f"{updated}件のIPアドレスのBANを解除する (投稿不可にする)")
    reject_ban_ip.short_description = "選択したIPのBANを解除する (投稿不可にする)"
