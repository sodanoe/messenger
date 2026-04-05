// ─────────────────────────────────────────────────────────
//  API helper  —  авто-рефреш access токена при 401
// ─────────────────────────────────────────────────────────

let _refreshing = null; // промис текущего рефреша, чтобы не дублировать запросы

async function _doRefresh() {
    const r = await fetch(API_BASE() + '/auth/refresh', {
        method: 'POST',
        credentials: 'include', // cookie летит автоматически
    });
    if (!r.ok) {
        // refresh токен протух или отозван — разлогиниваем
        token = null;
        localStorage.removeItem('msng_token');
        window.location.reload();
        throw new Error('Session expired');
    }
    const data = await r.json();
    token = data.access_token;
    localStorage.setItem('token', token);
    return token;
}

async function _refreshOnce() {
    // Несколько параллельных запросов получат один и тот же промис
    if (!_refreshing) {
        _refreshing = _doRefresh().finally(() => {
            _refreshing = null;
        });
    }
    return _refreshing;
}

async function api(path, method = 'GET', body = null, _retry = true) {
    const opts = {
        method,
        credentials: 'include',
        headers: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
    };
    if (body) opts.body = JSON.stringify(body);

    const r = await fetch(API_BASE() + path, opts);

    // Access токен протух — пробуем рефрешнуть и повторить запрос
    if (r.status === 401 && _retry && path !== '/auth/refresh') {
        await _refreshOnce();
        return api(path, method, body, false); // _retry=false — не зациклиться
    }

    if (!r.ok) {
        let msg = `HTTP ${r.status}`;
        try {
            const j = await r.json();
            msg = j.detail || msg;
        } catch {}
        throw new Error(msg);
    }
    if (r.status === 204) return null;
    return r.json();
}
