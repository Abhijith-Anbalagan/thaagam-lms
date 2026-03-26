from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Q
from accounts.decorators import role_required
from accounts.models import User
from .models import School, GlobalCourse, GlobalConcept, GlobalConceptVideo
from .forms import SchoolForm, SchoolEditForm, AdminEditForm, GlobalCourseForm, GlobalConceptForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm

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
            return redirect('superadmin_schools_list')
    return render(request, 'superadmin/create_school.html', {'form': form})



@role_required('super_admin')
def delete_school(request, school_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    school = get_object_or_404(School, pk=school_id)
    name = school.name
    school.delete()
    messages.success(request, f'School "{name}" permanently deleted.')
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

    return render(request, 'superadmin/course_detail.html', {
        'course':                 course,
        'concepts':               concepts,
        'beginner_concepts':      beginner_concepts,
        'intermediate_concepts':  intermediate_concepts,
        'advanced_concepts':      advanced_concepts,
        'total_concepts':         total_concepts,
        'progress_pct':           progress_pct,
        'all_schools':            School.objects.filter(is_active=True),  
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
