import traceback
from unicodedata import category
from aiohttp import request
from django.http import HttpResponse, FileResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
import json
import random  # Add this import
from datetime import datetime, timedelta, timezone
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q
from ams.settings import MEDIA_ROOT, MEDIA_URL
from attendance.models import Attendance, UserProfile,Course, Department,Student, Class, ClassStudent, Quiz, LeaveApplication, Feedback

from attendance.forms import UserRegistration, UpdateProfile, UpdateProfileMeta, UpdateProfileAvatar, AddAvatar, SaveDepartment, SaveCourse, SaveClass, SaveStudent, SaveClassStudent, UpdatePasswords, UpdateFaculty

import pandas as pd
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
import io
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch
import xlsxwriter
from django.db import transaction

from django.contrib.auth.decorators import login_required
from .decorators import role_required  # Import from local decorators.py

ADMIN_ROLE = 1
FACULTY_ROLE = 2
STUDENT_ROLE = 3

deparment_list = Department.objects.exclude(status = 2).all()
context = {
    'page_title' : 'Simple Blog Site',
    'deparment_list' : deparment_list,
    'deparment_list_limited' : deparment_list[:3]
}
#login
def create_default_admin():
    try:
        User.objects.get(username='admin')
    except User.DoesNotExist:
        User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
        print("Default admin user created")

def create_default_faculty():
    try:
        # Check if faculty1 already exists
        if not User.objects.filter(username='faculty1').exists():
            with transaction.atomic():  # Use transaction to ensure data consistency
                # Create user
                user = User.objects.create_user(
                    username='faculty1',
                    email='faculty1@example.com',
                    password='faculty123',
                    first_name='Faculty',
                    last_name='One',
                    is_staff=True
                )
                
                # Get or create Computer Science department
                department, _ = Department.objects.get_or_create(
                    name='Computer Science',
                    defaults={
                        'description': 'Department of Computer Science',
                        'status': 1
                    }
                )
                
                # Delete any existing profile
                UserProfile.objects.filter(user=user).delete()
                
                # Create faculty profile with explicit user_type=2
                faculty = UserProfile.objects.create(
                    user=user,
                    user_type=2,  # Faculty type
                    contact='1234567890',
                    department=department
                )
                
                # Create sample data for this faculty
                create_sample_faculty_data(faculty)
                
                print("Default faculty user created with sample data")
                return True
        else:
            # If user exists, ensure it has faculty profile
            user = User.objects.get(username='faculty1')
            profile = UserProfile.objects.get(user=user)
            if profile.user_type != 2:
                profile.user_type = 2
                profile.save()
                print("Updated existing faculty profile to correct user type")
            return True
    except Exception as e:
        print(f"Error creating default faculty: {str(e)}")
        return False

def login_user(request):
    create_default_admin()  # Create default admin if doesn't exist
    create_default_faculty()  # Create default faculty if doesn't exist
    create_default_student()  # Create default student if doesn't exist
    
    if request.user.is_authenticated:
        return redirect('home-page')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Print for debugging
        print(f"Login attempt - Username: {username}")
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome {user.first_name}!')
            next_url = request.POST.get('next', 'home-page')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password')
            print("Authentication failed")  # Debugging line
    
    return render(request, 'login.html')

#Logout
def logoutuser(request):
    logout(request)
    return redirect('/')

@login_required
def home(request):
    try:
        context = {
            'page_title': "Dashboard",
        }
        
        print(f"User type: {request.user.profile.user_type}")  # Debug print
        
        if request.user.profile.user_type == 3:  # Student
            return render(request, 'student/dashboard.html', context)
        elif request.user.profile.user_type == 2:  # Faculty
            faculty_classes = Class.objects.filter(assigned_faculty=request.user.profile)
            context.update({
                'classes': faculty_classes,
            })
            print("Rendering faculty dashboard")  # Debug print
            return render(request, 'faculty/dashboard.html', context)
        else:  # Admin/Superuser
            try:
                # Basic statistics
                total_students = Student.objects.count()
                total_faculty = UserProfile.objects.filter(user_type=2).count()
                total_courses = Course.objects.count()
                total_departments = Department.objects.count()

                # Students per Course data
                courses = Course.objects.all()
                course_labels = [str(course.name) for course in courses]  # Convert to string
                course_data = [Student.objects.filter(course=course).count() for course in courses]

                # Faculty per Department data
                departments = Department.objects.all()
                dept_labels = [str(dept.name) for dept in departments]  # Convert to string
                dept_data = [UserProfile.objects.filter(user_type=2, department=dept).count() for dept in departments]

                # Recent activities
                recent_activities = []
                
                # Recent students
                for student in Student.objects.order_by('-id')[:3]:
                    recent_activities.append({
                        'message': f'New student {student.first_name} {student.last_name} enrolled',
                        'timestamp': datetime.now()
                    })
                
                # Recent faculty
                for faculty in UserProfile.objects.filter(user_type=2).order_by('-id')[:3]:
                    recent_activities.append({
                        'message': f'New faculty {faculty.user.get_full_name()} joined',
                        'timestamp': datetime.now()
                    })

                context.update({
                    'total_students': total_students,
                    'total_faculty': total_faculty,
                    'total_courses': total_courses,
                    'total_departments': total_departments,
                    'course_labels': json.dumps(course_labels),
                    'course_data': json.dumps(course_data),
                    'dept_labels': json.dumps(dept_labels),
                    'dept_data': json.dumps(dept_data),
                    'recent_activities': sorted(recent_activities, key=lambda x: x['timestamp'], reverse=True)[:5]
                })

                print("Context prepared successfully:", context)  # Debug print
                return render(request, 'superuser/dashboard.html', context)

            except Exception as e:
                print(f"Error preparing dashboard data: {str(e)}")  # Debug print
                context.update({
                    'total_students': 0,
                    'total_faculty': 0,
                    'total_courses': 0,
                    'total_departments': 0,
                    'course_labels': json.dumps([]),
                    'course_data': json.dumps([]),
                    'dept_labels': json.dumps([]),
                    'dept_data': json.dumps([]),
                    'recent_activities': []
                })
                return render(request, 'superuser/dashboard.html', context)
                
    except Exception as e:
        print(f"Error in home view: {str(e)}")  # Debug print
        messages.error(request, "An error occurred while loading the dashboard.")
        return render(request, 'superuser/dashboard.html', {'page_title': "Dashboard"})

# Add this function to create sample classes
def create_sample_classes(request):
    try:
        # Clear existing classes
        Class.objects.all().delete()

        # Get courses and faculty
        courses = Course.objects.all()
        
        # Create sample classes
        sample_classes = [
            {
                'course': Course.objects.get(name='Computer Science'),
                'name': 'CS101 - Introduction to Programming',
                'schedule': 'Monday and Wednesday, 9:00 AM - 10:30 AM',
                'status': 1
            },
            {
                'course': Course.objects.get(name='Computer Science'),
                'name': 'CS102 - Data Structures',
                'schedule': 'Tuesday and Thursday, 11:00 AM - 12:30 PM',
                'status': 1
            },
            {
                'course': Course.objects.get(name='Information Technology'),
                'name': 'IT101 - Information Systems',
                'schedule': 'Monday and Wednesday, 2:00 PM - 3:30 PM',
                'status': 1
            },
            {
                'course': Course.objects.get(name='Software Engineering'),
                'name': 'SE101 - Software Development',
                'schedule': 'Tuesday and Thursday, 1:00 PM - 2:30 PM',
                'status': 1
            },
            {
                'course': Course.objects.get(name='Information Technology'),
                'name': 'IT102 - Network Fundamentals',
                'schedule': 'Friday, 10:00 AM - 1:00 PM',
                'status': 1
            }
        ]

        created_classes = []
        for class_data in sample_classes:
            class_obj = Class.objects.create(**class_data)
            created_classes.append(class_obj.name)

        return JsonResponse({
            'status': 'success',
            'message': 'Sample classes created successfully',
            'classes': created_classes
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })

def registerUser(request):
    user = request.user
    if user.is_authenticated:
        return redirect('home-page')
    context['page_title'] = "Register User"
    if request.method == 'POST':
        data = request.POST
        form = UserRegistration(data)
        if form.is_valid():
            form.save()
            newUser = User.objects.all().last()
            try:
                profile = UserProfile.objects.get(user = newUser)
            except:
                profile = None
            if profile is None:
                UserProfile(user = newUser, dob= data['dob'], contact= data['contact'], address= data['address'], avatar = request.FILES['avatar']).save()
            else:
                UserProfile.objects.filter(id = profile.id).update(user = newUser, dob= data['dob'], contact= data['contact'], address= data['address'])
                avatar = AddAvatar(request.POST,request.FILES, instance = profile)
                if avatar.is_valid():
                    avatar.save()
            username = form.cleaned_data.get('username')
            pwd = form.cleaned_data.get('password1')
            loginUser = authenticate(username= username, password = pwd)
            login(request, loginUser)
            return redirect('home-page')
        else:
            context['reg_form'] = form

    return render(request,'register.html',context)

@login_required
def profile(request):
    context = {
        'page_title': "My Profile"
    }
    
    if request.user.profile.user_type == 3:  # Student
        try:
            student = Student.objects.get(student_code=request.user.username)
        except Student.DoesNotExist:
            # Create student profile with course (using the first available course)
            default_course = Course.objects.filter(status=1).first()
            if not default_course:
                messages.error(request, "No active courses found. Please contact administrator.")
                return redirect('home-page')
                
            student = Student.objects.create(
                student_code=request.user.username,
                first_name=request.user.first_name,
                last_name=request.user.last_name,
                gender=request.user.profile.gender if hasattr(request.user.profile, 'gender') else "",
                course=default_course,  # Add this line
                status=1
            )
            messages.success(request, "Student profile has been created automatically.")
        context['student'] = student

    return render(request, 'profile.html', context)
    
@login_required
def update_profile(request):
    if request.method == 'POST':
        try:
            # Update User model fields
            request.user.first_name = request.POST.get('first_name')
            request.user.last_name = request.POST.get('last_name')
            request.user.email = request.POST.get('email')
            request.user.save()

            # Update Profile fields
            profile = request.user.profile
            profile.contact = request.POST.get('contact')
            profile.address = request.POST.get('address')
            profile.save()

            messages.success(request, "Profile updated successfully!")
        except Exception as e:
            messages.error(request, f"Error updating profile: {str(e)}")
    return redirect('profile')

@login_required
def update_avatar(request):
    context['page_title'] = "Update Avatar"
    user = User.objects.get(id= request.user.id)
    context['userData'] = user
    context['userProfile'] = user.profile
    if user.profile.avatar:
        img = user.profile.avatar.url
    else:
        img = MEDIA_URL+"/default/default-avatar.png"

    context['img'] = img
    if request.method == 'POST':
        form = UpdateProfileAvatar(request.POST, request.FILES,instance=user)
        if form.is_valid():
            form.save()
            messages.success(request,"Your Profile has been updated successfully")
            return redirect("profile")
        else:
            context['form'] = form
            form = UpdateProfileAvatar(instance=user)
    return render(request,'update_avatar.html',context)

@login_required
def update_password(request):
    context['page_title'] = "Update Password"
    if request.method == 'POST':
        form = UpdatePasswords(user = request.user, data= request.POST)
        if form.is_valid():
            form.save()
            messages.success(request,"Your Account Password has been updated successfully")
            update_session_auth_hash(request, form.user)
            return redirect("profile")
        else:
            context['form'] = form
    else:
        form = UpdatePasswords(request.POST)
        context['form'] = form
    return render(request,'update_password.html',context)

#Department
@login_required
def department(request):
    departments = Department.objects.all()
    context['page_title'] = "Department Management"
    context['departments'] = departments
    return render(request, 'department_mgt.html',context)

