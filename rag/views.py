import os
import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from accounts.decorators import role_required
from .models import RAGDocument, ChatMessage
from .forms import RAGDocumentForm

# --- Admin Views ---

@role_required('super_admin', 'school_admin')
def manage_documents(request):
    school = request.user.school
    if request.user.role == 'super_admin':
        documents = RAGDocument.objects.all().order_by('-created_at')
    else:
        documents = RAGDocument.objects.filter(school=school).order_by('-created_at')
    
    processed_count = documents.filter(status='processed').count()
    pending_count = documents.filter(status='pending').count()
    
    form = RAGDocumentForm()
    return render(request, 'rag/manage_documents.html', {
        'documents': documents,
        'processed_count': processed_count,
        'pending_count': pending_count,
        'form': form,
        'active_nav': 'rag_manage'
    })

@role_required('super_admin', 'school_admin')
def upload_document(request):
    if request.method == 'POST':
        form = RAGDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.uploaded_by = request.user
            if request.user.role != 'super_admin':
                 doc.school = request.user.school
            doc.save()
            messages.success(request, f'Document "{doc.title}" saved locally. You can sync it to the AI Knowledge Base when ready.')
            return redirect('rag_manage_documents')
    return redirect('rag_manage_documents')

@role_required('super_admin', 'school_admin')
def sync_document(request, doc_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=400)
    
    doc = get_object_or_404(RAGDocument, id=doc_id)
    
    # Check permissions
    if request.user.role != 'super_admin' and doc.school != request.user.school:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    # --- API Integration Point ---
    api_url = os.getenv('RAG_API_UPLOAD_URL')
    api_key = os.getenv('RAG_API_KEY')
    
    if not (api_url and api_key):
        return JsonResponse({
            'success': False, 
            'error': 'API Configuration missing. Please update your .env file with RAG_API_UPLOAD_URL and RAG_API_KEY.'
        })

    try:
        # Example multi-part upload
        with open(doc.file.path, 'rb') as f:
            resp = requests.post(
                api_url, 
                files={'file': f}, 
                headers={'Authorization': f'Bearer {api_key}'},
                timeout=60
            )
        
        if resp.status_code == 200:
            data = resp.json()
            doc.external_id = data.get('id')
            doc.status = 'processed'
            doc.save()
            return JsonResponse({'success': True, 'status': 'processed'})
        else:
            doc.status = 'error'
            doc.save()
            return JsonResponse({'success': False, 'error': f'API returned status {resp.status_code}'})
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Connection failed: {str(e)}'})

@role_required('super_admin', 'school_admin')
def delete_document(request, doc_id):
    if request.method == 'POST':
        doc = get_object_or_404(RAGDocument, id=doc_id)
        # Check permissions
        if request.user.role != 'super_admin' and doc.school != request.user.school:
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        
        # --- Optional: Call API to delete ---
        
        doc.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

# --- Student Views ---

@role_required('student')
def student_chat(request):
    from students.views import _student_layout_context
    
    classrooms = request.user.joined_classrooms.all()
    classroom = classrooms.first()
    
    if not classroom:
        return redirect('student_join_class')
        
    history_qs = ChatMessage.objects.filter(user=request.user).order_by('-timestamp')[:50]
    history = list(history_qs)
    history.reverse() # Show in chronological order
    
    context = {
        'history': history,
        'classroom': classroom,
        'nav_classroom': classroom,
        **_student_layout_context(request, classroom=classroom, active_nav='ai_chat')
    }
    return render(request, 'rag/chat.html', context)

@role_required('student')
def api_chat_proxy(request):
    if request.method == 'POST':
        query = request.POST.get('query')
        if not query:
            return JsonResponse({'success': False, 'error': 'Query required'})
        
        ai_response = "AI API not configured yet. Please update your .env with API details."
        
        # --- API Integration Point ---
        # api_url = os.getenv('RAG_API_CHAT_URL')
        # api_key = os.getenv('RAG_API_KEY')
        # if api_url and api_key:
        #     try:
        #         payload = {'query': query, 'user_id': request.user.id}
        #         resp = requests.post(
        #             api_url, 
        #             json=payload, 
        #             headers={'Authorization': f'Bearer {api_key}'},
        #             timeout=20
        #         )
        #         if resp.status_code == 200:
        #             ai_response = resp.json().get('response', 'No response content.')
        #         else:
        #             ai_response = f"Error from AI API ({resp.status_code})."
        #     except Exception as e:
        #         ai_response = f"Connection error: {str(e)}"
        
        # Placeholder for demonstration if no API configured
        if "AI API not configured" in ai_response:
            ai_response = f"Demo Mode: I received your message '{query}'. Once the API is linked, I will provide real answers from your documents!"

        # Save to local history
        ChatMessage.objects.create(user=request.user, query=query, response=ai_response)
        
        return JsonResponse({
            'success': True,
            'response': ai_response
        })
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)
