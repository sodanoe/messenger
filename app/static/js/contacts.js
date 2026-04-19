// ─────────────────────────────────────────────────────────
//  Search
// ─────────────────────────────────────────────────────────

function onSearchInput(val) {
    const trimmed = val.trim();
    el('search-clear').style.display = trimmed ? 'block' : 'none';
    clearTimeout(searchTimer);
    if (!trimmed) {
        hideSearch();
        return;
    }
    searchTimer = setTimeout(() => doSearch(trimmed), 280);
}

async function doSearch(q) {
    try {
        renderSearch(await api(`/users/search?q=${encodeURIComponent(q)}`));
    } catch {
        renderSearch([]);
    }
}

function renderSearch(users) {
    const wrap = el('search-results');
    el('sidebar-tabs').style.display = 'none';
    el('contact-list').style.display = 'none';
    wrap.style.display = 'block';
    searchActive = true;
    if (!users.length) {
        wrap.innerHTML = '<div class="search-empty">Никого не найдено</div>';
        return;
    }
    const contactIds = new Set(contacts.map((c) => c.contact_user_id));
    wrap.innerHTML =
        '<div class="search-header">Результаты поиска</div>' +
        users
            .map((u) => {
                const isContact = contactIds.has(u.id);
                const onlineDot = u.is_online ? '<div class="online-dot"></div>' : '';
                const statusColor = u.is_online ? 'color:var(--green)' : '';
                return `<div class="search-item">
      <div class="avatar" style="position:relative">${initials(u.username)}${onlineDot}</div>
      <div class="contact-info">
        <div class="contact-name">${esc(u.username)}</div>
        <div class="contact-last" style="${statusColor}">${u.is_online ? '● online' : 'offline'}</div>
      </div>
      <div class="search-actions">
        ${
            isContact
                ? `<span class="action-btn already">✓ добавлен</span><button class="action-btn" data-uid="${u.id}" data-uname="${esc(u.username)}" data-online="${!!u.is_online}" onclick="openDMFromEl(this)">💬</button>`
                : `<button class="action-btn add" data-uid="${u.id}" data-uname="${esc(u.username)}" onclick="addAndChatFromEl(this)">＋</button><button class="action-btn" data-uid="${u.id}" data-uname="${esc(u.username)}" data-online="${!!u.is_online}" onclick="openDMFromEl(this)">💬</button>`
        }
      </div>
    </div>`;
            })
            .join('');
}

function hideSearch() {
    searchActive = false;
    el('search-results').style.display = 'none';
    el('sidebar-tabs').style.display = 'flex';
    el('contact-list').style.display = 'block';
}

function clearSearch() {
    el('search-input').value = '';
    el('search-clear').style.display = 'none';
    clearTimeout(searchTimer);
    hideSearch();
}

async function addAndChat(userId, username) {
    try {
        await api('/contacts', 'POST', { username });
        await loadContacts();
        toast(`${username} добавлен`, 'ok');
    } catch (e) {
        if (!e.message.includes('409') && !e.message.includes('already')) {
            toast(e.message, 'err');
            return;
        }
    }
    clearSearch();
    openDMById(userId, username, false);
}

function openDMFromEl(btn) {
    const uid = +btn.dataset.uid,
        uname = btn.dataset.uname,
        online = btn.dataset.online === 'true';
    clearSearch();
    openDMById(uid, uname, online);
}

function addAndChatFromEl(btn) {
    addAndChat(+btn.dataset.uid, btn.dataset.uname);
}

async function openDMById(userId, username, isOnline) {
    clearSearch();
    const c = contacts.find((c) => c.contact_user_id === userId);
    // Берём актуальный статус из контакта
    const onlineStatus = c ? c.is_online : isOnline;
    openDM(userId, username, onlineStatus);
}

// ─────────────────────────────────────────────────────────
//  Contacts / Chats
// ─────────────────────────────────────────────────────────

async function loadContacts() {
    try {
        contacts = await api('/contacts');

        // Получаем список чатов
        const chatsData = await api('/chats/');
        const allChats = chatsData.chats || [];

        // Для каждого контакта ищем его direct чат и последнее сообщение
        for (const contact of contacts) {
            // Находим direct чат с этим пользователем
            const directChat = allChats.find(
                (chat) => chat.type === 'direct' && chat.other_user_id === contact.contact_user_id,
            );

            if (directChat) {
                try {
                    const history = await api(`/chats/${directChat.id}/messages?limit=1`);
                    if (history.messages && history.messages.length > 0) {
                        contact.last_message = history.messages[0];
                    }
                } catch (e) {
                    console.error('Error loading messages for chat', directChat.id, e);
                }
            }
        }

        // Сортируем по дате последнего сообщения
        contacts.sort((a, b) => {
            const timeA = a.last_message ? new Date(a.last_message.created_at).getTime() : 0;
            const timeB = b.last_message ? new Date(b.last_message.created_at).getTime() : 0;
            return timeB - timeA;
        });

        if (activeTab === 'dm' && !searchActive) renderContacts();
    } catch (e) {
        console.error('Error loading contacts:', e);
        toast('Ошибка загрузки контактов', 'err');
    }
}

