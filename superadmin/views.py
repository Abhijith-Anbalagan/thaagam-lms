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
        'school':      school,
        'admins':      admins,
        'admin_count': admins.count(),     # ← pass count for "Add Admin" button logic
        'teachers':    teachers,
        'students':    students,
        'management':  management,
        'classrooms':  classrooms,
        'teacher_enrollments': teacher_enrollments,
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
        admin_id = request.POST.get('admin_id')
        if not admin_id:
            return JsonResponse({'error': 'Admin ID is required.'}, status=400)

        admin = get_object_or_404(User, pk=admin_id, school=school, role='school_admin')

        new_email = request.POST.get('email', '').strip()
        if new_email != admin.email and User.objects.filter(email=new_email).exclude(pk=admin.pk).exists():
            return JsonResponse({'error': 'This email is already in use.'}, status=400)

        # ── Split full_name → first_name + last_name ──
        full_name  = request.POST.get('full_name', '').strip()
        parts      = full_name.split(' ', 1)
        admin.first_name = parts[0]
        admin.last_name  = parts[1] if len(parts) > 1 else ''
        admin.email      = new_email
        admin.save()

        return JsonResponse({
            'success':   True,
            'admin_id':  admin.pk,
            'full_name': admin.get_full_name() or admin.username,
            'email':     admin.email,
        })

    elif section == 'add_admin':
        # ── Block if already 3 admins ──
        existing_count = User.objects.filter(school=school, role='school_admin').count()
        if existing_count >= 3:
            return JsonResponse({'error': 'Maximum 3 admins allowed per school.'}, status=400)

        name     = request.POST.get('name', '').strip()
        email    = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()

        if not name or not email or not password:
            return JsonResponse({'error': 'Name, email and password are all required.'}, status=400)

        if User.objects.filter(email=email).exists():
            return JsonResponse({'error': f'Email "{email}" is already in use.'}, status=400)

        # Generate unique username from email prefix
        base = email.split('@')[0]
        username = base
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f'{base}{counter}'
            counter += 1

        new_admin = User(
            username=username,
            email=email,
            first_name=name,
            role='school_admin',
            school=school,
        )
        new_admin.set_password(password)
        new_admin.save()

        return JsonResponse({
            'success':   True,
            'admin_id':  new_admin.pk,
            'full_name': new_admin.get_full_name() or new_admin.username,
            'email':     new_admin.email,
            'counter':   User.objects.filter(school=school, role='school_admin').count(),
        })

    elif section == 'edit_user':
        user_id = request.POST.get('user_id')
        user_role = request.POST.get('role')  # 'teacher', 'student', or 'management'

        if not user_id or not user_role:
            return JsonResponse({'error': 'User ID and role are required.'}, status=400)

        user = get_object_or_404(User, pk=user_id, school=school, role=user_role)

        new_email = request.POST.get('email', '').strip()
        if new_email != user.email and User.objects.filter(email=new_email).exclude(pk=user.pk).exists():
            return JsonResponse({'error': 'This email is already in use.'}, status=400)

        full_name = request.POST.get('full_name', '').strip()
        parts = full_name.split(' ', 1)
        user.first_name = parts[0]
        user.last_name = parts[1] if len(parts) > 1 else ''
        user.email = new_email
        user.save()

        return JsonResponse({
            'success': True,
            'user_id': user.pk,
            'full_name': user.get_full_name() or user.username,
            'email': user.email,
        })

    return JsonResponse({'error': 'Invalid section.'}, status=400)

