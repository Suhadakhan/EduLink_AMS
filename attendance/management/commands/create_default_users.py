from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from attendance.models import UserProfile, Department

class Command(BaseCommand):
    help = 'Creates default admin user'

    def handle(self, *args, **kwargs):
        try:
            # Create admin user if it doesn't exist
            if not User.objects.filter(username='admin').exists():
                admin_user = User.objects.create_superuser(
                    username='admin',
                    email='admin@example.com',
                    password='admin123',
                    first_name='Admin',
                    last_name='User'
                )

                # Create department if it doesn't exist
                department, _ = Department.objects.get_or_create(
                    name='Administration',
                    defaults={
                        'description': 'Admin Department',
                        'status': 1
                    }
                )

                # Create admin profile
                UserProfile.objects.create(
                    user=admin_user,
                    user_type=1,  # Admin type
                    department=department,
                    contact='1234567890'
                )

                self.stdout.write(self.style.SUCCESS('Successfully created admin user'))
                self.stdout.write(self.style.SUCCESS('Username: admin'))
                self.stdout.write(self.style.SUCCESS('Password: admin123'))
            else:
                self.stdout.write(self.style.WARNING('Admin user already exists'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating admin user: {str(e)}')) 