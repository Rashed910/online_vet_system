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
    from datetime import datetime

    selected_date_str = request.GET.get('date', '').strip()
    selected_date = None
    weekday = None
    if selected_date_str:
        try:
            selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
            weekday = selected_date.weekday()
        except ValueError:
            selected_date = None
            weekday = None

    selected_specialty = request.GET.get('specialty', '').strip()

    doctors_list = Doctor.objects.filter(
        is_active=True,
    ).select_related('user').order_by('user__first_name')

    if selected_specialty:
        doctors_list = doctors_list.filter(specialty__icontains=selected_specialty)

    all_specialties = list(
        Doctor.objects.filter(is_active=True)
        .exclude(specialty__exact='')
        .values_list('specialty', flat=True)
        .distinct()
        .order_by()
    )

    doctor_data = []
    for doc in doctors_list:
        avail_qs = doc.availabilities.filter(is_available=True)
        if weekday is not None:
            avail_qs = avail_qs.filter(day_of_week=weekday)
        has_availability = avail_qs.exists()
        if selected_date is not None and not has_availability:
            continue
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
        'selected_date': selected_date_str,
        'selected_specialty': selected_specialty,
        'all_specialties': all_specialties,
        'today': datetime.now().date(),
    }
    return render(request, 'doctors.html', context)


@login_required
def doctor_detail(request, doctor_id):
    from vet.models import Availability
    from datetime import datetime, timedelta

    doctor = get_object_or_404(Doctor, id=doctor_id, is_active=True)

    now = timezone.localtime(timezone.now())
    today = now.date()
    selected_date_str = request.GET.get('date', today.strftime('%Y-%m-%d'))
    try:
        selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    except ValueError:
        selected_date = today

    weekday = selected_date.weekday()
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
    now = timezone.localtime(timezone.now())
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


COUNTRY_PHONE_RULES = {
    '+880': {'name': 'Bangladesh', 'min': 10, 'max': 10},
    '+1':  {'name': 'USA/Canada', 'min': 10, 'max': 10},
    '+44': {'name': 'UK', 'min': 10, 'max': 10},
    '+91': {'name': 'India', 'min': 10, 'max': 10},
    '+86': {'name': 'China', 'min': 11, 'max': 11},
    '+81': {'name': 'Japan', 'min': 10, 'max': 10},
    '+82': {'name': 'South Korea', 'min': 10, 'max': 10},
    '+966': {'name': 'Saudi Arabia', 'min': 9, 'max': 9},
    '+971': {'name': 'UAE', 'min': 9, 'max': 9},
    '+92':  {'name': 'Pakistan', 'min': 10, 'max': 10},
    '+60':  {'name': 'Malaysia', 'min': 9, 'max': 10},
    '+65':  {'name': 'Singapore', 'min': 8, 'max': 8},
    '+62':  {'name': 'Indonesia', 'min': 9, 'max': 12},
    '+63':  {'name': 'Philippines', 'min': 10, 'max': 10},
    '+66':  {'name': 'Thailand', 'min': 9, 'max': 10},
    '+84':  {'name': 'Vietnam', 'min': 9, 'max': 10},
    '+20':  {'name': 'Egypt', 'min': 10, 'max': 10},
    '+27':  {'name': 'South Africa', 'min': 9, 'max': 9},
    '+234': {'name': 'Nigeria', 'min': 10, 'max': 11},
    '+254': {'name': 'Kenya', 'min': 9, 'max': 10},
    '+61':  {'name': 'Australia', 'min': 9, 'max': 9},
    '+64':  {'name': 'New Zealand', 'min': 9, 'max': 9},
    '+49':  {'name': 'Germany', 'min': 10, 'max': 12},
    '+33':  {'name': 'France', 'min': 9, 'max': 9},
    '+39':  {'name': 'Italy', 'min': 9, 'max': 10},
    '+34':  {'name': 'Spain', 'min': 9, 'max': 9},
    '+7':   {'name': 'Russia', 'min': 10, 'max': 10},
    '+55':  {'name': 'Brazil', 'min': 10, 'max': 11},
    '+52':  {'name': 'Mexico', 'min': 10, 'max': 10},
    '+90':  {'name': 'Turkey', 'min': 10, 'max': 10},
}


def validate_phone_by_country(phone_digits, country_code):
    rules = COUNTRY_PHONE_RULES.get(country_code)
    if not rules:
        return True, None
    if not (rules['min'] <= len(phone_digits) <= rules['max']):
        return False, f"{rules['name']} phone numbers must be {rules['min']} digits (entered: {len(phone_digits)})."
    return True, None


@login_required
def book_appointment(request):
    if request.method == 'POST':
        doctor_id = request.POST.get('doctor_id')
        date_str = request.POST.get('date')
        time_str = request.POST.get('time')
        payment_method = request.POST.get('payment_method')
        transaction_id = request.POST.get('transaction_id', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()

        def back_with_error(msg):
            from django.contrib import messages as _m
            _m.error(request, msg)
            return redirect('doctor_detail', doctor_id=doctor_id) if doctor_id else redirect('booking_doctors')

        if payment_method not in ['BKASH', 'NAGAD']:
            return back_with_error('Please select a valid payment method (bKash or Nagad).')

        if not transaction_id:
            return back_with_error('Please provide your bKash/Nagad transaction ID for payment verification.')

        if len(transaction_id) < 6:
            return back_with_error('Transaction ID looks too short. Please enter the full transaction ID.')

        if not phone_number:
            return back_with_error('Please provide your phone number used for payment.')

        country_code = request.POST.get('country_code', '+880').strip()
        phone_digits = ''.join(c for c in phone_number if c.isdigit())
        country_digits = ''.join(c for c in country_code if c.isdigit())

        if phone_digits.startswith('0'):
            phone_digits = phone_digits[1:]

        valid, err = validate_phone_by_country(phone_digits, country_code)
        if not valid:
            return back_with_error(err)

        full_phone = '+' + country_digits + phone_digits

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
            return back_with_error('Invalid date or time format.')

        if not date_obj or not time_obj:
            return back_with_error('Please select a valid date and time.')

        existing = Appointment.objects.filter(
            doctor=doctor,
            date=date_obj,
            time=time_obj,
            status__in=['PENDING', 'CONFIRMED'],
        ).exists()

        if existing:
            return back_with_error('This time slot is already booked. Please choose another slot.')

        from datetime import datetime as _dt
        now_local = timezone.localtime(timezone.now())
        if date_obj == now_local.date() and time_obj <= now_local.time():
            return back_with_error('Cannot book a slot in the past. Please choose a future time.')

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
            phone_number=full_phone,
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
