from django.db import models
from django.conf import settings

class Doctor(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='doctor_profile')
    specialty = models.CharField(max_length=100)
    experience_years = models.IntegerField(default=0)
    qualification = models.CharField(max_length=200, blank=True)
    license_number = models.CharField(max_length=50, blank=True)
    consultation_fee = models.DecimalField(max_digits=8, decimal_places=2, default=1500.00)
    bio = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Dr. {self.user.get_full_name()} - {self.specialty}"

class Availability(models.Model):
    DAY_CHOICES = (
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    )
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='availabilities')
    day_of_week = models.IntegerField(choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.doctor} - {self.get_day_of_week_display()} {self.start_time}-{self.end_time}"

    class Meta:
        unique_together = ('doctor', 'day_of_week', 'start_time')
