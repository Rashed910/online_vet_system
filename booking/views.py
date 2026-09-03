from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.utils import timezone
from vet.models import Doctor
from patient.models import Patient
from booking.models import Appointment, Payment, Refund

TIME_SLOTS = ['09:00 AM', '10:00 AM', '11:00 AM', '12:00 PM', '01:00 PM', '02:00 PM', '03:30 PM', '05:00 PM']
PAYMENT_METHODS = [
    ('BKASH', 'bKash'),
    ('NAGAD', 'Nagad'),
]


@login_required
def doctors(request):
    from vet.models import Availability

    doctors_list = Doctor.objects.filter(
        is_active=True,
    ).select_related('user').order_by('user__first_name')

    doctor_data = []
    for doc in doctors_list:
        avail_days = list(
            doc.availabilities.filter(is_available=True)
            .values_list('day_of_week', flat=True)
            .distinct()
        )
        doctor_data.append({
            'doctor': doc,
            'available_days': avail_days,
        })

    context = {
        'doctor_data': doctor_data,
    }
    return render(request, 'doctors.html', context)


@login_required
def doctor_detail(request, doctor_id):
    from vet.models import Availability
    from datetime import datetime, timedelta

    doctor = get_object_or_404(Doctor, id=doctor_id, is_active=True)

    today = timezone.now().date()
    selected_date_str = request.GET.get('date', today.strftime('%Y-%m-%d'))
    try:
        selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    except ValueError:
        selected_date = today

    weekday = selected_date.weekday()
    now = timezone.now()
    is_today = (selected_date == today)
    current_time = now.time()

    available_slots_today = []
    slot = doctor.availabilities.filter(
        day_of_week=weekday, is_available=True
    ).first()

    if slot:
        current_dt = datetime.combine(selected_date, slot.start_time)
        end_dt = datetime.combine(selected_date, slot.end_time)
        while current_dt < end_dt:
            booked = Appointment.objects.filter(
                doctor=doctor,
                date=selected_date,
                time=current_dt.time(),
                status__in=['PENDING', 'CONFIRMED'],
            ).exists()
            is_past = is_today and current_dt.time() <= current_time
            available_slots_today.append({
                'time_24': current_dt.strftime('%H:%M'),
                'time_12': current_dt.strftime('%I:%M %p'),
                'booked': booked,
                'is_past': is_past,
            })
            current_dt += timedelta(minutes=30)

    next_7_days = []
    for i in range(0, 14):
        d = today + timedelta(days=i)
        wd = d.weekday()
        has_slot = doctor.availabilities.filter(
            day_of_week=wd, is_available=True
        ).exists()
        next_7_days.append({
            'date': d,
            'weekday': wd,
            'has_slot': has_slot,
            'is_today': d == today,
        })

    context = {
        'doctor': doctor,
        'selected_date': selected_date,
        'available_slots_today': available_slots_today,
        'next_7_days': next_7_days,
        'payment_methods': PAYMENT_METHODS,
    }
    return render(request, 'doctor_detail.html', context)


@require_GET
@login_required
def doctor_slots(request, doctor_id):
    from datetime import datetime
    doctor = get_object_or_404(Doctor, id=doctor_id, is_active=True)
    date_str = request.GET.get('date')
    if not date_str:
        return JsonResponse({'error': 'Missing date'}, status=400)
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Invalid date'}, status=400)

    weekday = date_obj.weekday()
    now = timezone.now()
    is_today = (date_obj == now.date())
    current_time = now.time()

    slots = []
    slot = doctor.availabilities.filter(
        day_of_week=weekday, is_available=True
    ).first()
    if slot:
        from datetime import timedelta
        current_dt = datetime.combine(date_obj, slot.start_time)
        end_dt = datetime.combine(date_obj, slot.end_time)
        while current_dt < end_dt:
            booked = Appointment.objects.filter(
                doctor=doctor,
                date=date_obj,
                time=current_dt.time(),
                status__in=['PENDING', 'CONFIRMED'],
            ).exists()
            is_past = is_today and current_dt.time() <= current_time
            slots.append({
                'time_24': current_dt.strftime('%H:%M'),
                'time_12': current_dt.strftime('%I:%M %p'),
                'booked': booked,
                'is_past': is_past,
            })
            current_dt += timedelta(minutes=30)

    return JsonResponse({'slots': slots})


@require_GET
@login_required
def booked_slots(request):
    doctor_id = request.GET.get('doctor_id')
    date_str = request.GET.get('date')
    if not doctor_id or not date_str:
        return JsonResponse({'error': 'Missing doctor_id or date'}, status=400)

    from datetime import datetime
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Invalid date format'}, status=400)

    booked = Appointment.objects.filter(
        doctor_id=doctor_id,
        date=date_obj,
        status__in=['PENDING', 'CONFIRMED'],
    ).values_list('time', flat=True)

    booked_slots = []
    for t in booked:
        booked_slots.append(t.strftime('%I:%M %p'))

    return JsonResponse({'booked_slots': booked_slots})


