from django.core.management.base import BaseCommand
from attendance.models import Student, ClassStudent

class Command(BaseCommand):
    help = 'Check if a specific student exists and their enrollment status'

    def handle(self, *args, **options):
        # Check for Suhada
        students = Student.objects.filter(first_name__icontains='Suhada')
        self.stdout.write(f"Found {students.count()} students with name 'Suhada'")
        
        for student in students:
            self.stdout.write(f"\nStudent details:")
            self.stdout.write(f"ID: {student.id}")
            self.stdout.write(f"Enrollment: {student.enrollment_number}")
            self.stdout.write(f"Name: {student.first_name} {student.last_name}")
            
            # Check class enrollments
            enrollments = ClassStudent.objects.filter(student=student)
            self.stdout.write(f"Enrolled in {enrollments.count()} classes:")
            for enrollment in enrollments:
                self.stdout.write(f"- {enrollment.classIns.name}") 