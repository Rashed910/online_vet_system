from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.http import HttpResponse
from datetime import datetime, timedelta
from vet.models import Doctor
from patient.models import Patient
from booking.models import Appointment, Refund
from booking.models import Payment

User = get_user_model()


@login_required
def admin_dashboard(request):
    if request.user.role != 'ADMIN':
        return render(request, '403.html', status=403)

    total_doctors = Doctor.objects.count()
    active_doctors = Doctor.objects.filter(is_active=True).count()
    total_patients = Patient.objects.count()
    total_appointments = Appointment.objects.count()
    pending_payments = Payment.objects.filter(status='PENDING').count()
    today_appointments = Appointment.objects.filter(date=timezone.now().date()).count()

    total_revenue = Payment.objects.filter(status='PAID').aggregate(total=Sum('amount'))['total'] or 0
    total_refunded = Refund.objects.filter(status='PROCESSED').aggregate(total=Sum('refund_amount'))['total'] or 0

    context = {
        'total_doctors': total_doctors,
        'active_doctors': active_doctors,
        'total_patients': total_patients,
        'total_appointments': total_appointments,
        'pending_payments': pending_payments,
        'today_appointments': today_appointments,
        'total_revenue': total_revenue,
        'total_refunded': total_refunded,
    }
    return render(request, 'adminpanel_dashboard.html', context)


@login_required
def vet_management(request):
    if request.user.role != 'ADMIN':
        return render(request, '403.html', status=403)
    doctors = Doctor.objects.select_related('user').all()
    context = {'doctors': doctors}
    return render(request, 'admin_vet_management.html', context)


@login_required
def patient_management(request):
    if request.user.role != 'ADMIN':
        return render(request, '403.html', status=403)
    patients = Patient.objects.select_related('user').all()
    context = {'patients': patients}
    return render(request, 'admin_patient_management.html', context)


@login_required
def routine_control(request):
    if request.user.role != 'ADMIN':
        return render(request, '403.html', status=403)
    from vet.models import Availability
    routines = Availability.objects.select_related('doctor', 'doctor__user').all()
    context = {'routines': routines}
    return render(request, 'admin_routine_control.html', context)


@login_required
def reports(request):
    if request.user.role != 'ADMIN':
        return render(request, '403.html', status=403)

    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    daily_appointments = Appointment.objects.filter(date=today)
    weekly_appointments = Appointment.objects.filter(date__gte=week_ago, date__lte=today)
    monthly_appointments = Appointment.objects.filter(date__gte=month_ago, date__lte=today)

    daily_revenue = Payment.objects.filter(
        status='PAID',
        paid_at__date=today,
    ).aggregate(total=Sum('amount'))['total'] or 0

    weekly_revenue = Payment.objects.filter(
        status='PAID',
        paid_at__date__gte=week_ago,
        paid_at__date__lte=today,
    ).aggregate(total=Sum('amount'))['total'] or 0

    monthly_revenue = Payment.objects.filter(
        status='PAID',
        paid_at__date__gte=month_ago,
        paid_at__date__lte=today,
    ).aggregate(total=Sum('amount'))['total'] or 0

    daily_refunds = Refund.objects.filter(created_at__date=today)
    weekly_refunds = Refund.objects.filter(created_at__date__gte=week_ago, created_at__date__lte=today)
    monthly_refunds = Refund.objects.filter(created_at__date__gte=month_ago, created_at__date__lte=today)

    daily_refund_amount = daily_refunds.aggregate(total=Sum('refund_amount'))['total'] or 0
    weekly_refund_amount = weekly_refunds.aggregate(total=Sum('refund_amount'))['total'] or 0
    monthly_refund_amount = monthly_refunds.aggregate(total=Sum('refund_amount'))['total'] or 0

    context = {
        'daily_appointments': daily_appointments,
        'weekly_appointments': weekly_appointments,
        'monthly_appointments': monthly_appointments,
        'daily_revenue': daily_revenue,
        'weekly_revenue': weekly_revenue,
        'monthly_revenue': monthly_revenue,
        'daily_refunds': daily_refunds,
        'weekly_refunds': weekly_refunds,
        'monthly_refunds': monthly_refunds,
        'daily_refund_amount': daily_refund_amount,
        'weekly_refund_amount': weekly_refund_amount,
        'monthly_refund_amount': monthly_refund_amount,
    }
    return render(request, 'admin_reports.html', context)


