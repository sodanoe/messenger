// ─────────────────────────────────────────────────────────
//  Open chat
// ─────────────────────────────────────────────────────────

async function openDM(userId, username, isOnline) {
    currentChat = {
        type: 'dm',
        id: userId,
        name: username,
        is_online: isOnline,
    };
    el('app').classList.add('chat-open');
    showChat(true);
    el('chat-members-btn').style.display = 'none';
    el('chat-name').textContent = username;
    el('chat-avatar').textContent = initials(username);
    el('chat-avatar').style.color = 'var(--accent)';
    el('messages').innerHTML = '';
    Object.keys(msgStore).forEach((k) => delete msgStore[k]);
    clearReply();
    removePendingMedia();
    updateOnlineStatus(userId, isOnline);
    renderContacts();
    try {
        const data = await api(`/messages/${userId}`);
        renderMessages(data.messages.reverse());
        api(`/messages/${userId}/read`, 'POST').catch(() => {});
        loadContacts().then(() => {
            if (!searchActive) renderContacts();
        });
    } catch (e) {
        toast(e.message, 'err');
    }
}

async function openGroup(groupId, groupName) {
    currentChat = { type: 'group', id: groupId, name: groupName };
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
    try {
        const data = await api(`/groups/${groupId}/messages`);
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
        appendMessage(
            {
                id: m.id,
                content: m.content,
                isMe,
                createdAt: m.created_at,
                readAt: m.read_at || null,
                mediaUrl: m.media_url || null,
                replyTo: m.reply_to || null,
                reactions: m.reactions || [],
                senderUsername: m.sender_username || null,
            },
            false,
        );
    });
    scrollBottom();
}

function appendMessage(
    {
        id = null,
        content,
        isMe,
        createdAt,
        readAt = null,
        mediaUrl = null,
        replyTo = null,
        reactions = [],
        senderUsername = null,
    },
    animate = true,
) {
    const wrap = el('messages');
    const row = document.createElement('div');
    row.className = `msg-row ${isMe ? 'me' : 'other'}`;
    if (!animate) row.style.animation = 'none';
    if (id) {
        row.dataset.msgId = id;
        msgStore[id] = {
            id,
            senderName: isMe ? 'Вы' : senderUsername || currentChat?.name || `#${id}`,
            content: content || '',
            mediaUrl: mediaUrl || null,
        };
    }

    // Подпись отправителя — только в группах для чужих сообщений
    const senderLabel =
        !isMe && currentChat?.type === 'group'
            ? `<div class="msg-sender-name">${esc(senderUsername || '?')}</div>`
            : '';

    // Reply quote
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

    // Media
    let mediaHtml = '';
    if (mediaUrl) {
        const fullUrl = mediaUrl.startsWith('http') ? mediaUrl : API_BASE() + mediaUrl;
        mediaHtml = `<div class="msg-media"><img src="${fullUrl}" onclick="openLightbox('${fullUrl}')" alt="photo" loading="lazy"></div>`;
    }

    // Bubble
    const bubbleHtml = content ? `<div class="msg-bubble">${esc(content)}</div>` : '';

    // Reactions
    const reactionsHtml = `<div class="msg-reactions">${renderReactionPills(id, reactions)}</div>`;

    // Actions
    const actionsHtml = id
        ? `<div class="msg-actions">
    <button class="msg-action-btn" onclick="replyToMsg(${id})" title="Ответить">↩</button>
    <button class="msg-action-btn" onclick="showReactionPicker(${id}, this)" title="Реакция">😊</button>
    ${isMe ? `<button class="msg-action-btn danger" onclick="deleteMsg(${id})" title="Удалить">🗑</button>` : ''}
  </div>`
        : '';

    // Статус прочтения — только для своих сообщений в личке
    const statusHtml =
        isMe && currentChat?.type === 'dm'
            ? `<span class="msg-status" style="${readAt ? 'color:var(--accent)' : ''}">${readAt ? '✓✓' : '✓'}</span>`
            : '';

    row.innerHTML = `<div>${actionsHtml}${senderLabel}${replyHtml}${mediaHtml}${bubbleHtml}${reactionsHtml}<div class="msg-meta"><span class="msg-time">${fmtTime(createdAt)}</span>${statusHtml}</div></div>`;
    wrap.appendChild(row);
    if (animate) scrollBottom(true);
}

function scrollBottom(smooth = false) {
    const w = el('messages');
    requestAnimationFrame(() =>
        w.scrollTo({
            top: w.scrollHeight,
            behavior: smooth ? 'smooth' : 'instant',
        }),
    );
}

function scrollToMsg(msgId) {
    const target = document.querySelector(`[data-msg-id="${msgId}"]`);
    if (target) target.scrollIntoView({ behavior: 'smooth', block: 'center' });
}