@login_required
@role_required([ADMIN_ROLE])
def manage_department(request, pk=None):
    print("manage_department called with pk:", pk)  # Debug log
    context = {}
    if pk:
        try:
            department = get_object_or_404(Department, pk=pk)
            context['department'] = department
            print("Found department:", department)  # Debug log
        except Exception as e:
            print("Error getting department:", e)  # Debug log
    return render(request, 'manage_department.html', context)

@login_required
@role_required([ADMIN_ROLE])
def save_department(request):
    resp = {'status': 'failed', 'msg': ''}
    if request.method == 'POST':
        try:
            if request.POST.get('id'):
                department = Department.objects.get(id=request.POST['id'])
                form = SaveDepartment(request.POST, instance=department)
            else:
                form = SaveDepartment(request.POST)
                
            if form.is_valid():
                form.save()
                resp['status'] = 'success'
                resp['msg'] = 'Department saved successfully'
            else:
                resp['msg'] = 'Form validation failed: ' + str(form.errors)
        except Exception as e:
            resp['msg'] = str(e)
            
    return JsonResponse(resp)

@login_required
def delete_department(request):
    resp={'status' : 'failed', 'msg':''}
    if request.method == 'POST':
        id = request.POST['id']
        try:
            department = Department.objects.filter(id = id).first()
            department.delete()
            resp['status'] = 'success'
            messages.success(request,'Department has been deleted successfully.')
        except Exception as e:
            raise print(e)
    return HttpResponse(json.dumps(resp),content_type="application/json")


#Course
@login_required
def course(request):
    courses = Course.objects.all()
    context['page_title'] = "Course Management"
    context['courses'] = courses
    return render(request, 'course_mgt.html',context)

@login_required
@role_required([ADMIN_ROLE])
def manage_course(request, pk=None):
    context = {
        'departments': Department.objects.filter(status=1).all()
    }
    if pk is not None:
        course = Course.objects.get(id=pk)
        context['course'] = course
    return render(request, 'manage_course_modal.html', context)

@login_required
@role_required([ADMIN_ROLE])
def save_course(request):
    resp = {'status': 'failed', 'msg': ''}
    if request.method == 'POST':
        try:
            post = request.POST
            print("POST data:", post)  # Debug print
            
            if post.get('id'):  # Changed from direct access to using get()
                course = Course.objects.get(id=post['id'])
                form = SaveCourse(post, instance=course)
            else:
                form = SaveCourse(post)

            if form.is_valid():
                form.save()
                resp['status'] = 'success'
                resp['msg'] = 'Course saved successfully'
            else:
                print("Form errors:", form.errors)  # Debug print
                for field in form:
                    for error in field.errors:
                        resp['msg'] += str(error) + '<br>'
        except Exception as e:
            print("Error saving course:", str(e))  # Debug print
            resp['msg'] = str(e)
            
    return JsonResponse(resp)

@login_required
@role_required([ADMIN_ROLE])
def delete_course(request):
    resp = {'status': 'failed', 'msg': ''}
    if request.method == 'POST':
        try:
            course = Course.objects.get(id=request.POST['id'])
            course.delete()
            resp['status'] = 'success'
            messages.success(request, 'Course deleted successfully')
        except Exception as e:
            resp['msg'] = str(e)
    return JsonResponse(resp)

#Faculty
@login_required
@role_required([ADMIN_ROLE])
def faculty(request):
    """View for faculty management"""
    try:
        print("\n=== Faculty Management Debug Info ===")
        print(f"User: {request.user.username}")
        print(f"User type: {request.user.profile.user_type}")
        
        context = {
            'page_title': "Faculty Management",
            'faculties': UserProfile.objects.filter(user_type=FACULTY_ROLE).all(),
            'departments': Department.objects.filter(status=1).all()
        }
        
        print(f"Found {context['faculties'].count()} faculty members")
        print(f"Found {context['departments'].count()} departments")
        
        # Update template path to use superuser directory
        return render(request, 'superuser/faculty_management.html', context)
        
    except Exception as e:
        print(f"Error in faculty view: {str(e)}")
        print(f"Error traceback: {traceback.format_exc()}")
        messages.error(request, f"Error loading faculty management: {str(e)}")
        return redirect('home-page')

@login_required
@role_required([ADMIN_ROLE])
def manage_faculty(request, pk=None):
    print("\n=== Manage Faculty Debug Info ===")  # Debug print
    print(f"Request method: {request.method}")
    print(f"PK: {pk}")
    
    try:
        context = {
            'page_title': 'Add Faculty' if not pk else 'Edit Faculty',
            'departments': Department.objects.all()
        }
        
        print(f"Found {context['departments'].count()} departments")  # Debug print
        
        if pk:
            faculty = UserProfile.objects.get(id=pk)
            context['faculty'] = faculty
            print(f"Found faculty: {faculty.user.get_full_name()}")  # Debug print
        
        print("Rendering template: superuser/manage_faculty.html")  # Debug print
        return render(request, 'superuser/manage_faculty.html', context)
        
    except Exception as e:
        print(f"Error in manage_faculty view: {str(e)}")  # Debug print
        print(f"Error traceback: {traceback.format_exc()}")  # Debug print
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
def view_faculty(request,pk=None):
    if pk == None:
        faculty = {}
    elif pk > 0:
        faculty = UserProfile.objects.filter(id=pk).first()
    else:
        faculty = {}
    context['page_title'] = "Manage Faculty"
    context['faculty'] = faculty
    return render(request, 'faculty_details.html',context)

@login_required
@role_required([ADMIN_ROLE])
def save_faculty(request):
    print("\n=== Save Faculty Debug Info ===")
    print(f"Request method: {request.method}")
    print(f"POST data: {request.POST}")
    
    resp = {'status': 'failed', 'msg': ''}
    if request.method == 'POST':
        try:
            with transaction.atomic():
                post = request.POST
                print(f"Processing faculty save with data: {post}")
                
                # Validate required fields
                required_fields = ['first_name', 'last_name', 'email', 'department', 'contact']
                if not post.get('id'):  # New faculty
                    required_fields.append('password')
                
                for field in required_fields:
                    if not post.get(field):
                        resp['msg'] = f'{field.replace("_", " ").title()} is required.'
                        return JsonResponse(resp)

                if post.get('id'):
                    # Update existing faculty
                    faculty = UserProfile.objects.get(id=post['id'])
                    user = faculty.user
                else:
                    # Create new faculty
                    email = post.get('email')
                    # Check if email exists
                    if User.objects.filter(email=email).exists():
                        resp['msg'] = 'Email already exists.'
                        return JsonResponse(resp)
                    
                    # Generate unique username
                    base_username = email.split('@')[0]
                    username = base_username
                    counter = 1
                    while User.objects.filter(username=username).exists():
                        username = f"{base_username}{counter}"
                        counter += 1
                    
                    # Create user
                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        password=post.get('password'),
                        first_name=post.get('first_name'),
                        last_name=post.get('last_name'),
                        is_staff=True
                    )
                    
                    # Delete any existing profile that might have been auto-created
                    UserProfile.objects.filter(user=user).delete()
                    
                    # Create faculty profile
                    faculty = UserProfile.objects.create(
                        user=user,
                        user_type=FACULTY_ROLE,
                        contact=post.get('contact'),
                        department_id=post.get('department')
                    )
                    print(f"Created new faculty profile for user: {user.username}")
                
                # Update user fields
                user.first_name = post.get('first_name')
                user.last_name = post.get('last_name')
                user.email = post.get('email')
                user.save()
                print(f"Updated user fields for: {user.username}")
                
                # Update faculty profile
                faculty.contact = post.get('contact')
                faculty.department_id = post.get('department')
                faculty.save()
                print(f"Updated faculty profile for: {user.username}")

                resp['status'] = 'success'
                resp['msg'] = 'Faculty saved successfully.'
                
        except Exception as e:
            print(f"Error saving faculty: {str(e)}")
            print(f"Error traceback: {traceback.format_exc()}")
            resp['msg'] = str(e)
    
    print(f"Returning response: {resp}")
    return JsonResponse(resp)

@login_required
def delete_faculty(request):
    resp = {'status': 'failed', 'msg': ''}
    if request.method == 'POST':
        try:
            faculty = User.objects.get(id=request.POST['id'])
            faculty.delete()
            resp['status'] = 'success'
            messages.success(request, 'Faculty has been deleted successfully.')
        except Exception as e:
            print(f"Error deleting faculty: {str(e)}")
            resp['msg'] = str(e)
    return JsonResponse(resp)


    
#Class
@login_required
def classPage(request):
    if request.user.profile.user_type == 1:
        classes = Class.objects.all()
    else:
        classes = Class.objects.filter(assigned_faculty=request.user.profile).all()

    # Add courses to context
    courses = Course.objects.filter(status=1)

    context = {
        'page_title': "Class Management",
        'classes': classes,
        'courses': courses
    }
    return render(request, 'faculty/class_list.html', context)

@login_required
def manage_class(request,pk=None):
    faculty = UserProfile.objects.filter(user_type= 2).all()
    if pk == None:
        _class = {}
    elif pk > 0:
        _class = Class.objects.filter(id=pk).first()
    else:
        _class = {}
    context['page_title'] = "Manage Class"
    context['faculties'] = faculty
    context['class'] = _class

    return render(request, 'manage_class.html',context)

@login_required
def view_class(request, pk):
    try:
        class_obj = Class.objects.get(id=pk)
        students = ClassStudent.objects.filter(classIns=class_obj).select_related('student')
        
        context = {
            'page_title': f"Class Details - {class_obj.name}",
            'class': class_obj,
            'students': students
        }
        return render(request, 'class_details.html', context)
    except Class.DoesNotExist:
        messages.error(request, "Class not found")
        return redirect('class-page')

@login_required
def save_class(request):
    resp = { 'status':'failed' , 'msg' : '' }
    if request.method == 'POST':
        data = request.POST
        if data.get('id'):
            class_obj = Class.objects.filter(id=data['id']).first()
            form = SaveClass(data, instance=class_obj)
        else:
            form = SaveClass(data)

        if form.is_valid():
            form.save()
            resp['status'] = 'success'
            messages.success(request, 'Class has been saved successfully')
        else:
            for field in form:
                for error in field.errors:
                    resp['msg'] += str(error + '<br>')
    
    return JsonResponse(resp)

@login_required
def delete_class(request):
    resp={'status' : 'failed', 'msg':''}
    if request.method == 'POST':
        id = request.POST['id']
        try:
            _class = Class.objects.filter(id = id).first()
            _class.delete()
            resp['status'] = 'success'
            messages.success(request,'Class has been deleted successfully.')
        except Exception as e:
            raise print(e)
    return HttpResponse(json.dumps(resp),content_type="application/json")

@login_required
def manage_class_student(request,classPK = None):
    if classPK is None:
        return HttpResponse('Class ID is Unknown')
    else:
        context['classPK'] = classPK
        _class  = Class.objects.get(id = classPK)
        # print(ClassStudent.objects.filter(classIns = _class))
        students = Student.objects.exclude(id__in = ClassStudent.objects.filter(classIns = _class).values_list('student').distinct()).all()
        context['students'] = students
        return render(request, 'manage_class_student.html',context)
@login_required
def save_class_student(request):
    resp = {'status' : 'failed', 'msg':''}
    if request.method == 'POST':
        form = SaveClassStudent(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request,"Student has been added successfully.")
            resp['status'] = 'success'
        else:
            for field in form:
                for error in field.errors:
                    resp['msg'] += str(error+"<br>")
    return HttpResponse(json.dumps(resp),content_type = 'json')

@login_required
def delete_class_student(request):
    resp={'status' : 'failed', 'msg':''}
    if request.method == 'POST':
        id = request.POST['id']
        try:
            cs = ClassStudent.objects.filter(id = id).first()
            cs.delete()
            resp['status'] = 'success'
            messages.success(request,'Student has been deleted from Class successfully.')
        except Exception as e:
            raise print(e)
    return HttpResponse(json.dumps(resp),content_type="application/json")


