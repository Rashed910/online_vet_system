from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from patient.models import Patient
from django.contrib.auth import get_user_model
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
        apt.payment.status == 'PENDING' and apt.status == 'PENDING'
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

    context = {
        'patient': patient,
    }
    return render(request, 'manage_profile.html', context)


@login_required
def update_pet_profile(request):
    if request.user.role != 'PATIENT':
        return render(request, '403.html', status=403)

    if request.method == 'POST':
        try:
            patient = request.user.patient_profile
        except Patient.DoesNotExist:
            patient = Patient.objects.create(user=request.user)

        patient.pet_name = request.POST.get('pet_name', '').strip()
        patient.species = request.POST.get('species', '').strip()
        patient.age = request.POST.get('age') or None
        patient.weight = request.POST.get('weight') or None
        patient.save()

        messages.success(request, 'Pet profile updated successfully.')

    return redirect('manage_profile')


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

        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.country_code = country_code
        user.phone = phone
        user.address = address
        user.save()

        messages.success(request, 'Your profile has been updated.')

    return redirect('manage_profile')