function renderContacts() {
    const wrap = el('contact-list');
    if (!contacts.length) {
        wrap.innerHTML =
            '<div class="empty-list">Нет контактов.<br>Найди пользователя через поиск.</div>';
        return;
    }
    wrap.innerHTML = contacts
        .map((c) => {
            let lastMsgText = 'нет сообщений';
            let lastMsgTime = '';

            if (c.last_message) {
                const isMe = c.last_message.sender_id === me?.id;
                lastMsgText =
                    (isMe ? 'Вы: ' : '') + (c.last_message.content || '📷 Фото').slice(0, 25);
                lastMsgTime = timeAgo(c.last_message.created_at);
            }

            return `<div class="contact-item ${isActiveDM(c.contact_user_id)}" onclick="openDMById(${c.contact_user_id},'${esc(c.username)}',${c.is_online})">
    <div class="avatar">${initials(c.username)}${c.is_online ? '<div class="online-dot"></div>' : ''}</div>
    <div class="contact-info">
      <div class="contact-name">${esc(c.username || c.contact_user_id)}</div>
      <div class="contact-last">${esc(lastMsgText)}</div>
    </div>
    <div class="contact-meta">
      <div class="contact-time">${lastMsgTime}</div>
      ${c.has_unread ? '<div class="unread-dot"></div>' : ''}
    </div>
  </div>`;
        })
        .join('');
}

function updateContactLastMessage(chatId, message) {
    // Находим контакт по chat_id
    const contact = contacts.find((c) => {
        // Ищем direct чат с этим chat_id
        const chat = chats.find((ch) => ch.id === chatId && ch.type === 'direct');
        return chat && c.contact_user_id === chat.other_user_id;
    });

    if (contact) {
        contact.last_message = message;
        // Сортируем контакты по времени последнего сообщения
        contacts.sort((a, b) => {
            const timeA = a.last_message ? new Date(a.last_message.created_at).getTime() : 0;
            const timeB = b.last_message ? new Date(b.last_message.created_at).getTime() : 0;
            return timeB - timeA;
        });
    }
}

async function updateContactAfterDelete(chatId) {
    // Находим контакт по chat_id
    const contact = contacts.find((c) => {
        const chat = chats.find((ch) => ch.id === chatId && ch.type === 'direct');
        return chat && c.contact_user_id === chat.other_user_id;
    });

    if (contact) {
        // Загружаем последнее сообщение заново
        try {
            const history = await api(`/chats/${chatId}/messages?limit=1`);
            if (history.messages && history.messages.length > 0) {
                contact.last_message = history.messages[0];
            } else {
                contact.last_message = null;
            }

            // Сортируем контакты
            contacts.sort((a, b) => {
                const timeA = a.last_message ? new Date(a.last_message.created_at).getTime() : 0;
                const timeB = b.last_message ? new Date(b.last_message.created_at).getTime() : 0;
                return timeB - timeA;
            });
        } catch (e) {
            console.error('Error updating contact after delete:', e);
        }
    }
}

async function loadGroups() {
    try {
        const allChats = await api('/chats/');
        chats = allChats.chats || [];
        if (activeTab === 'groups' && !searchActive) renderGroups();
    } catch {
        toast('Ошибка загрузки групп', 'err');
    }
}

function renderGroups() {
    const wrap = el('contact-list');
    const groupChats = chats.filter((c) => c.type === 'group');
    const createBtn = `<button class="create-group-btn" onclick="promptCreateGroup()">＋ Создать группу</button>`;
    if (!groupChats.length) {
        wrap.innerHTML = createBtn + '<div class="empty-list">Нет групп.</div>';
        return;
    }
    wrap.innerHTML =
        createBtn +
        groupChats
            .map(
                (
                    g,
                ) => `<div class="contact-item ${isActiveGroup(g.id)}" onclick="openGroup(${g.id},'${esc(g.name)}')">
    <div class="avatar" style="color:var(--accent2)">#</div>
    <div class="contact-info"><div class="contact-name">${esc(g.name)}</div><div class="contact-last">группа</div></div>
  </div>`,
            )
            .join('');
}

async function promptCreateGroup() {
    const name = prompt('Название группы:');
    if (!name?.trim()) return;
    try {
        await api('/chats/group', 'POST', { name: name.trim(), member_ids: [] });
        await loadGroups();
        if (activeTab === 'groups') renderGroups();
        toast('Группа создана', 'ok');
    } catch (e) {
        toast(e.message, 'err');
    }
}

function switchTab(tab) {
    activeTab = tab;
    el('tab-dm').classList.toggle('active', tab === 'dm');
    el('tab-groups').classList.toggle('active', tab === 'groups');
    tab === 'dm' ? renderContacts() : renderGroups();
}
