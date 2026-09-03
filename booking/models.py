from django.db import models
from django.conf import settings

class Appointment(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    )
    patient = models.ForeignKey('patient.Patient', on_delete=models.CASCADE, related_name='appointments')
    doctor = models.ForeignKey('vet.Doctor', on_delete=models.CASCADE, related_name='appointments')
    date = models.DateField()
    time = models.TimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    fee = models.DecimalField(max_digits=8, decimal_places=2, default=1500.00)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.patient.pet_name} - {self.doctor} - {self.date} {self.time}"

    class Meta:
        ordering = ['-date', '-time']

class Payment(models.Model):
    PAYMENT_STATUS = (
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('REFUNDED', 'Refunded'),
        ('FAILED', 'Failed'),
    )
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name='payment')
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='PENDING')
    transaction_id = models.CharField(max_length=100, blank=True)
    payment_method = models.CharField(max_length=50, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Payment for {self.appointment} - {self.amount} ({self.status})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.status == 'PAID' and self.appointment_id and self.appointment.status == 'PENDING':
            self.appointment.status = 'CONFIRMED'
            self.appointment.save(update_fields=['status'])
        elif self.status == 'FAILED' and self.appointment_id and self.appointment.status == 'PENDING':
            self.appointment.status = 'CANCELLED'
            self.appointment.save(update_fields=['status'])
        elif self.status == 'REFUNDED' and self.appointment_id and self.appointment.status not in ['CANCELLED']:
            self.appointment.status = 'CANCELLED'
            self.appointment.save(update_fields=['status'])

class Refund(models.Model):
    REFUND_STATUS = (
        ('PENDING', 'Pending'),
        ('PROCESSED', 'Processed'),
        ('REJECTED', 'Rejected'),
    )
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name='refund')
    original_amount = models.DecimalField(max_digits=8, decimal_places=2)
    deduction_percentage = models.IntegerField(default=10)
    refund_amount = models.DecimalField(max_digits=8, decimal_places=2)
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=REFUND_STATUS, default='PENDING')
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Refund for {self.appointment} - {self.refund_amount} ({self.status})"

    def save(self, *args, **kwargs):
        self.refund_amount = self.original_amount * (100 - self.deduction_percentage) / 100
        super().save(*args, **kwargs)
