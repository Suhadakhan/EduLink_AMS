from django.contrib import admin
from .models import Department, Course, Student,UserProfile, Class, Attendance

# Register your models here.

admin.site.register(Attendance)
admin.site.register(UserProfile)
admin.site.register(Department)
admin.site.register(Course)
admin.site.register(Class)
admin.site.register(Student)

