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
                const onlineDot = u.is_online
                    ? '<div class="online-dot"></div>'
                    : '';
                const statusColor = u.is_online ? 'color:var(--green)' : '';
                // FIX: data-атрибуты вместо inline строк с username (XSS через esc + HTML decode)
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
// FIX: обёртки для data-атрибутов (защита от XSS через inline onclick + username)
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
    openDM(userId, username, c ? c.is_online : isOnline);
}

// ─────────────────────────────────────────────────────────
//  Contacts / Groups
// ─────────────────────────────────────────────────────────

async function loadContacts() {
    try {
        contacts = await api('/contacts');
        if (activeTab === 'dm' && !searchActive) renderContacts();
    } catch {
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
        .map(
            (
                c,
            ) => `<div class="contact-item ${isActiveDM(c.contact_user_id)}" onclick="openDM(${c.contact_user_id},'${esc(c.username)}',${c.is_online})">
    <div class="avatar">${initials(c.username)}${c.is_online ? '<div class="online-dot"></div>' : ''}</div>
    <div class="contact-info">
      <div class="contact-name">${esc(c.username || c.contact_user_id)}</div>
      <div class="contact-last">${c.last_message ? timeAgo(c.last_message.created_at) : 'нет сообщений'}</div>
    </div>
    ${c.has_unread ? '<div class="unread-dot"></div>' : ''}
  </div>`,
        )
        .join('');
}

async function loadGroups() {
    try {
        groups = await api('/groups');
        if (activeTab === 'groups' && !searchActive) renderGroups();
    } catch {
        toast('Ошибка загрузки групп', 'err');
    }
}

function renderGroups() {
    const wrap = el('contact-list');
    const createBtn = `<button class="create-group-btn" onclick="promptCreateGroup()">＋ Создать группу</button>`;
    if (!groups.length) {
        wrap.innerHTML = createBtn + '<div class="empty-list">Нет групп.</div>';
        return;
    }
    wrap.innerHTML =
        createBtn +
        groups
            .map(
                (
                    g,
                ) => `<div class="contact-item ${isActiveGroup(g.id)}" onclick="openGroup(${g.id},'${esc(g.name)}')">
    <div class="avatar" style="color:var(--accent2)">#</div>
    <div class="contact-info"><div class="contact-name">${esc(g.name)}</div><div class="contact-last">group</div></div>
  </div>`,
            )
            .join('');
}

async function promptCreateGroup() {
    const name = prompt('Название группы:');
    if (!name?.trim()) return;
    try {
        await api('/groups', 'POST', { name: name.trim() });
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
