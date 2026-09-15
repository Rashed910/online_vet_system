from django.contrib import admin
from patient.models import Patient, MedicalHistory, Prescription
from booking.models import Appointment
from django.utils.html import format_html
from django.urls import path
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import io


class MedicalHistoryInline(admin.TabularInline):
    model = MedicalHistory
    extra = 0
    readonly_fields = ('created_at',)
    fields = ('appointment', 'diagnosis', 'notes', 'medicines', 'dosage', 'frequency', 'duration', 'date', 'created_at')
    ordering = ('-date', '-created_at')

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('id','user', 'created_at', 'prescriptions_count')
    list_filter = ('species', 'created_at')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'pet_name', 'species')
    readonly_fields = ('created_at', 'prescriptions_display')
    inlines = [MedicalHistoryInline]
    fieldsets = (
        ('User Info', {'fields': ('user',)}),
        ('Pet Info', {'fields': ('pet_name', 'species', 'breed', 'age', 'weight')}),
        ('Medical History', {'fields': ('medical_history',)}),
        ('Prescriptions', {'fields': ('prescriptions_display',)}),
        ('Timestamps', {'fields': ('created_at',)}),
    )

    def prescriptions_count(self, obj):
        return Prescription.objects.filter(appointment__patient=obj).count()
    prescriptions_count.short_description = 'Prescriptions'

    def prescriptions_display(self, obj):
        prescriptions = Prescription.objects.filter(appointment__patient=obj).select_related('appointment').order_by('-created_at')
        if not prescriptions:
            return "No prescriptions"
        
        html = '<table style="width:100%; border-collapse:collapse;">'
        html += '<thead><tr style="background:#f5f5f5;">'
        html += '<th style="padding:8px; border:1px solid #ddd; text-align:left;">Appointment</th>'
        html += '<th style="padding:8px; border:1px solid #ddd; text-align:left;">Date</th>'
        html += '<th style="padding:8px; border:1px solid #ddd; text-align:left;">Medicines</th>'
        html += '<th style="padding:8px; border:1px solid #ddd; text-align:left;">Dosage</th>'
        html += '<th style="padding:8px; border:1px solid #ddd; text-align:left;">Frequency</th>'
        html += '<th style="padding:8px; border:1px solid #ddd; text-align:left;">Duration</th>'
        html += '</tr></thead><tbody>'
        
        for p in prescriptions:
            html += f'<tr>'
            html += f'<td style="padding:8px; border:1px solid #ddd;">{p.appointment}</td>'
            html += f'<td style="padding:8px; border:1px solid #ddd;">{p.appointment.date}</td>'
            html += f'<td style="padding:8px; border:1px solid #ddd;">{p.medicines}</td>'
            html += f'<td style="padding:8px; border:1px solid #ddd;">{p.dosage}</td>'
            html += f'<td style="padding:8px; border:1px solid #ddd;">{p.frequency}</td>'
            html += f'<td style="padding:8px; border:1px solid #ddd;">{p.duration}</td>'
            html += f'</tr>'
        
        html += '</tbody></table>'
        return format_html(html)
    prescriptions_display.short_description = 'Prescriptions'


