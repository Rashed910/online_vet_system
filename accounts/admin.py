from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('id', 'username', 'email', 'role', 'phone', 'is_staff', 'created_at')
    list_filter = ('role', 'is_staff', 'is_superuser', 'created_at')
    search_fields = ('username', 'email', 'phone')
    ordering = ('username',)
    readonly_fields = ('created_at',)
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('role', 'phone', 'country_code', 'address', 'created_at')}),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Additional Info', {'fields': ('role', 'phone', 'country_code', 'address')}),
    )
