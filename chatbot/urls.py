from django.urls import path
from . import views

urlpatterns = [
    path('chatbot/', views.chatbot_view, name='chatbot'),
    path('chatbot/api/', views.chat_api, name='chat_api'),
]
