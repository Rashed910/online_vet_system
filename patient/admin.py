from django.contrib import admin
from .models import Patient, MedicalHistory, Prescription

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('user', 'user_email', 'user_phone', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'user__email', 'user__phone')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email'
    user_email.admin_order_field = 'user__email'

    def user_phone(self, obj):
        return obj.user.phone or '-'
    user_phone.short_description = 'Phone'
    user_phone.admin_order_field = 'user__phone'

@admin.register(MedicalHistory)
class MedicalHistoryAdmin(admin.ModelAdmin):
    list_display = ('patient', 'date', 'diagnosis')
    list_filter = ('date',)
    search_fields = ('patient__user__username', 'patient__user__email', 'diagnosis')
    ordering = ('-date',)

@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ('appointment', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('appointment__patient__user__username', 'appointment__patient__user__email', 'medicines')
    ordering = ('-created_at',)
