// ─────────────────────────────────────────────────────────
//  Open chat
// ─────────────────────────────────────────────────────────

let isLoadingHistory = false;
let historyCursor = null;
let hasMoreHistory = true;

async function openDM(userId, username, isOnline) {
    let chat;
    hideReactionPicker();

    // Сбрасываем пагинацию
    historyCursor = null;
    hasMoreHistory = true;
    isLoadingHistory = false;

    try {
        chat = await api('/chats/direct', 'POST', { user_id: userId });
    } catch (e) {
        toast(e.message, 'err');
        return;
    }

    currentChat = {
        type: 'direct',
        id: chat.id,
        name: username,
        other_user_id: userId,
    };

    el('app').classList.add('chat-open');
    showChat(true);
    el('chat-members-btn').style.display = 'none';
    el('chat-name').textContent = username;
    el('chat-avatar').textContent = initials(username);
    el('chat-avatar').style.color = 'var(--accent)';

    const s = el('chat-status');
    s.textContent = isOnline ? 'online' : 'offline';
    s.className = 'chat-status' + (isOnline ? ' online' : '');

    el('messages').innerHTML = '';
    Object.keys(msgStore).forEach((k) => delete msgStore[k]);
    clearReply();
    removePendingMedia();
    updateOnlineStatus(userId, isOnline);
    renderContacts();

    const wrap = el('messages');
    wrap.removeEventListener('scroll', onMessagesScroll);
    wrap.addEventListener('scroll', onMessagesScroll);

    try {
        const data = await api(`/chats/${chat.id}/messages`);
        historyCursor = data.next_cursor;
        hasMoreHistory = data.next_cursor !== null;
        renderMessages(data.messages.reverse());
    } catch (e) {
        toast(e.message, 'err');
    }
}

async function openGroup(chatId, groupName) {
    currentChat = { type: 'group', id: chatId, name: groupName };
    hideReactionPicker();

    // Сбрасываем пагинацию
    historyCursor = null;
    hasMoreHistory = true;
    isLoadingHistory = false;

    el('app').classList.add('chat-open');
    showChat(true);
    el('chat-members-btn').style.display = 'block';
    el('chat-name').textContent = groupName;
    el('chat-avatar').textContent = '#';
    el('chat-avatar').style.color = 'var(--accent2)';
    el('chat-status').textContent = 'group chat';
    el('chat-status').className = 'chat-status';
    el('messages').innerHTML = '';
    Object.keys(msgStore).forEach((k) => delete msgStore[k]);
    clearReply();
    removePendingMedia();
    renderGroups();

    const wrap = el('messages');
    wrap.removeEventListener('scroll', onMessagesScroll);
    wrap.addEventListener('scroll', onMessagesScroll);

    try {
        const data = await api(`/chats/${chatId}/messages`);
        historyCursor = data.next_cursor;
        hasMoreHistory = data.next_cursor !== null;
        renderMessages(data.messages.reverse());
    } catch (e) {
        toast(e.message, 'err');
    }
}

function showChat(visible) {
    el('chat-placeholder').style.display = visible ? 'none' : 'flex';
    el('chat-window').style.display = visible ? 'flex' : 'none';
    el('back-btn').style.display = visible && window.innerWidth < 768 ? 'block' : 'none';
}

// ─────────────────────────────────────────────────────────
//  Message rendering
// ─────────────────────────────────────────────────────────

