from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('attendance', '0002_leaveapplication_leave_type'),
        ('attendance', '0002_add_leave_type'),
    ]

    operations = [
        # No operations needed since both migrations are trying to add the same field
    ] 