#Student
@login_required
@role_required([ADMIN_ROLE])
def student(request):
    context = {
        'page_title': 'Student Management',
        'students': Student.objects.all(),
        'courses': Course.objects.filter(status=1)
    }
    return render(request, 'superuser/student_mgt.html', context)  # CORRECT TEMPLATE

@login_required
@role_required([ADMIN_ROLE])
def manage_student(request, pk=None):
    print("\n=== Manage Student Debug Info ===")
    print(f"Request method: {request.method}")
    print(f"PK: {pk}")
    
    if request.method == 'POST':
        # Handle form submission
        if pk:
            # Edit existing student
            student = get_object_or_404(Student, pk=pk)
            form = SaveStudent(request.POST, instance=student)
        else:
            # Add new student
            form = SaveStudent(request.POST)
            
        if form.is_valid():
            form.save()
            messages.success(request, 'Student saved successfully')
            return redirect('student-list')
        else:
            messages.error(request, 'Error saving student')
    else:
        # Display form
        if pk:
            # Edit form
            student = get_object_or_404(Student, pk=pk)
            form = SaveStudent(instance=student)
        else:
            # Add form
            form = SaveStudent()
    
    context = {
        'form': form,
        'courses': Course.objects.filter(status=1),
        'pk': pk
    }
    
    return render(request, 'superuser/manage_student.html', context)

@login_required
@role_required([ADMIN_ROLE])
def view_student(request, pk):
    student = Student.objects.get(id=pk)
    context = {
        'student': student
    }
    return render(request, 'superuser/view_student.html', context)

@login_required
@role_required([ADMIN_ROLE])
def save_student(request):
    print("\n=== Save Student Debug Info ===")  # Debug print
    print(f"Request method: {request.method}")
    print(f"POST data: {request.POST}")
    
    resp = {'status': 'failed', 'msg': ''}
    if request.method == 'POST':
        try:
            with transaction.atomic():
                post = request.POST
                
                # Validate required fields
                required_fields = ['enrollment_number', 'first_name', 'course']
                for field in required_fields:
                    if not post.get(field):
                        resp['msg'] = f'{field.replace("_", " ").title()} is required.'
                        return JsonResponse(resp)

                # Check if student exists for update
                if post.get('id'):
                    student = Student.objects.get(id=post['id'])
                else:
                    # Check if enrollment number already exists
                    if Student.objects.filter(enrollment_number=post['enrollment_number']).exists():
                        resp['msg'] = 'Enrollment number already exists.'
                        return JsonResponse(resp)
                    student = Student()

                # Update student fields
                student.enrollment_number = post['enrollment_number']
                student.first_name = post['first_name']
                student.last_name = post.get('last_name', '')
                student.course_id = post['course']
                student.contact = post.get('contact', '')
                student.save()

                print(f"Student saved: {student.enrollment_number}")  # Debug print
                resp['status'] = 'success'
                resp['msg'] = 'Student saved successfully.'
                
        except Exception as e:
            print(f"Error saving student: {str(e)}")  # Debug print
            print(f"Error traceback: {traceback.format_exc()}")  # Debug print
            resp['msg'] = str(e)
    
    print(f"Returning response: {resp}")  # Debug print
    return JsonResponse(resp)

@login_required
@role_required([ADMIN_ROLE])
def delete_student(request):
    resp = {'status': 'failed', 'msg': ''}
    if request.method == 'POST':
        try:
            student = Student.objects.get(id=request.POST['id'])
            student.delete()
            resp['status'] = 'success'
            messages.success(request, 'Student deleted successfully')
        except Exception as e:
            resp['msg'] = str(e)
    return JsonResponse(resp)

# Faculty views
@login_required
@role_required([FACULTY_ROLE])
def manage_feedback(request):
    feedbacks = Feedback.objects.all().order_by('-created_at')
    context = {
        'page_title': 'Manage Feedback',
        'feedbacks': feedbacks
    }
    return render(request, 'faculty/feedback.html', context)

# Student views
@login_required
@role_required([STUDENT_ROLE])
def submit_feedback(request):
    try:
        # Get or create student
        student, created = Student.objects.get_or_create(
            enrollment_number=request.user.username,
            defaults={
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'course': Course.objects.filter(status=1).first()
            }
        )

        if request.method == 'POST':
            try:
                subject = request.POST.get('subject')
                message = request.POST.get('message')
                
                if not subject or not message:
                    messages.error(request, "Both subject and message are required.")
                    return redirect('feedback')
                
                # Create feedback without timestamps
                feedback = Feedback.objects.create(
                    student=student,
                    subject=subject,
                    message=message
                )
                
                messages.success(request, 'Feedback submitted successfully!')
                return redirect('feedback')
            except Exception as e:
                messages.error(request, f'Error submitting feedback: {str(e)}')
        
        # Get feedback list
        feedback_list = Feedback.objects.filter(student=student).order_by('-id')
        
        context = {
            'page_title': 'Submit Feedback',
            'feedback_list': feedback_list
        }
        return render(request, 'student/feedback.html', context)
        
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return redirect('home-page')

@login_required
@role_required([STUDENT_ROLE])
def student_attendance(request):
    try:
        # Get or create student
        student, created = Student.objects.get_or_create(
            enrollment_number=request.user.username,
            defaults={
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'course': Course.objects.filter(status=1).first()
            }
        )

        # Get or create class enrollment
        class_enrollments = ClassStudent.objects.filter(student=student)
        if not class_enrollments.exists():
            # Get first active class
            default_class = Class.objects.filter(status=1).first()
            if default_class:
                ClassStudent.objects.create(
                    student=student,
                    classIns=default_class
                )
                class_enrollments = ClassStudent.objects.filter(student=student)

        attendance_data = []
        today = datetime.now().date()

        for enrollment in class_enrollments:
            class_obj = enrollment.classIns
            attendance_records = Attendance.objects.filter(
                student=student,
                classIns=class_obj
            ).order_by('-attendance_date')

            today_attendance = attendance_records.filter(attendance_date=today).first()

            class_data = {
                'class_name': class_obj.name,
                'class_id': class_obj.id,  # Make sure class_id is included
                'faculty': f"{class_obj.assigned_faculty.user.first_name} {class_obj.assigned_faculty.user.last_name}",
                'schedule': class_obj.schedule,
                'attendance_records': attendance_records,
                'total_classes': attendance_records.count(),
                'present': attendance_records.filter(type='1').count(),
                'late': attendance_records.filter(type='2').count(),
                'absent': attendance_records.filter(type='3').count(),
                'today_attendance': today_attendance
            }

            if class_data['total_classes'] > 0:
                present_count = class_data['present'] + class_data['late']
                class_data['attendance_percentage'] = (present_count / class_data['total_classes']) * 100
            else:
                class_data['attendance_percentage'] = 0

            attendance_data.append(class_data)

        context = {
            'attendance_data': attendance_data,
            'student': student,
            'today': today,
            'has_classes': len(attendance_data) > 0
        }

        return render(request, 'student/attendance.html', context)

    except Exception as e:
        messages.error(request, f"Error retrieving attendance: {str(e)}")
        return redirect('home-page')

@login_required
@role_required([STUDENT_ROLE])
def student_leave_application(request):
    try:
        student = Student.objects.get(enrollment_number=request.user.username)
        applications = LeaveApplication.objects.filter(student=student).order_by('-created_at')
        context = {
            'page_title': 'Leave Application',
            'applications': applications
        }
        return render(request, 'student/leave_application.html', context)
    except Student.DoesNotExist:
        messages.error(request, "Student profile not found")
        return redirect('profile')

# Common views (accessible to all authenticated users)
@login_required
def profile(request):
    context = {
        'page_title': "My Profile"
    }

    return render(request,'profile.html',context)
    
@login_required
def update_profile(request):
    context['page_title'] = "Update Profile"
    user = User.objects.get(id= request.user.id)
    profile = UserProfile.objects.get(user= user)
    context['userData'] = user
    context['userProfile'] = profile
    if request.method == 'POST':
        data = request.POST
        # if data['password1'] == '':
        # data['password1'] = '123'
        form = UpdateProfile(data, instance=user)
        if form.is_valid():
            form.save()
            form2 = UpdateProfileMeta(data, instance=profile)
            if form2.is_valid():
                form2.save()
                messages.success(request,"Your Profile has been updated successfully")
                return redirect("profile")
            else:
                # form = UpdateProfile(instance=user)
                context['form2'] = form
        else:
            context['form1'] = form
            form = UpdateProfile(instance=request.user)
    return render(request,'update_profile.html',context)

@login_required
def update_avatar(request):
    context['page_title'] = "Update Avatar"
    user = User.objects.get(id= request.user.id)
    context['userData'] = user
    context['userProfile'] = user.profile
    if user.profile.avatar:
        img = user.profile.avatar.url
    else:
        img = MEDIA_URL+"/default/default-avatar.png"

    context['img'] = img
    if request.method == 'POST':
        form = UpdateProfileAvatar(request.POST, request.FILES,instance=user)
        if form.is_valid():
            form.save()
            messages.success(request,"Your Profile has been updated successfully")
            return redirect("profile")
        else:
            context['form'] = form
            form = UpdateProfileAvatar(instance=user)
    return render(request,'update_avatar.html',context)

@login_required
def update_password(request):
    context['page_title'] = "Update Password"
    if request.method == 'POST':
        form = UpdatePasswords(user = request.user, data= request.POST)
        if form.is_valid():
            form.save()
            messages.success(request,"Your Account Password has been updated successfully")
            update_session_auth_hash(request, form.user)
            return redirect("profile")
        else:
            context['form'] = form
    else:
        form = UpdatePasswords(request.POST)
        context['form'] = form
    return render(request,'update_password.html',context)

@login_required
@role_required([STUDENT_ROLE])
def class_schedule(request):
    try:
        # Try to get student by enrollment number
        student = Student.objects.filter(
            enrollment_number=request.user.username
        ).first()
        
        # If no student found, create one
        if not student:
            # Get default course
            default_course = Course.objects.filter(status=1).first()
            if not default_course:
                messages.error(request, "No active courses found. Please contact administrator.")
                return redirect('home-page')
            
            # Create student record
            student = Student.objects.create(
                enrollment_number=request.user.username,
                student_code=request.user.username,
                first_name=request.user.first_name,
                last_name=request.user.last_name,
                course=default_course
            )
            messages.success(request, "Student profile has been created automatically.")

        # Get all classes for this student
        class_enrollments = ClassStudent.objects.filter(student=student).select_related('classIns')
        
        # Format class schedule data
        schedule_data = []
        for enrollment in class_enrollments:
            class_obj = enrollment.classIns
            schedule_data.append({
                'name': class_obj.name,
                'schedule': class_obj.schedule,
                'faculty': f"{class_obj.assigned_faculty.user.first_name} {class_obj.assigned_faculty.user.last_name}",
                'course': class_obj.course.name,
                'level': class_obj.level,
                'school_year': class_obj.school_year
            })

        context = {
            'page_title': 'Class Schedule',
            'schedule_data': schedule_data,
            'student': student
        }
        return render(request, 'student/schedule.html', context)
        
    except Exception as e:
        messages.error(request, f"Error retrieving schedule: {str(e)}")
        return redirect('home-page')

