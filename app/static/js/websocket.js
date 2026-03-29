// ─────────────────────────────────────────────────────────
//  WebSocket
// ─────────────────────────────────────────────────────────

let reconnectTimer = null;
let reconnectDelay = 3000;

function connectWS() {
  wsClose();
  const wsBase = API_BASE().replace(/^http/, 'ws');
  ws = new WebSocket(`${wsBase}/ws?token=${token}`);
  const indicator = el('ws-status');
  ws.onopen = () => {
    indicator.className = 'connected';
    reconnectDelay = 3000;  // сбрасываем backoff при успешном коннекте
    heartbeatTimer = setInterval(() => { if (ws && ws.readyState === WebSocket.OPEN) ws.send('ping'); }, 20000);
  };
  ws.onmessage = ({ data }) => {
    let msg; try { msg = JSON.parse(data); } catch { return; }

    if (msg.type === 'new_message') {
      if (currentChat?.type === 'dm' && currentChat?.id === msg.from) {
        appendMessage({
          id: msg.id,
          content: msg.content,
          isMe: false,
          createdAt: msg.created_at,
          mediaUrl: msg.media_url || null,
          replyTo: msg.reply_to || null,
          reactions: [],
        }, true);
        api(`/messages/${msg.from}/read`, 'POST').catch(()=>{});
      } else {
        const c = contacts.find(c => c.contact_user_id === msg.from);
        if (c) { c.has_unread = true; if (!searchActive) renderContacts(); }
        notifyUser(getUsername(msg.from), msg.content);
        toast(`💬 ${getUsername(msg.from)}: ${msg.content.slice(0,50)}`, 'ok');
      }
      loadContacts().then(() => { if (!searchActive) renderContacts(); });
    }

    if (msg.type === 'group_message') {
      if (currentChat?.type === 'group' && currentChat?.id === msg.group_id) {
        const isMe = msg.sender_id === me?.id;
        // Не дублируем своё оптимистичное сообщение
        if (!isMe) {
          appendMessage({ id: msg.id ?? null, content: msg.content, isMe: false, createdAt: msg.created_at, reactions: [] }, true);
        }
      } else {
        const g = groups.find(g => g.id === msg.group_id);
        notifyUser(`# ${g?.name || msg.group_id}`, msg.content);
        toast(`# ${g?.name || msg.group_id}: ${msg.content.slice(0,50)}`, 'ok');
      }
    }

    if (msg.type === 'reaction_update') {
      updateMessageReactions(msg.message_id, msg.reactions);
    }

    if (msg.type === 'user_online')  { updateOnlineStatus(msg.user_id, true);  loadContacts().then(()=>{ if(!searchActive) renderContacts(); }); }
    if (msg.type === 'user_offline') { updateOnlineStatus(msg.user_id, false); loadContacts().then(()=>{ if(!searchActive) renderContacts(); }); }
  };
  ws.onerror = () => { indicator.className = 'error'; };
  ws.onclose = () => {
    indicator.className = '';
    clearInterval(heartbeatTimer);
    if (token) {
      clearTimeout(reconnectTimer);   // FIX: не накапливаем таймеры
      reconnectTimer = setTimeout(connectWS, reconnectDelay);
      reconnectDelay = Math.min(reconnectDelay * 1.5, 30000);  // FIX: exponential backoff, макс 30с
    }
  };
}

function wsClose() { clearInterval(heartbeatTimer); clearTimeout(reconnectTimer); if (ws) { ws.onclose = null; ws.close(); ws = null; } }
