// ─────────────────────────────────────────────────────────
//  Send message
// ─────────────────────────────────────────────────────────

async function sendMessage() {
  if (!currentChat) return;
  const input   = el('msg-input');
  const content = input.value.trim();
  if (!content && !pendingMediaId) return;

  input.value = ''; autoGrow(input);

  // Сохраняем состояние ДО очистки
  const sentReplyTo  = replyTo ? { ...replyTo } : null;
  const sentMediaId  = pendingMediaId;   // FIX: сохраняем до removePendingMedia()
  const sentMediaUrl = pendingMediaUrl;
  clearReply();

  // Оптимистичное отображение — показываем сразу
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
        content:      content || '',
        media_id:     sentMediaId,        // FIX: используем сохранённый id
        reply_to_id:  sentReplyTo?.id || null,
      });
    } else {
      await api(`/groups/${currentChat.id}/messages`, 'POST', { content: content || '' });
    }
  } catch(e) {
    // FIX: убираем оптимистичный «призрак» при ошибке
    const wrap = el('messages');
    const ghost = [...wrap.querySelectorAll('.msg-row')].reverse().find(r => !r.dataset.msgId);
    if (ghost) ghost.remove();
    toast(e.message + ' (сообщение не доставлено)', 'err');
    input.value = content;
    if (sentReplyTo) { replyTo = sentReplyTo; el('reply-preview-text').textContent = `${sentReplyTo.senderName}: ${sentReplyTo.content ? sentReplyTo.content.slice(0,60) : '📷 Фото'}`; el('reply-preview').style.display = 'flex'; }
  }
}

function handleKey(e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } }
function autoGrow(el) { el.style.height = 'auto'; el.style.height = Math.min(el.scrollHeight, 120) + 'px'; }
