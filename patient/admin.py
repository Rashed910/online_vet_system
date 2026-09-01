from django.contrib import admin
from .models import Patient, MedicalHistory, Prescription

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('pet_name', 'species', 'breed', 'age', 'user', 'created_at')
    list_filter = ('species', 'created_at')
    search_fields = ('pet_name', 'user__username', 'user__email')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)

@admin.register(MedicalHistory)
class MedicalHistoryAdmin(admin.ModelAdmin):
    list_display = ('patient', 'date', 'diagnosis')
    list_filter = ('date',)
    search_fields = ('patient__pet_name', 'diagnosis')
    ordering = ('-date',)

@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ('appointment', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('appointment__patient__pet_name', 'medicines')
    ordering = ('-created_at',)