@login_required
@role_required([STUDENT_ROLE])
def mark_student_attendance(request):
    if request.method == 'POST':
        try:
            # Get or create student
            student = Student.objects.get(enrollment_number=request.user.username)
            status = request.POST.get('status')
            today = datetime.now().date()
            
            # Get all classes for this student
            class_enrollments = ClassStudent.objects.filter(student=student)
            
            if not class_enrollments.exists():
                return JsonResponse({
                    'status': 'error',
                    'message': 'No classes found for this student'
                })
            
            # Mark attendance for all enrolled classes
            for enrollment in class_enrollments:
                # Create or update attendance record
                attendance, created = Attendance.objects.update_or_create(
                    student=student,
                    classIns=enrollment.classIns,
                    attendance_date=today,
                    defaults={'type': status}
                )
            
            # Get updated attendance stats
            total_classes = Attendance.objects.filter(student=student).count()
            present_count = Attendance.objects.filter(student=student, type='1').count()
            late_count = Attendance.objects.filter(student=student, type='2').count()
            absent_count = Attendance.objects.filter(student=student, type='3').count()
            
            attendance_percentage = ((present_count + late_count) / total_classes * 100) if total_classes > 0 else 0
            
            return JsonResponse({
                'status': 'success',
                'message': 'Attendance marked successfully',
                'stats': {
                    'total': total_classes,
                    'present': present_count,
                    'late': late_count,
                    'absent': absent_count,
                    'percentage': round(attendance_percentage, 2)
                }
            })
            
        except Student.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Student profile not found'
            })
        except Exception as e:
            print(f"Error marking attendance: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    })

@login_required
@role_required([FACULTY_ROLE])
def faculty_feedback(request):
    """View for faculty to see feedback from their students"""
    try:
        # Get all classes taught by this faculty
        faculty_classes = Class.objects.filter(assigned_faculty=request.user.profile)
        
        # Get feedback from students in those classes
        feedback_list = Feedback.objects.filter(
            student__classstudent__classIns__in=faculty_classes
        ).select_related('student').order_by('-created_at')
        context = {
            'page_title': 'Student Feedback',
            'feedback_list': feedback_list
        }
        return render(request, 'faculty/feedback.html', context)
    except Exception as e:
        messages.error(request, f"Error loading feedback: {str(e)}")
        return redirect('home-page')

@login_required
@role_required([FACULTY_ROLE])
def faculty_leave_applications(request):
    """View for faculty to manage student leave applications"""
    try:
        # Get all classes taught by this faculty
        faculty_classes = Class.objects.filter(assigned_faculty=request.user.profile)
        
        # Get leave applications from students in those classes
        applications = LeaveApplication.objects.filter(
            student__classstudent__classIns__in=faculty_classes
        ).select_related('student').order_by('-created_at')
        context = {
            'page_title': 'Leave Applications',
            'applications': applications
        }
        return render(request, 'faculty/leave_applications.html', context)
    except Exception as e:
        messages.error(request, f"Error loading leave applications: {str(e)}")
        return redirect('home-page')

@login_required
@role_required([FACULTY_ROLE])
def update_leave_status(request):
    if request.method == 'POST':
        try:
            application_id = request.POST.get('application_id')
            new_status = request.POST.get('status')
            
            # Get the leave application
            application = LeaveApplication.objects.get(id=application_id)
            
            # Verify faculty teaches this student
            faculty_classes = Class.objects.filter(assigned_faculty=request.user.profile)
            student_in_class = ClassStudent.objects.filter(
                student=application.student,
                classIns__in=faculty_classes
            ).exists()
            
            if student_in_class:
                application.status = new_status
                application.save()
                return JsonResponse({'status': 'success'})
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Unauthorized to update this application'
                })
                
        except LeaveApplication.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Leave application not found'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    })

@login_required
@role_required([FACULTY_ROLE])
def faculty_data_management(request):
    """View for faculty to manage their data"""
    # Get faculty's classes
    faculty_classes = Class.objects.filter(assigned_faculty=request.user.profile)
    print(f"Faculty classes found: {faculty_classes.count()}")  # Add this for debugging
    
    context = {
        'page_title': 'Data Management',
        'classes': faculty_classes
    }
    return render(request, 'faculty/data_management.html', context)

@login_required
@role_required([FACULTY_ROLE])
def export_attendance(request):
    try:
        class_id = request.GET.get('class')
        format_type = request.GET.get('format', 'excel')  # Default to excel if not specified
        
        if not class_id:
            class_id = request.POST.get('class')
            
        if not class_id:
            messages.error(request, "Class ID is required")
            return redirect('faculty-data-management')
        
        class_obj = Class.objects.get(id=class_id, assigned_faculty=request.user.profile)
        
        if format_type == 'pdf':
            # Create PDF
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=letter,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=72
            )
            
            elements = []
            
            # Add title
            styles = getSampleStyleSheet()
            title = Paragraph(f"Attendance Report - {class_obj.name}", styles['Title'])
            elements.append(title)
            elements.append(Spacer(1, 12))
            
            # Prepare data
            data = [['Date', 'Student ID', 'Student Name', 'Status']]
            attendances = Attendance.objects.filter(classIns=class_obj).order_by('attendance_date', 'student__enrollment_number')
            
            for attendance in attendances:
                status_map = {'1': 'Present', '2': 'Tardy', '3': 'Absent'}
                data.append([
                    attendance.attendance_date.strftime('%Y-%m-%d'),
                    attendance.student.enrollment_number,
                    f"{attendance.student.first_name} {attendance.student.last_name}",
                    status_map.get(attendance.type, 'Unknown')
                ])
            
            # Create table
            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            
            elements.append(table)
            
            # Build PDF
            doc.build(elements)
            buffer.seek(0)
            
            # Return PDF
            response = HttpResponse(buffer, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename=attendance_report_{class_obj.name}.pdf'
            
        else:  # Excel format
            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename=attendance_report_{class_obj.name}.xlsx'
            
            workbook = xlsxwriter.Workbook(response)
            worksheet = workbook.add_worksheet()
            
            # Add headers with formatting
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#4B5563',
                'font_color': 'white'
            })
            
            headers = ['Date', 'Student ID', 'Student Name', 'Status']
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)
                worksheet.set_column(col, col, 20)
            
            # Add attendance data
            row = 1
            attendances = Attendance.objects.filter(classIns=class_obj).order_by('attendance_date', 'student__enrollment_number')
            
            for attendance in attendances:
                worksheet.write(row, 0, attendance.attendance_date.strftime('%Y-%m-%d'))
                worksheet.write(row, 1, attendance.student.enrollment_number)
                worksheet.write(row, 2, f"{attendance.student.first_name} {attendance.student.last_name}")
                status_map = {'1': 'Present', '2': 'Tardy', '3': 'Absent'}
                worksheet.write(row, 3, status_map.get(attendance.type, 'Unknown'))
                row += 1
            
            workbook.close()
        
        return response
        
    except Exception as e:
        print(f"Export error: {str(e)}")  # Add debug print
        messages.error(request, f"Error exporting attendance: {str(e)}")
        return redirect('faculty-data-management')

@login_required
@role_required([FACULTY_ROLE])
def import_attendance(request):
    if request.method == 'POST':
        try:
            class_id = request.POST.get('class')
            file = request.FILES.get('file')
            
            print(f"Starting import for class ID: {class_id}")  # Debug
            
            if not file:
                raise ValueError("No file was uploaded")
            
            class_obj = Class.objects.get(id=class_id)
            
            # Read Excel file, skip empty rows
            df = pd.read_excel(file)
            df = df.dropna(how='all')  # Remove completely empty rows
            print(f"Excel data after removing empty rows:\n{df}")  # Debug
            
            # Print debug information
            print("Available columns:", list(df.columns))
            
            success_count = 0
            error_count = 0
            errors = []
            
            # Keep track of student names to update
            student_names_to_update = {}
            
            # Process each row
            for index, row in df.iterrows():
                try:
                    # Skip row if any required field is empty
                    if pd.isna(row['Date']) or pd.isna(row['Student ID']) or pd.isna(row['Status']):
                        print(f"Skipping row {index + 2} due to missing required data")
                        continue
                        
                    date_val = row['Date']
                    student_id = str(row['Student ID']).strip()
                    status = str(row['Status']).strip()
                    student_name = str(row['Student Name']).strip() if 'Student Name' in row else ''
                    
                    print(f"Processing row - Date: {date_val}, Student ID: {student_id}, Status: {status}, Name: {student_name}")
                    
                    # Store student name for updating later
                    if student_name:
                        student_names_to_update[student_id] = student_name
                    
                    # Verify student is in this class
                    try:
                        student = Student.objects.get(enrollment_number=student_id)
                        if not ClassStudent.objects.filter(classIns=class_obj, student=student).exists():
                            raise ValueError(f"Student {student_id} is not enrolled in this class")
                    except Student.DoesNotExist:
                        raise ValueError(f"Student with ID {student_id} does not exist")
                    
                    print(f"Found student: {student}")
                    
                    # Convert date if needed
                    if isinstance(date_val, str):
                        date_val = datetime.strptime(date_val, '%Y-%m-%d').date()
                    elif isinstance(date_val, datetime):
                        date_val = date_val.date()
                    
                    print(f"Processed date: {date_val}")
                    
                    # Validate status
                    if status not in ['1', '2', '3']:
                        raise ValueError(f"Invalid status '{status}' for student {student_id}. Must be 1 (Present), 2 (Tardy), or 3 (Absent)")
                    
                    # Create or update attendance
                    attendance, created = Attendance.objects.update_or_create(
                        student=student,
                        classIns=class_obj,
                        attendance_date=date_val,
                        defaults={'type': status}
                    )
                    success_count += 1
                    print(f"Attendance {'created' if created else 'updated'} for {student_id}")
                    
                except Exception as e:
                    error_count += 1
                    errors.append(f"Row {index + 2}: {str(e)}")
                    print(f"Error processing row {index + 2}: {str(e)}")
            
            # Update student names after processing attendance
            if student_names_to_update:
                for student_id, name in student_names_to_update.items():
                    try:
                        # Split name into first and last name if possible
                        name_parts = name.split(maxsplit=1)
                        first_name = name_parts[0]
                        last_name = name_parts[1] if len(name_parts) > 1 else ''
                        
                        Student.objects.filter(enrollment_number=student_id).update(
                            first_name=first_name,
                            last_name=last_name
                        )
                        print(f"Updated name for student {student_id}: {name}")
                    except Exception as e:
                        print(f"Error updating name for student {student_id}: {str(e)}")
            
            if success_count > 0:
                messages.success(request, f'Successfully imported {success_count} attendance records and updated student names')
            if error_count > 0:
                messages.warning(request, f'Failed to import {error_count} records:\n' + '\n'.join(errors))
                
        except Exception as e:
            print(f"Import error: {str(e)}")
            messages.error(request, f'Error importing attendance: {str(e)}')
            
    return redirect('faculty-data-management')

@login_required
@role_required([FACULTY_ROLE])
def download_template(request):
    """View for downloading templates"""
    print("\n=== Download Template Debug Info ===")
    print(f"User: {request.user.username}")
    print(f"Is authenticated: {request.user.is_authenticated}")
    print(f"User type: {request.user.userprofile.user_type}")
    print(f"Request path: {request.path}")
    print(f"Request GET params: {request.GET}")

    template_type = request.GET.get('type')
    print(f"Template type requested: {template_type}")

    try:
        # Create workbook
        workbook = Workbook()
        sheet = workbook.active
        
        # Define headers and styling
        header_font = Font(bold=True)
        header_fill = PatternFill(start_color='E0E0E0', end_color='E0E0E0', fill_type='solid')
        
        if template_type == 'faculty':
            print("Creating faculty template")
            headers = ['Name', 'Department', 'Contact']
            sample_data = [
                ['John Doe', 'Computer Science', '1234567890'],
                ['Jane Smith', 'Computer Science', '0987654321']
            ]
            filename = 'faculty_template.xlsx'
            
        elif template_type == 'students':
            print("Creating student template")
            headers = ['Enrollment Number', 'Name', 'Course', 'Contact']
            sample_data = [
                ['2024CS001', 'John Doe', 'Computer Science', '1234567890'],
                ['2024CS002', 'Jane Smith', 'Computer Science', '0987654321']
            ]
            filename = 'students_template.xlsx'
            
        else:
            print(f"Invalid template type: {template_type}")
            return HttpResponse('Invalid template type', status=400)

        print(f"Writing headers: {headers}")
        # Write headers
        for col, header in enumerate(headers, 1):
            cell = sheet.cell(row=1, column=col)
            cell.value = header
            cell.font = header_font
            cell.fill = header_fill
        
        print("Writing sample data")
        # Write sample data
        for row_idx, row_data in enumerate(sample_data, 2):
            for col_idx, value in enumerate(row_data, 1):
                cell = sheet.cell(row=row_idx, column=col_idx)
                cell.value = value
        
        print("Creating response")
        # Create response
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        print("Saving workbook")
        # Save workbook
        workbook.save(response)
        print("Template generated successfully")
        return response
        
    except Exception as e:
        print(f"Error generating template: {str(e)}")
        print(f"Error traceback: {traceback.format_exc()}")
        return HttpResponse(f"Error generating template: {str(e)}", status=500)

