from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from vet.models import Doctor, Availability
from django.contrib.auth import get_user_model
User = get_user_model()


@login_required
def vet_dashboard(request):
    if request.user.role != 'DOCTOR':
        return render(request, '403.html', status=403)
    from django.utils import timezone
    from datetime import datetime, timedelta
    from patient.models import MedicalHistory

    try:
        doctor = request.user.doctor_profile
        all_appointments = doctor.appointments.filter(
            payment__status='PAID',
            status__in=['CONFIRMED', 'COMPLETED'],
        ).order_by('-date', '-time')
        my_patients = all_appointments.values_list('patient', flat=True).distinct()
        recent_medical_histories = MedicalHistory.objects.filter(
            patient_id__in=list(my_patients),
            appointment__doctor=doctor,
        ).select_related('patient', 'patient__user', 'appointment').order_by('-date', '-id')[:10]
    except Exception:
        doctor = None
        all_appointments = []
        recent_medical_histories = []

    today = timezone.now().date()
    today_appointments = all_appointments.filter(date=today) if doctor else []
    patients_seen_today = today_appointments.filter(status='COMPLETED').count()
    patients_remaining = today_appointments.exclude(status__in=['COMPLETED', 'CANCELLED']).count()

    total_today = today_appointments.count()
    if doctor:
        from vet.models import Availability
        today_weekday = today.weekday()
        today_slots = Availability.objects.filter(doctor=doctor, day_of_week=today_weekday, is_available=True)
        total_minutes = 0
        for slot in today_slots:
            delta = datetime.combine(today, slot.end_time) - datetime.combine(today, slot.start_time)
            total_minutes += int(delta.total_seconds() / 60)
        appointments_per_slot = 30
        total_capacity_minutes = total_today * appointments_per_slot if total_today > 0 else 0
        remaining_capacity = max(0, total_minutes - total_capacity_minutes)
        hours = remaining_capacity // 60
        minutes = remaining_capacity % 60
        working_time = f"{hours}h {minutes}m" if total_minutes > 0 else "0h 0m"
    else:
        working_time = "0h 0m"

    context = {
        'doctor': doctor,
        'appointments': all_appointments[:10],
        'patients_seen_today': patients_seen_today,
        'patients_remaining': patients_remaining,
        'working_time': working_time,
        'total_today': total_today,
        'recent_medical_histories': recent_medical_histories,
    }
    return render(request, 'vet_dashboard.html', context)


@login_required
def booked_appointments(request):
    if request.user.role != 'DOCTOR':
        return render(request, '403.html', status=403)
    from patient.models import MedicalHistory
    try:
        doctor = request.user.doctor_profile
        appointments = doctor.appointments.filter(
            payment__status='PAID',
            status__in=['CONFIRMED', 'COMPLETED'],
        ).select_related('patient__user', 'payment')
        appointment_data = []
        for apt in appointments:
            histories = apt.patient.medical_histories.filter(appointment=apt).order_by('-date')
            appointment_data.append({
                'appointment': apt,
                'histories': histories,
            })
    except Exception:
        doctor = None
        appointment_data = []

    context = {
        'doctor': doctor,
        'appointment_data': appointment_data,
    }
    return render(request, 'vet_booked_appointments.html', context)


@login_required
def patient_medical_history(request):
    if request.user.role != 'DOCTOR':
        return render(request, '403.html', status=403)
    try:
        doctor = request.user.doctor_profile
        appointments = doctor.appointments.all()
    except Exception:
        doctor = None
        appointments = []

    context = {
        'doctor': doctor,
        'appointments': appointments,
    }
    return render(request, 'vet_patient_history.html', context)


