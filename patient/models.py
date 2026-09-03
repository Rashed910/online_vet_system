from django.db import models
from django.conf import settings

class Patient(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='patient_profile')
    pet_name = models.CharField(max_length=100)
    species = models.CharField(max_length=100)
    breed = models.CharField(max_length=100, blank=True)
    age = models.IntegerField(null=True, blank=True)
    weight = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    medical_history = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.user.email}"

class MedicalHistory(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='medical_histories')
    appointment = models.ForeignKey('booking.Appointment', on_delete=models.SET_NULL, null=True, blank=True, related_name='medical_histories')
    diagnosis = models.TextField()
    notes = models.TextField(blank=True)
    medical_suggestion = models.TextField(blank=True)
    medicines = models.TextField(blank=True)
    dosage = models.TextField(blank=True)
    frequency = models.CharField(max_length=100, blank=True)
    duration = models.CharField(max_length=100, blank=True)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient.user.get_full_name() or self.patient.user.username} - {self.diagnosis[:50]} - {self.date}"

class Prescription(models.Model):
    appointment = models.ForeignKey('booking.Appointment', on_delete=models.CASCADE, related_name='prescriptions')
    medicines = models.TextField()
    dosage = models.TextField()
    frequency = models.CharField(max_length=100, blank=True)
    duration = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Prescription for {self.appointment}"
