from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from django.db.models import Sum
from booking.models import Appointment, Payment, Refund
from patient.models import MedicalHistory
from datetime import datetime, date, timedelta
from django.utils import timezone


def admin_reports_view(request):
    if not request.user.is_authenticated or not request.user.is_staff:
        return render(request, '403.html', status=403)
    report_type = request.GET.get('type', 'daily')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    today = timezone.now().date()
    if report_type == 'daily' and not start_date:
        start_date = today
        end_date = today
    elif report_type == 'weekly' and not start_date:
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=6)
    elif report_type == 'monthly' and not start_date:
        start_date = today.replace(day=1)
        end_date = today
    if start_date and end_date:
        if not isinstance(start_date, date):
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            except ValueError:
                start_date = today
        if not isinstance(end_date, date):
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                end_date = today
    appointments = Appointment.objects.filter(date__range=[start_date, end_date])
    total_appointments = appointments.count()
    completed_appointments = appointments.filter(status='COMPLETED').count()
    cancelled_appointments = appointments.filter(status='CANCELLED').count()
    payments = Payment.objects.filter(created_at__date__range=[start_date, end_date], status='PAID')
    total_revenue = payments.aggregate(total=Sum('amount'))['total'] or 0
    refunds = Refund.objects.filter(created_at__date__range=[start_date, end_date], status='PROCESSED')
    total_refunded = refunds.aggregate(total=Sum('refund_amount'))['total'] or 0
    total_deduction = sum(r.original_amount * r.deduction_percentage / 100 for r in refunds)
    context = {
        'report_type': report_type,
        'start_date': start_date,
        'end_date': end_date,
        'total_appointments': total_appointments,
        'completed_appointments': completed_appointments,
        'cancelled_appointments': cancelled_appointments,
        'total_revenue': total_revenue,
        'total_refunded': total_refunded,
        'total_deduction': total_deduction,
        'net_income': total_revenue - total_refunded,
        'appointments': appointments[:50],
        'payments': payments[:50],
        'refunds': refunds[:50],
        'opts': {},
    }
    return render(request, 'admin/reports.html', context)


# Add reports URL to default admin site
from django.contrib.admin.sites import AdminSite

_original_get_urls = AdminSite.get_urls

def _patched_get_urls(self):
    urls = _original_get_urls(self)
    custom_urls = [
        path('reports/', admin_reports_view, name='admin_reports'),
    ]
    return custom_urls + urls

AdminSite.get_urls = _patched_get_urls
