// ─────────────────────────────────────────────────────────
//  Misc helpers
// ─────────────────────────────────────────────────────────

function goBack() {
    el('app').classList.remove('chat-open');
    currentChat = null;
    showChat(false);
    removePendingMedia();
    clearReply();
}
function updateOnlineStatus(userId, isOnline) {
    if (currentChat?.type === 'dm' && currentChat?.id === userId) {
        const s = el('chat-status');
        s.textContent = isOnline ? 'online' : 'offline';
        s.className = 'chat-status' + (isOnline ? ' online' : '');
    }
    const c = contacts.find((c) => c.contact_user_id === userId);
    if (c) c.is_online = isOnline;
}

async function genInvite() {
    try {
        const r = await api('/auth/invite', 'POST');
        lastInvite = r.code;
        renderInviteBox(lastInvite);
        toast('Инвайт создан — нажми чтобы скопировать', 'info');
    } catch (e) {
        toast(e.message, 'err');
    }
}
function renderInviteBox(code) {
    const box = el('invite-code-box');
    box.textContent = code;
    box.className = 'invite-code-box';
    el('invite-hint').textContent = 'Нажми на код чтобы скопировать';
}
function copyInvite() {
    if (!lastInvite) return;
    navigator.clipboard
        .writeText(lastInvite)
        .then(() => {
            toast(`Скопировано: ${lastInvite}`, 'ok');
            el('invite-hint').textContent = '✓ Скопировано';
        })
        .catch(() => prompt('Скопируй код:', lastInvite));
}

function showErr(errEl, msg) {
    errEl.textContent = msg;
    errEl.style.display = 'block';
}
function isActiveDM(uid) {
    return currentChat?.type === 'dm' && currentChat?.id === uid ? 'active' : '';
}
function isActiveGroup(gid) {
    return currentChat?.type === 'group' && currentChat?.id === gid ? 'active' : '';
}
function getUsername(uid) {
    return contacts.find((c) => c.contact_user_id === uid)?.username || `#${uid}`;
}
function initials(name) {
    return name ? name[0].toUpperCase() : '?';
}
function esc(s) {
    return String(s || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}
function normalizeDate(iso) {
    if (!iso) return iso;
    return iso.endsWith('Z') || /[+-]\d{2}:\d{2}$/.test(iso) ? iso : iso + 'Z';
}
function fmtTime(iso) {
    return new Date(normalizeDate(iso)).toLocaleTimeString('ru', {
        hour: '2-digit',
        minute: '2-digit',
    });
}
function fmtDay(iso) {
    const d = new Date(normalizeDate(iso)),
        now = new Date();
    if (d.toDateString() === now.toDateString()) return 'Сегодня';
    const y = new Date(now);
    y.setDate(y.getDate() - 1);
    if (d.toDateString() === y.toDateString()) return 'Вчера';
    return d.toLocaleDateString('ru', { day: 'numeric', month: 'long' });
}
function timeAgo(iso) {
    const sec = Math.floor((Date.now() - new Date(normalizeDate(iso))) / 1000);
    if (sec < 60) return 'только что';
    if (sec < 3600) return `${Math.floor(sec / 60)}м назад`;
    if (sec < 86400) return `${Math.floor(sec / 3600)}ч назад`;
    return new Date(normalizeDate(iso)).toLocaleDateString('ru', {
        day: 'numeric',
        month: 'short',
    });
}

let toastTimer;
function toast(msg, type = '') {
    const t = el('toast');
    t.textContent = msg;
    t.className = 'show ' + type;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => (t.className = ''), 3200);
}

// Lightbox
function openLightbox(url) {
    el('lightbox-img').src = url;
    el('lightbox').classList.add('open');
    document.removeEventListener('keydown', onLightboxKey);
    document.addEventListener('keydown', onLightboxKey);
}
function closeLightbox(e) {
    if (e && e.target === el('lightbox-img')) return;
    el('lightbox').classList.remove('open');
    el('lightbox-img').src = '';
    document.removeEventListener('keydown', onLightboxKey);
}
function onLightboxKey(e) {
    if (e.key === 'Escape') closeLightbox();
}

// Admin media settings
async function loadAdminSettings() {
    if (!isAdmin) return;
    try {
        const s = await api('/admin/media-settings');
        if (el('s-quality')) el('s-quality').value = s.quality;
        if (el('s-maxsize')) el('s-maxsize').value = s.max_size;
        if (el('s-colors')) el('s-colors').value = s.colors;
    } catch (e) {}
}
async function saveMediaSettings() {
    const quality = parseInt(el('s-quality').value) || null;
    const max_size = parseInt(el('s-maxsize').value) || null;
    const colors = parseInt(el('s-colors').value) || null;
    try {
        await api('/admin/media-settings', 'PATCH', {
            quality,
            max_size,
            colors,
        });
        toast('Настройки сохранены', 'ok');
    } catch (e) {
        toast(e.message, 'err');
    }
}

function setVh() {
    document.documentElement.style.setProperty('--vh', window.innerHeight * 0.01 + 'px');
}
setVh();
window.addEventListener('resize', setVh);

// Auto-login
(async () => {
    const saved = localStorage.getItem('msng_token');
    if (!saved) return;
    token = saved;
    try {
        const profile = await api('/users/me');
        me = { id: profile.id, username: profile.username };
        isAdmin = await checkAdmin();
        el('me-username').textContent = me.username;
        el('admin-badge').style.display = isAdmin ? 'inline' : 'none';
        el('admin-panel').style.display = isAdmin ? 'block' : 'none';
        el('api-host-label').textContent = new URL(API_BASE()).host;
        await loadContacts();
        await loadGroups();
        el('auth-screen').style.display = 'none';
        el('app').style.display = 'flex';
        connectWS();
        loadAdminSettings();
        requestNotifPermission();
    } catch (e) {
        token = null;
        localStorage.removeItem('msng_token');
    }
})();
document.addEventListener('contextmenu', function (e) {
    const row = e.target.closest('.msg-row');
    if (!row) return;

    e.preventDefault();

    // скрываем все
    document.querySelectorAll('.msg-actions').forEach((a) => {
        a.style.opacity = 0;
        a.style.visibility = 'hidden';
        a.style.pointerEvents = 'none';
    });

    const actions = row.querySelector('.msg-actions');
    if (!actions) return;

    actions.style.opacity = 1;
    actions.style.visibility = 'visible';
    actions.style.pointerEvents = 'auto';
});
document.addEventListener('click', (e) => {
    if (e.target.closest('.msg-actions')) return;

    document.querySelectorAll('.msg-actions').forEach((a) => {
        a.style.opacity = 0;
        a.style.visibility = 'hidden';
        a.style.pointerEvents = 'none';
    });
});
