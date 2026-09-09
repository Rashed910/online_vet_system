from django.shortcuts import render
from django.db.models import Q
from vet.models import Doctor

def index(request):
    doctor_search = request.GET.get('doctor_search', '').strip()
    
    doctors = Doctor.objects.filter(
        is_active=True,
    ).select_related('user').order_by('user__first_name')
    
    specialties = list(Doctor.objects.filter(is_active=True)
                       .exclude(specialty__exact='')
                       .values_list('specialty', flat=True)
                       .distinct().order_by())
    
    if doctor_search:
        doctors = doctors.filter(
            Q(specialty__icontains=doctor_search) | Q(user__first_name__icontains=doctor_search) | Q(user__last_name__icontains=doctor_search) | Q(qualification__icontains=doctor_search)
        )
    
    doctors = doctors[:6]
    
    doctor_data = []
    for doc in doctors:
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
        'doctor_search': doctor_search,
        'specialties': specialties,
    }
    return render(request, 'index.html', context)

def privacy_policy(request):
    return render(request, 'privacy_policy.html')

def terms_of_service(request):
    return render(request, 'terms_of_service.html')

def contact(request):
    return render(request, 'contact.html')
