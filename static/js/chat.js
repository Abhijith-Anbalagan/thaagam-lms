/* EduPlatform — chat.js
   Required globals (set in the template):
     window.CHAT_CLASSROOM_ID  — classroom pk
     window.CHAT_MY_ID         — logged-in user pk (number)
     window.CHAT_RECEIVER_ID   — the other party's pk (number)
*/
(function () {
  const classroomId = window.CHAT_CLASSROOM_ID;
  const myId        = Number(window.CHAT_MY_ID);
  const receiverId  = Number(window.CHAT_RECEIVER_ID);

  if (!classroomId || !receiverId) return;

  const msgContainer = document.getElementById('chat-messages');
  const input        = document.getElementById('chat-input');
  const sendBtn      = document.getElementById('chat-send');

  let socket;
  let pendingEcho = false; // true while we wait for our own echo back

  function connect() {
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
    socket = new WebSocket(`${proto}://${window.location.host}/ws/chat/${classroomId}/`);

    socket.onopen = () => {
      setStatus('online');
      if (input) input.disabled = false;
      if (sendBtn) sendBtn.disabled = false;
    };

    socket.onmessage = (e) => {
      const data = JSON.parse(e.data);
      const isMine = Number(data.sender_id) === myId;

      if (isMine && pendingEcho) {
        // Replace the optimistic bubble with the confirmed one (has real timestamp)
        const optimistic = msgContainer.querySelector('.bubble.sent.optimistic');
        if (optimistic) {
          optimistic.querySelector('.bubble-time').textContent = data.created_at;
          optimistic.classList.remove('optimistic');
          pendingEcho = false;
          msgContainer.scrollTop = msgContainer.scrollHeight;
          return;
        }
      }

      // Incoming message from the other party
      if (!isMine) {
        appendBubble(data.body, false, data.created_at);
      }
    };

    socket.onclose = () => {
      setStatus('offline');
      if (input) input.disabled = true;
      if (sendBtn) sendBtn.disabled = true;
      setTimeout(connect, 3000);
    };

    socket.onerror = () => setStatus('offline');
  }

  function setStatus(state) {
    const dot  = document.getElementById('chat-status-dot');
    const text = document.getElementById('chat-status-text');
    if (!dot || !text) return;
    if (state === 'online') {
      dot.style.background = '#22c55e';
      text.textContent     = 'Connected';
    } else {
      dot.style.background = '#ef4444';
      text.textContent     = 'Reconnecting…';
    }
  }

  function appendBubble(body, isMine, time, optimistic) {
    // Remove empty-state placeholder if present
    const empty = msgContainer.querySelector('.empty-state');
    if (empty) empty.remove();

    const wrap = document.createElement('div');
    wrap.className = `mb-4 flex ${isMine ? 'justify-end' : 'justify-start'}`;

    const bubbleClasses = [
      'bubble',
      isMine ? 'sent bg-blue-600 text-white' : 'recv border border-slate-200 bg-white text-slate-900',
      'max-w-[75%] rounded-[1.35rem] px-4 py-3 text-sm leading-6 shadow-sm',
      optimistic ? 'optimistic' : '',
    ].join(' ').trim();

    wrap.innerHTML = `<div class="${bubbleClasses}">${escapeHtml(body)}<div class="bubble-time mt-1 text-xs opacity-70">${time}</div></div>`;
    msgContainer.appendChild(wrap);
    msgContainer.scrollTop = msgContainer.scrollHeight;
  }

  function sendMessage() {
    const body = (input.value || '').trim();
    if (!body) return;
    if (!socket || socket.readyState !== WebSocket.OPEN) return;

    // Optimistic render — show immediately, replace on echo
    const now = new Date();
    const timeStr = now.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', hour12: true });
    appendBubble(body, true, timeStr, true);
    pendingEcho = true;

    socket.send(JSON.stringify({ body, receiver_id: receiverId }));
    input.value = '';
    input.focus();
  }

  function escapeHtml(str) {
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  if (sendBtn) sendBtn.addEventListener('click', sendMessage);
  if (input) {
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
    });
    input.disabled = true; // enabled once socket opens
  }
  if (sendBtn) sendBtn.disabled = true;

  if (msgContainer) msgContainer.scrollTop = msgContainer.scrollHeight;

  connect();
})();