@login_required
@role_required([ADMIN_ROLE])
def import_faculty(request):
    print("\n=== Import Faculty Debug Info ===")
    print(f"Request method: {request.method}")
    
    if request.method == 'POST':
        try:
            department_id = request.POST.get('department')
            excel_file = request.FILES.get('file')
            
            print(f"Department ID: {department_id}")
            print(f"File name: {excel_file.name}")
            
            if not department_id or not excel_file:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Both department and file are required.'
                })
            department = Department.objects.get(id=department_id)
            
            # Read Excel file
            if excel_file.name.endswith('.xlsx'):
                df = pd.read_excel(excel_file, engine='openpyxl')
            elif excel_file.name.endswith('.xls'):
                df = pd.read_excel(excel_file, engine='xlrd')
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Invalid file format. Please upload .xlsx or .xls file.'
                })
                
            print("Excel file read successfully")
            print(f"Columns found: {df.columns.tolist()}")
            
            success_count = 0
            errors = []
            
            # Process each row within a transaction
            with transaction.atomic():
                for index, row in df.iterrows():
                    try:
                        first_name = str(row['First Name']).strip()
                        last_name = str(row.get('Last Name', '')).strip()
                        email = str(row['Email']).strip()
                        contact = str(row.get('Contact', '')).strip()
                        
                        print(f"Processing faculty: {first_name} {last_name}")
                        
                        # Skip empty rows
                        if pd.isna(first_name) or pd.isna(email):
                            continue
                        
                        # Check if user with this email exists
                        existing_user = User.objects.filter(email=email).first()
                        if existing_user:
                            errors.append(f"Row {index + 2}: Email {email} already exists")
                            continue
                        
                        # Generate unique username
                        base_username = email.split('@')[0]
                        username = base_username
                        counter = 1
                        while User.objects.filter(username=username).exists():
                            username = f"{base_username}{counter}"
                            counter += 1
                        
                        # Create user
                        user = User.objects.create_user(
                            username=username,
                            email=email,
                            password='faculty123',  # Default password
                            first_name=first_name,
                            last_name=last_name,
                            is_staff=True
                        )
                        
                        # Delete any existing profile
                        UserProfile.objects.filter(user=user).delete()
                        
                        # Create faculty profile
                        UserProfile.objects.create(
                            user=user,
                            user_type=FACULTY_ROLE,
                            department=department,
                            contact=contact
                        )
                        
                        success_count += 1
                        print(f"Successfully created faculty: {username}")
                        
                    except Exception as e:
                        error_msg = f"Row {index + 2}: {str(e)}"
                        print(error_msg)
                        errors.append(error_msg)
            
            message = f"Successfully imported {success_count} faculty members."
            if errors:
                message += f"\nErrors in {len(errors)} rows:\n" + "\n".join(errors)
            
            return JsonResponse({
                'status': 'success' if success_count > 0 else 'error',
                'message': message,
                'errors': errors
            })
            
        except Exception as e:
            print(f"Error importing faculty: {str(e)}")
            print(f"Error traceback: {traceback.format_exc()}")
            return JsonResponse({
                'status': 'error',
                'message': f'Error importing faculty data: {str(e)}'
            })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    })

@login_required
@role_required([ADMIN_ROLE])
def import_students(request):
    print("\n=== Import Students Debug Info ===")
    print(f"Request method: {request.method}")
    
    if request.method == 'POST':
        try:
            course_id = request.POST.get('course')
            excel_file = request.FILES.get('file')
            
            print(f"Course ID: {course_id}")
            print(f"File name: {excel_file.name}")
            
            if not course_id or not excel_file:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Both course and file are required.'
                })

            course = Course.objects.get(id=course_id)
            
            # Read Excel file
            if excel_file.name.endswith('.xlsx'):
                df = pd.read_excel(excel_file, engine='openpyxl')
            elif excel_file.name.endswith('.xls'):
                df = pd.read_excel(excel_file, engine='xlrd')
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Invalid file format. Please upload .xlsx or .xls file.'
                })

            print("Excel file read successfully")
            print(f"Columns found: {df.columns.tolist()}")
            
            # Validate required columns
            required_columns = ['Enrollment Number', 'First Name']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Missing required columns: {", ".join(missing_columns)}'
                })

            success_count = 0
            errors = []
            
            # Process each row
            for index, row in df.iterrows():
                try:
                    # Extract data from row
                    enrollment_number = str(row['Enrollment Number']).strip()
                    first_name = str(row['First Name']).strip()
                    last_name = str(row.get('Last Name', '')).strip()
                    contact = str(row.get('Contact', '')).strip()
                    
                    # Skip empty rows
                    if pd.isna(enrollment_number) or pd.isna(first_name):
                        continue
                    
                    # Check if student already exists
                    if Student.objects.filter(enrollment_number=enrollment_number).exists():
                        errors.append(f"Row {index + 2}: Student with enrollment number {enrollment_number} already exists")
                        continue
                    
                    # Create student without status field
                    Student.objects.create(
                        enrollment_number=enrollment_number,
                        first_name=first_name,
                        last_name=last_name,
                        course=course,
                        contact=contact
                    )
                    success_count += 1
                    print(f"Created student: {enrollment_number} - {first_name} {last_name}")
                    
                except Exception as e:
                    error_msg = f"Row {index + 2}: {str(e)}"
                    print(error_msg)
                    errors.append(error_msg)
            
            message = f"Successfully imported {success_count} students."
            if errors:
                message += f"\nErrors in {len(errors)} rows:\n" + "\n".join(errors)
            
            return JsonResponse({
                'status': 'success' if success_count > 0 else 'error',
                'message': message,
                'errors': errors
            })
            
        except Exception as e:
            print(f"Error importing students: {str(e)}")
            print(f"Error traceback: {traceback.format_exc()}")
            return JsonResponse({
                'status': 'error',
                'message': f'Error importing students data: {str(e)}'
            })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    })

@login_required
def update_student_names(request):
    try:
        # Update student names
        student_data = [
            {'enrollment_number': '2024CS001', 'first_name': 'Suhada', 'last_name': ''},
            {'enrollment_number': '2024CS002', 'first_name': 'Student2', 'last_name': ''},
            {'enrollment_number': '2024CS003', 'first_name': 'Student3', 'last_name': ''},
            {'enrollment_number': '2024CS004', 'first_name': 'Student4', 'last_name': ''},
            {'enrollment_number': '2024CS005', 'first_name': 'Student5', 'last_name': ''}
        ]

        for data in student_data:
            Student.objects.filter(enrollment_number=data['enrollment_number']).update(
                first_name=data['first_name'],
                last_name=data['last_name']
            )

        messages.success(request, "Student names updated successfully")
    except Exception as e:
        messages.error(request, f"Error updating student names: {str(e)}")
    
    return redirect('class-page')

@login_required
@role_required([ADMIN_ROLE])
def reports(request):
    context = {
        'page_title': 'Generate Reports',
        'departments': Department.objects.all(),
        'courses': Course.objects.all()
    }
    return render(request, 'reports.html', context)

@login_required
@role_required([ADMIN_ROLE])
def generate_report(request):
    report_type = request.GET.get('type')
    
    # Create PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    # Get styles
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    
    # Initialize elements list
    elements = []
    
    if report_type == 'departments':
        status = request.GET.get('status')
        departments = Department.objects.all()
        if status != 'all':
            departments = departments.filter(status=status)
            
        elements.append(Paragraph("Departments Report", title_style))
        data = [['ID', 'Name', 'Description', 'Status']]
        for dept in departments:
            data.append([
                str(dept.id),
                dept.name,
                dept.description or '',
                'Active' if dept.status == 1 else 'Inactive'
            ])
            
    elif report_type == 'courses':
        department = request.GET.get('department')
        status = request.GET.get('status')
        courses = Course.objects.all()
        if department != 'all':
            courses = courses.filter(department_id=department)
        if status != 'all':
            courses = courses.filter(status=status)
            
        elements.append(Paragraph("Courses Report", title_style))
        data = [['ID', 'Name', 'Department', 'Status']]
        for course in courses:
            data.append([
                str(course.id),
                course.name,
                course.department.name,
                'Active' if course.status == 1 else 'Inactive'
            ])
            
    elif report_type == 'faculty':
        department = request.GET.get('department')
        faculty = UserProfile.objects.filter(user_type=2)
        if department != 'all':
            faculty = faculty.filter(department_id=department)
            
        elements.append(Paragraph("Faculty Report", title_style))
        data = [['ID', 'Name', 'Email', 'Department', 'Contact']]
        for f in faculty:
            data.append([
                str(f.id),
                f'{f.user.first_name} {f.user.last_name}',
                f.user.email,
                f.department.name if f.department else '',
                f.contact
            ])
            
    elif report_type == 'students':
        course = request.GET.get('course')
        students = Student.objects.all()
        if course != 'all':
            students = students.filter(course_id=course)
            
        elements.append(Paragraph("Students Report", title_style))
        data = [['ID', 'Enrollment', 'Name', 'Course', 'Contact']]
        for student in students:
            data.append([
                str(student.id),
                student.enrollment_number,
                f'{student.first_name} {student.last_name}',
                student.course.name,
                student.contact or ''
            ])
    
    # Create table
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    elements.append(table)
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    
    # Return PDF
    return FileResponse(
        buffer, 
        as_attachment=True, 
        filename=f'{report_type}_report.pdf'
    )

def create_sample_faculty_data(faculty_profile):
    try:
        # Create sample classes
        sample_classes = [
            {
                'name': 'CS101 - Introduction to Programming',
                'schedule': 'Monday and Wednesday, 9:00 AM - 10:30 AM',
                'course': Course.objects.get(name='Computer Science'),
                'assigned_faculty': faculty_profile,
                'status': 1
            },
            {
                'name': 'CS102 - Data Structures',
                'schedule': 'Tuesday and Thursday, 11:00 AM - 12:30 PM',
                'course': Course.objects.get(name='Computer Science'),
                'assigned_faculty': faculty_profile,
                'status': 1
            }
        ]

        # Create classes and add students
        for class_data in sample_classes:
            class_obj = Class.objects.create(**class_data)
            
            # Add sample students
            sample_students = [
                {'enrollment_number': '2024CS001', 'first_name': 'John', 'last_name': 'Doe'},
                {'enrollment_number': '2024CS002', 'first_name': 'Jane', 'last_name': 'Smith'},
                {'enrollment_number': '2024CS003', 'first_name': 'Mike', 'last_name': 'Johnson'}
            ]

            for student_data in sample_students:
                student = Student.objects.get_or_create(
                    enrollment_number=student_data['enrollment_number'],
                    defaults={
                        **student_data,
                        'course': class_data['course'],
                        'gender': 'Male',
                        'contact': '1234567890'
                    }
                )[0]

                # Add student to class
                ClassStudent.objects.get_or_create(
                    classIns=class_obj,
                    student=student
                )

        return True
    except Exception as e:
        print(f"Error creating sample faculty data: {str(e)}")
        return False

