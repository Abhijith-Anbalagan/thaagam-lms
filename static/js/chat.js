/* EduPlatform — chat.js
   Globals required in template:
     window.CHAT_CLASSROOM_ID, CHAT_MY_ID, CHAT_RECEIVER_ID, CHAT_CSRF_TOKEN
*/
(function () {
  const classroomId = window.CHAT_CLASSROOM_ID;
  const myId        = Number(window.CHAT_MY_ID);
  const receiverId  = Number(window.CHAT_RECEIVER_ID);
  const csrfToken   = window.CHAT_CSRF_TOKEN || '';

  if (!classroomId || !receiverId) return;

  const msgContainer = document.getElementById('chat-messages');
  const input        = document.getElementById('chat-input');
  const sendBtn      = document.getElementById('chat-send');
  const fileBtn      = document.getElementById('chat-file-btn');
  const fileInput    = document.getElementById('chat-file-input');
  const filePreview  = document.getElementById('chat-file-preview');

  let socket;
  let pendingEcho = false;
  let pendingFile = null; // { file, isImage }

  // ── WebSocket ──────────────────────────────────────────────────────────────
  function connect() {
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
    socket = new WebSocket(`${proto}://${window.location.host}/ws/chat/${classroomId}/`);

    socket.onopen = () => {
      setStatus('online');
      if (input)   input.disabled   = false;
      if (sendBtn) sendBtn.disabled = false;
    };

    socket.onmessage = (e) => {
      const data   = JSON.parse(e.data);
      const isMine = Number(data.sender_id) === myId;

      if (isMine) {
        // Confirm optimistic bubble — update time and patch real URL if attachment
        const opt = msgContainer.querySelector('.bubble.optimistic');
        if (opt) {
          opt.querySelector('.bubble-time').textContent = data.created_at;
          opt.classList.remove('optimistic');
          // Patch doc link href with real server URL
          if (data.attachment_url && !data.is_image) {
            const link = opt.querySelector('a.doc-link');
            if (link) link.href = data.attachment_url;
          }
          // Patch image src with real server URL
          if (data.attachment_url && data.is_image) {
            const img = opt.querySelector('img.chat-img');
            if (img) { img.src = data.attachment_url; img.parentElement.href = data.attachment_url; }
          }
          pendingEcho = false;
          msgContainer.scrollTop = msgContainer.scrollHeight;
        }
        return;
      }

      // Incoming from other party
      appendBubble(data.body, false, data.created_at, false,
                   data.attachment_url, data.attachment_name, data.is_image);
    };

    socket.onclose = () => {
      setStatus('offline');
      if (input)   input.disabled   = true;
      if (sendBtn) sendBtn.disabled = true;
      setTimeout(connect, 3000);
    };
    socket.onerror = () => setStatus('offline');
  }

  // ── Status ─────────────────────────────────────────────────────────────────
  function setStatus(state) {
    const dot  = document.getElementById('chat-status-dot')  || document.getElementById('status-dot');
    const text = document.getElementById('chat-status-text') || document.getElementById('status-text');
    if (!dot || !text) return;
    const map = { online: ['#22c55e','Connected'], offline: ['#ef4444','Offline'] };
    const [color, label] = map[state] || ['#facc15','Reconnecting…'];
    dot.style.background = color;
    text.textContent     = label;
  }

  // ── Bubble renderer ────────────────────────────────────────────────────────
  function appendBubble(body, isMine, time, optimistic, attachmentUrl, attachmentName, isImage) {
    const empty = msgContainer.querySelector('.empty-state');
    if (empty) empty.remove();

    const wrap = document.createElement('div');
    wrap.className = `bubble-row mb-3 flex ${isMine ? 'justify-end sent' : 'justify-start recv'}`;

    const useInline = window.CHAT_USE_INLINE_STYLES;

    let base, bubbleStyle = '';
    if (useInline) {
      // Inline styles for non-Tailwind pages (teacher classroom_detail)
      base = `bubble optimistic-target${optimistic ? ' optimistic' : ''}`;
      bubbleStyle = isMine
        ? 'max-width:70%;border-radius:14px;padding:9px 13px;font-size:13.5px;line-height:1.5;word-break:break-word;overflow:hidden;background:#4c68d7;color:#fff;border-bottom-right-radius:4px;'
        : 'max-width:70%;border-radius:14px;padding:9px 13px;font-size:13.5px;line-height:1.5;word-break:break-word;overflow:hidden;background:#f4f5f9;color:#1a1f36;border:1px solid #e8e8ec;border-bottom-left-radius:4px;';
    } else {
      // Tailwind classes for student chat
      const sentCls = 'bubble optimistic-target bg-blue-600 text-white';
      const recvCls = 'bubble optimistic-target bg-white text-slate-900 border border-slate-200';
      base = (isMine ? sentCls : recvCls) +
             ' max-w-[72%] rounded-2xl shadow-sm text-sm leading-relaxed' +
             (optimistic ? ' optimistic' : '');
    }

    let inner = '';

    if (attachmentUrl || (optimistic && attachmentName)) {
      const url  = attachmentUrl || '#';
      const name = escapeHtml(attachmentName || 'file');

      if (isImage) {
        // ── Image bubble ──────────────────────────────────────────────────
        inner += `
          <a href="${url}" target="_blank" class="block">
            <img src="${url}" class="chat-img w-full rounded-xl object-cover"
                 style="max-height:240px;min-width:160px;" alt="image"/>
          </a>`;
        if (body) inner += `<p class="px-3 pt-2 pb-1">${escapeHtml(body)}</p>`;
        inner += `<div class="bubble-time px-3 pb-2 text-xs opacity-60 text-right">${time}</div>`;
      } else {
        // ── Document bubble ───────────────────────────────────────────────
        const ext  = (attachmentName || '').split('.').pop().toLowerCase();
        const icons = { pdf:'📄', doc:'📝', docx:'📝', xls:'📊', xlsx:'📊',
                        ppt:'📑', pptx:'📑', zip:'🗜️', txt:'📃' };
        const icon = icons[ext] || '📎';
        const cardBg = isMine ? 'bg-blue-500 border-blue-400' : 'bg-slate-50 border-slate-200';
        inner += `
          <a href="${url}" target="_blank" class="doc-link flex items-center gap-3 rounded-xl border ${cardBg} px-4 py-3 no-underline transition hover:opacity-80">
            <span class="text-2xl flex-shrink-0">${icon}</span>
            <div class="min-w-0 flex-1">
              <p class="truncate font-medium text-sm ${isMine ? 'text-white' : 'text-slate-800'}">${name}</p>
              <p class="text-xs mt-0.5 ${isMine ? 'text-blue-200' : 'text-slate-400'}">Tap to download</p>
            </div>
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 flex-shrink-0 ${isMine ? 'text-blue-200' : 'text-slate-400'}" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
            </svg>
          </a>`;
        if (body) inner += `<p class="px-1 pt-2 pb-1">${escapeHtml(body)}</p>`;
        inner += `<div class="bubble-time pt-1 pb-1 px-1 text-xs opacity-60 text-right">${time}</div>`;
      }
    } else {
      // Text-only bubble
      if (useInline) {
        inner = `<span>${escapeHtml(body)}</span><div class="bubble-time" style="font-size:10px;opacity:.6;margin-top:3px;text-align:right;">${time}</div>`;
      } else {
        inner = `<p class="px-4 py-3">${escapeHtml(body)}</p>
                 <div class="bubble-time px-4 pb-2 text-xs opacity-60 text-right">${time}</div>`;
      }
    }

    wrap.innerHTML = `<div class="${base}"${bubbleStyle ? ` style="${bubbleStyle}"` : ''}>${inner}</div>`;
    msgContainer.appendChild(wrap);
    msgContainer.scrollTop = msgContainer.scrollHeight;
  }

  function escapeHtml(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  // ── Send text ──────────────────────────────────────────────────────────────
  function sendMessage() {
    const body = (input ? input.value : '').trim();
    if (pendingFile) { uploadFile(body); return; }
    if (!body) return;
    if (!socket || socket.readyState !== WebSocket.OPEN) return;

    const time = now();
    appendBubble(body, true, time, true);
    pendingEcho = true;
    socket.send(JSON.stringify({ body, receiver_id: receiverId }));
    if (input) { input.value = ''; input.focus(); }
  }

  function now() {
    return new Date().toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', hour12: true });
  }

  // ── File picker ────────────────────────────────────────────────────────────
  if (fileBtn && fileInput) {
    fileBtn.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', () => {
      const file = fileInput.files[0];
      if (!file) return;
      pendingFile = { file, isImage: file.type.startsWith('image/') };
      showPreviewStrip(file);
      fileInput.value = '';
    });
  }

  function showPreviewStrip(file) {
    if (!filePreview) return;
    const isImg = file.type.startsWith('image/');
    const name  = escapeHtml(file.name);
    const size  = file.size < 1024 * 1024
      ? (file.size / 1024).toFixed(0) + ' KB'
      : (file.size / 1024 / 1024).toFixed(1) + ' MB';

    const thumb = isImg
      ? `<img src="${URL.createObjectURL(file)}" class="h-9 w-9 rounded-lg object-cover flex-shrink-0"/>`
      : `<span class="text-xl flex-shrink-0">📎</span>`;

    filePreview.innerHTML = `
      <div class="flex items-center gap-2 rounded-2xl border border-blue-200 bg-blue-50 px-3 py-2 text-sm">
        ${thumb}
        <div class="min-w-0 flex-1">
          <p class="truncate font-medium text-slate-700 text-xs">${name}</p>
          <p class="text-xs text-slate-400">${size}</p>
        </div>
        <button id="chat-file-clear" class="flex-shrink-0 text-slate-400 hover:text-red-500 text-base leading-none">✕</button>
      </div>`;
    filePreview.classList.remove('hidden');
    document.getElementById('chat-file-clear').addEventListener('click', clearFile);
  }

  function clearFile() {
    pendingFile = null;
    if (filePreview) { filePreview.innerHTML = ''; filePreview.classList.add('hidden'); }
  }

  // ── Upload via HTTP ────────────────────────────────────────────────────────
  function uploadFile(body) {
    if (!pendingFile) return;
    const { file, isImage } = pendingFile;

    // Optimistic bubble — use blob URL for images, filename for docs
    const blobUrl = isImage ? URL.createObjectURL(file) : null;
    appendBubble(body, true, now(), true, blobUrl, file.name, isImage);
    clearFile();
    if (input) { input.value = ''; input.focus(); }

    const fd = new FormData();
    fd.append('file', file);
    fd.append('receiver_id', receiverId);
    if (body) fd.append('body', body);

    fetch(`/chat/upload/${classroomId}/`, {
      method: 'POST',
      headers: { 'X-CSRFToken': csrfToken },
      body: fd,
    }).then(r => r.json()).then(d => {
      if (d.error) console.error('Upload error:', d.error);
    }).catch(err => console.error('Upload failed:', err));
  }

  // ── Listeners ──────────────────────────────────────────────────────────────
  if (sendBtn) sendBtn.addEventListener('click', sendMessage);
  if (input) {
    input.addEventListener('keydown', e => {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
    });
    input.disabled = true;
  }
  if (sendBtn) sendBtn.disabled = true;
  if (msgContainer) msgContainer.scrollTop = msgContainer.scrollHeight;

  connect();
})();
