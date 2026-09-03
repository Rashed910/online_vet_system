from django.db import migrations, models


def set_empty_phones_to_null(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    User.objects.filter(phone='').update(phone=None)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_user_country_code'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='phone',
            field=models.CharField(max_length=20, blank=True, null=True),
        ),
        migrations.RunPython(set_empty_phones_to_null, reverse_code=migrations.RunPython.noop),
        migrations.AlterField(
            model_name='user',
            name='phone',
            field=models.CharField(max_length=20, unique=True, blank=True, null=True),
        ),
    ]
