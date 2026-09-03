from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from patient.models import Patient
from django.contrib.auth import get_user_model
from booking.views import validate_phone_by_country
User = get_user_model()


@login_required
def dashboard(request):
    if request.user.role != 'PATIENT':
        return render(request, '403.html', status=403)
    try:
        patient = request.user.patient_profile
        appointments = patient.appointments.select_related('doctor__user', 'payment').order_by('-date', '-time')[:5]
    except Patient.DoesNotExist:
        patient = None
        appointments = []

    has_pending = any(
        getattr(apt, 'payment', None) and apt.payment.status == 'PENDING' and apt.status == 'PENDING'
        for apt in appointments
    )

    context = {
        'patient': patient,
        'appointments': appointments,
        'has_pending_payment': has_pending,
    }
    return render(request, 'dashboard.html', context)


@login_required
def my_appointments(request):
    if request.user.role != 'PATIENT':
        return render(request, '403.html', status=403)
    try:
        patient = request.user.patient_profile
        appointments = patient.appointments.select_related('doctor__user', 'payment').order_by('-date', '-time')
    except Patient.DoesNotExist:
        patient = None
        appointments = []

    context = {
        'patient': patient,
        'appointments': appointments,
    }
    return render(request, 'my_appointments.html', context)


@login_required
def cancel_refund_list(request):
    if request.user.role != 'PATIENT':
        return render(request, '403.html', status=403)
    try:
        patient = request.user.patient_profile
        appointments = patient.appointments.filter(
            status='CANCELLED',
            payment__status='REFUNDED',
        ).prefetch_related('refund')
    except Patient.DoesNotExist:
        patient = None
        appointments = []

    enriched_appointments = []
    for apt in appointments:
        fee = float(apt.fee)
        deduction = round(fee * 0.10, 2)
        refund = round(fee * 0.90, 2)
        enriched_appointments.append({
            'appointment': apt,
            'original_fee': fee,
            'deduction': deduction,
            'refund_amount': refund,
        })

    context = {
        'patient': patient,
        'enriched_appointments': enriched_appointments,
    }
    return render(request, 'cancel_refund_list.html', context)


@login_required
def manage_profile(request):
    if request.user.role != 'PATIENT':
        return render(request, '403.html', status=403)
    try:
        patient = request.user.patient_profile
    except Patient.DoesNotExist:
        patient = Patient.objects.create(user=request.user)

    phone_display = ''
    if request.user.phone:
        cc = request.user.country_code or '+880'
        phone_display = request.user.phone[len(cc):] if request.user.phone.startswith(cc) else request.user.phone

    context = {
        'patient': patient,
        'phone_display': phone_display,
    }
    return render(request, 'manage_profile.html', context)


@login_required
def update_patient_profile(request):
    if request.user.role != 'PATIENT':
        return render(request, '403.html', status=403)

    if request.method == 'POST':
        user = request.user
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        country_code = request.POST.get('country_code', '+880').strip()
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()

        if not first_name or not email:
            messages.error(request, 'Name and email are required.')
            return redirect('manage_profile')

        if User.objects.filter(email=email).exclude(id=user.id).exists():
            messages.error(request, 'This email is already in use.')
            return redirect('manage_profile')

        if phone:
            phone_digits = ''.join(c for c in phone if c.isdigit())
            country_digits = ''.join(c for c in country_code if c.isdigit())
            if phone_digits.startswith('0'):
                phone_digits = phone_digits[1:]
            valid, err = validate_phone_by_country(phone_digits, country_code)
            if not valid:
                messages.error(request, err)
                return redirect('manage_profile')
            full_phone = '+' + country_digits + phone_digits
            if User.objects.filter(phone=full_phone).exclude(id=user.id).exists():
                messages.error(request, 'This phone number is already used by another account.')
                return redirect('manage_profile')
            phone = full_phone
        else:
            phone = ''

        orig_first = user.first_name
        orig_last = user.last_name
        orig_email = user.email
        orig_country = user.country_code
        orig_phone = user.phone
        orig_address = user.address

        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.country_code = country_code
        user.phone = phone
        user.address = address

        changed = any([
            user.first_name != orig_first,
            user.last_name != orig_last,
            user.email != orig_email,
            user.country_code != orig_country,
            (user.phone or '') != (orig_phone or ''),
            user.address != orig_address,
        ])
        user.save()

        if changed:
            messages.success(request, 'Your profile has been updated.')
        else:
            messages.info(request, 'No changes were made to your profile.')

    return redirect('manage_profile')
