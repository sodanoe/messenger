// ─────────────────────────────────────────────────────────
//  Send message
// ─────────────────────────────────────────────────────────

async function sendMessage() {
  if (!currentChat) return;
  const input   = el('msg-input');
  const content = input.value.trim();
  if (!content && !pendingMediaId) return;

  input.value = ''; autoGrow(input);

  const sentReplyTo  = replyTo ? { ...replyTo } : null;
  const sentMediaId  = pendingMediaId;
  const sentMediaUrl = pendingMediaUrl;
  clearReply();

  appendMessage({
    id: null,
    content: content || '',
    isMe: true,
    createdAt: new Date().toISOString(),
    mediaUrl: sentMediaUrl,
    replyTo: sentReplyTo ? { id: sentReplyTo.id, sender_id: me.id, content: sentReplyTo.content, media_url: sentReplyTo.mediaUrl || null } : null,
    reactions: [],
  }, true);
  removePendingMedia();

  try {
    if (currentChat.type === 'dm') {
      await api(`/messages/${currentChat.id}`, 'POST', {
        content:     content || '',
        media_id:    sentMediaId,
        reply_to_id: sentReplyTo?.id || null,
      });
    } else {
      // FIX: передаём media_id и reply_to_id для групп
      await api(`/groups/${currentChat.id}/messages`, 'POST', {
        content:     content || '',
        media_id:    sentMediaId,
        reply_to_id: sentReplyTo?.id || null,
      });
    }
  } catch(e) {
    const wrap = el('messages');
    const ghost = [...wrap.querySelectorAll('.msg-row')].reverse().find(r => !r.dataset.msgId);
    if (ghost) ghost.remove();
    toast(e.message + ' (сообщение не доставлено)', 'err');
    input.value = content;
    if (sentReplyTo) {
      replyTo = sentReplyTo;
      el('reply-preview-text').textContent = `${sentReplyTo.senderName}: ${sentReplyTo.content ? sentReplyTo.content.slice(0,60) : '📷 Фото'}`;
      el('reply-preview').style.display = 'flex';
    }
  }
}

function handleKey(e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } }
function autoGrow(el) { el.style.height = 'auto'; el.style.height = Math.min(el.scrollHeight, 120) + 'px'; }

async function deleteMsg(msgId) {
  if (!confirm('Удалить сообщение?')) return;
  try {
    if (currentChat.type === 'dm') {
      await api(`/messages/${msgId}`, 'DELETE');
    } else {
      await api(`/groups/${currentChat.id}/messages/${msgId}`, 'DELETE');
    }
    document.querySelector(`[data-msg-id="${msgId}"]`)?.remove();
  } catch(e) { toast(e.message, 'err'); }
}