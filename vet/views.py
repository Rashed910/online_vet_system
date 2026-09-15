from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from vet.models import Doctor, Availability
from patient.models import MedicalHistory
from django.contrib.auth import get_user_model
from booking.views import validate_phone_by_country
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
        today_slots = Availability.objects.filter(doctor=doctor, day_of_week=today_weekday, is_available=True).order_by('start_time')
        now_local = timezone.localtime(timezone.now())
        current_time = now_local.time()
        remaining_minutes = 0
        for slot in today_slots:
            if slot.start_time <= current_time < slot.end_time:
                remaining = datetime.combine(today, slot.end_time) - datetime.combine(today, current_time)
                remaining_minutes = int(remaining.total_seconds() / 60)
                break
        hours = remaining_minutes // 60
        minutes = remaining_minutes % 60
        working_time = f"{hours}h {minutes}m"
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
    from datetime import datetime
    from patient.models import MedicalHistory

    selected_date_str = request.GET.get('date', '').strip()
    selected_date = None
    if selected_date_str:
        try:
            selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        except ValueError:
            selected_date = None

    try:
        doctor = request.user.doctor_profile
        appointments = doctor.appointments.filter(
            payment__status='PAID',
            status__in=['CONFIRMED', 'COMPLETED'],
        ).select_related('patient__user', 'payment').order_by('date', 'time')
        if selected_date is not None:
            appointments = appointments.filter(date=selected_date)
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
        'selected_date': selected_date_str,
        'today': datetime.now().date(),
    }
    return render(request, 'vet_booked_appointments.html', context)


@login_required
def patient_medical_history(request):
    if request.user.role != 'DOCTOR':
        return render(request, '403.html', status=403)
    from datetime import datetime

    selected_date_str = request.GET.get('date', '').strip()
    selected_date = None
    if selected_date_str:
        try:
            selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        except ValueError:
            selected_date = None

    try:
        doctor = request.user.doctor_profile
        appointments = doctor.appointments.filter(status='COMPLETED').select_related('patient__user').prefetch_related('patient__medical_histories')
        if selected_date is not None:
            appointments = appointments.filter(date=selected_date)
    except Exception:
        doctor = None
        appointments = []

    context = {
        'doctor': doctor,
        'appointments': appointments,
        'selected_date': selected_date_str,
    }
    return render(request, 'vet_patient_history.html', context)


