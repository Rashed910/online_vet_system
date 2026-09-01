from django.db import migrations
from datetime import time


def seed_doctors(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    Doctor = apps.get_model('vet', 'Doctor')
    Availability = apps.get_model('vet', 'Availability')

    doctors_data = [
        {
            'username': 'sarah.jenkins',
            'first_name': 'Sarah',
            'last_name': 'Jenkins',
            'email': 'sarah@vetcure.com',
            'specialty': 'Avian Specialist (Macaw & Parrot)',
            'experience_years': 8,
            'consultation_fee': 1500.00,
            'bio': 'Specialized in parrot and macaw care, including behavioral therapy and nutritional planning.',
        },
        {
            'username': 'michael.vance',
            'first_name': 'Michael',
            'last_name': 'Vance',
            'email': 'michael@vetcure.com',
            'specialty': 'Exotic Bird Surgeon',
            'experience_years': 12,
            'consultation_fee': 2500.00,
            'bio': 'Board-certified surgeon specializing in complex avian procedures and emergency care.',
        },
        {
            'username': 'ayesha.rahman',
            'first_name': 'Ayesha',
            'last_name': 'Rahman',
            'email': 'ayesha@vetcure.com',
            'specialty': 'General Avian Physician',
            'experience_years': 5,
            'consultation_fee': 1200.00,
            'bio': 'General avian health, routine checkups, and preventive care for companion birds.',
        },
        {
            'username': 'robert.chen',
            'first_name': 'Robert',
            'last_name': 'Chen',
            'email': 'robert@vetcure.com',
            'specialty': 'Small Pet Specialist',
            'experience_years': 10,
            'consultation_fee': 1800.00,
            'bio': 'Expert in rabbit, guinea pig, ferret, and small mammal care with a focus on holistic treatment.',
        },
        {
            'username': 'emma.wilson',
            'first_name': 'Emma',
            'last_name': 'Wilson',
            'email': 'emma@vetcure.com',
            'specialty': 'Exotic Pet Specialist',
            'experience_years': 7,
            'consultation_fee': 2000.00,
            'bio': 'Specializes in reptiles, amphibians, and exotic pets. Experienced in herpetology and wildlife medicine.',
        },
        {
            'username': 'david.park',
            'first_name': 'David',
            'last_name': 'Park',
            'email': 'david@vetcure.com',
            'specialty': 'General Practitioner',
            'experience_years': 6,
            'consultation_fee': 1000.00,
            'bio': 'General veterinary practice covering routine checkups, vaccinations, and emergency consultations for all pet types.',
        },
    ]

    for d in doctors_data:
        user = User.objects.filter(username=d['username']).first()
        if not user:
            user = User.objects.create_user(
                username=d['username'],
                email=d['email'],
                password='doc123!',
                first_name=d['first_name'],
                last_name=d['last_name'],
                role='DOCTOR',
            )
        else:
            user.role = 'DOCTOR'
            user.save()
        Doctor.objects.get_or_create(
            user=user,
            defaults={
                'specialty': d['specialty'],
                'experience_years': d['experience_years'],
                'qualification': 'DVM, Licensed Veterinarian',
                'license_number': 'DOC-{}'.format(d['username'].split('.')[0].upper()),
                'consultation_fee': d['consultation_fee'],
                'bio': d['bio'],
                'is_active': True,
            },
        )

    # Add availability (Mon-Fri 9AM-5PM) for all doctors
    for doctor in Doctor.objects.all():
        for day in range(5):
            Availability.objects.get_or_create(
                doctor=doctor,
                day_of_week=day,
                defaults={
                    'start_time': time(9, 0),
                    'end_time': time(17, 0),
                    'is_available': True,
                },
            )


def unseed_doctors(apps, schema_editor):
    Doctor = apps.get_model('vet', 'Doctor')
    Availability = apps.get_model('vet', 'Availability')
    Availability.objects.all().delete()
    Doctor.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0002_initial'),
        ('vet', '0001_initial'),
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_doctors, unseed_doctors),
    ]
