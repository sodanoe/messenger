// ─────────────────────────────────────────────────────────
//  API helper
// ─────────────────────────────────────────────────────────

async function api(path, method = 'GET', body = null) {
    const opts = {
        method,
        headers: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
    };
    if (body) opts.body = JSON.stringify(body);
    const r = await fetch(API_BASE() + path, opts);
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
