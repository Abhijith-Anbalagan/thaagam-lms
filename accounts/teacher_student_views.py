from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.db import models
from accounts.models import User, StudentCredentialLog
from accounts.services.student_management_service import StudentManagementService
from django.utils import timezone

def role_required(role_name):
    def decorator(view_func):
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            if request.user.role == role_name:
                return view_func(request, *args, **kwargs)
            messages.error(request, "You do not have permission to access this page.")
            return redirect(request.user.get_dashboard_url())
        return _wrapped_view
    return decorator

@role_required('teacher')
def teacher_student_credentials(request):
    school = request.user.school
    students = User.objects.filter(school=school, role='student').order_by('-date_joined')
    # Consolidated Logs: Show all creations + ONLY the latest reset per student
    latest_reset_ids = StudentCredentialLog.objects.filter(
        school=school, action_type='reset'
    ).values('generated_id').annotate(latest_id=models.Max('id')).values('latest_id')

    credential_logs = StudentCredentialLog.objects.filter(
        models.Q(action_type='create') | models.Q(id__in=latest_reset_ids),
        school=school
    ).order_by('-created_at')
    
    # Active Tab from GET or Session or Default
    active_tab = request.GET.get('tab', 'single')
    search_q = request.GET.get('q', '').strip()

    # Search Logic
    if search_q:
        students = students.filter(
            models.Q(username__icontains=search_q) | 
            models.Q(email__icontains=search_q)
        )
        credential_logs = credential_logs.filter(
            models.Q(student_name__icontains=search_q) |
            models.Q(generated_id__icontains=search_q)
        )

    # Apply slice AFTER filtering
    credential_logs = credential_logs[:50]

    # Handle success modal via session (survives redirect)
    generated_creds = request.session.pop('generated_creds', None)

    if request.method == 'POST':
        action = request.POST.get('action')
        target_tab = request.POST.get('active_tab', 'single')
        
        # Single Student Creation
        if action == 'create_single':
            name = request.POST.get('name', '').strip()
            dob = request.POST.get('dob', '').strip().replace('-', '').replace('/', '')
            domain = request.POST.get('domain', '').strip()
            
            if not all([name, dob, domain]):
                messages.error(request, "All fields are required.")
            else:
                # Prevention check
                existing = User.objects.filter(username=name, school=school, role='student').first()
                if existing:
                    messages.warning(request, f"A student named '{name}' already exists in your school.")
                    # Still show their credentials if requested or just stop
                
                try:
                    user, password = StudentManagementService.create_student(name, dob, domain, school, teacher=request.user)
                    request.session['generated_creds'] = {
                        'name': user.username,
                        'email': user.email,
                        'password': password,
                        'type': 'new'
                    }
                    messages.success(request, f"Student account created successfully!")
                    return redirect(f"{request.path}?tab={target_tab}")
                except Exception as e:
                    messages.error(request, f"Error creating student: {str(e)}")

        # Bulk Student Creation
        elif action == 'bulk_create':
            domain = request.POST.get('domain', '').strip()
            excel_file = request.FILES.get('excel_file')
            
            if not domain or not excel_file:
                messages.error(request, "Domain and Excel file are required.")
            else:
                try:
                    output_data = StudentManagementService.process_bulk_excel(excel_file, domain, school, teacher=request.user)
                    response = HttpResponse(
                        output_data,
                        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    )
                    response['Content-Disposition'] = f'attachment; filename="student_credentials_{timezone.now().strftime("%Y%m%d_%H%M")}.xlsx"'
                    return response
                except Exception as e:
                    messages.error(request, f"Bulk creation failed: {str(e)}")
            return redirect(f"{request.path}?tab=bulk")

        # Change Password
        elif action == 'change_password':
            student_id = request.POST.get('student_id')
            student = get_object_or_404(User, pk=student_id, school=school, role='student')
            new_password = StudentManagementService.generate_random_password()
            student.set_password(new_password)
            student.save()
            
            # Log the reset
            StudentCredentialLog.objects.create(
                school=school,
                student_name=student.username,
                generated_id=student.email,
                plain_password=new_password,
                teacher=request.user,
                action_type='reset'
            )

            request.session['generated_creds'] = {
                'name': student.username,
                'email': student.email,
                'password': new_password,
                'type': 'reset'
            }
            messages.success(request, f"Password reset for {student.username}.")
            return redirect(f"{request.path}?tab={target_tab}")

    return render(request, 'teacher/student_credentials.html', {
        'students': students,
        'school': school,
        'generated_creds': generated_creds,
        'credential_logs': credential_logs,
        'active_tab': active_tab,
        'search_q': search_q,
    })

import openpyxl
from io import BytesIO

@role_required('teacher')
def export_credential_logs(request):
    school = request.user.school
    logs = StudentCredentialLog.objects.filter(school=school).order_by('-created_at')
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Student Credentials"
    
    headers = ["Student Name", "System ID (Email)", "Password", "Type", "Created At", "Created By"]
    ws.append(headers)
    
    for log in logs:
        ws.append([
            log.student_name,
            log.generated_id,
            log.plain_password,
            log.get_action_type_display(),
            log.created_at.strftime("%Y-%m-%d %H:%M"),
            log.teacher.username if log.teacher else "System"
        ])
        
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="student_credentials_log_{timezone.now().strftime("%Y%m%d")}.xlsx"'
    return response