def create_default_student():
    try:
        # Check if student1 already exists
        if not User.objects.filter(username='student1').exists():
            with transaction.atomic():
                # Create user
                user = User.objects.create_user(
                    username='student1',
                    email='student1@example.com',
                    password='student123',
                    first_name='Student',
                    last_name='One',
                    is_staff=False
                )

                # Get Computer Science course
                course = Course.objects.get(name='Computer Science')

                # Create student profile
                student = Student.objects.create(
                    enrollment_number='2024CS001',
                    first_name='Student',
                    last_name='One',
                    gender='Male',
                    course=course,
                    contact='1234567890'
                )

                # Create UserProfile for student
                UserProfile.objects.create(
                    user=user,
                    user_type=3,  # Student type
                    contact='1234567890'
                )

                print("Default student created:")
                print("Username: student1")
                print("Password: student123")
                return True
    except Exception as e:
        print(f"Error creating default student: {str(e)}")
        return False

def create_sample_class_data(faculty_profile):
    try:
        # Create sample classes with more realistic data
        sample_classes = [
            {
                'name': 'CS101 - Introduction to Programming',
                'schedule': 'Monday and Wednesday, 9:00 AM - 10:30 AM',
                'course': Course.objects.get(name='Computer Science'),
                'assigned_faculty': faculty_profile,
                'status': 1
            },
            {
                'name': 'CS102 - Data Structures',
                'schedule': 'Tuesday and Thursday, 11:00 AM - 12:30 PM',
                'course': Course.objects.get(name='Computer Science'),
                'assigned_faculty': faculty_profile,
                'status': 1
            }
        ]

        # Sample students
        sample_students = [
            {'enrollment_number': '2024CS001', 'first_name': 'John', 'last_name': 'Doe'},
            {'enrollment_number': '2024CS002', 'first_name': 'Jane', 'last_name': 'Smith'},
            {'enrollment_number': '2024CS003', 'first_name': 'Mike', 'last_name': 'Johnson'},
            {'enrollment_number': '2024CS004', 'first_name': 'Sarah', 'last_name': 'Williams'},
            {'enrollment_number': '2024CS005', 'first_name': 'David', 'last_name': 'Brown'}
        ]

        # Create classes and add students
        for class_data in sample_classes:
            class_obj = Class.objects.create(**class_data)
            
            # Add students to class
            for student_data in sample_students:
                student = Student.objects.get_or_create(
                    enrollment_number=student_data['enrollment_number'],
                    defaults={
                        **student_data,
                        'course': class_data['course'],
                        'gender': 'Male',
                        'contact': '1234567890'
                    }
                )[0]

                # Add student to class
                ClassStudent.objects.get_or_create(
                    classIns=class_obj,
                    student=student
                )

                # Create attendance records for the last 30 days
                for i in range(30):
                    date = datetime.now().date() - timedelta(days=i)
                    if date.weekday() < 5:  # Only weekdays
                        Attendance.objects.get_or_create(
                            classIns=class_obj,
                            student=student,
                            attendance_date=date,
                            defaults={
                                # Random attendance: 70% present, 20% late, 10% absent
                                'type': str(random.choices([1, 2, 3], weights=[70, 20, 10])[0])
                            }
                        )

        return True
    except Exception as e:
        print(f"Error creating sample class data: {str(e)}")
        return False

@login_required
def search_students(request):
    try:
        query = request.GET.get('q', '').strip()
        class_id = request.GET.get('class_id')
        
        if not query:
            return JsonResponse({'status': 'error', 'message': 'Search query is required'})
            
        # Get the class object
        class_obj = Class.objects.get(id=class_id)
        
        # Debug prints
        print(f"Search query: '{query}'")
        print(f"Class ID: {class_id}")
        print(f"Class name: {class_obj.name}")
        
        # Get all enrolled students in this class
        enrolled_student_ids = ClassStudent.objects.filter(
            classIns=class_obj
        ).values_list('student_id', flat=True)
        
        # Search for students with broader criteria
        students = Student.objects.filter(
            id__in=enrolled_student_ids
        ).filter(
            Q(enrollment_number__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(first_name__istartswith=query) |
            Q(last_name__istartswith=query)
        ).distinct()
        
        # Debug print all students found
        print(f"Found {students.count()} matching students:")
        for s in students:
            print(f"- ID: {s.id}, Name: {s.first_name} {s.last_name}, Enrollment: {s.enrollment_number}")
        
        # Format student data
        student_data = []
        for student in students:
            # Get latest attendance for this student
            latest_attendance = Attendance.objects.filter(
                student=student,
                classIns=class_obj
            ).order_by('-attendance_date').first()
            
            data = {
                'id': student.id,
                'enrollment_number': student.enrollment_number,
                'name': f"{student.first_name} {student.last_name}".strip(),
                'course': student.course.name if student.course else '',
                'latest_attendance': {
                    'date': latest_attendance.attendance_date.strftime('%Y-%m-%d') if latest_attendance else None,
                    'status': latest_attendance.type if latest_attendance else None
                }
            }
            student_data.append(data)
            print(f"Added to results: {data}")

        return JsonResponse({
            'status': 'success',
            'students': student_data,
            'total_found': len(student_data)
        })
        
    except Exception as e:
        print(f"Search error: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })

@login_required
@role_required([ADMIN_ROLE])
def admin_search(request):
    try:
        query = request.GET.get('q', '').strip()
        if not query:
            return JsonResponse({
                'status': 'error',
                'message': 'Search query is required'
            })

        # Search in different models
        results = {
            'departments': [],
            'courses': [],
            'faculty': [],
            'students': []
        }

        # Search departments
        departments = Department.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )[:5]
        for dept in departments:
            results['departments'].append({
                'name': dept.name,
                'url': reverse('department-page')  # Add specific department URL if needed
            })

        # Search courses
        courses = Course.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )[:5]
        for course in courses:
            results['courses'].append({
                'name': course.name,
                'url': reverse('course-page')  # Add specific course URL if needed
            })

        # Search faculty
        faculty = UserProfile.objects.filter(
            user_type=FACULTY_ROLE
        ).filter(
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(user__email__icontains=query)
        )[:5]
        for f in faculty:
            results['faculty'].append({
                'name': f'{f.user.first_name} {f.user.last_name}',
                'url': reverse('faculty-page')  # Add specific faculty URL if needed
            })

        # Search students
        students = Student.objects.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(enrollment_number__icontains=query)
        )[:5]
        for student in students:
            results['students'].append({
                'name': f'{student.first_name} {student.last_name} ({student.enrollment_number})',
                'url': reverse('student-page')  # Add specific student URL if needed
            })

        return JsonResponse({
            'status': 'success',
            'results': results
        })

    except Exception as e:
        print(f"Admin search error: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })

def setup_default_data():
    try:
        print("Starting setup...")
        
        # First clean up existing data in the correct order
        print("Cleaning up existing data...")
        with transaction.atomic():
            # Delete attendance records first
            Attendance.objects.all().delete()
            print("Deleted attendance records")
            
            # Delete class student relationships
            ClassStudent.objects.all().delete()
            print("Deleted class student relationships")
            
            # Delete classes
            Class.objects.all().delete()
            print("Deleted classes")
            
            # Delete students
            Student.objects.all().delete()
            print("Deleted students")
            
            # Delete courses
            Course.objects.all().delete()
            print("Deleted courses")
            
            # Delete departments
            Department.objects.all().delete()
            print("Deleted departments")
            
            # Delete user profiles
            UserProfile.objects.all().delete()
            print("Deleted user profiles")
            
            # Delete all users
            User.objects.all().delete()
            print("Deleted users")
            
            print("Database cleaned successfully")
            
            # Now create new data
            print("\nCreating new data...")
            
            # 1. Create default admin
            admin_user = User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123'
            )
            print("Created admin user")

            # 2. Create default department
            department = Department.objects.create(
                name='Computer Science',
                description='Department of Computer Science',
                status=1
            )
            print("Created department")

            # 3. Create default course
            course = Course.objects.create(
                name='Computer Science',
                department=department,
                description='Bachelor of Computer Science',
                status=1
            )
            print("Created course")

            # 4. Create default faculty
            faculty_user = User.objects.create_user(
                username='faculty1',
                password='faculty123',
                email='faculty1@example.com',
                first_name='Faculty',
                last_name='One',
                is_staff=True
            )
            
            faculty_profile = UserProfile.objects.create(
                user=faculty_user,
                user_type=2,  # Faculty type
                department=department,
                contact='1234567890'
            )
            print("Created faculty")

            # 5. Create default students with user accounts
            student_data = [
                {'username': 'student1', 'enrollment_number': '2024CS001', 'first_name': 'Suhada', 'last_name': ''},
                {'username': 'student2', 'enrollment_number': '2024CS002', 'first_name': 'Student2', 'last_name': ''},
                {'username': 'student3', 'enrollment_number': '2024CS003', 'first_name': 'Student3', 'last_name': ''},
                {'username': 'student4', 'enrollment_number': '2024CS004', 'first_name': 'Student4', 'last_name': ''},
                {'username': 'student5', 'enrollment_number': '2024CS005', 'first_name': 'Student5', 'last_name': ''}
            ]

            for data in student_data:
                # Create user account for student
                student_user = User.objects.create_user(
                    username=data['username'],
                    password='student123',
                    email=f"{data['username']}@example.com",
                    first_name=data['first_name'],
                    last_name=data['last_name']
                )
                
                # Create student profile
                UserProfile.objects.create(
                    user=student_user,
                    user_type=3,  # Student type
                    contact='1234567890'
                )
                
                # Create student record
                Student.objects.create(
                    enrollment_number=data['enrollment_number'],
                    first_name=data['first_name'],
                    last_name=data['last_name'],
                    course=course,
                    status=1
                )
            print("Created students")

            # 6. Create default class
            class_obj = Class.objects.create(
                name='Machine Learning',
                course=course,
                assigned_faculty=faculty_profile,
                schedule='Monday and Wednesday, 9:00 AM - 10:30 AM',
                status=1
            )
            print("Created class")

            # 7. Enroll students in class
            for student in Student.objects.all():
                ClassStudent.objects.create(
                    classIns=class_obj,
                    student=student
                )
            print("Enrolled students in class")

            print("\nSetup completed successfully!")
            print("\nLogin Credentials:")
            print("------------------")
            print("Admin:")
            print("Username: admin")
            print("Password: admin123")
            print("\nFaculty:")
            print("Username: faculty1")
            print("Password: faculty123")
            print("\nStudents:")
            print("Username: student1 through student5")
            print("Password: student123 (same for all students)")

            return True
            
    except Exception as e:
        print(f"Error in setup: {str(e)}")
        print("Rolling back all changes...")
        return False

@login_required
def download_attendance_template(request):
    """View for downloading attendance template for faculty"""
    print("\n=== Download Attendance Template Debug Info ===")
    print(f"User: {request.user.username}")
    print(f"User type: {request.user.profile.user_type}")
    
    class_id = request.GET.get('class')
    if not class_id:
        messages.error(request, "Class ID is required")
        return redirect('faculty-data-management')
        
    try:
        class_obj = Class.objects.get(id=class_id)
        students = ClassStudent.objects.filter(classIns=class_obj)
        
        workbook = Workbook()
        sheet = workbook.active
        
        # Headers
        headers = ['Student ID', 'Name', 'Status', 'Remarks']
        for col, header in enumerate(headers, 1):
            cell = sheet.cell(row=1, column=col)
            cell.value = header
            cell.font = Font(bold=True)
        
        # Student data
        for idx, student in enumerate(students, 2):
            sheet.cell(row=idx, column=1).value = student.student.enrollment_number
            sheet.cell(row=idx, column=2).value = f"{student.student.first_name} {student.student.last_name}"
            sheet.cell(row=idx, column=3).value = "Present"  # Default value
            sheet.cell(row=idx, column=4).value = ""  # Empty remarks
        
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="attendance_template_{class_obj.name}.xlsx"'
        
        workbook.save(response)
        return response
        
    except Exception as e:
        print(f"Error generating attendance template: {str(e)}")
        messages.error(request, f"Error generating template: {str(e)}")
        return redirect('faculty-data-management')

