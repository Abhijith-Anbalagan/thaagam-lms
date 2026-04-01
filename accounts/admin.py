from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Invitation
from .models import Testimonial

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



@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'rating', 'status', 'created_at']
    list_filter = ['status']
    actions = ['approve_testimonials', 'reject_testimonials']

    def approve_testimonials(self, request, queryset):
        queryset.update(status='approved')
    approve_testimonials.short_description = 'Approve selected testimonials'

    def reject_testimonials(self, request, queryset):
        queryset.update(status='rejected')
    reject_testimonials.short_description = 'Reject selected testimonials'