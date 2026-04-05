// ─────────────────────────────────────────────────────────
//  Reactions
// ─────────────────────────────────────────────────────────

function renderReactionPills(msgId, reactions) {
    if (!reactions || !reactions.length) return '';
    const grouped = {};
    reactions.forEach((r) => {
        if (!grouped[r.emoji]) grouped[r.emoji] = { count: 0, mine: false };
        grouped[r.emoji].count++;
        if (r.user_id === me?.id) grouped[r.emoji].mine = true;
    });
    return Object.entries(grouped)
        .map(
            ([emoji, { count, mine }]) =>
                `<span class="reaction-pill${mine ? ' mine' : ''}" onclick="reactToMessage(${msgId}, '${emoji}')">${emoji}${count > 1 ? `<span class="r-count">${count}</span>` : ''}</span>`,
        )
        .join('');
}

function updateMessageReactions(msgId, reactions) {
    const row = document.querySelector(`[data-msg-id="${msgId}"]`);
    if (!row) return;
    const container = row.querySelector('.msg-reactions');
    if (container) container.innerHTML = renderReactionPills(msgId, reactions);
}

// FIX: выбираем эндпоинт в зависимости от типа чата
async function reactToMessage(msgId, emoji) {
    try {
        if (currentChat?.type === 'group') {
            await api(
                `/groups/${currentChat.id}/messages/${msgId}/react`,
                'POST',
                { emoji },
            );
        } else {
            await api(`/messages/${msgId}/react`, 'POST', { emoji });
        }
    } catch (e) {
        toast(e.message, 'err');
    }
}

function showReactionPicker(msgId, anchor) {
    pickerMsgId = msgId;
    const picker = el('reaction-picker');
    const rect = anchor.getBoundingClientRect();
    picker.style.display = 'flex';
    const left = Math.min(rect.left, window.innerWidth - 290);
    const top = rect.top - 54;
    picker.style.left = Math.max(6, left) + 'px';
    picker.style.top = Math.max(6, top) + 'px';
}

function hideReactionPicker() {
    pickerMsgId = null;
    el('reaction-picker').style.display = 'none';
}

async function doReact(emoji) {
    if (!pickerMsgId) return;
    const id = pickerMsgId;
    hideReactionPicker();
    await reactToMessage(id, emoji);
}

document.addEventListener('click', (e) => {
    if (
        !el('reaction-picker').contains(e.target) &&
        !e.target.closest('.msg-action-btn')
    ) {
        hideReactionPicker();
    }
});

// ─────────────────────────────────────────────────────────
//  Reply
// ─────────────────────────────────────────────────────────

function replyToMsg(msgId) {
    const data = msgStore[msgId];
    if (!data) return;
    replyTo = {
        id: data.id,
        senderName: data.senderName,
        content: data.content,
        mediaUrl: data.mediaUrl || null,
    };
    const preview = data.content
        ? data.content.slice(0, 60)
        : data.mediaUrl
          ? '📷 Фото'
          : '—';
    el('reply-preview-text').textContent = `${data.senderName}: ${preview}`;
    el('reply-preview').style.display = 'flex';
    el('msg-input').focus();
}

function clearReply() {
    replyTo = null;
    el('reply-preview').style.display = 'none';
    el('reply-preview-text').textContent = '';
}