@login_required
def view_patient(request, appointment_id):
    if request.user.role != 'DOCTOR':
        return render(request, '403.html', status=403)

    from booking.models import Appointment
    from patient.models import MedicalHistory
    from django.shortcuts import get_object_or_404

    appointment = get_object_or_404(Appointment, id=appointment_id)

    if appointment.doctor.user != request.user:
        return render(request, '403.html', status=403)

    if appointment.payment.status != 'PAID' or appointment.status not in ['CONFIRMED', 'COMPLETED']:
        from django.contrib import messages as _m
        _m.warning(request, 'This appointment is not available. It must be paid and confirmed first.')
        return redirect('vet_booked_appointments')

    patient = appointment.patient
    medical_histories = patient.medical_histories.all().order_by('-date')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_medical_history':
            diagnosis = request.POST.get('diagnosis', '').strip()
            notes = request.POST.get('notes', '').strip()
            medical_suggestion = request.POST.get('medical_suggestion', '').strip()
            medicines = request.POST.get('medicines', '').strip()
            dosage = request.POST.get('dosage', '').strip()
            frequency = request.POST.get('frequency', '').strip()
            duration = request.POST.get('duration', '').strip()
            date_str = request.POST.get('date', '').strip()
            from datetime import datetime
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else datetime.now().date()
            except ValueError:
                date_obj = datetime.now().date()

            if diagnosis:
                history = MedicalHistory.objects.create(
                    patient=patient,
                    appointment=appointment,
                    diagnosis=diagnosis,
                    notes=notes,
                    medical_suggestion=medical_suggestion,
                    medicines=medicines,
                    dosage=dosage,
                    frequency=frequency,
                    duration=duration,
                    date=date_obj,
                )
                has_prescription = bool(medicines or dosage or frequency or duration)
                if has_prescription and appointment.status not in ['COMPLETED', 'CANCELLED']:
                    appointment.status = 'COMPLETED'
                    appointment.save()
                messages.success(request, 'Diagnosis, prescription and medical suggestion saved successfully.')

        elif action == 'edit_medical_history':
            history_id = request.POST.get('history_id')
            history = MedicalHistory.objects.filter(id=history_id, patient=patient).first()
            if history:
                history.diagnosis = request.POST.get('diagnosis', history.diagnosis).strip()
                history.notes = request.POST.get('notes', history.notes).strip()
                history.medical_suggestion = request.POST.get('medical_suggestion', history.medical_suggestion).strip()
                history.medicines = request.POST.get('medicines', history.medicines).strip()
                history.dosage = request.POST.get('dosage', history.dosage).strip()
                history.frequency = request.POST.get('frequency', history.frequency).strip()
                history.duration = request.POST.get('duration', history.duration).strip()
                date_str = request.POST.get('date', '').strip()
                if date_str:
                    from datetime import datetime
                    try:
                        history.date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    except ValueError:
                        pass
                history.save()
                messages.success(request, 'Diagnosis, prescription and medical suggestion updated successfully.')

        elif action == 'delete_medical_history':
            history_id = request.POST.get('history_id')
            MedicalHistory.objects.filter(id=history_id, patient=patient).delete()
            messages.success(request, 'Medical history deleted.')

        elif action == 'update_status':
            new_status = request.POST.get('status', '')
            if new_status in ['PENDING', 'CONFIRMED', 'COMPLETED', 'CANCELLED']:
                appointment.status = new_status
                appointment.save()
                messages.success(request, f'Appointment status updated to {new_status}.')

        return redirect('vet_view_patient', appointment_id=appointment_id)

    context = {
        'doctor': request.user.doctor_profile if hasattr(request.user, 'doctor_profile') else None,
        'appointment': appointment,
        'patient': patient,
        'medical_histories': medical_histories,
    }
    return render(request, 'vet_view_patient.html', context)


@login_required
def api_update_status(request, appointment_id):
    if request.user.role != 'DOCTOR':
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    from booking.models import Appointment
    from django.shortcuts import get_object_or_404

    appointment = get_object_or_404(Appointment, id=appointment_id)
    if appointment.doctor.user != request.user:
        return JsonResponse({'error': 'Not your appointment'}, status=403)

    new_status = request.POST.get('status', '')
    if new_status not in ['PENDING', 'CONFIRMED', 'COMPLETED', 'CANCELLED']:
        return JsonResponse({'error': 'Invalid status'}, status=400)

    appointment.status = new_status
    appointment.save()

    status_colors = {
        'PENDING': 'amber',
        'CONFIRMED': 'blue',
        'COMPLETED': 'emerald',
        'CANCELLED': 'red',
    }
    color = status_colors.get(new_status, 'slate')

    return JsonResponse({
        'success': True,
        'status': new_status,
        'color': color,
        'message': f'Appointment status updated to {new_status}',
    })


