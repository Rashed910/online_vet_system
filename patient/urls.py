from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='patient_dashboard'),
    path('my-appointments/', views.my_appointments, name='my_appointments'),
    path('my-prescriptions/', views.my_prescriptions, name='my_prescriptions'),
    path('prescription/print/<int:history_id>/', views.print_prescription, name='print_prescription'),
    path('cancel-refund/', views.cancel_refund_list, name='cancel_refund_list'),
    path('manage-profile/', views.manage_profile, name='manage_profile'),
    path('profile/update/', views.update_patient_profile, name='update_patient_profile'),
]
