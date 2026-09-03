from django.contrib import admin
from .models import Appointment, Payment, Refund

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient_user', 'doctor', 'date', 'time', 'status', 'fee', 'created_at')
    list_filter = ('status', 'date', 'doctor', 'created_at')
    search_fields = ('patient__user__username', 'patient__user__email', 'doctor__user__username', 'notes')
    ordering = ('-date', '-time')
    readonly_fields = ('created_at', 'updated_at')

    def patient_user(self, obj):
        return obj.patient.user.get_full_name() or obj.patient.user.username
    patient_user.short_description = 'Patient'
    patient_user.admin_order_field = 'patient__user__username'

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('appointment', 'amount', 'status', 'payment_method', 'created_at', 'paid_at')
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('appointment__patient__user__username', 'appointment__patient__user__email', 'transaction_id')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)

@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ('appointment', 'original_amount', 'refund_amount', 'deduction_percentage', 'status', 'created_at', 'processed_at')
    list_filter = ('status', 'created_at')
    search_fields = ('appointment__patient__user__username', 'appointment__patient__user__email', 'reason')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'processed_at')
