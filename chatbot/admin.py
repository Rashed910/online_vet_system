from django.contrib import admin
from .models import DiseaseInfo, SymptomKeyword, ChatMessage

@admin.register(DiseaseInfo)
class DiseaseInfoAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'is_common', 'created_at')
    list_filter = ('category', 'is_common', 'created_at')
    search_fields = ('name', 'description', 'symptoms')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)

@admin.register(SymptomKeyword)
class SymptomKeywordAdmin(admin.ModelAdmin):
    list_display = ('keyword', 'disease')
    list_filter = ('disease__category',)
    search_fields = ('keyword', 'disease__name')
    ordering = ('keyword',)

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'sender', 'message', 'matched_disease', 'created_at')
    list_filter = ('sender', 'created_at')
    search_fields = ('session_id', 'message', 'matched_disease__name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