@role_required('super_admin')
def create_school(request):
    form = SchoolForm(request.POST or None)
    if request.method == 'POST':
        if not form.is_valid():
            # Show form field errors (name missing etc.)
            for field, errs in form.errors.items():
                for e in errs:
                    messages.error(request, f'{field}: {e}')
            return render(request, 'superadmin/create_school.html', {'form': form})

        # Collect dynamic admin inputs — admins[1][name], admins[1][email], admins[1][password]
        admins_data = []
        for i in range(1, 4):
            name     = request.POST.get(f'admins[{i}][name]', '').strip()
            email    = request.POST.get(f'admins[{i}][email]', '').strip()
            password = request.POST.get(f'admins[{i}][password]', '').strip()
            if email:  # only include if email is filled
                admins_data.append({
                    'name':     name,
                    'email':    email,
                    'password': password,
                    'index':    i,
                })

        # Must have at least 1 admin
        if not admins_data:
            messages.error(request, 'Please add at least one admin account.')
            return render(request, 'superadmin/create_school.html', {'form': form})

        # Validate each admin before saving anything
        errors = []
        for a in admins_data:
            if not a['name']:
                errors.append(f"Admin {a['index']}: Full name is required.")
            if not a['password']:
                errors.append(f"Admin {a['index']}: Password is required.")
            if User.objects.filter(email=a['email']).exists():
                errors.append(f"Admin {a['index']}: Email '{a['email']}' is already in use.")

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'superadmin/create_school.html', {'form': form})

        # ---- All valid — now save ----

        # 1. Save school
        school = form.save()

        # 2. Create each admin user
        from django.core.mail import send_mail
        for a in admins_data:
            # Generate unique username from email prefix
            base     = a['email'].split('@')[0]
            username = base
            counter  = 1
            while User.objects.filter(username=username).exists():
                username = f'{base}{counter}'
                counter += 1

            user = User(
                username=username,
                email=a['email'],
                first_name=a['name'],
                role='school_admin',
                school=school,
            )
            user.set_password(a['password'])
            user.save()

            send_mail(
                'Your EduPlatform School Admin Account',
                f"Login: {a['email']}\nPassword: {a['password']}\nURL: /login/",
                'noreply@eduplatform.com',
                [a['email']],
                fail_silently=True,
            )

        messages.success(
            request,
            f'School "{school.name}" created with {len(admins_data)} admin account(s).'
        )
        return redirect('superadmin_dashboard')   # ← redirects to dashboard

    return render(request, 'superadmin/create_school.html', {'form': form})

