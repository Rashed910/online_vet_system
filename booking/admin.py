from django.contrib import admin
from .models import Appointment, Payment, Refund

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'date', 'time', 'status', 'fee', 'created_at')
    list_filter = ('status', 'date', 'doctor', 'created_at')
    search_fields = ('patient__pet_name', 'doctor__user__username', 'notes')
    ordering = ('-date', '-time')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('appointment', 'amount', 'status', 'payment_method', 'created_at', 'paid_at')
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('appointment__patient__pet_name', 'transaction_id')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)

@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ('appointment', 'original_amount', 'refund_amount', 'deduction_percentage', 'status', 'created_at', 'processed_at')
    list_filter = ('status', 'created_at')
    search_fields = ('appointment__patient__pet_name', 'reason')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'processed_at')
