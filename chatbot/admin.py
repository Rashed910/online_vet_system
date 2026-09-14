from django.contrib import admin
from .models import ChatMessage

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'session_id', 'sender', 'message', 'matched_disease', 'created_at')
    list_filter = ('sender', 'created_at')
    search_fields = ('session_id', 'message', 'matched_disease__name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)