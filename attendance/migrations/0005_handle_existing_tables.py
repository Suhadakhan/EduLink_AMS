from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('attendance', '0004_add_feedback_timestamps'),
    ]

    operations = [
        migrations.RunSQL(
            # Forward SQL - do nothing if tables exist
            """
            SELECT 1;
            """,
            # Reverse SQL - do nothing
            "SELECT 1;"
        ),
    ] 