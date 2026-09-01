from django.urls import path
from . import views

urlpatterns = [
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/vet-management/', views.vet_management, name='admin_vet_management'),
    path('admin/patient-management/', views.patient_management, name='admin_patient_management'),
    path('admin/routine-control/', views.routine_control, name='admin_routine_control'),
    path('admin/reports/', views.reports, name='admin_reports'),
    path('admin/appointments/', views.admin_appointments, name='admin_appointments'),
    path('admin/payments/', views.admin_payments, name='admin_payments'),
    path('admin/payments/<int:payment_id>/approve/', views.approve_payment, name='approve_payment'),
    path('admin/export/<str:report_type>/', views.export_report, name='export_report'),
]