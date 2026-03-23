from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Count, Q
from accounts.decorators import role_required
from accounts.models import User
from .models import School, GlobalCourse
from .forms import SchoolForm, SchoolAdminForm, GlobalCourseForm


@role_required('super_admin')
def dashboard(request):
    from classrooms.models import Classroom
    schools = School.objects.annotate(
        student_count=Count('users', filter=Q(users__role='student')),
        teacher_count=Count('users', filter=Q(users__role='teacher')),
    )
    context = {
        'schools':          schools,
        'total_schools':    School.objects.count(),
        'total_students':   User.objects.filter(role='student').count(),
        'total_teachers':   User.objects.filter(role='teacher').count(),
        'total_classrooms': Classroom.objects.count(),
    }
    return render(request, 'superadmin/dashboard.html', context)


@role_required('super_admin')
def schools_list(request):
    schools = School.objects.all().order_by('-created_at')
    return render(request, 'superadmin/schools_list.html', {'schools': schools})


@role_required('super_admin')
def school_detail(request, school_id):
    school   = get_object_or_404(School, pk=school_id)
    teachers = User.objects.filter(school=school, role='teacher')
    students = User.objects.filter(school=school, role='student')
    from classrooms.models import Classroom
    classrooms = Classroom.objects.filter(school=school)
    return render(request, 'superadmin/school_detail.html', {
        'school': school, 'teachers': teachers,
        'students': students, 'classrooms': classrooms,
    })


@role_required('super_admin')
def create_school(request):
    form = SchoolForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        school = form.save()
        messages.success(request, f'School "{school.name}" created.')
        return redirect('superadmin_dashboard')
    return render(request, 'superadmin/schools_list.html', {'form': form, 'mode': 'create'})


@role_required('super_admin')
def create_school_admin(request):
    form = SchoolAdminForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        cd       = form.cleaned_data
        school   = cd['school']
        email    = cd['email']
        password = cd['password']
        if User.objects.filter(email=email).exists():
            messages.error(request, 'A user with this email already exists.')
        else:
            base = email.split('@')[0]; username = base; i = 1
            while User.objects.filter(username=username).exists():
                username = f'{base}{i}'; i += 1
            user = User.objects.create(
                username=username, email=email,
                role='school_admin', school=school,
                is_staff=False,
            )
            user.set_password(password)
            user.save()
            from django.core.mail import send_mail
            send_mail(
                'Your EduPlatform School Admin Account',
                f'Login: {email}\nPassword: {password}\nURL: /login/',
                'noreply@eduplatform.com', [email], fail_silently=True,
            )
            messages.success(request, f'School admin created for {school.name}.')
            return redirect('superadmin_dashboard')
    schools = School.objects.filter(is_active=True)
    return render(request, 'superadmin/dashboard.html', {
        'admin_form': form, 'schools': schools, 'mode': 'create_admin'
    })


@role_required('super_admin')
def toggle_school(request, school_id):
    school = get_object_or_404(School, pk=school_id)
    school.is_active = not school.is_active
    school.save()
    messages.success(request, f'School "{school.name}" {"activated" if school.is_active else "suspended"}.')
    return redirect('superadmin_schools_list')


@role_required('super_admin')
def all_admins(request):
    admins = User.objects.filter(role='school_admin').select_related('school')
    return render(request, 'superadmin/dashboard.html', {'admins': admins, 'mode': 'admins'})


@role_required('super_admin')
def course_create(request):
    form = GlobalCourseForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        course = form.save(commit=False)
        course.created_by = request.user
        course.save()
        messages.success(request, 'Course created.')
        return redirect('superadmin_dashboard')
    return render(request, 'superadmin/course_create.html', {'form': form})
