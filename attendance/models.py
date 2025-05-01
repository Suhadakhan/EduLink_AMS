from multiprocessing.spawn import old_main_modules
from statistics import mode
from unicodedata import category
from django.db import models
from django.contrib.auth.models import User

from django.dispatch import receiver
from django.db.models.signals import post_save
from django.utils import timezone
from datetime import datetime


class Department(models.Model):
    name = models.CharField(max_length=250)
    description = models.TextField(blank=True, null=True)
    status = models.IntegerField(default = 1)
    date_added = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE,related_name='profile')
    contact = models.CharField(max_length=250)
    dob = models.DateField(blank=True, null = True)
    address = models.TextField(blank=True, null = True)
    avatar = models.ImageField(blank=True, null = True, upload_to= 'images/')
    user_type = models.IntegerField(default = 2)
    gender = models.CharField(max_length=100, choices=[('Male','Male'),('Female','Female')], blank=True, null= True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, blank= True, null = True)

    def __str__(self):
        return self.user.username
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(
            user=instance,
            user_type=1 if instance.is_superuser else 3  # 1 for admin, 3 for regular users
        )

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if not hasattr(instance, 'profile'):
        UserProfile.objects.create(user=instance)
    instance.profile.save()

class Course(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    name = models.CharField(max_length=250)
    description = models.TextField(blank=True, null=True)
    status = models.IntegerField(default = 1)
    date_added = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Student(models.Model):
    enrollment_number = models.CharField(max_length=50, unique=True)
    first_name = models.CharField(max_length=250)
    middle_name = models.CharField(max_length=250, blank=True, null=True)
    last_name = models.CharField(max_length=250)
    gender = models.CharField(max_length=20, blank=True, null=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    contact = models.CharField(max_length=50, blank=True, null=True)
    dob = models.DateField(blank=True, null=True)

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return f"{self.enrollment_number} - {self.get_full_name()}"


class Class(models.Model):
    name = models.CharField(max_length=250)
    assigned_faculty = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    schedule = models.CharField(max_length=250)
    school_year = models.CharField(max_length=250)
    level = models.CharField(max_length=250)
    status = models.IntegerField(default=1)  # 1=Active, 2=Inactive

    def __str__(self):
        return self.name

    def is_attendance_marked_today(self, student):
        today = datetime.now().date()
        return Attendance.objects.filter(
            student=student,
            classIns=self,
            attendance_date=today
        ).exists()

class ClassStudent(models.Model):
    classIns = models.ForeignKey(Class,on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE) 

    def __str__(self):
        return self.student.enrollment_number

    def get_present(self):
        student =  self.student
        _class =  self.classIns
        try:
            present = Attendance.objects.filter(classIns= _class, student=student, type = 1).count()
            return present
        except:
            return 0
    
    def get_tardy(self):
        student =  self.student
        _class =  self.classIns
        try:
            present = Attendance.objects.filter(classIns= _class, student=student, type = 2).count()
            return present
        except:
            return 0

    def get_absent(self):
        student =  self.student
        _class =  self.classIns
        try:
            present = Attendance.objects.filter(classIns= _class, student=student, type = 3).count()
            return present
        except:
            return 0

class Attendance(models.Model):
    classIns = models.ForeignKey(Class,on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    attendance_date = models.DateField()
    type = models.CharField(max_length=250, choices = [
        ('1','Present'),
        ('2','Tardy'),
        ('3','Absent')
    ])
    date_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.classIns.name} - {self.student.enrollment_number} - {self.attendance_date}"

class Quiz(models.Model):
    title = models.CharField(max_length=200)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    description = models.TextField(blank=True, null=True)
    duration = models.IntegerField(help_text="Duration in minutes")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    text = models.TextField()
    marks = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.text[:50]

class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    text = models.CharField(max_length=200)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text

class LeaveApplication(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    
    LEAVE_TYPES = (
        ('sick', 'Sick Leave'),
        ('personal', 'Personal Leave'),
        ('emergency', 'Emergency Leave'),
    )
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPES, default='personal')
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.student} - {self.start_date} to {self.end_date}"

class Feedback(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.student.get_full_name()} - {self.subject}"

    class Meta:
        ordering = ['-created_at']
