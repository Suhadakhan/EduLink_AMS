import os
import django

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ams.settings')

# Setup Django
django.setup()

from django.contrib.auth.models import User

# Get the admin user
admin_user = User.objects.get(username='admin')

# Set a new password
admin_user.set_password('newpassword123')
admin_user.save()

print("Admin password reset to 'newpassword123'")