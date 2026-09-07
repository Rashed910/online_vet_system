from django.contrib import admin
from django.urls import path, include
from admin_panel.admin import admin_reports_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('admin/reports/', admin_reports_view, name='admin_reports'),
    path('', include('home.urls')),
    path('', include('accounts.urls')),
    path('', include('patient.urls')),
    path('', include('booking.urls')),
    path('', include('chatbot.urls')),
    path('', include('vet.urls')),
]
