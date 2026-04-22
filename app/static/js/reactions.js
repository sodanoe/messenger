// ─────────────────────────────────────────────────────────
//  Reactions
// ─────────────────────────────────────────────────────────

function renderReactionPills(msgId, reactions) {
    if (!reactions || !reactions.length) return '';
    const grouped = {};
    reactions.forEach((r) => {
        const key = r.emoji;
        if (!grouped[key]) grouped[key] = { count: 0, mine: false, url: r.custom_emoji_url };
        grouped[key].count++;
        if (r.user_id === me?.id) grouped[key].mine = true;
    });
    return Object.entries(grouped)
        .map(([emoji, { count, mine, url }]) => {
            const emojiHtml = url
                ? `<img src="${url}" class="reaction-emoji-img" alt="${emoji}">`
                : emoji;
            return `<span class="reaction-pill${mine ? ' mine' : ''}" onclick="reactToMessage(${msgId}, '${emoji.replace(/'/g, "\\'")}')">${emojiHtml}${count > 1 ? `<span class="r-count">${count}</span>` : ''}</span>`;
        })
        .join('');
}

function updateMessageReactions(msgId, reactions) {
    const row = document.querySelector(`[data-msg-id="${msgId}"]`);
    if (!row) return;
    const container = row.querySelector('.msg-reactions');
    if (container) {
        container.innerHTML = renderReactionPills(msgId, reactions);
    }
}

async function reactToMessage(msgId, emoji) {
    if (!currentChat) return;

    const msgData = msgStore[msgId];
    if (!msgData) return;

    const existingReaction = (msgData.reactions || []).find(
        (r) => r.emoji === emoji && r.user_id === me?.id,
    );

    try {
        if (existingReaction) {
            // Если реакция уже есть - удаляем
            await api(
                `/chats/${currentChat.id}/messages/${msgId}/reactions/${encodeURIComponent(emoji)}`,
                'DELETE',
            );
        } else {
            // Если нет - добавляем
            await api(`/chats/${currentChat.id}/messages/${msgId}/reactions`, 'POST', { emoji });
        }
        // UI обновится через WebSocket
    } catch (e) {
        toast(e.message, 'err');
    }
}

function showReactionPicker(msgId, anchor) {
    pickerMsgId = msgId;

    const picker = el('reaction-picker');
    picker.style.display = 'grid';

    const rect = anchor.getBoundingClientRect();
    const pickerRect = picker.getBoundingClientRect();

    const pickerWidth = pickerRect.width;
    const pickerHeight = pickerRect.height;

    const margin = 8;

    let left;
    let top;

    const spaceTop = rect.top;
    const spaceBottom = window.innerHeight - rect.bottom;
    const spaceLeft = rect.left;
    const spaceRight = window.innerWidth - rect.right;

    // ── Vertical positioning ──
    if (spaceTop > pickerHeight + margin) {
        // сверху
        top = rect.top - pickerHeight - margin;
    } else if (spaceBottom > pickerHeight + margin) {
        // снизу
        top = rect.bottom + margin;
    } else {
        // центрируем если мало места
        top = Math.max(margin, window.innerHeight / 2 - pickerHeight / 2);
    }

    // ── Horizontal positioning ──
    if (spaceRight > pickerWidth) {
        // слева от кнопки
        left = rect.left;
    } else if (spaceLeft > pickerWidth) {
        // справа
        left = rect.right - pickerWidth;
    } else {
        // центрируем
        left = Math.max(margin, window.innerWidth / 2 - pickerWidth / 2);
    }

    // защита от выхода за экран
    left = Math.max(margin, Math.min(left, window.innerWidth - pickerWidth - margin));
    top = Math.max(margin, Math.min(top, window.innerHeight - pickerHeight - margin));

    picker.style.left = left + 'px';
    picker.style.top = top + 'px';
}

function hideReactionPicker() {
    pickerMsgId = null;
    el('reaction-picker').style.display = 'none';
}

async function doReact(emoji) {
    if (!pickerMsgId) return;
    const id = pickerMsgId;
    hideReactionPicker();

    const msgData = msgStore[id];
    if (!msgData) return;

    const existingReaction = (msgData.reactions || []).find(
        (r) => r.emoji === emoji && r.user_id === me?.id,
    );

    try {
        if (existingReaction) {
            await api(
                `/chats/${currentChat.id}/messages/${id}/reactions/${encodeURIComponent(emoji)}`,
                'DELETE',
            );
        } else {
            await api(`/chats/${currentChat.id}/messages/${id}/reactions`, 'POST', { emoji });
        }
        // UI обновится через WebSocket
    } catch (e) {
        toast(e.message, 'err');
    }
}

document.addEventListener('click', (e) => {
    if (!el('reaction-picker').contains(e.target) && !e.target.closest('.msg-action-btn')) {
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
    const preview = data.content ? data.content.slice(0, 60) : data.mediaUrl ? '📷 Фото' : '—';
    el('reply-preview-text').textContent = `${data.senderName}: ${preview}`;
    el('reply-preview').style.display = 'flex';
    el('msg-input').focus();
}

function clearReply() {
    replyTo = null;
    el('reply-preview').style.display = 'none';
    el('reply-preview-text').textContent = '';
}
