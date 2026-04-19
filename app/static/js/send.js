// ─────────────────────────────────────────────────────────
//  Send message
// ─────────────────────────────────────────────────────────

async function sendMessage() {
    if (!currentChat) return;
    const input = el('msg-input');
    const content = input.value.trim();
    if (!content && !pendingMediaId) return;

    input.value = '';
    autoGrow(input);

    const sentReplyTo = replyTo ? { ...replyTo } : null;
    const sentMediaId = pendingMediaId;
    clearReply();
    removePendingMedia();

    // Ищем кнопку по классу
    const sendBtn = document.querySelector('.send-btn');
    if (sendBtn) {
        sendBtn.disabled = true;
        sendBtn.textContent = '⏳';
    }

    try {
        const response = await api(`/chats/${currentChat.id}/messages`, 'POST', {
            content: content || '',
            media_id: sentMediaId,
            reply_to_id: sentReplyTo?.id || null,
        });

        if (response && response.id) {
            appendMessage(
                {
                    id: response.id,
                    content: response.content,
                    isMe: true,
                    createdAt: response.created_at,
                    mediaUrl: response.media_url || null,
                    replyTo: response.reply_to || null,
                    reactions: [],
                    senderUsername: 'Вы',
                },
                true,
            );

            // Обновляем последнее сообщение в контактах
            updateContactLastMessage(currentChat.id, {
                id: response.id,
                content: response.content,
                created_at: response.created_at,
                sender_id: me.id,
                media_url: response.media_url,
            });

            // Перерисовываем список контактов
            if (activeTab === 'dm' && !searchActive) {
                renderContacts();
            }
        }
    } catch (e) {
        toast(e.message + ' (сообщение не доставлено)', 'err');
        input.value = content;
        if (sentReplyTo) {
            replyTo = sentReplyTo;
            el('reply-preview-text').textContent =
                `${sentReplyTo.senderName}: ${sentReplyTo.content ? sentReplyTo.content.slice(0, 60) : '📷 Фото'}`;
            el('reply-preview').style.display = 'flex';
        }
    } finally {
        if (sendBtn) {
            sendBtn.disabled = false;
            sendBtn.textContent = '➤';
        }
    }
}

async function editMsg(msgId) {
    const current = msgStore[msgId]?.content || '';
    const newContent = prompt('Редактировать сообщение:', current);
    if (newContent === null || newContent.trim() === current) return;
    if (!newContent.trim()) {
        toast('Сообщение не может быть пустым', 'err');
        return;
    }
    try {
        await api(`/chats/${currentChat.id}/messages/${msgId}`, 'PUT', {
            new_content: newContent.trim(),
        });
        // UI обновится через WebSocket — но добавим локально для отзывчивости
        const row = document.querySelector(`[data-msg-id="${msgId}"]`);
        if (row) {
            const bubble = row.querySelector('.msg-bubble');
            if (bubble) bubble.textContent = newContent.trim();
        }
        if (msgStore[msgId]) msgStore[msgId].content = newContent.trim();
    } catch (e) {
        toast(e.message, 'err');
    }
}

function handleKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
}

function autoGrow(el) {
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}

async function deleteMsg(msgId) {
    if (!confirm('Удалить сообщение?')) return;
    try {
        await api(`/chats/${currentChat.id}/messages/${msgId}`, 'DELETE');

        // Удаляем из DOM
        document.querySelector(`[data-msg-id="${msgId}"]`)?.remove();
        delete msgStore[msgId];

        // Обновляем контакт
        await updateContactAfterDelete(currentChat.id);

        // Перерисовываем
        if (activeTab === 'dm' && !searchActive) {
            renderContacts();
        }
    } catch (e) {
        toast(e.message, 'err');
    }
}
