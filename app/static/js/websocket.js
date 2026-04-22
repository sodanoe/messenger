// ─────────────────────────────────────────────────────────
//  WebSocket
// ─────────────────────────────────────────────────────────

let reconnectTimer = null;
let reconnectDelay = 3000;

async function connectWS() {
    wsClose();

    let ticket;
    try {
        const data = await api('/auth/ws/ticket', 'POST');
        ticket = data.ticket;
    } catch {
        console.error('Failed to get WS ticket');
        if (token) {
            clearTimeout(reconnectTimer);
            reconnectTimer = setTimeout(connectWS, reconnectDelay);
            reconnectDelay = Math.min(reconnectDelay * 1.5, 30000);
        }
        return;
    }

    const wsBase = API_BASE().replace(/^http/, 'ws');
    ws = new WebSocket(`${wsBase}/ws?ticket=${ticket}`);
    const indicator = el('ws-status');

    ws.onopen = () => {
        indicator.className = 'connected';
        reconnectDelay = 3000;
        heartbeatTimer = setInterval(() => {
            if (ws && ws.readyState === WebSocket.OPEN) ws.send('ping');
        }, 20000);
    };

    ws.onmessage = ({ data }) => {
        let msg;
        try {
            msg = JSON.parse(data);
        } catch {
            return;
        }

        console.log('[WS] received:', msg.type, msg);

        // Единое событие для DM и групп
        if (msg.type === 'new_message') {
            const isCurrentChat = currentChat?.id === msg.chat_id;
            const isMe = msg.sender_id === me?.id;

            // Обновляем последнее сообщение в контактах
            updateContactLastMessage(msg.chat_id, {
                id: msg.id,
                content: msg.content,
                created_at: msg.created_at,
                sender_id: msg.sender_id,
                media_url: msg.media_url,
            });

            if (isCurrentChat) {
                if (!isMe) {
                    appendMessage(
                        {
                            id: msg.id,
                            content: msg.content,
                            isMe: false,
                            createdAt: msg.created_at,
                            mediaUrl: msg.media_url || null,
                            replyTo: msg.reply_to || null,
                            reactions: [],
                            senderUsername: msg.sender_username || `#${msg.sender_id}`,
                            senderId: msg.sender_id,
                        },
                        true,
                    );
                }
            } else if (!isMe) {
                notifyUser(msg.sender_username || '?', msg.content);
                toast(`💬 ${msg.sender_username || '?'}: ${msg.content.slice(0, 50)}`, 'ok');
            }

            // Перерисовываем список контактов
            if (activeTab === 'dm' && !searchActive) {
                renderContacts();
            }
        }

        if (msg.type === 'message_deleted') {
            console.log('[WS] message_deleted:', msg);

            // Удаляем из DOM если это текущий чат
            if (currentChat?.id === msg.chat_id) {
                const row = document.querySelector(`[data-msg-id="${msg.message_id}"]`);
                if (row) {
                    row.remove();
                }
            }

            // Удаляем из msgStore
            delete msgStore[msg.message_id];

            // Обновляем последнее сообщение в контактах
            updateContactAfterDelete(msg.chat_id);

            // Перерисовываем список контактов
            if (activeTab === 'dm' && !searchActive) {
                renderContacts();
            }
        }

        if (msg.type === 'message_edited') {
            console.log('[WS] message_edited:', msg.message_id);
            if (currentChat?.id === msg.chat_id) {
                const row = document.querySelector(`[data-msg-id="${msg.message_id}"]`);
                if (row) {
                    const bubble = row.querySelector('.msg-bubble');
                    if (bubble && msg.new_content) {
                        const safeContent = esc(msg.new_content);
                        bubble.innerHTML = parseCustomEmojis(safeContent);
                    }
                    if (msgStore[msg.message_id]) {
                        msgStore[msg.message_id].content = msg.new_content;
                    }
                }
            }
        }

        if (msg.type === 'reaction_update') {
            console.log('[WS] reaction_update received:', msg);

            // Обновляем msgStore
            if (msgStore[msg.message_id]) {
                msgStore[msg.message_id].reactions = msg.reactions;
            }

            if (currentChat?.id === msg.chat_id) {
                updateMessageReactions(msg.message_id, msg.reactions);
            }
        }

        if (msg.type === 'user_online') {
            updateOnlineStatus(msg.user_id, true);
            loadContacts().then(() => {
                if (!searchActive) renderContacts();
            });
        }

        if (msg.type === 'user_offline') {
            updateOnlineStatus(msg.user_id, false);
            loadContacts().then(() => {
                if (!searchActive) renderContacts();
            });
        }
    };

    ws.onerror = (e) => {
        console.error('[WS] error:', e);
        indicator.className = 'error';
    };

    ws.onclose = (e) => {
        console.log('[WS] closed:', e.code, e.reason);
        indicator.className = '';
        clearInterval(heartbeatTimer);
        if (token) {
            clearTimeout(reconnectTimer);
            reconnectTimer = setTimeout(connectWS, reconnectDelay);
            reconnectDelay = Math.min(reconnectDelay * 1.5, 30000);
        }
    };
}

function wsClose() {
    clearInterval(heartbeatTimer);
    clearTimeout(reconnectTimer);
    if (ws) {
        ws.onclose = null;
        ws.close();
        ws = null;
    }
}
