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
  await refreshGroupMembers();
}

function closeGroupModal(e) {
  if (e && e.target !== el('group-modal')) return; // клик по оверлею
  _modalGroupId = null;
  el('group-modal').style.display = 'none';
}

// ── Загрузить и отрисовать список участников ─────────────

async function refreshGroupMembers() {
  if (!_modalGroupId) return;
  try {
    _modalMembers = await api(`/groups/${_modalGroupId}/members`);
    renderGroupMembers(_modalMembers);
  } catch(e) { toast(e.message, 'err'); }
}

function renderGroupMembers(members) {
  const wrap = el('group-members-list');
  if (!members.length) { wrap.innerHTML = '<div style="color:var(--text2);font-size:13px">Нет участников</div>'; return; }
  wrap.innerHTML = members.map(m => {
    const isMe = m.user_id === me?.id;
    const onlineDot = m.is_online
      ? '<span style="color:var(--green);font-size:10px;margin-left:4px">●</span>'
      : '';
    const removeBtn = !isMe
      ? `<button onclick="doRemoveMember(${m.user_id})"
           style="background:none;border:none;color:var(--text2);cursor:pointer;font-size:15px;line-height:1;padding:2px 4px;border-radius:4px;transition:color .15s"
           title="Удалить из группы"
           onmouseover="this.style.color='var(--danger,#e55)'" onmouseout="this.style.color='var(--text2)'">✕</button>`
      : '<span style="font-size:11px;color:var(--text2);padding:0 4px">вы</span>';
    return `<div style="display:flex;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid var(--border)">
      <div class="avatar" style="width:28px;height:28px;font-size:12px;flex-shrink:0">${initials(m.username)}</div>
      <span style="flex:1;font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(m.username)}${onlineDot}</span>
      ${removeBtn}
    </div>`;
  }).join('');
}

// ── Пригласить участника ──────────────────────────────────

async function doInviteMember() {
  const username = el('invite-username-input').value.trim();
  if (!username) return;
  if (!_modalGroupId) return;
  try {
    await api(`/groups/${_modalGroupId}/invite`, 'POST', { username });
    el('invite-username-input').value = '';
    toast(`${username} добавлен`, 'ok');
    await refreshGroupMembers();
  } catch(e) { toast(e.message, 'err'); }
}

// ── Удалить участника (кик) ───────────────────────────────

async function doRemoveMember(userId) {
  if (!_modalGroupId) return;
  const member = _modalMembers.find(m => m.user_id === userId);
  const name = member?.username || `#${userId}`;
  if (!confirm(`Удалить ${name} из группы?`)) return;
  try {
    await api(`/groups/${_modalGroupId}/members/${userId}`, 'DELETE');
    toast(`${name} удалён`, 'ok');
    await refreshGroupMembers();
  } catch(e) { toast(e.message, 'err'); }
}

// ── Покинуть группу (удалить себя) ───────────────────────

async function doLeaveGroup() {
  if (!_modalGroupId || !me) return;
  if (!confirm(`Покинуть группу «${currentChat?.name}»?`)) return;
  try {
    await api(`/groups/${_modalGroupId}/members/${me.id}`, 'DELETE');
    closeGroupModal();
    // Закрываем чат и обновляем список
    el('app').classList.remove('chat-open');
    currentChat = null;
    showChat(false);
    await loadGroups();
    if (activeTab === 'groups') renderGroups();
    toast('Вы покинули группу', 'ok');
  } catch(e) { toast(e.message, 'err'); }
}

// ── Закрытие по Escape ────────────────────────────────────

document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && el('group-modal').style.display === 'flex') {
    _modalGroupId = null;
    el('group-modal').style.display = 'none';
  }
});
