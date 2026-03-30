from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Q
from accounts.decorators import role_required
from accounts.models import User
from .models import School, GlobalCourse, GlobalConcept, GlobalConceptVideo, CourseEnrollment
from .forms import SchoolForm, SchoolEditForm, AdminEditForm, GlobalCourseForm, GlobalConceptForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.core.paginator import Paginator


@role_required('super_admin')
def profile_settings(request):
    user = request.user
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_profile':
            first_name = request.POST.get('first_name', '').strip()
            last_name  = request.POST.get('last_name', '').strip()
            email      = request.POST.get('email', '').strip()
            if email and email != user.email:
                if User.objects.filter(email=email).exclude(pk=user.pk).exists():
                    messages.error(request, 'This email is already in use.')
                    return redirect('superadmin_profile')
            user.first_name = first_name
            user.last_name  = last_name
            if email:
                user.email = email
            user.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('superadmin_profile')

        elif action == 'change_password':
            form = PasswordChangeForm(user=user, data=request.POST)
            if form.is_valid():
                form.save()
                update_session_auth_hash(request, form.user)  # keeps user logged in
                messages.success(request, 'Password changed successfully.')
                return redirect('superadmin_profile')
            else:
                for error in form.errors.values():
                    messages.error(request, error[0])
                return redirect('superadmin_profile')

    return render(request, 'superadmin/profile_settings.html', {'user': user})

@role_required('super_admin')
def dashboard(request):
    from classrooms.models import Classroom
    schools = School.objects.annotate(
        student_count=Count('users', filter=Q(users__role='student')),
        teacher_count=Count('users', filter=Q(users__role='teacher')),
    )
    courses = GlobalCourse.objects.prefetch_related('schools', 'concepts').order_by('-created_at')[:8]
    context = {
        'schools':           schools,
        'courses':           courses,
        'total_schools':     School.objects.count(),
        'total_students':    User.objects.filter(role='student').count(),
        'total_teachers':    User.objects.filter(role='teacher').count(),
        'total_management':  User.objects.filter(role='management').count(),
        'total_classrooms':  Classroom.objects.count(),
    }
    return render(request, 'superadmin/dashboard.html', context)


@role_required('super_admin')
def schools_list(request):
    schools = School.objects.all().order_by('-created_at')
    return render(request, 'superadmin/schools_list.html', {'schools': schools})


@role_required('super_admin')
def school_detail(request, school_id):
    school = get_object_or_404(School, pk=school_id)

    # ── Admins (max 3, no pagination needed) ──
    admins = User.objects.filter(school=school, role='school_admin').order_by('id')

    # ── Paginated sections (5 per page) ──
    def paginate(qs, param):
        paginator = Paginator(qs, 5)
        page = request.GET.get(param, 1)
        return paginator.get_page(page)

    teachers   = paginate(User.objects.filter(school=school, role='teacher'),     'teacher_page')
    students   = paginate(User.objects.filter(school=school, role='student'),     'student_page')
    management = paginate(User.objects.filter(school=school, role='management'), 'management_page')

    from classrooms.models import Classroom
    classrooms = paginate(Classroom.objects.filter(school=school), 'classroom_page')
    teacher_enrollments = CourseEnrollment.objects.filter(
        user__school=school,
        user__role='teacher',
    ).select_related('user', 'course').order_by('-enrolled_at')[:10]

    return render(request, 'superadmin/school_detail.html', {
        'school':              school,
        'admins':              admins,
        'teachers':            teachers,
        'students':            students,
        'management':          management,
        'classrooms':          classrooms,
        'teacher_enrollments': teacher_enrollments,
    })


@role_required('super_admin')
def school_edit(request, school_id):
    school = get_object_or_404(School, pk=school_id)
    
    if request.method == 'POST':
        form = SchoolEditForm(request.POST, instance=school)
        if form.is_valid():
            form.save()
            messages.success(request, f'School "{school.name}" updated successfully.')
            return redirect('superadmin_school_detail', school_id=school.pk)
    else:
        form = SchoolEditForm(instance=school)
    
    return render(request, 'superadmin/school_edit.html', {
        'school': school,
        'form': form,
    })


@role_required('super_admin')
def create_school(request):
    if request.method == 'POST':
        form = SchoolForm(request.POST)
        if form.is_valid():
            school = form.save()
            messages.success(request, f'School "{school.name}" created successfully.')
            return redirect('superadmin_school_detail', school_id=school.pk)
    else:
        form = SchoolForm()
    
    return render(request, 'superadmin/create_school.html', {'form': form})


