from django.urls import path
from . import views

urlpatterns = [
    path('', views.admin_dashboard, name='admin_dashboard'),
    path('doctors/', views.admin_doctors, name='admin_doctors'),
    path('patients/', views.admin_patients, name='admin_patients'),
    path('prescriptions/', views.admin_prescriptions, name='admin_prescriptions'),
    path('appointments/', views.admin_appointments, name='admin_appointments'),
    path('schedules/', views.admin_schedules, name='admin_schedules'),
    path('reports/', views.admin_reports, name='admin_reports'),
]