@login_required
@role_required([ADMIN_ROLE])
def admin_download_template(request):
    try:
        workbook = Workbook()
        sheet = workbook.active
        
        if request.GET.get('type') == 'faculty':
            # Faculty template (existing code)
            headers = ['First Name', 'Last Name', 'Email', 'Contact']
            sample_data = [
                ['John', 'Doe', 'john.doe@example.com', '1234567890'],
                ['Jane', 'Smith', 'jane.smith@example.com', '0987654321']
            ]
            filename = 'faculty_template.xlsx'
            
        elif request.GET.get('type') == 'students':
            # Updated student template with consistent column names
            headers = ['Enrollment Number', 'First Name', 'Last Name', 'Email', 'Contact']
            sample_data = [
                ['2024CS001', 'John', 'Doe', 'john.s@example.com', '1234567890'],
                ['2024CS002', 'Jane', 'Smith', 'jane.s@example.com', '0987654321']
            ]
            filename = 'students_template.xlsx'
            
        else:
            return HttpResponse('Invalid template type', status=400)
        
        # Write headers and style them
        for col, header in enumerate(headers, 1):
            cell = sheet.cell(row=1, column=col)
            cell.value = header
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color='E0E0E0', end_color='E0E0E0', fill_type='solid')
        
        # Write sample data
        for row_idx, row_data in enumerate(sample_data, 2):
            for col_idx, value in enumerate(row_data, 1):
                cell = sheet.cell(row=row_idx, column=col_idx)
                cell.value = value
        
        # Adjust column widths
        for col in sheet.columns:
            max_length = 0
            column = col[0].column_letter
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
                adjusted_width = (max_length + 2)
                sheet.column_dimensions[column].width = adjusted_width
        
        # Create response
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        workbook.save(response)
        return response
        
    except Exception as e:
        print(f"Error generating template: {str(e)}")
        print(f"Error traceback: {traceback.format_exc()}")
        return HttpResponse(f"Error generating template: {str(e)}", status=500)

@login_required
@role_required([FACULTY_ROLE])
def attendance_class(request):
    """View for faculty to manage class attendance"""
    try:
        # Get classes assigned to this faculty
        faculty_classes = Class.objects.filter(assigned_faculty=request.user.profile)
        print(f"Found {faculty_classes.count()} classes for faculty")
        
        context = {
            'page_title': 'Class Attendance',
            'classes': faculty_classes
        }
        
        # Use attendance.html template
        return render(request, 'faculty/attendance.html', context)
        
    except Exception as e:
        print(f"Error in attendance_class view: {str(e)}")
        messages.error(request, f"Error loading attendance: {str(e)}")
        return redirect('home-page')

@login_required
def attendance(request, classPK, date=None):
    """View for managing attendance for a specific class"""
    try:
        print("\n=== Attendance View Debug Info ===")
        print(f"Class PK: {classPK}")
        print(f"Date: {date}")
        
        # Get the class object
        class_obj = Class.objects.get(id=classPK)
        
        # Get enrolled students
        class_students = ClassStudent.objects.filter(classIns=class_obj).select_related('student')
        
        # If date is provided, get that day's attendance, else get today's
        if date:
            attendance_date = datetime.strptime(date, '%Y-%m-%d').date()
        else:
            attendance_date = datetime.now().date()
            
        print(f"Attendance date: {attendance_date}")
        
        # Get attendance records for the date
        attendance_records = Attendance.objects.filter(
            classIns=class_obj,
            attendance_date=attendance_date
        )
        
        # Create a list of students with their attendance status
        students_attendance = []
        for cs in class_students:
            attendance = attendance_records.filter(student=cs.student).first()
            students_attendance.append({
                'student': cs.student,
                'attendance': attendance.type if attendance else None
            })
        
        context = {
            'page_title': f"Attendance - {class_obj.name}",
            'class': class_obj,
            'students': students_attendance,
            'attendance_date': attendance_date,
        }
        
        print(f"Found {len(students_attendance)} students")
        print(f"Found {attendance_records.count()} attendance records")
        
        # Use the correct template path
        return render(request, 'faculty/attendance_mgt.html', context)
            
    except Exception as e:
        print(f"Error in attendance view: {str(e)}")
        print(f"Error traceback: {traceback.format_exc()}")
        messages.error(request, f"Error loading attendance: {str(e)}")
        return redirect('attendance-class')

@login_required
def save_attendance(request):
    print("\n=== Save Attendance Debug Info ===")
    print(f"Request method: {request.method}")
    print(f"POST data: {request.POST}")
    
    resp = {'status': 'failed', 'msg': ''}
    if request.method == 'POST':
        try:
            with transaction.atomic():
                data = request.POST
                class_id = data.get('class_id')
                attendance_date = data.get('attendance_date')
                
                print(f"Class ID: {class_id}")
                print(f"Attendance Date: {attendance_date}")
                
                if not class_id or not attendance_date:
                    resp['msg'] = 'Class and date are required.'
                    return JsonResponse(resp)
                
                class_obj = Class.objects.get(id=class_id)
                
                # Delete existing attendance records for this class and date
                Attendance.objects.filter(
                    classIns=class_obj,
                    attendance_date=attendance_date
                ).delete()
                
                # Process attendance for each student
                for key, value in data.items():
                    if key.startswith('student_'):
                        student_id = key.replace('student_', '')
                        attendance_type = value
                        
                        print(f"Processing student {student_id} with status {attendance_type}")
                        
                        # Create new attendance record
                        Attendance.objects.create(
                            classIns=class_obj,
                            student_id=student_id,
                            attendance_date=attendance_date,
                            type=attendance_type
                        )
                
                resp['status'] = 'success'
                resp['msg'] = 'Attendance saved successfully.'
                
        except Exception as e:
            print(f"Error saving attendance: {str(e)}")
            print(f"Error traceback: {traceback.format_exc()}")
            resp['msg'] = str(e)
    
    print(f"Returning response: {resp}")
    return JsonResponse(resp)

@login_required
@role_required([ADMIN_ROLE])
def export_data(request):
    """View for exporting data"""
    print("\n=== Export Data Debug Info ===")
    print(f"Request method: {request.method}")
    
    try:
        data_type = request.GET.get('type')
        print(f"Export type requested: {data_type}")
        
        if data_type == 'faculty':
            # Export faculty data
            faculty_list = UserProfile.objects.filter(user_type=FACULTY_ROLE)
            
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Faculty Data"
            
            # Write headers
            headers = ['Name', 'Email', 'Department', 'Contact']
            for col, header in enumerate(headers, 1):
                cell = sheet.cell(row=1, column=col)
                cell.value = header
                cell.font = Font(bold=True)
            
            # Write data
            for idx, faculty in enumerate(faculty_list, 2):
                sheet.cell(row=idx, column=1).value = f"{faculty.user.first_name} {faculty.user.last_name}"
                sheet.cell(row=idx, column=2).value = faculty.user.email
                sheet.cell(row=idx, column=3).value = faculty.department.name
                sheet.cell(row=idx, column=4).value = faculty.contact
            
            filename = "faculty_data.xlsx"
            
        elif data_type == 'students':
            # Export student data
            students = Student.objects.all()
            
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Student Data"
            
            # Write headers
            headers = ['Enrollment Number', 'Name', 'Course', 'Contact']
            for col, header in enumerate(headers, 1):
                cell = sheet.cell(row=1, column=col)
                cell.value = header
                cell.font = Font(bold=True)
            
            # Write data
            for idx, student in enumerate(students, 2):
                sheet.cell(row=idx, column=1).value = student.enrollment_number
                sheet.cell(row=idx, column=2).value = f"{student.first_name} {student.last_name}"
                sheet.cell(row=idx, column=3).value = student.course.name
                sheet.cell(row=idx, column=4).value = student.contact
            
            filename = "student_data.xlsx"
            
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid export type'
            })
        
        # Create response
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        workbook.save(response)
        return response
        
    except Exception as e:
        print(f"Error exporting data: {str(e)}")
        print(f"Error traceback: {traceback.format_exc()}")
        return JsonResponse({
            'status': 'error',
            'message': f'Error exporting data: {str(e)}'
        })

@login_required
@role_required([ADMIN_ROLE])
def process_bulk_upload(request):
    """View for handling bulk uploads"""
    print("\n=== Process Bulk Upload Debug Info ===")
    print(f"Request method: {request.method}")
    
    if request.method == 'POST':
        try:
            upload_type = request.POST.get('type')
            file = request.FILES.get('file')
            
            print(f"Upload type: {upload_type}")
            print(f"File name: {file.name if file else 'No file'}")
            
            if not upload_type or not file:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Both type and file are required.'
                })

            # Read Excel file
            if file.name.endswith('.xlsx'):
                df = pd.read_excel(file, engine='openpyxl')
            elif file.name.endswith('.xls'):
                df = pd.read_excel(file, engine='xlrd')
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Invalid file format. Please upload .xlsx or .xls file.'
                })

            success_count = 0
            errors = []
            
            if upload_type == 'faculty':
                # Process faculty data
                department_id = request.POST.get('department')
                if not department_id:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Department is required for faculty upload.'
                    })
                
                department = Department.objects.get(id=department_id)
                
                # Process each row
                for index, row in df.iterrows():
                    try:
                        # Create faculty
                        success_count += 1
                    except Exception as e:
                        errors.append(f"Row {index + 2}: {str(e)}")
                        
            elif upload_type == 'students':
                # Process student data
                course_id = request.POST.get('course')
                if not course_id:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Course is required for student upload.'
                    })
                
                course = Course.objects.get(id=course_id)
                
                # Process each row
                for index, row in df.iterrows():
                    try:
                        # Create student
                        success_count += 1
                    except Exception as e:
                        errors.append(f"Row {index + 2}: {str(e)}")
            
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Invalid upload type.'
                })

            message = f"Successfully processed {success_count} records."
            if errors:
                message += f"\nErrors in {len(errors)} rows:\n" + "\n".join(errors)
            
            return JsonResponse({
                'status': 'success' if success_count > 0 else 'error',
                'message': message,
                'errors': errors
            })
            
        except Exception as e:
            print(f"Error processing bulk upload: {str(e)}")
            print(f"Error traceback: {traceback.format_exc()}")
            return JsonResponse({
                'status': 'error',
                'message': f'Error processing bulk upload: {str(e)}'
            })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    })

@login_required
def leave_application(request):
    """View for handling leave applications"""
    print("\n=== Leave Application Debug Info ===")
    print(f"User: {request.user.username}")
    print(f"User type: {request.user.profile.user_type}")
    
    try:
        if request.user.profile.user_type == STUDENT_ROLE:
            # For students
            student = Student.objects.get(enrollment_number=request.user.username)
            applications = LeaveApplication.objects.filter(student=student).order_by('-created_at')
            
            context = {
                'page_title': 'Leave Application',
                'applications': applications
            }
            return render(request, 'student/leave_application.html', context)
            
        elif request.user.profile.user_type == FACULTY_ROLE:
            # For faculty
            applications = LeaveApplication.objects.filter(
                student__classstudent__classIns__assigned_faculty=request.user.profile
            ).order_by('-created_at')
            
            context = {
                'page_title': 'Student Leave Applications',
                'applications': applications
            }
            return render(request, 'faculty/leave_applications.html', context)
            
        else:
            # For admin
            applications = LeaveApplication.objects.all().order_by('-created_at')
            context = {
                'page_title': 'All Leave Applications',
                'applications': applications
            }
            return render(request, 'superuser/leave_applications.html', context)
            
    except Exception as e:
        print(f"Error in leave_application view: {str(e)}")
        print(f"Error traceback: {traceback.format_exc()}")
        messages.error(request, f"Error loading leave applications: {str(e)}")
        return redirect('home-page')