@role_required('super_admin')
def toggle_school(request, school_id):
    school = get_object_or_404(School, pk=school_id)
    school.is_active = not school.is_active
    school.save()
    status = 'activated' if school.is_active else 'deactivated'
    messages.success(request, f'School "{school.name}" has been {status}.')
    return redirect('superadmin_school_detail', school_id=school.pk)


@role_required('super_admin')
def delete_school(request, school_id):
    school = get_object_or_404(School, pk=school_id)
    name = school.name
    school.delete()
    messages.success(request, f'School "{name}" has been deleted.')
    return redirect('superadmin_schools_list')


@role_required('super_admin')
def delete_admin(request, admin_id):
    admin = get_object_or_404(User, pk=admin_id, role='school_admin')
    school = admin.school
    admin.delete()
    messages.success(request, f'Admin "{admin.get_full_name()}" has been deleted.')
    return redirect('superadmin_school_detail', school_id=school.pk)


@role_required('super_admin')
def delete_course(request, course_id):
    course = get_object_or_404(GlobalCourse, pk=course_id)
    title = course.title
    course.delete()
    messages.success(request, f'Course "{title}" has been deleted.')
    return redirect('superadmin_all_courses')


@role_required('super_admin')
def delete_user(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    school = user.school
    role_name = user.get_role_display()
    name = user.get_full_name() or user.username
    user.delete()
    messages.success(request, f'{role_name} "{name}" has been deleted.')
    return redirect('superadmin_school_detail', school_id=school.pk)


@role_required('super_admin')
def all_admins(request):
    admins = User.objects.filter(role='school_admin').select_related('school').order_by('-date_joined')
    paginator = Paginator(admins, 20)
    page = request.GET.get('page', 1)
    admins_page = paginator.get_page(page)
    
    return render(request, 'superadmin/all_admins.html', {'admins': admins_page})


@role_required('super_admin')
def admin_action(request, admin_id):
    admin = get_object_or_404(User, pk=admin_id, role='school_admin')
    action = request.POST.get('action')
    
    if action == 'toggle_active':
        admin.is_active = not admin.is_active
        admin.save()
        status = 'activated' if admin.is_active else 'deactivated'
        messages.success(request, f'Admin "{admin.get_full_name()}" has been {status}.')
    
    elif action == 'edit':
        return redirect('superadmin_school_detail', school_id=admin.school.pk)
    
    return redirect('superadmin_all_admins')


@role_required('super_admin')
def platform_analytics(request):
    from classrooms.models import Classroom
    
    total_schools = School.objects.count()
    active_schools = School.objects.filter(is_active=True).count()
    total_users = User.objects.count()
    total_students = User.objects.filter(role='student').count()
    total_teachers = User.objects.filter(role='teacher').count()
    total_admins = User.objects.filter(role='school_admin').count()
    total_courses = GlobalCourse.objects.count()
    published_courses = GlobalCourse.objects.filter(status='published').count()
    total_classrooms = Classroom.objects.count()
    total_enrollments = CourseEnrollment.objects.count()
    
    # Recent activity
    recent_schools = School.objects.order_by('-created_at')[:5]
    recent_courses = GlobalCourse.objects.order_by('-created_at')[:5]
    recent_enrollments = CourseEnrollment.objects.select_related('user', 'course').order_by('-enrolled_at')[:10]
    
    context = {
        'total_schools': total_schools,
        'active_schools': active_schools,
        'total_users': total_users,
        'total_students': total_students,
        'total_teachers': total_teachers,
        'total_admins': total_admins,
        'total_courses': total_courses,
        'published_courses': published_courses,
        'total_classrooms': total_classrooms,
        'total_enrollments': total_enrollments,
        'recent_schools': recent_schools,
        'recent_courses': recent_courses,
        'recent_enrollments': recent_enrollments,
    }
    
    return render(request, 'superadmin/platform_analytics.html', context)


@role_required('super_admin')
def course_list(request):
    courses = GlobalCourse.objects.prefetch_related('schools', 'concepts').order_by('-created_at')
    paginator = Paginator(courses, 12)
    page = request.GET.get('page', 1)
    courses_page = paginator.get_page(page)
    
    return render(request, 'superadmin/course_list.html', {'courses': courses_page})


@role_required('super_admin')
def all_courses(request):
    courses = GlobalCourse.objects.prefetch_related('schools', 'concepts').order_by('-created_at')
    paginator = Paginator(courses, 15)
    page = request.GET.get('page', 1)
    courses_page = paginator.get_page(page)
    
    if request.method == 'POST':
        form = GlobalCourseForm(request.POST, request.FILES)
        if form.is_valid():
            course = form.save(commit=False)
            course.created_by = request.user
            course.save()
            form.save_m2m()
            messages.success(request, f'Course "{course.title}" created successfully.')
            return redirect('superadmin_course_detail', course_id=course.pk)
    else:
        form = GlobalCourseForm()
    
    return render(request, 'superadmin/all_courses.html', {
        'courses': courses_page,
        'form': form,
    })


@role_required('super_admin')
def course_detail(request, course_id):
    course = get_object_or_404(GlobalCourse, pk=course_id)
    concepts = course.concepts.prefetch_related('videos').order_by('order', 'created_at')
    
    if request.method == 'POST':
        form = GlobalCourseForm(request.POST, request.FILES, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, f'Course "{course.title}" updated successfully.')
            return redirect('superadmin_course_detail', course_id=course.pk)
    else:
        form = GlobalCourseForm(instance=course)
    
    return render(request, 'superadmin/course_detail.html', {
        'course': course,
        'concepts': concepts,
        'form': form,
    })


@role_required('super_admin')
def concept_add(request, course_id):
    """
    Enhanced 5-step wizard for adding concepts:
    Step 1: Concept Info (header, h3_course)
    Step 2: Module Level & Videos
    Step 3: Course PDF
    Step 4: Quiz
    Step 5: Assignment (final submit)
    """
    course = get_object_or_404(GlobalCourse, pk=course_id)
    form = GlobalConceptForm(request.POST or None, request.FILES or None)
    
    if request.method == 'POST' and form.is_valid():
        concept = form.save(commit=False)
        concept.course = course
        
        # Step 2: Get level from wizard
        concept.level = request.POST.get('level', 'beginner')
        
        # Auto-order
        concept.order = course.concepts.count()
        concept.save()
        
        # Step 2: Save multiple videos
        video_files = request.FILES.getlist('video_files')
        video_titles = request.POST.getlist('video_titles')
        for i, vfile in enumerate(video_files):
            title = video_titles[i] if i < len(video_titles) else ''
            GlobalConceptVideo.objects.create(
                concept=concept,
                file=vfile,
                title=title or f'Video {i+1}',
                order=i
            )
        
        messages.success(
            request,
            f'✓ Concept "{concept.header}" has been successfully added to {course.title}!'
        )
        return redirect('superadmin_course_detail', course_id=course.pk)
    
    return render(request, 'superadmin/concept_add.html', {
        'form': form,
        'course': course
    })


@role_required('super_admin')
def concept_edit(request, concept_id):
    concept = get_object_or_404(GlobalConcept, pk=concept_id)
    course = concept.course
    
    if request.method == 'POST':
        form = GlobalConceptForm(request.POST, request.FILES, instance=concept)
        if form.is_valid():
            concept = form.save(commit=False)
            concept.level = request.POST.get('level', concept.level)
            concept.save()
            
            # Handle new videos
            video_files = request.FILES.getlist('video_files')
            video_titles = request.POST.getlist('video_titles')
            for i, vfile in enumerate(video_files):
                title = video_titles[i] if i < len(video_titles) else ''
                GlobalConceptVideo.objects.create(
                    concept=concept,
                    file=vfile,
                    title=title or f'Video {i+1}',
                    order=concept.videos.count()
                )
            
            messages.success(request, f'Concept "{concept.header}" updated successfully.')
            return redirect('superadmin_course_detail', course_id=course.pk)
    else:
        form = GlobalConceptForm(instance=concept)
    
    return render(request, 'superadmin/concept_edit.html', {
        'form': form,
        'concept': concept,
        'course': course
    })


@role_required('super_admin')
def concept_delete(request, concept_id):
    concept = get_object_or_404(GlobalConcept, pk=concept_id)
    course = concept.course
    header = concept.header
    concept.delete()
    messages.success(request, f'Concept "{header}" has been deleted.')
    return redirect('superadmin_course_detail', course_id=course.pk)


@role_required('super_admin')
def video_add(request, concept_id):
    concept = get_object_or_404(GlobalConcept, pk=concept_id)
    
    if request.method == 'POST':
        title = request.POST.get('title', '')
        video_file = request.FILES.get('file')
        video_url = request.POST.get('video_url', '')
        
        if video_file or video_url:
            order = concept.videos.count()
            GlobalConceptVideo.objects.create(
                concept=concept,
                title=title,
                file=video_file,
                video_url=video_url,
                order=order
            )
            messages.success(request, 'Video added successfully.')
        else:
            messages.error(request, 'Please provide either a video file or URL.')
        
        return redirect('superadmin_course_detail', course_id=concept.course.pk)
    
    return render(request, 'superadmin/video_add.html', {'concept': concept})


@role_required('super_admin')
def video_delete(request, video_id):
    video = get_object_or_404(GlobalConceptVideo, pk=video_id)
    concept = video.concept
    video.delete()
    messages.success(request, 'Video deleted successfully.')
    return redirect('superadmin_course_detail', course_id=concept.course.pk)


@role_required('super_admin')
def api_school_edit(request, school_id):
    """API endpoint for AJAX school/admin/user edits on school detail page."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=400)
    
    school = get_object_or_404(School, pk=school_id)
    section = request.POST.get('section', '').strip()
    
    # ── EDIT SCHOOL ──
    if section == 'school':
        name = request.POST.get('name', '').strip()
        address = request.POST.get('address', '').strip()
        if not name:
            return JsonResponse({'success': False, 'error': 'School name required'})
        school.name = name
        school.address = address
        school.save()
        return JsonResponse({'success': True, 'name': school.name, 'address': school.address})
    
    # ── EDIT ADMIN ──
    elif section == 'admin':
        admin_id = request.POST.get('admin_id')
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip()
        if not admin_id or not full_name or not email:
            return JsonResponse({'success': False, 'error': 'Missing required fields'})
        
        admin = get_object_or_404(User, pk=admin_id, role='school_admin', school=school)
        first, last = (full_name.split(' ', 1) if ' ' in full_name else (full_name, ''))
        admin.first_name = first
        admin.last_name = last
        admin.email = email
        admin.save()
        return JsonResponse({
            'success': True,
            'admin_id': admin.pk,
            'full_name': admin.get_full_name(),
            'email': admin.email
        })
    
    # ── ADD ADMIN ──
    elif section == 'add_admin':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        
        if not name or not email or not password:
            return JsonResponse({'success': False, 'error': 'Missing required fields'})
        
        # Check if admin with this email already exists
        if User.objects.filter(email=email).exists():
            return JsonResponse({'success': False, 'error': 'Email already in use'})
        
        # Check admin limit
        admin_count = User.objects.filter(school=school, role='school_admin').count()
        if admin_count >= 3:
            return JsonResponse({'success': False, 'error': 'Maximum 3 admins allowed'})
        
        first, last = (name.split(' ', 1) if ' ' in name else (name, ''))
        admin = User.objects.create_user(
            username=email,
            email=email,
            first_name=first,
            last_name=last,
            password=password,
            role='school_admin',
            school=school
        )
        
        admin_count = User.objects.filter(school=school, role='school_admin').count()
        return JsonResponse({
            'success': True,
            'admin_id': admin.pk,
            'full_name': admin.get_full_name(),
            'email': admin.email,
            'counter': admin_count
        })
    
    # ── EDIT USER (Teacher/Student/Management) ──
    elif section == 'edit_user':
        user_id = request.POST.get('user_id')
        role = request.POST.get('role', '').strip()
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip()
        
        if not user_id or not role or not full_name or not email:
            return JsonResponse({'success': False, 'error': 'Missing required fields'})
        
        user = get_object_or_404(User, pk=user_id, role=role, school=school)
        first, last = (full_name.split(' ', 1) if ' ' in full_name else (full_name, ''))
        user.first_name = first
        user.last_name = last
        user.email = email
        user.save()
        
        return JsonResponse({
            'success': True,
            'user_id': user.pk,
            'full_name': user.get_full_name(),
            'email': user.email
        })
    
    return JsonResponse({'success': False, 'error': 'Invalid section'})


def api_profile_sync(request):
    """API endpoint — returns current user's profile data for sync checking."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    user = request.user
    return JsonResponse({
        'success': True,
        'user_id': user.pk,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': user.email,
        'full_name': user.get_full_name() or user.username,
    })