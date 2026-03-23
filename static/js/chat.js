/* EduPlatform — chat.js
   Handles WebSocket connection, send, and render for both
   teacher and student chat views.

   Required globals (set in the template via <script> block):
     window.CHAT_CLASSROOM_ID  — classroom pk
     window.CHAT_MY_ID         — logged-in user pk
     window.CHAT_RECEIVER_ID   — the other party's pk
*/

(function () {
  const classroomId = window.CHAT_CLASSROOM_ID;
  const myId        = window.CHAT_MY_ID;
  const receiverId  = window.CHAT_RECEIVER_ID;

  if (!classroomId || !receiverId) return;

  const msgContainer = document.getElementById('chat-messages');
  const input        = document.getElementById('chat-input');
  const sendBtn      = document.getElementById('chat-send');

  let socket;

  function connect() {
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
    socket = new WebSocket(`${proto}://${window.location.host}/ws/chat/${classroomId}/`);

    socket.onopen    = () => console.log('[Chat] connected');
    socket.onmessage = (e) => {
      const data = JSON.parse(e.data);
      appendBubble(data.body, data.sender_id === myId, data.created_at);
    };
    socket.onclose = () => {
      console.warn('[Chat] disconnected — retrying in 3s');
      setTimeout(connect, 3000);
    };
    socket.onerror = (err) => console.error('[Chat] error', err);
  }

  function appendBubble(body, isMine, time) {
    const wrap = document.createElement('div');
    wrap.innerHTML = `
      <div class="bubble ${isMine ? 'sent' : 'recv'}">
        ${escapeHtml(body)}
        <div class="bubble-time">${time}</div>
      </div>`;
    msgContainer.appendChild(wrap);
    msgContainer.scrollTop = msgContainer.scrollHeight;
  }

  function sendMessage() {
    const body = (input.value || '').trim();
    if (!body || !socket || socket.readyState !== WebSocket.OPEN) return;
    socket.send(JSON.stringify({ body, receiver_id: receiverId }));
    input.value = '';
    input.focus();
  }

  function escapeHtml(str) {
    return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  // Event listeners
  if (sendBtn)  sendBtn.addEventListener('click', sendMessage);
  if (input)    input.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } });

  // Scroll to bottom on load
  if (msgContainer) msgContainer.scrollTop = msgContainer.scrollHeight;

  connect();
})();