@login_required
def submit_leave(request):
    """View for submitting leave applications"""
    print("\n=== Submit Leave Debug Info ===")
    print(f"Request method: {request.method}")
    
    if request.method == 'POST':
        try:
            student = Student.objects.get(enrollment_number=request.user.username)
            
            # Create leave application
            leave = LeaveApplication.objects.create(
                student=student,
                start_date=request.POST.get('start_date'),
                end_date=request.POST.get('end_date'),
                reason=request.POST.get('reason'),
                status='pending'
            )
            
            messages.success(request, 'Leave application submitted successfully')
            return redirect('leave-application')
            
        except Exception as e:
            print(f"Error submitting leave: {str(e)}")
            print(f"Error traceback: {traceback.format_exc()}")
            messages.error(request, f"Error submitting leave: {str(e)}")
            return redirect('leave-application')
    
    return redirect('leave-application')

@login_required
@role_required([ADMIN_ROLE])
def create_default_courses(request):
    """View for creating default courses"""
    print("\n=== Create Default Courses Debug Info ===")
    print(f"User: {request.user.username}")
    
    try:
        # Get or create Computer Science department
        department, _ = Department.objects.get_or_create(
            name='Computer Science',
            defaults={
                'description': 'Department of Computer Science',
                'status': 1
            }
        )
        
        # Default courses data
        default_courses = [
            {
                'name': 'B.Tech Computer Science',
                'description': 'Bachelor of Technology in Computer Science',
                'department': department
            },
            {
                'name': 'M.Tech Computer Science',
                'description': 'Master of Technology in Computer Science',
                'department': department
            }
        ]
        
        courses_created = 0
        for course_data in default_courses:
            course, created = Course.objects.get_or_create( 
                name=course_data['name'],
                defaults={
                    'description': course_data['description'],
                    'department': course_data['department'],
                    'status': 1
                }
            )
            if created:
                courses_created += 1
                print(f"Created course: {course.name}")
        
        messages.success(request, f'Successfully created {courses_created} default courses')
        
    except Exception as e:
        print(f"Error creating default courses: {str(e)}")
        print(f"Error traceback: {traceback.format_exc()}")
        messages.error(request, f"Error creating default courses: {str(e)}")
    
    return redirect('course-page')

@login_required
@role_required([ADMIN_ROLE])
def academic_units(request):
    """View for managing academic units (departments and courses)"""
    print("\n=== Academic Units Debug Info ===")
    print(f"User: {request.user.username}")
    print(f"User type: {request.user.profile.user_type}")
    
    try:
        context = {
            'page_title': 'Academic Units',
            'departments': Department.objects.all().order_by('name'),
            'courses': Course.objects.all().order_by('name')
        }
        
        print(f"Found {context['departments'].count()} departments")
        print(f"Found {context['courses'].count()} courses")
        
        return render(request, 'superuser/academic_units.html', context)
        
    except Exception as e:
        print(f"Error in academic_units view: {str(e)}")
        print(f"Error traceback: {traceback.format_exc()}")
        messages.error(request, f"Error loading academic units: {str(e)}")
        return redirect('home-page')

@login_required
@role_required([ADMIN_ROLE])
def register(request):
    """View for user registration"""
    print("\n=== Register Debug Info ===")
    print(f"Request method: {request.method}")
    
    if request.method == 'POST':
        try:
            form = UserRegistration(request.POST)
            if form.is_valid():
                user = form.save(commit=False)
                user.save()
                
                # Create user profile
                profile = UserProfile.objects.create(
                    user=user,
                    user_type=request.POST.get('user_type', STUDENT_ROLE),
                    contact=request.POST.get('contact', ''),
                    department_id=request.POST.get('department')
                )
                
                messages.success(request, 'User registered successfully')
                return redirect('home-page')
            else:
                messages.error(request, 'Error registering user. Please check the form.')
        except Exception as e:
            print(f"Error in registration: {str(e)}")
            print(f"Error traceback: {traceback.format_exc()}")
            messages.error(request, f'Error registering user: {str(e)}')
    else:
        form = UserRegistration()
    
    context = {
        'page_title': 'Register User',
        'form': form,
        'departments': Department.objects.filter(status=1)
    }
    return render(request, 'registration/register.html', context)

@login_required
@role_required([ADMIN_ROLE])
def create_default_users(request):
    """View for creating default users"""
    print("\n=== Create Default Users Debug Info ===")
    print(f"User: {request.user.username}")
    
    try:
        # Create default admin user if doesn't exist
        admin_user, admin_created = User.objects.get_or_create(
            username='admin',
            defaults={
                'first_name': 'Admin',
                'last_name': 'User',
                'email': 'admin@edulink.com',
                'is_staff': True,
                'is_superuser': True
            }
        )
        if admin_created:
            admin_user.set_password('admin123')
            admin_user.save()
            UserProfile.objects.create(
                user=admin_user,
                user_type=ADMIN_ROLE,
                contact='1234567890'
            )
            print("Created admin user")

        # Create default faculty user
        faculty_user, faculty_created = User.objects.get_or_create(
            username='faculty',
            defaults={
                'first_name': 'Faculty',
                'last_name': 'User',
                'email': 'faculty@edulink.com'
            }
        )
        if faculty_created:
            faculty_user.set_password('faculty123')
            faculty_user.save()
            department = Department.objects.first()  # Get first department
            UserProfile.objects.create(
                user=faculty_user,
                user_type=FACULTY_ROLE,
                contact='9876543210',
                department=department
            )
            print("Created faculty user")

        # Create default student user
        student_user, student_created = User.objects.get_or_create(
            username='student',
            defaults={
                'first_name': 'Student',
                'last_name': 'User',
                'email': 'student@edulink.com'
            }
        )
        if student_created:
            student_user.set_password('student123')
            student_user.save()
            UserProfile.objects.create(
                user=student_user,
                user_type=STUDENT_ROLE,
                contact='5555555555'
            )
            # Create student record
            course = Course.objects.first()  # Get first course
            if course:
                Student.objects.create(
                    enrollment_number='STU001',
                    first_name='Student',
                    last_name='User',
                    course=course,
                    contact='5555555555'
                )
            print("Created student user")

        created_count = sum([admin_created, faculty_created, student_created])
        messages.success(request, f'Successfully created {created_count} default users')
        
    except Exception as e:
        print(f"Error creating default users: {str(e)}")
        print(f"Error traceback: {traceback.format_exc()}")
        messages.error(request, f"Error creating default users: {str(e)}")
    
    return redirect('home-page')

@login_required
@role_required([FACULTY_ROLE])
def faculty_students(request):
    """View for faculty to see all their students"""
    try:
        # Get all classes taught by this faculty
        faculty_classes = Class.objects.filter(assigned_faculty=request.user.profile)
        
        # Get all students enrolled in these classes
        enrolled_students = Student.objects.filter(
            classstudent__classIns__in=faculty_classes
        ).distinct()
        
        context = {
            'page_title': 'My Students',
            'students': enrolled_students,
            'classes': faculty_classes  # For the add student form
        }
        
        return render(request, 'faculty/students.html', context)
        
    except Exception as e:
        messages.error(request, f"Error loading students: {str(e)}")
        return redirect('home-page')

@login_required
@role_required([FACULTY_ROLE])
def faculty_add_student(request):
    if request.method == 'POST':
        try:
            # Get form data
            enrollment_number = request.POST.get('enrollment_number')
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            class_id = request.POST.get('class')
            contact = request.POST.get('contact', '')
            
            # Validate required fields
            if not all([enrollment_number, first_name, class_id]):
                raise ValueError("Enrollment number, name and class are required")
            
            # Get the class object and verify faculty teaches it
            class_obj = Class.objects.get(
                id=class_id, 
                assigned_faculty=request.user.profile
            )
            
            # Create or update student
            student, created = Student.objects.get_or_create(
                enrollment_number=enrollment_number,
                defaults={
                    'first_name': first_name,
                    'last_name': last_name,
                    'contact': contact,
                    'course': class_obj.course
                }
            )
            
            if not created:
                # Update existing student
                student.first_name = first_name
                student.last_name = last_name
                student.contact = contact
                student.save()
            
            # Add student to class if not already enrolled
            ClassStudent.objects.get_or_create(
                student=student,
                classIns=class_obj
            )
            
            messages.success(request, 'Student added successfully')
            return JsonResponse({'status': 'success'})
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })
    
    # GET request - return form template
    try:
        faculty_classes = Class.objects.filter(assigned_faculty=request.user.profile)
        context = {
            'classes': faculty_classes
        }
        return render(request, 'faculty/add_student.html', context)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })

@login_required
@role_required([FACULTY_ROLE])
def faculty_import_students(request):
    if request.method == 'POST':
        try:
            class_id = request.POST.get('class')
            file = request.FILES.get('file')
            
            if not class_id or not file:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Both class and file are required.'
                })

            # Get the class and verify faculty teaches it
            class_obj = Class.objects.get(
                id=class_id,
                assigned_faculty=request.user.profile
            )
            
            # Read Excel file
            if file.name.endswith('.xlsx'):
                df = pd.read_excel(file, engine='openpyxl')
            elif file.name.endswith('.xls'):
                df = pd.read_excel(file, engine='xlrd')
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Invalid file format. Please upload .xlsx or .xls file.'
                })

            success_count = 0
            errors = []
            
            # Process each row
            for index, row in df.iterrows():
                try:
                    enrollment_number = str(row['Enrollment Number']).strip()
                    first_name = str(row['First Name']).strip()
                    last_name = str(row.get('Last Name', '')).strip()
                    contact = str(row.get('Contact', '')).strip()
                    
                    if pd.isna(enrollment_number) or pd.isna(first_name):
                        continue
                    
                    # Create or update student
                    student, created = Student.objects.get_or_create(
                        enrollment_number=enrollment_number,
                        defaults={
                            'first_name': first_name,
                            'last_name': last_name,
                            'contact': contact,
                            'course': class_obj.course
                        }
                    )
                    
                    # Add student to class
                    ClassStudent.objects.get_or_create(
                        student=student,
                        classIns=class_obj
                    )
                    
                    success_count += 1
                    
                except Exception as e:
                    errors.append(f"Row {index + 2}: {str(e)}")
            
            return JsonResponse({
                'status': 'success',
                'message': f'Successfully imported {success_count} students. {len(errors)} errors.',
                'errors': errors
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    })

@login_required
@role_required([FACULTY_ROLE])
def faculty_download_template(request):
    """View for faculty to download student import template"""
    try:
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Students Import"
        
        # Add headers
        headers = ['Enrollment Number', 'First Name', 'Last Name', 'Contact']
        for col, header in enumerate(headers, 1):
            cell = sheet.cell(row=1, column=col)
            cell.value = header
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color='E0E0E0', end_color='E0E0E0', fill_type='solid')
        
        # Add sample data
        sample_data = [
            ['2024CS001', 'John', 'Doe', '1234567890'],
            ['2024CS002', 'Jane', 'Smith', '0987654321']
        ]
        
        for row_idx, row_data in enumerate(sample_data, 2):
            for col_idx, value in enumerate(row_data, 1):
                cell = sheet.cell(row=row_idx, column=col_idx)
                cell.value = value
        
        # Create response
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="student_import_template.xlsx"'
        
        workbook.save(response)
        return response
        
    except Exception as e:
        print(f"Error generating template: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })