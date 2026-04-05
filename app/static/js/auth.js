// ─────────────────────────────────────────────────────────
//  Auth
// ─────────────────────────────────────────────────────────

function switchAuthTab(tab) {
    el('form-login').style.display = tab === 'login' ? 'block' : 'none';
    el('form-register').style.display = tab === 'register' ? 'block' : 'none';
    document
        .querySelectorAll('.auth-tab')
        .forEach((b, i) =>
            b.classList.toggle('active', (i === 0) === (tab === 'login')),
        );
    el('login-err').style.display = el('reg-err').style.display = 'none';
}

async function doLogin() {
    const username = v('l-user'),
        password = v('l-pass');
    const btn = el('login-btn'),
        err = el('login-err');
    err.style.display = 'none';
    btn.disabled = true;
    btn.textContent = '…';
    try {
        const r = await api('/auth/login', 'POST', { username, password });
        await onAuthSuccess(r.access_token);
    } catch (e) {
        showErr(err, e.message);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Войти';
    }
}

async function doRegister() {
    const username = v('r-user'),
        password = v('r-pass'),
        invite_code = v('r-invite');
    if (!username || !password || !invite_code)
        return showErr(el('reg-err'), 'Заполни все поля');
    const btn = el('reg-btn'),
        err = el('reg-err');
    err.style.display = 'none';
    btn.disabled = true;
    btn.textContent = '…';
    try {
        const r = await api('/auth/register', 'POST', {
            username,
            password,
            invite_code,
        });
        await onAuthSuccess(r.access_token);
    } catch (e) {
        showErr(err, e.message);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Зарегистрироваться';
    }
}

el('l-pass').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') doLogin();
});
el('r-invite').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') doRegister();
});

async function onAuthSuccess(accessToken) {
    token = accessToken;
    localStorage.setItem('msng_token', token);
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
}

async function checkAdmin() {
    try {
        await api('/admin/media-settings');
        return true;
    } catch {
        return false;
    }
}

function doLogout() {
    token = null;
    me = null;
    isAdmin = false;
    currentChat = null;
    lastInvite = null;
    pendingMediaId = null;
    replyTo = null;
    localStorage.removeItem('msng_token');
    wsClose();
    clearSearch();
    hideReactionPicker();
    el('app').style.display = 'none';
    el('auth-screen').style.display = 'block';
    el('l-pass').value = '';
    el('contact-list').innerHTML = '';
    el('messages').innerHTML = '';
    el('invite-code-box').textContent = 'нет кода';
    el('invite-code-box').className = 'invite-code-box empty';
    el('invite-hint').textContent = 'Создай код и отправь новому пользователю';
    showChat(false);
    switchAuthTab('login');
    stopTitleBlink();
}
