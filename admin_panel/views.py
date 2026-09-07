from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import datetime, date, timedelta
from vet.models import Doctor, Availability
from patient.models import Patient, MedicalHistory
from booking.models import Appointment, Payment, Refund

@login_required
def admin_dashboard(request):
    if request.user.role != 'ADMIN':
        return render(request, '403.html', status=403)
    
    today = timezone.now().date()
    
    # Statistics
    total_patients = Patient.objects.count()
    total_doctors = Doctor.objects.filter(is_active=True).count()
    total_appointments = Appointment.objects.count()
    total_prescriptions = MedicalHistory.objects.count()
    
    # Appointment stats
    pending_appointments = Appointment.objects.filter(status='PENDING').count()
    confirmed_appointments = Appointment.objects.filter(status='CONFIRMED').count()
    completed_appointments = Appointment.objects.filter(status='COMPLETED').count()
    cancelled_appointments = Appointment.objects.filter(status='CANCELLED').count()
    
    # Payment stats
    total_revenue = Payment.objects.filter(status='PAID').aggregate(total=Sum('amount'))['total'] or 0
    pending_payments = Payment.objects.filter(status='PENDING').count()
    
    # Refund stats
    total_refunded = Refund.objects.filter(status='PROCESSED').aggregate(total=Sum('refund_amount'))['total'] or 0
    pending_refunds = Refund.objects.filter(status='PENDING').count()
    
    # Recent appointments
    recent_appointments = Appointment.objects.select_related('patient__user', 'doctor__user', 'payment').order_by('-created_at')[:10]
    
    # Recent payments
    recent_payments = Payment.objects.select_related('appointment__patient__user', 'appointment__doctor__user').order_by('-created_at')[:10]
    
    context = {
        'total_patients': total_patients,
        'total_doctors': total_doctors,
        'total_appointments': total_appointments,
        'total_prescriptions': total_prescriptions,
        'pending_appointments': pending_appointments,
        'confirmed_appointments': confirmed_appointments,
        'completed_appointments': completed_appointments,
        'cancelled_appointments': cancelled_appointments,
        'total_revenue': total_revenue,
        'pending_payments': pending_payments,
        'total_refunded': total_refunded,
        'pending_refunds': pending_refunds,
        'recent_appointments': recent_appointments,
        'recent_payments': recent_payments,
    }
    return render(request, 'admin/dashboard.html', context)


@login_required
def admin_doctors(request):
    if request.user.role != 'ADMIN':
        return render(request, '403.html', status=403)
    
    doctors = Doctor.objects.select_related('user').all().order_by('-created_at')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add':
            username = request.POST.get('username', '').strip()
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            email = request.POST.get('email', '').strip()
            phone = request.POST.get('phone', '').strip()
            specialty = request.POST.get('specialty', '').strip()
            experience_years = request.POST.get('experience_years', '').strip()
            qualification = request.POST.get('qualification', '').strip()
            license_number = request.POST.get('license_number', '').strip()
            consultation_fee = request.POST.get('consultation_fee', '').strip()
            bio = request.POST.get('bio', '').strip()
            password = request.POST.get('password', '').strip()
            
            if not all([username, first_name, last_name, email, phone, specialty, password]):
                messages.error(request, 'Please fill in all required fields.')
                return redirect('admin_doctors')
            
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Username already exists. Please choose a unique username.')
                return redirect('admin_doctors')
            
            if User.objects.filter(email=email).exists():
                messages.error(request, 'Email already exists.')
                return redirect('admin_doctors')
            
            user = User.objects.create_user(
                username=username,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                role='DOCTOR',
                password=password
            )
            
            Doctor.objects.create(
                user=user,
                specialty=specialty,
                experience_years=int(experience_years) if experience_years else 0,
                qualification=qualification,
                license_number=license_number,
                consultation_fee=float(consultation_fee) if consultation_fee else 1500.00,
                bio=bio
            )
            
            messages.success(request, f'Doctor {first_name} {last_name} added successfully.')
            return redirect('admin_doctors')
        
        elif action == 'edit':
            doctor_id = request.POST.get('doctor_id')
            doctor = get_object_or_404(Doctor, id=doctor_id)
            username = request.POST.get('username', '').strip()
            
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            if User.objects.filter(username=username).exclude(id=doctor.user.id).exists():
                messages.error(request, 'Username already exists. Please choose a unique username.')
                return redirect('admin_doctors')
            
            doctor.user.username = username
            doctor.user.first_name = request.POST.get('first_name', '').strip()
            doctor.user.last_name = request.POST.get('last_name', '').strip()
            doctor.user.email = request.POST.get('email', '').strip()
            doctor.user.phone = request.POST.get('phone', '').strip()
            doctor.specialty = request.POST.get('specialty', '').strip()
            doctor.experience_years = int(request.POST.get('experience_years', 0))
            doctor.qualification = request.POST.get('qualification', '').strip()
            doctor.license_number = request.POST.get('license_number', '').strip()
            doctor.consultation_fee = float(request.POST.get('consultation_fee', 1500.00))
            doctor.bio = request.POST.get('bio', '').strip()
            doctor.is_active = 'is_active' in request.POST
            
            doctor.user.save()
            doctor.save()
            
            messages.success(request, f'Doctor {doctor.user.get_full_name()} updated successfully.')
            return redirect('admin_doctors')
        
        elif action == 'delete':
            doctor_id = request.POST.get('doctor_id')
            doctor = get_object_or_404(Doctor, id=doctor_id)
            name = doctor.user.get_full_name()
            doctor.user.delete()
            messages.success(request, f'Doctor {name} deleted successfully.')
            return redirect('admin_doctors')
    
    context = {
        'doctors': doctors,
    }
    return render(request, 'admin/doctors.html', context)


@login_required
def admin_patients(request):
    if request.user.role != 'ADMIN':
        return render(request, '403.html', status=403)
    
    patients = Patient.objects.select_related('user').all().order_by('-created_at')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add':
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            email = request.POST.get('email', '').strip()
            phone = request.POST.get('phone', '').strip()
            address = request.POST.get('address', '').strip()
            
            if not all([first_name, last_name, email, phone]):
                messages.error(request, 'Please fill in all required fields.')
                return redirect('admin_patients')
            
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            if User.objects.filter(email=email).exists():
                messages.error(request, 'Email already exists.')
                return redirect('admin_patients')
            
            user = User.objects.create_user(
                username=email,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                address=address,
                role='PATIENT',
                password='patient123'
            )
            
            Patient.objects.create(user=user)
            messages.success(request, f'Patient {first_name} {last_name} added successfully.')
            return redirect('admin_patients')
        
        elif action == 'edit':
            patient_id = request.POST.get('patient_id')
            patient = get_object_or_404(Patient, id=patient_id)
            
            patient.user.first_name = request.POST.get('first_name', '').strip()
            patient.user.last_name = request.POST.get('last_name', '').strip()
            patient.user.email = request.POST.get('email', '').strip()
            patient.user.phone = request.POST.get('phone', '').strip()
            patient.user.address = request.POST.get('address', '').strip()
            patient.user.save()
            
            messages.success(request, f'Patient {patient.user.get_full_name()} updated successfully.')
            return redirect('admin_patients')
        
        elif action == 'delete':
            patient_id = request.POST.get('patient_id')
            patient = get_object_or_404(Patient, id=patient_id)
            name = patient.user.get_full_name()
            patient.user.delete()
            messages.success(request, f'Patient {name} deleted successfully.')
            return redirect('admin_patients')
    
    context = {
        'patients': patients,
    }
    return render(request, 'admin/patients.html', context)


@login_required
def admin_prescriptions(request):
    if request.user.role != 'ADMIN':
        return render(request, '403.html', status=403)
    
    prescriptions = MedicalHistory.objects.select_related('patient__user', 'appointment__doctor__user').order_by('-created_at')
    
    context = {
        'prescriptions': prescriptions,
    }
    return render(request, 'admin/prescriptions.html', context)


@login_required
def admin_appointments(request):
    if request.user.role != 'ADMIN':
        return render(request, '403.html', status=403)
    
    appointments = Appointment.objects.select_related('patient__user', 'doctor__user', 'payment').order_by('-date', '-time')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_status':
            appointment_id = request.POST.get('appointment_id')
            new_status = request.POST.get('status')
            appointment = get_object_or_404(Appointment, id=appointment_id)
            appointment.status = new_status
            appointment.save()
            messages.success(request, f'Appointment status updated to {new_status}.')
    
    context = {
        'appointments': appointments,
    }
    return render(request, 'admin/appointments.html', context)


@login_required
def admin_schedules(request):
    if request.user.role != 'ADMIN':
        return render(request, '403.html', status=403)
    
    doctors = Doctor.objects.select_related('user').all().order_by('user__first_name')
    selected_doctor_id = request.GET.get('doctor_id')
    selected_doctor = None
    availabilities = None
    
    if selected_doctor_id:
        selected_doctor = get_object_or_404(Doctor, id=selected_doctor_id)
        availabilities = Availability.objects.filter(doctor=selected_doctor).order_by('day_of_week', 'start_time')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add':
            doctor_id = request.POST.get('doctor_id')
            day_of_week = request.POST.get('day_of_week')
            start_time = request.POST.get('start_time')
            end_time = request.POST.get('end_time')
            doctor = get_object_or_404(Doctor, id=doctor_id)
            
            Availability.objects.create(
                doctor=doctor,
                day_of_week=int(day_of_week),
                start_time=start_time,
                end_time=end_time,
                is_available=True
            )
            messages.success(request, f'Schedule added for {doctor.user.get_full_name()}.')
            return redirect(f'{request.path}?doctor_id={doctor_id}')
        
        elif action == 'delete':
            availability_id = request.POST.get('availability_id')
            availability = get_object_or_404(Availability, id=availability_id)
            doctor_id = availability.doctor.id
            availability.delete()
            messages.success(request, 'Schedule removed successfully.')
            return redirect(f'{request.path}?doctor_id={doctor_id}')
    
    context = {
        'doctors': doctors,
        'selected_doctor': selected_doctor,
        'availabilities': availabilities,
        'day_choices': Availability.DAY_CHOICES,
    }
    return render(request, 'admin/schedules.html', context)


@login_required
def admin_reports(request):
    if request.user.role != 'ADMIN':
        return render(request, '403.html', status=403)
    
    report_type = request.GET.get('type', 'daily')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    
    today = timezone.now().date()
    
    if report_type == 'daily' and not start_date:
        start_date = today
        end_date = today
    elif report_type == 'weekly' and not start_date:
        start_date = today - timedelta(days=6)
        end_date = today
    elif report_type == 'monthly' and not start_date:
        start_date = today - timedelta(days=29)
        end_date = today
    elif report_type == 'custom' and not start_date:
        start_date = today - timedelta(days=30)
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
    
    appointment_ids = appointments.values_list('id', flat=True)
    payments = Payment.objects.filter(appointment_id__in=appointment_ids, status='PAID')
    total_revenue = payments.aggregate(total=Sum('amount'))['total'] or 0
    
    refunds = Refund.objects.filter(appointment_id__in=appointment_ids, status='PROCESSED')
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
    }
    return render(request, 'admin/reports.html', context)
