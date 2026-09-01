from django.urls import path
from . import views

urlpatterns = [
    path('vet-dashboard/', views.vet_dashboard, name='vet_dashboard'),
    path('vet/booked-appointments/', views.booked_appointments, name='vet_booked_appointments'),
    path('vet/patient-history/', views.patient_medical_history, name='vet_patient_history'),
    path('vet/view-patient/<int:appointment_id>/', views.view_patient, name='vet_view_patient'),
    path('vet/availability/', views.manage_availability, name='vet_availability'),
    path('vet/profile-settings/', views.vet_profile_settings, name='vet_profile_settings'),
    path('vet/api/update-status/<int:appointment_id>/', views.api_update_status, name='api_update_status'),
]
