from django.contrib import admin
from .models import Doctor, Availability

@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'specialty', 'experience_years', 'consultation_fee', 'is_active', 'created_at')
    list_filter = ('specialty', 'is_active', 'created_at')
    search_fields = ('user__username', 'user__first_name', 'specialty')
    ordering = ('-experience_years',)
    readonly_fields = ('created_at',)

@admin.register(Availability)
class AvailabilityAdmin(admin.ModelAdmin):
    list_display = ('id', 'doctor', 'day_of_week', 'start_time', 'end_time', 'is_available')
    list_filter = ('day_of_week', 'is_available')
    search_fields = ('doctor__user__username', 'doctor__specialty')
    ordering = ('doctor', 'day_of_week')
