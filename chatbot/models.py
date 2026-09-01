from django.db import models

class DiseaseInfo(models.Model):
    CATEGORY_CHOICES = (
        ('VIRAL', 'Viral'),
        ('BACTERIAL', 'Bacterial'),
        ('FUNGAL', 'Fungal'),
        ('PARASITIC', 'Parasitic'),
        ('NUTRITIONAL', 'Nutritional'),
        ('BEHAVIORAL', 'Behavioral'),
        ('OTHER', 'Other'),
    )
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    description = models.TextField()
    symptoms = models.TextField()
    prevention = models.TextField()
    emergency_signs = models.TextField(blank=True)
    is_common = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class SymptomKeyword(models.Model):
    disease = models.ForeignKey(DiseaseInfo, on_delete=models.CASCADE, related_name='keywords')
    keyword = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.keyword} -> {self.disease.name}"

    class Meta:
        unique_together = ('disease', 'keyword')

class ChatMessage(models.Model):
    SENDER_CHOICES = (
        ('USER', 'User'),
        ('BOT', 'Bot'),
    )
    session_id = models.CharField(max_length=100)
    sender = models.CharField(max_length=10, choices=SENDER_CHOICES)
    message = models.TextField()
    matched_disease = models.ForeignKey(DiseaseInfo, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender}: {self.message[:50]}"

    class Meta:
        ordering = ['created_at']