@login_required
def book_appointment(request):
    if request.method == 'POST':
        doctor_id = request.POST.get('doctor_id')
        date_str = request.POST.get('date')
        time_str = request.POST.get('time')
        payment_method = request.POST.get('payment_method')
        transaction_id = request.POST.get('transaction_id', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()

        if payment_method not in ['BKASH', 'NAGAD']:
            messages.error(request, 'Please select a valid payment method (bKash or Nagad).')
            return redirect('booking_doctors')

        if not transaction_id:
            messages.error(request, 'Please provide your bKash/Nagad transaction ID for payment verification.')
            return redirect('booking_doctors')

        if len(transaction_id) < 6:
            messages.error(request, 'Transaction ID looks too short. Please enter the full transaction ID.')
            return redirect('booking_doctors')

        if not phone_number:
            messages.error(request, 'Please provide your phone number used for payment.')
            return redirect('booking_doctors')

        phone_digits = ''.join(c for c in phone_number if c.isdigit())
        if len(phone_digits) < 10 or len(phone_digits) > 15:
            messages.error(request, 'Please enter a valid phone number (10-15 digits).')
            return redirect('booking_doctors')

        try:
            doctor = Doctor.objects.get(id=doctor_id, is_active=True)
        except Doctor.DoesNotExist:
            messages.error(request, 'Selected doctor is not available.')
            return redirect('booking_doctors')

        try:
            patient = request.user.patient_profile
        except Patient.DoesNotExist:
            patient = Patient.objects.create(user=request.user)

        from datetime import datetime
        try:
            if time_str:
                try:
                    time_obj = datetime.strptime(time_str, '%H:%M').time()
                except ValueError:
                    time_obj = datetime.strptime(time_str, '%I:%M %p').time()
            else:
                time_obj = None
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else None
        except ValueError:
            messages.error(request, 'Invalid date or time format.')
            return redirect('booking_doctors')

        if not date_obj or not time_obj:
            messages.error(request, 'Please select a valid date and time.')
            return redirect('booking_doctors')

        existing = Appointment.objects.filter(
            doctor=doctor,
            date=date_obj,
            time=time_obj,
            status__in=['PENDING', 'CONFIRMED'],
        ).exists()

        if existing:
            messages.error(request, 'This time slot is already booked. Please choose another slot.')
            return redirect('booking_doctors')

        from datetime import datetime as _dt
        if date_obj == _dt.now().date() and time_obj <= _dt.now().time():
            messages.error(request, 'Cannot book a slot in the past. Please choose a future time.')
            return redirect('booking_doctors')

        appointment = Appointment.objects.create(
            patient=patient,
            doctor=doctor,
            date=date_obj,
            time=time_obj,
            status='PENDING',
            fee=doctor.consultation_fee,
        )

        Payment.objects.create(
            appointment=appointment,
            amount=doctor.consultation_fee,
            status='PENDING',
            payment_method=payment_method,
            transaction_id=transaction_id,
            phone_number=phone_number,
        )

        messages.info(request, f'Appointment booked! Your payment (Transaction ID: {transaction_id}) is pending admin approval. You will be notified once approved.')
        return redirect('booking_success', appointment_id=appointment.id)

    return redirect('booking_doctors')


@login_required
def booking_success(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    if appointment.patient.user != request.user:
        return redirect('patient_dashboard')
    return render(request, 'booking_success.html', {'appointment': appointment})


@login_required
def receipt(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    if appointment.patient.user != request.user:
        return redirect('patient_dashboard')
    return render(request, 'receipt.html', {'appointment': appointment})


@login_required
def cancel_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)

    # Verify ownership
    if appointment.patient.user != request.user:
        messages.error(request, 'You do not have permission to cancel this appointment.')
        return redirect('patient_dashboard')

    if appointment.status == 'CANCELLED':
        messages.info(request, 'This appointment is already cancelled.')
        return redirect('patient_dashboard')

    if request.method == 'POST':
        payment = appointment.payment
        was_paid = (payment.status == 'PAID')

        # Update appointment status
        appointment.status = 'CANCELLED'
        appointment.save()

        if was_paid:
            # Payment was confirmed by admin — issue a refund
            refund, created = Refund.objects.get_or_create(
                appointment=appointment,
                defaults={
                    'original_amount': appointment.fee,
                    'deduction_percentage': 10,
                    'reason': request.POST.get('reason', 'Cancelled by patient'),
                },
            )
            if created:
                refund.refund_amount = appointment.fee * 90 / 100
                refund.status = 'PROCESSED'
                refund.processed_at = timezone.now()
                refund.save()

            payment.status = 'REFUNDED'
            payment.save()

            messages.success(request, 'Appointment cancelled successfully. Your refund slip is ready.')
            return redirect('refund_slip', refund_id=refund.id)
        else:
            # Payment was still PENDING — no refund needed
            if payment.status == 'PENDING':
                payment.status = 'FAILED'
                payment.save()
            messages.success(request, 'Appointment cancelled. Your pending payment has been marked as failed. As per our policy, refund is only issued AFTER payment is confirmed — so no refund will be processed for this cancellation.')
            return redirect('patient_dashboard')

    return redirect('patient_dashboard')


@login_required
def refund_slip(request, refund_id):
    refund = get_object_or_404(Refund, id=refund_id)

    # Verify ownership
    if refund.appointment.patient.user != request.user:
        messages.error(request, 'You do not have permission to view this refund slip.')
        return redirect('patient_dashboard')

    deduction = refund.original_amount - refund.refund_amount
    context = {
        'refund': refund,
        'deduction': deduction,
        'appointment': refund.appointment,
    }
    return render(request, 'refund_slip.html', context)