@login_required
def admin_appointments(request):
    if request.user.role != 'ADMIN':
        return render(request, '403.html', status=403)
    appointments = Appointment.objects.select_related(
        'patient__user', 'doctor__user', 'payment'
    ).order_by('-date', '-time')
    context = {'appointments': appointments}
    return render(request, 'admin_appointments.html', context)


@login_required
def admin_payments(request):
    if request.user.role != 'ADMIN':
        return render(request, '403.html', status=403)
    payments = Payment.objects.select_related(
        'appointment__patient__user', 'appointment__doctor__user'
    ).order_by('-created_at')
    context = {'payments': payments}
    return render(request, 'admin_payments.html', context)


@login_required
def approve_payment(request, payment_id):
    if request.user.role != 'ADMIN':
        return render(request, '403.html', status=403)
    if request.method == 'POST':
        from django.db import transaction
        payment = get_object_or_404(Payment, id=payment_id)
        action = request.POST.get('action', 'approve')
        with transaction.atomic():
            if action == 'approve':
                payment.status = 'PAID'
                payment.paid_at = timezone.now()
                payment.save(update_fields=['status', 'paid_at'])
                appointment = payment.appointment
                appointment.status = 'CONFIRMED'
                appointment.save(update_fields=['status'])
                messages.success(request, f'Payment #{payment.id} approved. Appointment #{appointment.id} status updated to CONFIRMED.')
            elif action == 'reject':
                payment.status = 'FAILED'
                payment.save(update_fields=['status'])
                appointment = payment.appointment
                appointment.status = 'CANCELLED'
                appointment.save(update_fields=['status'])
                messages.warning(request, f'Payment #{payment.id} rejected. Appointment #{appointment.id} cancelled.')
    return redirect('admin_payments')


@login_required
def export_report(request, report_type):
    if request.user.role != 'ADMIN':
        return render(request, '403.html', status=403)

    today = timezone.now().date()
    if report_type == 'daily':
        appointments = Appointment.objects.filter(date=today).select_related('patient__user', 'doctor__user', 'payment')
        title = f"Daily Report - {today}"
    elif report_type == 'weekly':
        week_ago = today - timedelta(days=7)
        appointments = Appointment.objects.filter(date__gte=week_ago, date__lte=today).select_related('patient__user', 'doctor__user', 'payment')
        title = f"Weekly Report ({week_ago} to {today})"
    elif report_type == 'monthly':
        month_ago = today - timedelta(days=30)
        appointments = Appointment.objects.filter(date__gte=month_ago, date__lte=today).select_related('patient__user', 'doctor__user', 'payment')
        title = f"Monthly Report ({month_ago} to {today})"
    else:
        appointments = Appointment.objects.select_related('patient__user', 'doctor__user', 'payment')
        title = "All Appointments Report"

    content = f"VetCare {title}\n"
    content += "=" * 80 + "\n\n"
    content += f"{'Date':<12} {'Time':<10} {'Patient':<25} {'Doctor':<25} {'Status':<12} {'Fee':<8}\n"
    content += "-" * 100 + "\n"
    total_revenue = 0
    for apt in appointments:
        content += f"{str(apt.date):<12} {apt.time.strftime('%I:%M %p'):<10} {apt.patient.pet_name[:24]:<25} {str(apt.doctor)[:24]:<25} {apt.status:<12} {apt.fee}\n"
        if hasattr(apt, 'payment') and apt.payment.status == 'PAID':
            total_revenue += float(apt.payment.amount)
    content += "-" * 100 + "\n"
    content += f"Total Appointments: {appointments.count()}\n"
    content += f"Total Revenue: BDT {total_revenue:.2f}\n"

    response = HttpResponse(content, content_type='text/plain')
    response['Content-Disposition'] = f'attachment; filename="vetcare_report_{report_type}_{today}.txt"'
    return response
