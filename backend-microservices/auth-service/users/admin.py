"""
Admin configuration for users app.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, OAuthAccount, PasswordReset


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'username', 'role', 'is_active', 'no_show_count', 'force_online_payment']
    list_filter = ['role', 'is_active', 'force_online_payment']
    search_fields = ['email', 'username', 'phone']
    ordering = ['-date_joined']
    
    # Disable admin logging to avoid UUID/INTEGER conflict in django_admin_log
    def log_addition(self, request, object, message):
        pass
    
    def log_change(self, request, object, message):
        pass
    
    def log_deletion(self, request, object, object_repr):
        pass
    
    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        ('Personal info', {'fields': ('phone', 'address', 'avatar')}),
        ('Permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser')}),
        ('Parking info', {'fields': ('no_show_count', 'force_online_payment')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2', 'role'),
        }),
    )


@admin.register(OAuthAccount)
class OAuthAccountAdmin(admin.ModelAdmin):
    list_display = ['user', 'provider', 'provider_user_id', 'created_at']
    list_filter = ['provider']
    search_fields = ['user__email', 'provider_user_id']
    ordering = ['-created_at']


@admin.register(PasswordReset)
class PasswordResetAdmin(admin.ModelAdmin):
    list_display = ['user', 'token', 'expires_at', 'used', 'created_at']
    list_filter = ['used']
    search_fields = ['user__email', 'token']
    ordering = ['-created_at']
