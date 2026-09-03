from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('home.urls')),
    path('', include('accounts.urls')),
    path('', include('patient.urls')),
    path('', include('booking.urls')),
    path('', include('chatbot.urls')),
    path('', include('vet.urls')),
]