@login_required
def vet_prescriptions(request):
    if request.user.role != 'DOCTOR':
        return render(request, '403.html', status=403)
    try:
        doctor = request.user.doctor_profile
        prescriptions = MedicalHistory.objects.all().select_related('patient__user', 'appointment__doctor__user').order_by('-date', '-created_at')
    except Exception:
        doctor = None
        prescriptions = []

    context = {
        'doctor': doctor,
        'prescriptions': prescriptions,
    }
    return render(request, 'vet_prescriptions.html', context)


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

        if action == 'add_prescription':
            medicines = request.POST.get('medicines', '').strip()
            dosage = request.POST.get('dosage', '').strip()
            frequency = request.POST.get('frequency', '').strip()
            duration = request.POST.get('duration', '').strip()
            notes = request.POST.get('notes', '').strip()
            date_str = request.POST.get('date', '').strip()
            from datetime import datetime
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else appointment.date
            except ValueError:
                date_obj = appointment.date

            if medicines or dosage or frequency or duration:
                MedicalHistory.objects.update_or_create(
                    patient=patient,
                    appointment=appointment,
                    date=date_obj,
                    defaults={
                        'diagnosis': 'Consultation',
                        'notes': notes,
                        'medical_suggestion': '',
                        'medicines': medicines,
                        'dosage': dosage,
                        'frequency': frequency,
                        'duration': duration,
                    }
                )
                if appointment.status not in ['COMPLETED', 'CANCELLED']:
                    appointment.status = 'COMPLETED'
                    appointment.save()
                messages.success(request, 'Prescription saved successfully.')

        elif action == 'edit_prescription':
            history_id = request.POST.get('history_id')
            history = MedicalHistory.objects.filter(id=history_id, patient=patient).first()
            if history:
                history.medicines = request.POST.get('medicines', history.medicines).strip()
                history.dosage = request.POST.get('dosage', history.dosage).strip()
                history.frequency = request.POST.get('frequency', history.frequency).strip()
                history.duration = request.POST.get('duration', history.duration).strip()
                history.notes = request.POST.get('notes', history.notes).strip()
                date_str = request.POST.get('date', '').strip()
                if date_str:
                    try:
                        history.date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    except ValueError:
                        pass
                history.save()
                messages.success(request, 'Prescription updated successfully.')

        elif action == 'delete_prescription':
            history_id = request.POST.get('history_id')
            MedicalHistory.objects.filter(id=history_id, patient=patient).delete()
            messages.success(request, 'Prescription deleted.')

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
        'existing_prescription': patient.medical_histories.filter(appointment=appointment).first(),
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

    try:
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
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


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
            from vet.models import Availability
            # Check if day already exists for this doctor
            if Availability.objects.filter(doctor=doctor, day_of_week=day_of_week).exists():
                messages.error(request, 'Availability for this day already exists. Please edit the existing slot instead.')
            else:
                try:
                    start_obj = datetime.strptime(start_time, '%H:%M').time()
                    end_obj = datetime.strptime(end_time, '%H:%M').time()
                    if start_obj >= end_obj:
                        messages.error(request, 'End time must be after start time.')
                    else:
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

    user = request.user

    if request.method == 'POST':
        orig_first = user.first_name
        orig_last = user.last_name
        orig_email = user.email
        orig_country = user.country_code
        orig_phone = user.phone
        orig_address = user.address

        user.first_name = request.POST.get('first_name', '').strip()
        user.last_name = request.POST.get('last_name', '').strip()
        user.email = request.POST.get('email', '').strip()
        user.country_code = request.POST.get('country_code', '+880').strip()
        phone = request.POST.get('phone', '').strip()
        user.address = request.POST.get('address', '').strip()

        if phone:
            phone_digits = ''.join(c for c in phone if c.isdigit())
            country_digits = ''.join(c for c in user.country_code if c.isdigit())
            if phone_digits.startswith('0'):
                phone_digits = phone_digits[1:]
            valid, err = validate_phone_by_country(phone_digits, user.country_code)
            if not valid:
                messages.error(request, err)
                return redirect('vet_profile_settings')
            full_phone = '+' + country_digits + phone_digits
            if User.objects.filter(phone=full_phone).exclude(id=user.id).exists():
                messages.error(request, 'This phone number is already used by another account.')
                return redirect('vet_profile_settings')
            user.phone = full_phone
        else:
            user.phone = ''

        user_changed = any([
            user.first_name != orig_first,
            user.last_name != orig_last,
            user.email != orig_email,
            user.country_code != orig_country,
            (user.phone or '') != (orig_phone or ''),
            (user.address or '') != (orig_address or ''),
        ])
        user.save()

        doctor_changed = False
        if doctor:
            orig_specialty = doctor.specialty
            orig_fee = doctor.consultation_fee
            orig_qual = doctor.qualification
            orig_bio = doctor.bio

            doctor.specialty = request.POST.get('specialty', doctor.specialty)
            doctor.consultation_fee = request.POST.get('consultation_fee', doctor.consultation_fee)
            doctor.qualification = request.POST.get('qualification', doctor.qualification)
            doctor.bio = request.POST.get('bio', doctor.bio)

            doctor_changed = any([
                doctor.specialty != orig_specialty,
                str(doctor.consultation_fee) != str(orig_fee),
                doctor.qualification != orig_qual,
                doctor.bio != orig_bio,
            ])
            doctor.save()

        if user_changed or doctor_changed:
            messages.success(request, 'Profile updated successfully.')
        else:
            messages.info(request, 'No changes were made to your profile.')
        return redirect('vet_profile_settings')

    cc = user.country_code or '+880'
    context = {
        'doctor': doctor,
        'phone_display': (user.phone[len(cc):] if user.phone and user.phone.startswith(cc) else (user.phone or '')),
    }
    return render(request, 'vet_profile_settings.html', context)
