// ─────────────────────────────────────────────────────────
//  Group UI — создание, управление участниками
// ─────────────────────────────────────────────────────────

let _modalGroupId = null;
let _modalMembers = [];

// ── Открыть модалку для текущей группы ───────────────────

async function openGroupInfo() {
    if (!currentChat || currentChat.type !== 'group') return;
    _modalGroupId = currentChat.id;
    el('group-modal-title').textContent = currentChat.name;
    el('invite-username-input').value = '';
    el('group-modal').style.display = 'flex';
    renderContactPicker();
    await refreshGroupMembers();
}

function closeGroupModal(e) {
    if (e && e.target !== el('group-modal')) return;
    _modalGroupId = null;
    el('group-modal').style.display = 'none';
}

// ── Загрузить и отрисовать список участников ─────────────

async function refreshGroupMembers() {
    if (!_modalGroupId) return;
    try {
        _modalMembers = await api(`/groups/${_modalGroupId}/members`);
        renderGroupMembers(_modalMembers);
        renderContactPicker(); // обновляем пикер — вдруг кто уже в группе
    } catch (e) {
        toast(e.message, 'err');
    }
}

function renderGroupMembers(members) {
    const wrap = el('group-members-list');
    if (!members.length) {
        wrap.innerHTML = '<div style="color:var(--text2);font-size:13px">Нет участников</div>';
        return;
    }

    const myRole = members.find((m) => m.user_id === me?.id)?.role;
    const isAdmin = myRole === 'admin';

    wrap.innerHTML = members
        .map((m) => {
            const isMe = m.user_id === me?.id;
            const roleBadge =
                m.role === 'admin'
                    ? '<span style="font-size:10px;color:var(--accent);background:rgba(99,102,241,.15);padding:1px 5px;border-radius:4px;margin-left:4px">admin</span>'
                    : '';
            const removeBtn =
                isAdmin && !isMe
                    ? `<button onclick="doRemoveMember(${m.user_id})"
           style="background:none;border:none;color:var(--text2);cursor:pointer;font-size:15px;line-height:1;padding:2px 4px;border-radius:4px;transition:color .15s"
           title="Удалить из группы"
           onmouseover="this.style.color='var(--danger,#e55)'" onmouseout="this.style.color='var(--text2)'">✕</button>`
                    : isMe
                      ? '<span style="font-size:11px;color:var(--text2);padding:0 4px">вы</span>'
                      : '';

            return `<div style="display:flex;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid var(--border)">
      <div class="avatar" style="width:28px;height:28px;font-size:12px;flex-shrink:0">${initials(m.username)}</div>
      <span style="flex:1;font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(m.username)}${roleBadge}</span>
      ${removeBtn}
    </div>`;
        })
        .join('');
}

// ── Пикер контактов ───────────────────────────────────────

function renderContactPicker() {
    const wrap = el('contact-picker-list');
    if (!wrap) return;

    const memberIds = new Set(_modalMembers.map((m) => m.user_id));
    const available = contacts.filter((c) => !memberIds.has(c.contact_user_id));

    if (!available.length) {
        wrap.innerHTML =
            '<div style="color:var(--text2);font-size:12px;padding:4px 0">Все контакты уже в группе</div>';
        return;
    }

    wrap.innerHTML = available
        .map(
            (c) =>
                `<button onclick="doInviteContact(${c.contact_user_id}, '${esc(c.username)}')"
       style="display:flex;align-items:center;gap:6px;width:100%;background:none;border:1px solid var(--border);border-radius:6px;padding:5px 8px;cursor:pointer;color:var(--text);font-size:13px;transition:background .15s"
       onmouseover="this.style.background='var(--bg)'" onmouseout="this.style.background='none'">
      <div class="avatar" style="width:22px;height:22px;font-size:10px;flex-shrink:0">${initials(c.username)}</div>
      <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(c.username)}</span>
      <span style="margin-left:auto;color:var(--accent);font-size:12px">+ добавить</span>
    </button>`,
        )
        .join('');
}

async function doInviteContact(userId, username) {
    if (!_modalGroupId) return;
    try {
        await api(`/groups/${_modalGroupId}/invite`, 'POST', { username });
        toast(`${username} добавлен`, 'ok');
        await refreshGroupMembers();
    } catch (e) {
        toast(e.message, 'err');
    }
}

// ── Пригласить участника вручную (поле ввода) ─────────────

async function doInviteMember() {
    const username = el('invite-username-input').value.trim();
    if (!username || !_modalGroupId) return;
    try {
        await api(`/groups/${_modalGroupId}/invite`, 'POST', { username });
        el('invite-username-input').value = '';
        toast(`${username} добавлен`, 'ok');
        await refreshGroupMembers();
    } catch (e) {
        toast(e.message, 'err');
    }
}

// ── Удалить участника (кик) ───────────────────────────────

async function doRemoveMember(userId) {
    if (!_modalGroupId) return;
    const member = _modalMembers.find((m) => m.user_id === userId);
    const name = member?.username || `#${userId}`;
    if (!confirm(`Удалить ${name} из группы?`)) return;
    try {
        await api(`/groups/${_modalGroupId}/members/${userId}`, 'DELETE');
        toast(`${name} удалён`, 'ok');
        await refreshGroupMembers();
    } catch (e) {
        toast(e.message, 'err');
    }
}

// ── Покинуть группу ───────────────────────────────────────

async function doLeaveGroup() {
    if (!_modalGroupId || !me) return;
    if (!confirm(`Покинуть группу «${currentChat?.name}»?`)) return;
    try {
        // FIX: используем новый эндпоинт /leave вместо DELETE /members/{id}
        await api(`/groups/${_modalGroupId}/leave`, 'POST');
        closeGroupModal();
        el('app').classList.remove('chat-open');
        currentChat = null;
        showChat(false);
        await loadGroups();
        if (activeTab === 'groups') renderGroups();
        toast('Вы покинули группу', 'ok');
    } catch (e) {
        toast(e.message, 'err');
    }
}

// ── Удалить группу (только для админа) ───────────────────

async function doDeleteGroup() {
    if (!_modalGroupId) return;
    if (!confirm(`Удалить группу «${currentChat?.name}»? Это действие необратимо.`)) return;
    try {
        await api(`/groups/${_modalGroupId}`, 'DELETE');
        closeGroupModal();
        el('app').classList.remove('chat-open');
        currentChat = null;
        showChat(false);
        await loadGroups();
        if (activeTab === 'groups') renderGroups();
        toast('Группа удалена', 'ok');
    } catch (e) {
        toast(e.message, 'err');
    }
}

// ── Закрытие по Escape ────────────────────────────────────

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && el('group-modal').style.display === 'flex') {
        _modalGroupId = null;
        el('group-modal').style.display = 'none';
    }
});
