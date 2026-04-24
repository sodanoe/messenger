import { useState } from 'react';
import { login, register, fetchMe, checkAdmin } from '../../services/auth';
import { getContacts } from '../../services/contacts';
import { getGroups } from '../../services/groups';
import useAppStore from '../../store/useAppStore';
import { useNotifications } from '../../hooks/useNotifications';
import styles from './LoginPage.module.css';

export default function LoginPage() {
  const [tab, setTab] = useState('login');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [lUser, setLUser] = useState('');
  const [lPass, setLPass] = useState('');

  const [rUser, setRUser] = useState('');
  const [rPass, setRPass] = useState('');
  const [rInvite, setRInvite] = useState('');

  const { setToken, setMe, setIsAdmin, setContacts, setGroups } = useAppStore();
  const { requestPermission } = useNotifications();

  async function onAuthSuccess(accessToken) {
    setToken(accessToken);
    const profile = await fetchMe();
    setMe({ id: profile.id, username: profile.username });
    const admin = await checkAdmin();
    setIsAdmin(admin);
    const [contacts, groups] = await Promise.all([getContacts(), getGroups()]);
    setContacts(contacts);
    setGroups(groups);
    requestPermission();
    // navigate не нужен — App сам покажет ChatPage когда token установлен
  }

  async function doLogin() {
    if (!lUser || !lPass) return setError('Заполни все поля');
    setError('');
    setLoading(true);
    try {
      const r = await login(lUser, lPass);
      await onAuthSuccess(r.access_token);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function doRegister() {
    if (!rUser || !rPass || !rInvite) return setError('Заполни все поля');
    setError('');
    setLoading(true);
    try {
      const r = await register(rUser, rPass, rInvite);
      await onAuthSuccess(r.access_token);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={styles.screen}>
      <div className={styles.logo}>// messenger</div>

      <div className={styles.tabs}>
        <button
          className={`${styles.tab} ${tab === 'login' ? styles.active : ''}`}
          onClick={() => {
            setTab('login');
            setError('');
          }}
        >
          Вход
        </button>
        <button
          className={`${styles.tab} ${tab === 'register' ? styles.active : ''}`}
          onClick={() => {
            setTab('register');
            setError('');
          }}
        >
          Регистрация
        </button>
      </div>

      {tab === 'login' && (
        <div className={styles.form}>
          <div className={styles.field}>
            <label>Username</label>
            <input
              value={lUser}
              onChange={(e) => setLUser(e.target.value)}
              placeholder="admin"
              autoComplete="username"
            />
          </div>
          <div className={styles.field}>
            <label>Password</label>
            <input
              type="password"
              value={lPass}
              onChange={(e) => setLPass(e.target.value)}
              placeholder="••••••••"
              autoComplete="current-password"
              onKeyDown={(e) => e.key === 'Enter' && doLogin()}
            />
          </div>
          <button className={styles.btn} onClick={doLogin} disabled={loading}>
            {loading ? '…' : 'Войти'}
          </button>
        </div>
      )}

      {tab === 'register' && (
        <div className={styles.form}>
          <div className={styles.field}>
            <label>Username</label>
            <input
              value={rUser}
              onChange={(e) => setRUser(e.target.value)}
              placeholder="username"
              autoComplete="username"
            />
          </div>
          <div className={styles.field}>
            <label>Password</label>
            <input
              type="password"
              value={rPass}
              onChange={(e) => setRPass(e.target.value)}
              placeholder="••••••••"
              autoComplete="new-password"
            />
          </div>
          <div className={styles.field}>
            <label>Invite code</label>
            <input
              value={rInvite}
              onChange={(e) => setRInvite(e.target.value)}
              placeholder="Код от администратора"
              autoComplete="off"
              onKeyDown={(e) => e.key === 'Enter' && doRegister()}
            />
          </div>
          <button
            className={styles.btn}
            onClick={doRegister}
            disabled={loading}
          >
            {loading ? '…' : 'Зарегистрироваться'}
          </button>
        </div>
      )}

      {error && <div className={styles.error}>{error}</div>}
    </div>
  );
}
