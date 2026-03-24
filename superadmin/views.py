from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Q
from accounts.decorators import role_required
from accounts.models import User
from .models import School, GlobalCourse, GlobalConcept
from .forms import SchoolForm, SchoolEditForm, AdminEditForm, GlobalCourseForm, GlobalConceptForm


@role_required('super_admin')
def dashboard(request):
    from classrooms.models import Classroom
    schools = School.objects.annotate(
        student_count=Count('users', filter=Q(users__role='student')),
        teacher_count=Count('users', filter=Q(users__role='teacher')),
    )
    courses = GlobalCourse.objects.prefetch_related('schools', 'concepts').order_by('-created_at')
    context = {
        'schools':          schools,
        'courses':          courses,
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
    school     = get_object_or_404(School, pk=school_id)
    admin      = User.objects.filter(school=school, role='school_admin').first()
    teachers   = User.objects.filter(school=school, role='teacher')
    students   = User.objects.filter(school=school, role='student')
    management = User.objects.filter(school=school, role='management')
    from classrooms.models import Classroom
    classrooms = Classroom.objects.filter(school=school)
    return render(request, 'superadmin/school_detail.html', {
        'school': school, 'admin': admin,
        'teachers': teachers, 'students': students,
        'management': management, 'classrooms': classrooms,
    })


@role_required('super_admin')
def school_edit(request, school_id):
    """AJAX endpoint — edits school info or admin info."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    school  = get_object_or_404(School, pk=school_id)
    section = request.POST.get('section')   # 'school' or 'admin'

    if section == 'school':
        form = SchoolEditForm(request.POST, instance=school)
        if form.is_valid():
            form.save()
            return JsonResponse({
                'success': True,
                'name':    school.name,
                'address': school.address,
            })
        return JsonResponse({'error': list(form.errors.values())[0][0]}, status=400)

    elif section == 'admin':
        admin = User.objects.filter(school=school, role='school_admin').first()
        if not admin:
            return JsonResponse({'error': 'No admin found for this school.'}, status=404)
        # check email uniqueness if changed
        new_email = request.POST.get('email', '').strip()
        if new_email != admin.email and User.objects.filter(email=new_email).exclude(pk=admin.pk).exists():
            return JsonResponse({'error': 'This email is already in use.'}, status=400)
        form = AdminEditForm(request.POST, instance=admin)
        if form.is_valid():
            form.save()
            return JsonResponse({
                'success':    True,
                'full_name':  admin.get_full_name() or admin.username,
                'email':      admin.email,
                'username':   admin.username,
            })
        return JsonResponse({'error': list(form.errors.values())[0][0]}, status=400)

    return JsonResponse({'error': 'Invalid section.'}, status=400)


@role_required('super_admin')
def create_school(request):
    form = SchoolForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        cd    = form.cleaned_data
        email = cd['admin_email']
        if User.objects.filter(email=email).exists():
            form.add_error('admin_email', 'A user with this email already exists.')
        else:
            school = form.save()
            base = email.split('@')[0]; username = base; i = 1
            while User.objects.filter(username=username).exists():
                username = f'{base}{i}'; i += 1
            admin_user = User(
                username=username,
                email=email,
                first_name=cd['admin_name'],
                role='school_admin',
                school=school,
            )
            admin_user.set_password(cd['admin_password'])
            admin_user.save()
            from django.core.mail import send_mail
            send_mail(
                'Your EduPlatform School Admin Account',
                f'Login: {email}\nPassword: {cd["admin_password"]}\nURL: /login/',
                'noreply@eduplatform.com', [email], fail_silently=True,
            )
            messages.success(request, f'School "{school.name}" and admin account created.')
            return redirect('superadmin_dashboard')
    schools = School.objects.all().order_by('-created_at')
    return render(request, 'superadmin/schools_list.html', {'form': form, 'schools': schools, 'mode': 'create'})



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
def course_list(request):
    form    = GlobalCourseForm(request.POST or None)
    courses = GlobalCourse.objects.prefetch_related('schools', 'concepts').order_by('-created_at')
    if request.method == 'POST' and form.is_valid():
        course = form.save(commit=False)
        course.created_by = request.user
        course.status     = 'draft'
        course.save()
        form.save_m2m()
        messages.success(request, f'Course "{course.title}" created.')
        return redirect('superadmin_course_list')
    return render(request, 'superadmin/course_list.html', {'form': form, 'courses': courses})


@role_required('super_admin')
def course_detail(request, course_id):
    course   = get_object_or_404(GlobalCourse, pk=course_id)
    concepts = course.concepts.all()
    if request.method == 'POST':
        action = request.POST.get('action')
        if action in ('publish', 'draft'):
            course.status = 'published' if action == 'publish' else 'draft'
            course.save()
            messages.success(request, f'Course marked as {course.status}.')
            return redirect('superadmin_course_detail', course_id=course.pk)
    return render(request, 'superadmin/course_detail.html', {
        'course': course, 'concepts': concepts,
    })


@role_required('super_admin')
def concept_add(request, course_id):
    course = get_object_or_404(GlobalCourse, pk=course_id)
    form   = GlobalConceptForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        concept        = form.save(commit=False)
        concept.course = course
        concept.order  = course.concepts.count()
        concept.save()
        messages.success(request, f'Concept "{concept.header}" added.')
        return redirect('superadmin_course_detail', course_id=course.pk)
    return render(request, 'superadmin/concept_add.html', {'form': form, 'course': course})