@login_required
def manage_availability(request):
    if request.user.role != 'DOCTOR':
        return render(request, '403.html', status=403)
    try:
        doctor = request.user.doctor_profile
    except Exception:
        doctor = None

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add' and doctor:
            day_of_week = int(request.POST.get('day_of_week', 0))
            start_time = request.POST.get('start_time', '')
            end_time = request.POST.get('end_time', '')
            from datetime import datetime
            try:
                start_obj = datetime.strptime(start_time, '%H:%M').time()
                end_obj = datetime.strptime(end_time, '%H:%M').time()
                if start_obj >= end_obj:
                    messages.error(request, 'End time must be after start time.')
                else:
                    from vet.models import Availability
                    Availability.objects.create(
                        doctor=doctor,
                        day_of_week=day_of_week,
                        start_time=start_obj,
                        end_time=end_obj,
                        is_available=True,
                    )
                    messages.success(request, 'Availability slot added successfully.')
            except ValueError:
                messages.error(request, 'Invalid time format.')

        elif action == 'delete' and doctor:
            slot_id = request.POST.get('slot_id')
            from vet.models import Availability
            Availability.objects.filter(id=slot_id, doctor=doctor).delete()
            messages.success(request, 'Slot deleted.')

        elif action == 'toggle' and doctor:
            slot_id = request.POST.get('slot_id')
            from vet.models import Availability
            slot = Availability.objects.filter(id=slot_id, doctor=doctor).first()
            if slot:
                slot.is_available = not slot.is_available
                slot.save()
                messages.success(request, f'Slot {"enabled" if slot.is_available else "disabled"}.')

        elif action == 'edit' and doctor:
            slot_id = request.POST.get('slot_id')
            day_of_week = int(request.POST.get('day_of_week', 0))
            start_time = request.POST.get('start_time', '')
            end_time = request.POST.get('end_time', '')
            from datetime import datetime
            from vet.models import Availability
            slot = Availability.objects.filter(id=slot_id, doctor=doctor).first()
            if slot:
                try:
                    start_obj = datetime.strptime(start_time, '%H:%M').time()
                    end_obj = datetime.strptime(end_time, '%H:%M').time()
                    if start_obj >= end_obj:
                        messages.error(request, 'End time must be after start time.')
                    else:
                        slot.day_of_week = day_of_week
                        slot.start_time = start_obj
                        slot.end_time = end_obj
                        slot.save()
                        messages.success(request, 'Availability slot updated successfully.')
                except ValueError:
                    messages.error(request, 'Invalid time format.')

        return redirect('vet_availability')

    try:
        availabilities = doctor.availabilities.all() if doctor else []
    except Exception:
        availabilities = []

    context = {
        'doctor': doctor,
        'availabilities': availabilities,
    }
    return render(request, 'vet_availability.html', context)


@login_required
def vet_profile_settings(request):
    if request.user.role != 'DOCTOR':
        return render(request, '403.html', status=403)
    try:
        doctor = request.user.doctor_profile
    except Exception:
        doctor = None

    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', '').strip()
        user.last_name = request.POST.get('last_name', '').strip()
        user.email = request.POST.get('email', '').strip()
        user.country_code = request.POST.get('country_code', '+880').strip()
        user.phone = request.POST.get('phone', '').strip()
        user.save()

        if doctor:
            doctor.specialty = request.POST.get('specialty', doctor.specialty)
            doctor.consultation_fee = request.POST.get('consultation_fee', doctor.consultation_fee)
            doctor.qualification = request.POST.get('qualification', doctor.qualification)
            doctor.bio = request.POST.get('bio', doctor.bio)
            doctor.save()

        messages.success(request, 'Profile updated successfully.')
        return redirect('vet_profile_settings')

    context = {
        'doctor': doctor,
    }
    return render(request, 'vet_profile_settings.html', context)