@role_required('super_admin')
def delete_school(request, school_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    school = get_object_or_404(School, pk=school_id)
    name = school.name
    
    # Delete all admin accounts associated with this school
    User.objects.filter(school=school, role='school_admin').delete()
    
    # Delete the school
    school.delete()
    messages.success(request, f'School "{name}" and its admin accounts permanently deleted.')
    return JsonResponse({'success': True})


@role_required('super_admin')
def delete_admin(request, admin_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    admin = get_object_or_404(User, pk=admin_id, role='school_admin')
    admin.delete()
    return JsonResponse({'success': True})


@role_required('super_admin')
def delete_course(request, course_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    course = get_object_or_404(GlobalCourse, pk=course_id)
    course.delete()
    return JsonResponse({'success': True})


@role_required('super_admin')
def delete_user(request, user_id):
    """Delete any non-super_admin user from a school detail page."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    user = get_object_or_404(User, pk=user_id)
    if user.role == 'super_admin':
        return JsonResponse({'error': 'Cannot delete super admin.'}, status=403)
    user.delete()
    return JsonResponse({'success': True})


@role_required('super_admin')
def toggle_school(request, school_id):
    school = get_object_or_404(School, pk=school_id)
    school.is_active = not school.is_active
    school.save()
    messages.success(request, f'School "{school.name}" {"activated" if school.is_active else "suspended"}.')
    return redirect('superadmin_schools_list')


@role_required('super_admin')
def all_admins(request):
    admins = User.objects.filter(role='school_admin').select_related('school').order_by('school__name')
    
    # Get all active schools + mark which ones already have an admin
    schools_with_admin_pks = set(
        User.objects.filter(role='school_admin', school__isnull=False).values_list('school_id', flat=True)
    )
    all_schools = School.objects.filter(is_active=True).order_by('name')
    for s in all_schools:
        s.has_admin = s.pk in schools_with_admin_pks  # adds .has_admin to each school

    return render(request, 'superadmin/admin_management.html', {
        'admins': admins,
        'schools_without_admin': all_schools,  # same variable name so template doesn't break
    })


@role_required('super_admin')
def admin_action(request, admin_id):
    """Suspend/activate or transfer a school admin."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    admin  = get_object_or_404(User, pk=admin_id, role='school_admin')
    action = request.POST.get('action')
    if action == 'toggle':
        admin.is_active = not admin.is_active
        admin.save()
        return JsonResponse({'success': True, 'is_active': admin.is_active})
    elif action == 'transfer':
        new_school_id = request.POST.get('school_id')
        new_school    = get_object_or_404(School, pk=new_school_id)

            # If target school already has an admin, unlink them first
        User.objects.filter(school=new_school, role='school_admin').exclude(pk=admin.pk).update(school=None)
        admin.school  = new_school
        admin.save()
        return JsonResponse({'success': True, 'school_name': new_school.name})
    return JsonResponse({'error': 'Invalid action'}, status=400)


@role_required('super_admin')
def platform_analytics(request):
    from classrooms.models import Classroom
    from assignments.models import Submission
    from django.db.models import Avg

    # Annotate each school with student, teacher, classroom counts
    school_breakdown = School.objects.annotate(
        sc=Count('users', filter=Q(users__role='student')),
        tc=Count('users', filter=Q(users__role='teacher')),
        cc=Count('classrooms', distinct=True),       # ← NEW: classroom count
    ).order_by('-sc')

    total_submissions  = Submission.objects.count()
    graded_submissions = Submission.objects.filter(score__isnull=False).count()
    avg_score = Submission.objects.filter(
        score__isnull=False
    ).aggregate(avg=Avg('score'))['avg']

    # NEW: max values for progress bar calculation
    max_students = max((s.sc for s in school_breakdown), default=1) or 1
    max_teachers = max((s.tc for s in school_breakdown), default=1) or 1

    return render(request, 'superadmin/analytics.html', {
        'schools':            School.objects.count(),
        'active_schools':     School.objects.filter(is_active=True).count(),    # NEW
        'suspended_schools':  School.objects.filter(is_active=False).count(),   # NEW
        'total_students':     User.objects.filter(role='student').count(),
        'total_teachers':     User.objects.filter(role='teacher').count(),
        'total_classrooms':   Classroom.objects.count(),
        'total_courses':      GlobalCourse.objects.count(),
        'published_courses':  GlobalCourse.objects.filter(status='published').count(),
        'total_submissions':  total_submissions,
        'graded_submissions': graded_submissions,
        'avg_score':          round(avg_score, 1) if avg_score else None,
        'school_breakdown':   school_breakdown,
        'max_students':       max_students,   # NEW
        'max_teachers':       max_teachers,   # NEW
    })


@role_required('super_admin')
def all_courses(request):
    courses = GlobalCourse.objects.prefetch_related('schools', 'concepts').order_by('-created_at')
    draft_count     = courses.filter(status='draft').count()
    published_count = courses.filter(status='published').count()
    return render(request, 'superadmin/all_courses.html', {
        'courses':         courses,
        'draft_count':     draft_count,
        'published_count': published_count,
    })


@role_required('super_admin')
def course_list(request):
    # ADD request.FILES to the form constructor
    form    = GlobalCourseForm(request.POST or None, request.FILES or None)
    courses = GlobalCourse.objects.prefetch_related('schools', 'concepts').order_by('-created_at')
    if request.method == 'POST' and form.is_valid():
        course = form.save(commit=False)
        course.created_by = request.user
        course.status     = 'draft'
        course.save()
        form.save_m2m()
        messages.success(request, f'Course "{course.title}" created.')
        return redirect('superadmin_course_detail', course_id=course.pk)
    return render(request, 'superadmin/course_list.html', {'form': form, 'courses': courses})


@role_required('super_admin')
def course_detail(request, course_id):
    course   = get_object_or_404(GlobalCourse, pk=course_id)
    concepts = course.concepts.prefetch_related('videos').all()

    if request.method == 'POST':
        action = request.POST.get('action')
        if action in ('publish', 'draft'):
            course.status = 'published' if action == 'publish' else 'draft'
            course.save()
            messages.success(request, f'Course marked as {course.status}.')
            return redirect('superadmin_course_detail', course_id=course.pk)
        # NEW: handle course meta update (cover, language, hours, summary)
        if action == 'update_meta':
            form = GlobalCourseForm(request.POST, request.FILES, instance=course)
            if form.is_valid():
                form.save()
                messages.success(request, 'Course updated.')
            return redirect('superadmin_course_detail', course_id=course.pk)

    # Group concepts by level for GUVI-style sidebar
    beginner_concepts     = concepts.filter(level='beginner')
    intermediate_concepts = concepts.filter(level='intermediate')
    advanced_concepts     = concepts.filter(level='advanced')

    # Total videos & completion (basic count — extend later with UserProgress model)
    total_concepts = concepts.count()
    # Placeholder progress — replace with real user progress later
    completed_count = 0
    progress_pct    = int((completed_count / total_concepts * 100)) if total_concepts else 0
    teacher_enrollments = CourseEnrollment.objects.filter(
        course=course,
        user__role='teacher',
    ).select_related('user', 'user__school').order_by('-enrolled_at')

    return render(request, 'superadmin/course_detail.html', {
        'course':                 course,
        'concepts':               concepts,
        'beginner_concepts':      beginner_concepts,
        'intermediate_concepts':  intermediate_concepts,
        'advanced_concepts':      advanced_concepts,
        'total_concepts':         total_concepts,
        'progress_pct':           progress_pct,
        'all_schools':            School.objects.filter(is_active=True),
        'teacher_enrollments':    teacher_enrollments,
    })


@role_required('super_admin')
def concept_edit(request, concept_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    concept = get_object_or_404(GlobalConcept, pk=concept_id)
    field   = request.POST.get('field')
    value   = request.POST.get('value', '').strip()
    if field in ('header', 'h3_course', 'quiz', 'assignment'):
        setattr(concept, field, value)
        concept.save()
        return JsonResponse({'success': True})
    return JsonResponse({'error': 'Invalid field'}, status=400)


@role_required('super_admin')
def concept_delete(request, concept_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    concept = get_object_or_404(GlobalConcept, pk=concept_id)
    concept.delete()
    return JsonResponse({'success': True})


@role_required('super_admin')
def video_delete(request, video_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    video = get_object_or_404(GlobalConceptVideo, pk=video_id)
    video.delete()
    return JsonResponse({'success': True})


@role_required('super_admin')
def video_add(request, concept_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    concept = get_object_or_404(GlobalConcept, pk=concept_id)
    vfile   = request.FILES.get('video_files')
    if not vfile:
        return JsonResponse({'error': 'No file provided'}, status=400)
    title = request.POST.get('video_titles', '').strip()
    order = concept.videos.count()
    GlobalConceptVideo.objects.create(concept=concept, file=vfile, title=title, order=order)
    return JsonResponse({'success': True})


@role_required('super_admin')
def concept_add(request, course_id):
    course = get_object_or_404(GlobalCourse, pk=course_id)
    form   = GlobalConceptForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        concept        = form.save(commit=False)
        concept.course = course
        concept.level  = request.POST.get('level', 'beginner')
        concept.order  = course.concepts.count()
        concept.save()
        # Save multiple videos
        video_files  = request.FILES.getlist('video_files')
        video_titles = request.POST.getlist('video_titles')
        for i, vfile in enumerate(video_files):
            title = video_titles[i] if i < len(video_titles) else ''
            GlobalConceptVideo.objects.create(
                concept=concept, file=vfile, title=title, order=i
            )
        messages.success(request, f'Concept "{concept.header}" added.')
        return redirect('superadmin_course_detail', course_id=course.pk)
    return render(request, 'superadmin/concept_add.html', {'form': form, 'course': course})


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
        
        if User.objects.filter(email=email).exists():
            return JsonResponse({'success': False, 'error': 'Email already in use'})
        
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
    
    # ── DELETE ADMIN ──
    elif section == 'delete_admin':
        admin_id = request.POST.get('admin_id')
        if not admin_id:
            return JsonResponse({'success': False, 'error': 'Admin ID required'})
        
        admin = get_object_or_404(User, pk=admin_id, role='school_admin', school=school)
        admin.delete()
        admin_count = User.objects.filter(school=school, role='school_admin').count()
        return JsonResponse({'success': True, 'counter': admin_count})
    
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
    
    # ── DELETE USER ──
    elif section == 'delete_user':
        user_id = request.POST.get('user_id')
        role = request.POST.get('role', '').strip()
        
        if not user_id or not role:
            return JsonResponse({'success': False, 'error': 'Missing required fields'})
        
        user = get_object_or_404(User, pk=user_id, role=role, school=school)
        user.delete()
        return JsonResponse({'success': True})
    
    # ── ADD USER (Teacher/Student/Management) ──
    elif section == 'add_user':
        role = request.POST.get('role', '').strip()
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        
        if not role or not name or not email or not password:
            return JsonResponse({'success': False, 'error': 'Missing required fields'})
        
        if role not in ['teacher', 'student', 'management']:
            return JsonResponse({'success': False, 'error': 'Invalid role'})
        
        if User.objects.filter(email=email).exists():
            return JsonResponse({'success': False, 'error': 'Email already in use'})
        
        first, last = (name.split(' ', 1) if ' ' in name else (name, ''))
        user = User.objects.create_user(
            username=email,
            email=email,
            first_name=first,
            last_name=last,
            password=password,
            role=role,
            school=school
        )
        
        return JsonResponse({
            'success': True,
            'user_id': user.pk,
            'full_name': user.get_full_name(),
            'email': user.email,
            'role': role
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