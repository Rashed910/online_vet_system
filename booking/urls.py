from django.urls import path
from . import views

urlpatterns = [
    path('doctors/', views.doctors, name='booking_doctors'),
    path('booked-slots/', views.booked_slots, name='booked_slots'),
    path('book/', views.book_appointment, name='book_appointment'),
    path('booking-success/<int:appointment_id>/', views.booking_success, name='booking_success'),
    path('receipt/<int:appointment_id>/', views.receipt, name='receipt'),
    path('cancel/<int:appointment_id>/', views.cancel_appointment, name='cancel_appointment'),
    path('refund-slip/<int:refund_id>/', views.refund_slip, name='refund_slip'),
]
