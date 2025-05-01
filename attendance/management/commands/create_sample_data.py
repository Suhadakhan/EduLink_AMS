from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from attendance.models import Course, Department, Class, Student, UserProfile, ClassStudent, LeaveApplication, Attendance, Feedback
from datetime import datetime, timedelta
import random

class Command(BaseCommand):
    help = 'Creates sample data for the attendance system'

    def handle(self, *args, **kwargs):
        try:
            # Create Department
            department = Department.objects.get_or_create(
                name='Computer Science',
                defaults={
                    'description': 'Department of Computer Science',
                    'status': 1
                }
            )[0]

            # Create Courses
            courses_data = [
                {
                    'name': 'B.Tech Computer Science',
                    'description': 'Bachelor of Technology in Computer Science',
                },
                {
                    'name': 'BCA',
                    'description': 'Bachelor of Computer Applications',
                },
                {
                    'name': 'MCA',
                    'description': 'Master of Computer Applications',
                }
            ]

            created_courses = []
            for course_data in courses_data:
                course = Course.objects.get_or_create(
                    name=course_data['name'],
                    defaults={
                        'department': department,
                        'description': course_data['description'],
                        'status': 1
                    }
                )[0]
                created_courses.append(course)

            # Create Faculty Users
            faculty_data = [
                {'username': 'faculty1', 'first_name': 'John', 'last_name': 'Doe'},
                {'username': 'faculty2', 'first_name': 'Jane', 'last_name': 'Smith'},
                {'username': 'faculty3', 'first_name': 'Robert', 'last_name': 'Johnson'}
            ]

            faculty_profiles = []
            for f_data in faculty_data:
                faculty_user = User.objects.get_or_create(
                    username=f_data['username'],
                    defaults={
                        'first_name': f_data['first_name'],
                        'last_name': f_data['last_name'],
                        'email': f'{f_data["username"]}@example.com'
                    }
                )[0]
                faculty_user.set_password('faculty123')
                faculty_user.save()

                faculty_profile = UserProfile.objects.get_or_create(
                    user=faculty_user,
                    defaults={
                        'user_type': 2,
                        'department': department,
                        'contact': '1234567890'
                    }
                )[0]
                faculty_profiles.append(faculty_profile)

            # Create Classes
            classes_data = [
                {
                    'name': 'CS101 - Introduction to Programming',
                    'schedule': 'Monday and Wednesday, 9:00 AM - 10:30 AM',
                    'course': created_courses[0],
                    'assigned_faculty': faculty_profiles[0],
                    'school_year': '2024-2025',
                    'level': '1st Year'
                },
                {
                    'name': 'CS102 - Data Structures',
                    'schedule': 'Tuesday and Thursday, 11:00 AM - 12:30 PM',
                    'course': created_courses[0],
                    'assigned_faculty': faculty_profiles[1],
                    'school_year': '2024-2025',
                    'level': '1st Year'
                },
                {
                    'name': 'CS103 - Database Management',
                    'schedule': f'{datetime.now().strftime("%A")}, 2:00 PM - 3:30 PM',
                    'course': created_courses[0],
                    'assigned_faculty': faculty_profiles[2],
                    'school_year': '2024-2025',
                    'level': '1st Year'
                }
            ]

            created_classes = []
            for class_data in classes_data:
                class_obj = Class.objects.get_or_create(
                    name=class_data['name'],
                    defaults=class_data
                )[0]
                created_classes.append(class_obj)

            # Create Students
            students_data = [
                {'enrollment_number': '2024CS001', 'first_name': 'Alice', 'last_name': 'Johnson'},
                {'enrollment_number': '2024CS002', 'first_name': 'Bob', 'last_name': 'Smith'},
                {'enrollment_number': '2024CS003', 'first_name': 'Charlie', 'last_name': 'Brown'},
                {'enrollment_number': '2024CS004', 'first_name': 'Diana', 'last_name': 'Wilson'},
                {'enrollment_number': '2024CS005', 'first_name': 'Edward', 'last_name': 'Davis'}
            ]

            for student_data in students_data:
                # Create Student
                student = Student.objects.get_or_create(
                    enrollment_number=student_data['enrollment_number'],
                    defaults={
                        'first_name': student_data['first_name'],
                        'last_name': student_data['last_name'],
                        'course': created_courses[0],  # Assign to first course
                        'contact': '1234567890'
                    }
                )[0]

                # Create User for Student
                student_user = User.objects.get_or_create(
                    username=student_data['enrollment_number'],
                    defaults={
                        'first_name': student_data['first_name'],
                        'last_name': student_data['last_name'],
                        'email': f"{student_data['enrollment_number']}@example.com"
                    }
                )[0]
                student_user.set_password('student123')
                student_user.save()

                # Create Student Profile
                UserProfile.objects.get_or_create(
                    user=student_user,
                    defaults={
                        'user_type': 3,
                        'contact': '1234567890'
                    }
                )

                # Add Student to Classes
                for class_obj in created_classes:
                    ClassStudent.objects.get_or_create(
                        student=student,
                        classIns=class_obj
                    )

                # Create Sample Attendance Records (last 7 days)
                for i in range(7):
                    date = datetime.now().date() - timedelta(days=i)
                    for class_obj in created_classes:
                        # Randomly assign attendance status
                        attendance_type = random.choice(['1', '2', '3'])  # 1=Present, 2=Late, 3=Absent
                        Attendance.objects.get_or_create(
                            student=student,
                            classIns=class_obj,
                            attendance_date=date,
                            defaults={'type': attendance_type}
                        )

                # Create Sample Leave Application
                LeaveApplication.objects.get_or_create(
                    student=student,
                    defaults={
                        'start_date': datetime.now().date() + timedelta(days=5),
                        'end_date': datetime.now().date() + timedelta(days=7),
                        'reason': f'Medical Leave for {student_data["first_name"]}',
                        'status': random.choice(['pending', 'approved', 'rejected'])
                    }
                )

                # Create Sample Feedback
                Feedback.objects.get_or_create(
                    student=student,
                    defaults={
                        'subject': 'Course Feedback',
                        'message': f'Sample feedback from {student_data["first_name"]}'
                    }
                )

            # Create Admin User if doesn't exist
            User.objects.get_or_create(
                username='admin',
                defaults={
                    'is_superuser': True,
                    'is_staff': True,
                    'email': 'admin@example.com'
                }
            )[0].set_password('admin123')

            self.stdout.write(self.style.SUCCESS('Successfully created sample data'))
            self.stdout.write(self.style.SUCCESS('\nLogin Credentials:'))
            self.stdout.write(self.style.SUCCESS('Admin - username: admin, password: admin123'))
            self.stdout.write(self.style.SUCCESS('Faculty - username: faculty1/2/3, password: faculty123'))
            self.stdout.write(self.style.SUCCESS('Students - username: 2024CS001-005, password: student123'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}')) 