function createMessageRow({
    id = null,
    content,
    isMe,
    createdAt,
    mediaUrl = null,
    replyTo = null,
    reactions = [],
    senderUsername = null,
}) {
    const row = document.createElement('div');
    row.className = `msg-row ${isMe ? 'me' : 'other'}`;
    row.style.animation = 'none';

    if (id) {
        row.dataset.msgId = id;
        msgStore[id] = {
            id,
            senderName: isMe ? 'Вы' : senderUsername || currentChat?.name || `#${id}`,
            content: content || '',
            mediaUrl: mediaUrl || null,
            reactions: reactions || [],
        };
    }

    const senderLabel =
        !isMe && currentChat?.type === 'group'
            ? `<div class="msg-sender-name">${esc(senderUsername || '?')}</div>`
            : '';

    let replyHtml = '';
    if (replyTo) {
        const author =
            replyTo.sender_id === me?.id ? 'Вы' : currentChat?.name || `#${replyTo.sender_id}`;
        const hasText = replyTo.content && replyTo.content.trim();
        const hasMedia = replyTo.media_url;
        const snippet = hasText ? esc(replyTo.content.slice(0, 80)) : hasMedia ? '📷 Фото' : '—';
        const thumbUrl = hasMedia
            ? hasMedia.startsWith('http')
                ? hasMedia
                : API_BASE() + hasMedia
            : null;
        const thumbHtml = thumbUrl
            ? `<img class="reply-thumb" src="${thumbUrl}" onclick="event.stopPropagation();openLightbox('${thumbUrl}')" alt="фото">`
            : '';
        replyHtml = `<div class="msg-reply-quote" onclick="scrollToMsg(${replyTo.id})">
      <div style="flex:1;min-width:0;">
        <span class="reply-author">${esc(author)}</span>
        <span class="reply-content">${snippet}</span>
      </div>
      ${thumbHtml}
    </div>`;
    }

    let mediaHtml = '';
    if (mediaUrl) {
        const fullUrl = mediaUrl.startsWith('http') ? mediaUrl : API_BASE() + mediaUrl;
        mediaHtml = `<div class="msg-media"><img src="${fullUrl}" onclick="openLightbox('${fullUrl}')" alt="photo" loading="lazy"></div>`;
    }

    const trimmed = content?.trim() || '';
    const isSingleCustomEmoji = /^:[a-zA-Z0-9_]+:$/.test(trimmed);
    const isSingleUnicodeEmoji = /^\p{Emoji}$/u.test(trimmed);
    const isSingleEmoji = isSingleCustomEmoji || isSingleUnicodeEmoji;

    const safeContent = esc(content || '');
    const bubbleHtml = content
        ? `<div class="msg-bubble${isSingleEmoji ? ' single-emoji' : ''}">${parseCustomEmojis(safeContent)}</div>`
        : '';

    const reactionsHtml = `<div class="msg-reactions">${renderReactionPills(id, reactions)}</div>`;

    const actionsHtml = id
        ? `<div class="msg-actions">
    <button class="msg-action-btn" onclick="replyToMsg(${id})" title="Ответить">↩</button>
    <button class="msg-action-btn" onclick="showReactionPicker(${id}, this)" title="Реакция">😊</button>
    ${
        isMe
            ? `
        <button class="msg-action-btn" onclick="editMsg(${id})" title="Редактировать">✏️</button>
        <button class="msg-action-btn danger" onclick="deleteMsg(${id})" title="Удалить">🗑</button>
    `
            : ''
    }
    </div>`
        : '';

    row.innerHTML = `<div>${actionsHtml}${senderLabel}${replyHtml}${mediaHtml}${bubbleHtml}${reactionsHtml}<div class="msg-meta"><span class="msg-time">${fmtTime(createdAt)}</span></div></div>`;

    return row;
}

function appendMessage(data, animate = true) {
    const wrap = el('messages');
    const row = createMessageRow(data);
    if (animate) row.style.animation = '';
    wrap.appendChild(row);

    if (animate) {
        scrollBottom(true);

        if (data.mediaUrl) {
            const img = row.querySelector('.msg-media img');
            if (img && !img.complete) {
                img.addEventListener('load', () => scrollBottom(true), { once: true });
                img.addEventListener('error', () => scrollBottom(true), { once: true });
            }
        }
    }
}

