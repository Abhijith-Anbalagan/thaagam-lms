from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Invitation

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'role', 'school', 'is_active']
    list_filter  = ['role', 'is_active']
    fieldsets    = UserAdmin.fieldsets + (
        ('EduPlatform', {'fields': ('role', 'school', 'phone', 'avatar')}),
    )

@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ['email', 'role', 'school', 'invited_by', 'accepted', 'expires_at']
