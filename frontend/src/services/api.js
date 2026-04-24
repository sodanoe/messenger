import { API_BASE } from '../config';
import useAppStore from '../store/useAppStore';

let _refreshing = null;

async function _doRefresh() {
  const r = await fetch(API_BASE() + '/auth/refresh', {
    method: 'POST',
    credentials: 'include',
  });
  if (!r.ok) {
    useAppStore.getState().logout();
    throw new Error('Session expired');
  }
  const data = await r.json();
  useAppStore.getState().setToken(data.access_token);
  return data.access_token;
}

async function _refreshOnce() {
  if (!_refreshing) {
    _refreshing = _doRefresh().finally(() => {
      _refreshing = null;
    });
  }
  return _refreshing;
}

export async function api(path, method = 'GET', body = null, _retry = true) {
  const token = useAppStore.getState().token;

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

  if (r.status === 401 && _retry && path !== '/auth/refresh') {
    await _refreshOnce();
    return api(path, method, body, false);
  }

  if (!r.ok) {
    let msg = `HTTP ${r.status}`;
    try {
      const j = await r.json();
      msg = j.detail || msg;
    } catch {
      // intentional
    }
    throw new Error(msg);
  }

  if (r.status === 204) return null;
  return r.json();
}

/**
 * Загрузка медиафайла (multipart/form-data)
 * @param {File} file
 * @returns {Promise<{id: string, url: string}>}
 */
export async function uploadMedia(file) {
  const token = useAppStore.getState().token;
  const fd = new FormData();
  fd.append('file', file);
  const resp = await fetch(API_BASE() + '/media/upload', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: fd,
  });
  if (!resp.ok) {
    const err = await resp.json();
    throw new Error(err.detail || 'Upload failed');
  }
  return resp.json();
}