function renderMessages(msgs) {
    const wrap = el('messages');
    let lastDay = null;

    msgs.forEach((m) => {
        const isMe = m.sender_id === me.id;
        const day = fmtDay(m.created_at);
        if (day !== lastDay) {
            const d = document.createElement('div');
            d.className = 'day-divider';
            d.textContent = day;
            wrap.appendChild(d);
            lastDay = day;
        }
        const row = createMessageRow({
            id: m.id,
            content: m.content,
            isMe,
            createdAt: m.created_at,
            mediaUrl: m.media_url || null,
            replyTo: m.reply_to || null,
            reactions: m.reactions || [],
            senderUsername: m.sender_username || null,
        });
        wrap.appendChild(row);
    });

    wrap.scrollTop = wrap.scrollHeight;

    requestAnimationFrame(() => {
        wrap.scrollTop = wrap.scrollHeight;
        setTimeout(() => (wrap.scrollTop = wrap.scrollHeight), 50);
        setTimeout(() => (wrap.scrollTop = wrap.scrollHeight), 150);
    });

    const images = wrap.querySelectorAll('img');
    if (images.length > 0) {
        let loadedCount = 0;
        const totalImages = images.length;

        const onImageLoad = () => {
            loadedCount++;
            if (loadedCount === totalImages) {
                wrap.scrollTop = wrap.scrollHeight;
            }
        };

        images.forEach((img) => {
            if (img.complete) {
                onImageLoad();
            } else {
                img.addEventListener('load', onImageLoad, { once: true });
                img.addEventListener('error', onImageLoad, { once: true });
            }
        });
    }
}

// ─────────────────────────────────────────────────────────
//  Pagination
// ─────────────────────────────────────────────────────────

function onMessagesScroll() {
    const wrap = el('messages');
    if (!currentChat || isLoadingHistory || !hasMoreHistory) return;

    if (wrap.scrollTop < 50) {
        loadMoreMessages();
    }
}

async function loadMoreMessages() {
    if (!currentChat || isLoadingHistory || !hasMoreHistory) return;

    isLoadingHistory = true;
    const wrap = el('messages');
    const oldScrollHeight = wrap.scrollHeight;
    const oldScrollTop = wrap.scrollTop;

    try {
        const url = `/chats/${currentChat.id}/messages${historyCursor ? `?cursor=${historyCursor}` : ''}`;
        const data = await api(url);

        if (data.messages && data.messages.length > 0) {
            const oldMessages = data.messages.reverse();

            const fragment = document.createDocumentFragment();
            let lastDay = null;

            oldMessages.forEach((m) => {
                const isMe = m.sender_id === me.id;
                const day = fmtDay(m.created_at);
                if (day !== lastDay) {
                    const d = document.createElement('div');
                    d.className = 'day-divider';
                    d.textContent = day;
                    fragment.appendChild(d);
                    lastDay = day;
                }

                const row = createMessageRow({
                    id: m.id,
                    content: m.content,
                    isMe,
                    createdAt: m.created_at,
                    mediaUrl: m.media_url || null,
                    replyTo: m.reply_to || null,
                    reactions: m.reactions || [],
                    senderUsername: m.sender_username || null,
                });
                fragment.appendChild(row);
            });

            wrap.insertBefore(fragment, wrap.firstChild);

            const newScrollHeight = wrap.scrollHeight;
            wrap.scrollTop = newScrollHeight - oldScrollHeight + oldScrollTop;

            historyCursor = data.next_cursor;
            hasMoreHistory = data.next_cursor !== null;
        } else {
            hasMoreHistory = false;
        }
    } catch (e) {
        toast('Ошибка загрузки истории', 'err');
    } finally {
        isLoadingHistory = false;
    }
}

// ─────────────────────────────────────────────────────────
//  Utils
// ─────────────────────────────────────────────────────────

const emojiCache = {};

function parseCustomEmojis(text) {
    if (!text) return text;

    return text.replace(/:([a-zA-Z0-9_]+):/g, (match, shortcode) => {
        const emoji = customEmojis?.find((e) => e.shortcode === shortcode);
        if (emoji) {
            const url = `/emojis/${shortcode}.png`;
            return `<img src="${url}" class="inline-emoji" alt=":${shortcode}:" title=":${shortcode}:">`;
        }
        return match;
    });
}

function scrollBottom(smooth = false) {
    const w = el('messages');
    requestAnimationFrame(() =>
        w.scrollTo({ top: w.scrollHeight, behavior: smooth ? 'smooth' : 'instant' }),
    );
}

function scrollToMsg(msgId) {
    const target = document.querySelector(`[data-msg-id="${msgId}"]`);
    if (target) target.scrollIntoView({ behavior: 'smooth', block: 'center' });
}