@admin.register(MedicalHistory)
class MedicalHistoryAdmin(admin.ModelAdmin):
    list_display = ('patient', 'diagnosis_short', 'appointment', 'date', 'created_at', 'download_pdf')
    list_filter = ('date', 'created_at', 'patient__species')
    search_fields = ('patient__user__username', 'patient__user__first_name', 'patient__user__last_name', 'patient__pet_name', 'diagnosis', 'notes')
    readonly_fields = ('created_at',)
    exclude = ('medical_suggestion',)
    date_hierarchy = 'date'
    ordering = ('-date', '-created_at')
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:pk>/download-pdf/', self.admin_site.admin_view(self.download_pdf_view), name='medicalhistory_download_pdf'),
        ]
        return custom_urls + urls
    
    def download_pdf_view(self, request, pk):
        medical_history = get_object_or_404(MedicalHistory, pk=pk)
        return self.generate_medicalhistory_pdf(medical_history)
    
    def download_pdf(self, obj):
        return format_html(
            '<a class="button" href="{}">Download PDF</a>',
            f'{obj.pk}/download-pdf/'
        )
    download_pdf.short_description = 'PDF'
    
    def generate_medicalhistory_pdf(self, medical_history):
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=18, spaceAfter=6, alignment=TA_CENTER, textColor=colors.HexColor('#059669'))
        subtitle_style = ParagraphStyle('CustomSubtitle', parent=styles['Heading2'], fontSize=14, spaceAfter=12, alignment=TA_CENTER, textColor=colors.HexColor('#374151'))
        normal_style = ParagraphStyle('CustomNormal', parent=styles['Normal'], fontSize=10, spaceAfter=6, leading=14)
        section_style = ParagraphStyle('SectionStyle', parent=styles['Heading3'], fontSize=12, spaceBefore=12, spaceAfter=6, textColor=colors.HexColor('#059669'))
        
        appointment = medical_history.appointment
        patient = medical_history.patient
        doctor = appointment.doctor if appointment else None
        
        story = []
        
        # Header
        story.append(Paragraph("VetCare", title_style))
        story.append(Paragraph("Veterinary Prescription & Medical Report", subtitle_style))
        story.append(Spacer(1, 12))
        
        # Horizontal line
        story.append(Table([['']], colWidths=[17*cm], style=[('LINEBELOW', (0,0), (-1,-1), 2, colors.HexColor('#059669'))]))
        story.append(Spacer(1, 12))
        
        # Prescription info table
        info_data = [
            ['Medical Record ID:', f'#{medical_history.pk}'],
            ['Date Issued:', medical_history.created_at.strftime('%B %d, %Y')],
            ['Visit Date:', medical_history.date.strftime('%B %d, %Y')],
        ]
        
        if appointment:
            info_data.append(['Appointment Date:', appointment.date.strftime('%B %d, %Y')])
            info_data.append(['Appointment Time:', appointment.time.strftime('%I:%M %p')])
        
        info_table = Table(info_data, colWidths=[5*cm, 12*cm])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 12))
        
        # Patient & Doctor info
        story.append(Paragraph("Patient Information", section_style))
        patient_data = [
            ['Patient Name:', patient.user.get_full_name() or patient.user.username],
            ['Pet Name:', patient.pet_name],
            ['Species:', patient.species],
            ['Breed:', patient.breed or 'N/A'],
            ['Age:', f'{patient.age} years' if patient.age else 'N/A'],
            ['Weight:', f'{patient.weight} kg' if patient.weight else 'N/A'],
        ]
        patient_table = Table(patient_data, colWidths=[5*cm, 12*cm])
        patient_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(patient_table)
        story.append(Spacer(1, 12))
        
        if doctor:
            story.append(Paragraph("Prescribing Doctor", section_style))
            doctor_data = [
                ['Doctor Name:', doctor.user.get_full_name() or doctor.user.username],
                ['Specialty:', doctor.specialty],
                ['License:', doctor.license_number or 'N/A'],
            ]
            doctor_table = Table(doctor_data, colWidths=[5*cm, 12*cm])
            doctor_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(doctor_table)
            story.append(Spacer(1, 16))
        
        # Clinical Findings & Diagnosis
        story.append(Paragraph("Clinical Findings & Diagnosis", section_style))
        
        if medical_history.diagnosis:
            story.append(Paragraph("<b>Diagnosis:</b>", normal_style))
            story.append(Paragraph(medical_history.diagnosis, normal_style))
            story.append(Spacer(1, 8))
        
        if medical_history.medical_suggestion:
            story.append(Paragraph("<b>Medical Advice:</b>", normal_style))
            story.append(Paragraph(medical_history.medical_suggestion, normal_style))
            story.append(Spacer(1, 8))
        
        if medical_history.notes:
            story.append(Paragraph("<b>Additional Notes:</b>", normal_style))
            story.append(Paragraph(medical_history.notes, normal_style))
            story.append(Spacer(1, 12))
        
        # Prescribed Medicines
        story.append(Paragraph("Prescribed Medicines", section_style))
        
        med_data = [['Medicine', 'Dosage', 'Frequency', 'Duration', 'Notes']]
        med_data.append([
            medical_history.medicines or '—',
            medical_history.dosage or '—',
            medical_history.frequency or '—',
            medical_history.duration or '—',
            medical_history.notes or '—'
        ])
        
        med_table = Table(med_data, colWidths=[4*cm, 3*cm, 3*cm, 3*cm, 4*cm])
        med_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#059669')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0fdf4')]),
        ]))
        story.append(med_table)
        story.append(Spacer(1, 20))
        
        # Footer
        story.append(Paragraph("Important Notes", section_style))
        notes = [
            "Take medicines exactly as prescribed by your veterinarian.",
            "Complete the full course of antibiotics even if symptoms improve.",
            "Contact your vet immediately if any adverse reactions occur.",
            "Store medicines as directed (refrigerate if required).",
            "Keep all medicines out of reach of children and other pets.",
        ]
        for note in notes:
            story.append(Paragraph(f"• {note}", normal_style))
        
        story.append(Spacer(1, 24))
        
        # Signature line
        sig_data = [['', 'Veterinarian Signature', '', 'Date']]
        sig_table = Table(sig_data, colWidths=[2*cm, 5*cm, 5*cm, 5*cm])
        sig_table.setStyle(TableStyle([
            ('LINEABOVE', (1, 0), (1, 0), 1, colors.black),
            ('LINEABOVE', (3, 0), (3, 0), 1, colors.black),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('ALIGN', (3, 0), (3, 0), 'CENTER'),
            ('TOPPADDING', (0, 0), (-1, -1), 30),
        ]))
        story.append(sig_table)
        
        # Disclaimer
        story.append(Spacer(1, 24))
        disclaimer_style = ParagraphStyle('Disclaimer', parent=styles['Normal'], fontSize=8, textColor=colors.grey, alignment=TA_CENTER)
        story.append(Paragraph("Generated by VetCare Veterinary Management System | This is a computer-generated document.", disclaimer_style))
        
        doc.build(story)
        
        buffer.seek(0)
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="prescription_{medical_history.pk}_{medical_history.patient.pet_name}_{timezone.now().strftime("%Y%m%d")}.pdf"'
        return response
    
    def diagnosis_short(self, obj):
        return obj.diagnosis[:80] + '...' if len(obj.diagnosis) > 80 else obj.diagnosis
    diagnosis_short.short_description = 'Diagnosis'