from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('attendance', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='leaveapplication',
            name='leave_type',
            field=models.CharField(
                choices=[
                    ('sick', 'Sick Leave'),
                    ('personal', 'Personal Leave'),
                    ('emergency', 'Emergency Leave')
                ],
                default='personal',
                max_length=20
            ),
        ),
    ] 