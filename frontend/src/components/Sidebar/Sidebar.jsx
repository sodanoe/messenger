import { useEffect, useState } from 'react';
import useAppStore from '../../store/useAppStore';
import { api } from '../../services/api';
import ChatList from './ChatList/ChatList';
import { initials } from '../../utils/format';
import { getAvatarColor } from '../../utils/avatarColor';
import { createGroup } from '../../services/groups';
import toast from 'react-hot-toast';
import styles from './Sidebar.module.css';

function ChevronRight() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <polyline points="9 18 15 12 9 6" />
    </svg>
  );
}

function ChevronLeft() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <polyline points="15 18 9 12 15 6" />
    </svg>
  );
}

function SearchIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  );
}

export default function Sidebar() {
  const { me, isAdmin, chats, setChats, logout, lastInvite, setLastInvite } =
    useAppStore();

  const [screen, setScreen] = useState('chats');
  const [searchQuery, setSearchQuery] = useState('');
  const [notifications, setNotifications] = useState(true);
  const [theme, setTheme] = useState(
    () => localStorage.getItem('theme') || 'system',
  );

  const [editName, setEditName] = useState('');
  const [editStatus, setEditStatus] = useState('');
  const [oldPass, setOldPass] = useState('');
  const [newPass, setNewPass] = useState('');
  const [confirmPass, setConfirmPass] = useState('');
  const [showOld, setShowOld] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  // ─── Контакты из chats стора (актуальный онлайн-статус) ──
  const directContacts = (chats || [])
    .filter((c) => c.type === 'direct')
    .map((c) => ({
      id: c.other_user_id,
      username: c.name || c.other_username || '?',
      is_online: c.is_online ?? false,
    }));

  const filteredContacts = directContacts.filter(
    (c) =>
      !searchQuery ||
      c.username.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  useEffect(() => {
    api('/chats/', 'GET')
      .then((data) => setChats(data?.chats || []))
      .catch(() => setChats([]));
  }, [setChats]);

  useEffect(() => {
    function onKey(e) {
      if (e.key === 'Escape') {
        if (screen === 'search') {
          setScreen('chats');
          setSearchQuery('');
        } else if (screen !== 'chats') setScreen('chats');
      }
    }
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [screen]);

  useEffect(() => {
    if (theme === 'system') {
      document.documentElement.removeAttribute('data-theme');
      localStorage.removeItem('theme');
    } else {
      document.documentElement.setAttribute('data-theme', theme);
      localStorage.setItem('theme', theme);
    }
  }, [theme]);

  function openEditProfile() {
    setEditName(me?.username || '');
    setEditStatus(me?.status || '');
    setScreen('editProfile');
  }

  async function saveProfile() {
    try {
      await api('/profile', 'PATCH', {
        username: editName,
        status: editStatus,
      });
      toast.success('Сохранено');
      setScreen('profile');
    } catch (e) {
      toast.error(e.message);
    }
  }

  async function savePassword() {
    if (newPass !== confirmPass) {
      toast.error('Пароли не совпадают');
      return;
    }
    try {
      await api('/auth/change-password', 'POST', {
        old_password: oldPass,
        new_password: newPass,
      });
      toast.success('Пароль изменён');
      setOldPass('');
      setNewPass('');
      setConfirmPass('');
      setScreen('profile');
    } catch (e) {
      toast.error(e.message);
    }
  }

  async function handleCreateGroup() {
    const name = prompt('Название группы:');
    if (!name?.trim()) return;
    try {
      await createGroup(name.trim());
      const data = await api('/chats/', 'GET');
      if (data?.chats) setChats(data.chats);
      toast.success('Группа создана');
    } catch (e) {
      toast.error(e.message);
    }
  }

  async function genInvite() {
    try {
      const r = await api('/auth/invite', 'POST');
      setLastInvite(r.code);
      toast.success('Инвайт создан');
    } catch {}
  }

  function copyInvite() {
    if (!lastInvite) return;
    navigator.clipboard
      .writeText(lastInvite)
      .catch(() => prompt('Скопируй код:', lastInvite));
    toast.success('Скопировано');
  }

  // ─── Хедер ───────────────────────────────────────────────
  function renderHeader() {
    // При поиске — заменяем заголовок на инпут + крестик
    if (screen === 'search') {
      return (
        <div className={styles.header}>
          <input
            className={styles.searchHeaderInput}
            placeholder="Поиск..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            autoFocus
          />
          <button
            className={styles.searchBtn}
            onClick={() => {
              setScreen('chats');
              setSearchQuery('');
            }}
            title="Закрыть"
          >
            ✕
          </button>
        </div>
      );
    }

    return (
      <div className={styles.header}>
        <span className={styles.title}>Чаты</span>
        <button
          className={`${styles.searchBtn} ${screen === 'search' ? styles.active : ''}`}
          onClick={() => setScreen('search')}
          title="Поиск контактов"
        >
          <SearchIcon />
        </button>
        <button
          className={`${styles.myAvatarBtn} ${['profile', 'editProfile', 'settings', 'privacy', 'favorites'].includes(screen) ? styles.active : ''}`}
          onClick={() =>
            setScreen(
              ['chats', 'search'].includes(screen) ? 'profile' : 'chats',
            )
          }
          title="Профиль"
        >
          <div
            className={styles.myAvatar}
            style={{ background: getAvatarColor(me?.username) }}
          >
            {initials(me?.username || '?')}
          </div>
        </button>
      </div>
    );
  }

  // ─── Экраны ──────────────────────────────────────────────
  if (screen === 'chats') {
    return (
      <aside className={`${styles.sidebar} sidebar`}>
        {renderHeader()}
        <div className={styles.chatListContainer}>
          <ChatList chats={chats || []} />
        </div>
      </aside>
    );
  }

  if (screen === 'search') {
    return (
      <aside className={`${styles.sidebar} sidebar`}>
        {renderHeader()}
        <div className={styles.searchPanel}>
          <div className={styles.createGroupRow} onClick={handleCreateGroup}>
            <span className={styles.createGroupIcon}>
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                <circle cx="9" cy="7" r="4" />
                <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                <path d="M16 3.13a4 4 0 0 1 0 7.75" />
              </svg>
            </span>
            <span className={styles.createGroupLabel}>Создать группу</span>
            <span className={styles.createGroupChevron}>
              <ChevronRight />
            </span>
          </div>
          <div className={styles.sectionLabel}>Контакты</div>
          <div className={styles.contactsList}>
            {filteredContacts.length === 0 && (
              <div
                style={{
                  padding: '20px 16px',
                  color: 'var(--text2)',
                  fontSize: 13,
                  textAlign: 'center',
                }}
              >
                Контакты не найдены
              </div>
            )}
            {filteredContacts.map((c) => (
              <div key={c.id} className={styles.contactRow}>
                <div
                  className={styles.contactAvatar}
                  style={{ background: getAvatarColor(c.username) }}
                >
                  {initials(c.username)}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className={styles.contactName}>{c.username}</div>
                  <div className={styles.contactUsername}>@{c.username}</div>
                </div>
                <span
                  className={
                    c.is_online
                      ? styles.contactStatusOn
                      : styles.contactStatusOff
                  }
                >
                  {c.is_online ? 'в сети' : 'не в сети'}
                </span>
              </div>
            ))}
          </div>
        </div>
      </aside>
    );
  }

  if (screen === 'profile') {
    return (
      <aside className={`${styles.sidebar} sidebar`}>
        {renderHeader()}
        <div className={styles.panel}>
          <div className={styles.profileCard}>
            <div
              className={styles.profileAvatar}
              style={{ background: getAvatarColor(me?.username) }}
              onClick={openEditProfile}
            >
              {initials(me?.username || '?')}
              <div className={styles.profileEditBadge}>✎</div>
            </div>
            <div className={styles.profileName}>{me?.username}</div>
            <div className={styles.profileUsername}>@{me?.username}</div>
            <div className={styles.profileOnlineBadge}>В сети</div>
          </div>
          <div className={styles.profileMenu}>
            <div className={styles.profileSection}>
              <div className={styles.menuRow} onClick={openEditProfile}>
                <span className={styles.menuRowIcon}>
                  <svg
                    width="18"
                    height="18"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                    <circle cx="12" cy="7" r="4" />
                  </svg>
                </span>
                <div className={styles.menuRowBody}>
                  <div className={styles.menuRowLabel}>
                    Редактировать профиль
                  </div>
                  <div className={styles.menuRowSub}>Имя, статус</div>
                </div>
                <span className={styles.menuRowChevron}>
                  <ChevronRight />
                </span>
              </div>
              <div
                className={styles.menuRow}
                onClick={() => setScreen('settings')}
              >
                <span className={styles.menuRowIcon}>
                  <svg
                    width="18"
                    height="18"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <circle cx="12" cy="12" r="3" />
                    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
                  </svg>
                </span>
                <div className={styles.menuRowBody}>
                  <div className={styles.menuRowLabel}>Настройки</div>
                  <div className={styles.menuRowSub}>
                    Тема, уведомления, язык
                  </div>
                </div>
                <span className={styles.menuRowChevron}>
                  <ChevronRight />
                </span>
              </div>
              <div
                className={styles.menuRow}
                onClick={() => setScreen('favorites')}
              >
                <span className={styles.menuRowIcon}>
                  <svg
                    width="18"
                    height="18"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
                  </svg>
                </span>
                <div className={styles.menuRowBody}>
                  <div className={styles.menuRowLabel}>Избранное</div>
                  <div className={styles.menuRowSub}>Сохранённые сообщения</div>
                </div>
                <span className={styles.menuRowChevron}>
                  <ChevronRight />
                </span>
              </div>
              <div
                className={styles.menuRow}
                onClick={() => setScreen('privacy')}
              >
                <span className={styles.menuRowIcon}>
                  <svg
                    width="18"
                    height="18"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                  </svg>
                </span>
                <div className={styles.menuRowBody}>
                  <div className={styles.menuRowLabel}>Конфиденциальность</div>
                  <div className={styles.menuRowSub}>Сменить пароль</div>
                </div>
                <span className={styles.menuRowChevron}>
                  <ChevronRight />
                </span>
              </div>
            </div>
            {isAdmin && (
              <div className={styles.profileSection}>
                <div className={styles.menuRow}>
                  <span
                    className={styles.menuRowIcon}
                    style={{ color: '#F2D900' }}
                  >
                    <svg
                      width="18"
                      height="18"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M2 4l3 12h14l3-12-6 5-4-7-4 7-6-5zm3 16h14" />
                    </svg>
                  </span>
                  <div className={styles.menuRowBody}>
                    <div className={styles.menuRowLabel}>Админ-панель</div>
                    <div className={styles.menuRowSub}>
                      Управление пользователями
                    </div>
                  </div>
                  <span className={styles.menuRowChevron}>
                    <ChevronRight />
                  </span>
                </div>
                <div className={styles.menuRow} onClick={genInvite}>
                  <span className={styles.menuRowIcon}>🔗</span>
                  <div className={styles.menuRowBody}>
                    <div className={styles.menuRowLabel}>Создать инвайт</div>
                  </div>
                </div>
                {lastInvite && (
                  <div className={styles.menuRow} onClick={copyInvite}>
                    <span className={styles.menuRowIcon}>📋</span>
                    <div className={styles.menuRowBody}>
                      <div className={styles.menuRowLabel}>
                        Скопировать: {lastInvite}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
            <div className={styles.profileSection}>
              <div
                className={`${styles.menuRow} ${styles.menuRowDanger}`}
                onClick={() => {
                  logout();
                  setScreen('chats');
                }}
              >
                <span className={styles.menuRowIcon}>
                  <svg
                    width="18"
                    height="18"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                    <polyline points="16 17 21 12 16 7" />
                    <line x1="21" y1="12" x2="9" y2="12" />
                  </svg>
                </span>
                <div className={styles.menuRowBody}>
                  <div className={styles.menuRowLabel}>Выйти из аккаунта</div>
                </div>
                <span className={styles.menuRowChevron}>
                  <ChevronRight />
                </span>
              </div>
            </div>
          </div>
        </div>
      </aside>
    );
  }

  if (screen === 'editProfile') {
    return (
      <aside className={`${styles.sidebar} sidebar`}>
        {renderHeader()}
        <div className={styles.panel}>
          <div className={styles.profileCard}>
            <div
              className={styles.profileAvatar}
              style={{ background: getAvatarColor(me?.username) }}
            >
              {initials(me?.username || '?')}
              <div className={styles.profileEditBadge}>✎</div>
            </div>
            <div className={styles.profileName}>{me?.username}</div>
            <div className={styles.profileUsername}>@{me?.username}</div>
            <div className={styles.profileOnlineBadge}>В сети</div>
          </div>
          <div className={styles.subScreen}>
            <div
              className={styles.subHeader}
              onClick={() => setScreen('profile')}
            >
              <span className={styles.subHeaderBack}>
                <ChevronLeft />
              </span>
              <span className={styles.subHeaderTitle}>
                Редактировать профиль
              </span>
            </div>
            <div className={styles.subContent}>
              <div className={styles.fieldGroup}>
                <label className={styles.fieldLabel}>Имя</label>
                <input
                  className={styles.fieldInput}
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  placeholder="Введи имя"
                />
                <span className={styles.fieldHint}>
                  Видно всем пользователям
                </span>
              </div>
              <div className={styles.fieldGroup}>
                <label className={styles.fieldLabel}>Статус</label>
                <input
                  className={styles.fieldInput}
                  value={editStatus}
                  onChange={(e) => setEditStatus(e.target.value)}
                  placeholder="Что делаешь?"
                />
                <span className={styles.fieldHint}>
                  Видно всем пользователям
                </span>
              </div>
              <button className={styles.saveBtn} onClick={saveProfile}>
                Сохранить
              </button>
            </div>
          </div>
        </div>
      </aside>
    );
  }

  if (screen === 'settings') {
    const themes = [
      { id: 'system', label: 'Системная', color: '#888' },
      { id: 'dark', label: 'Тёмная', color: '#111' },
      { id: 'light', label: 'Светлая', color: '#fff' },
      { id: 'purple', label: 'Пурпурная', color: '#826FBB' },
    ];
    return (
      <aside className={`${styles.sidebar} sidebar`}>
        {renderHeader()}
        <div className={styles.panel}>
          <div className={styles.profileCard}>
            <div
              className={styles.profileAvatar}
              style={{ background: getAvatarColor(me?.username) }}
            >
              {initials(me?.username || '?')}
            </div>
            <div className={styles.profileName}>{me?.username}</div>
            <div className={styles.profileUsername}>@{me?.username}</div>
            <div className={styles.profileOnlineBadge}>В сети</div>
          </div>
          <div className={styles.subScreen}>
            <div
              className={styles.subHeader}
              onClick={() => setScreen('profile')}
            >
              <span className={styles.subHeaderBack}>
                <ChevronLeft />
              </span>
              <span className={styles.subHeaderTitle}>Настройки</span>
            </div>
            <div className={styles.subContent}>
              <div className={styles.fieldGroup}>
                <div className={styles.fieldLabel}>Тема</div>
                <div className={styles.themeRow}>
                  {themes.map((t) => (
                    <div
                      key={t.id}
                      className={styles.themeOption}
                      onClick={() => setTheme(t.id)}
                    >
                      <div
                        className={`${styles.themeCircle} ${theme === t.id ? styles.selected : ''}`}
                        style={{
                          background: t.color,
                          border:
                            t.id === 'light' ? '1px solid #D1DCE8' : undefined,
                        }}
                      >
                        {theme === t.id && (
                          <div className={styles.themeCheck}>✓</div>
                        )}
                      </div>
                      <span
                        className={`${styles.themeLabel} ${theme === t.id ? styles.selected : ''}`}
                      >
                        {t.label}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
              <div className={styles.fieldGroup}>
                <div className={styles.fieldLabel}>Уведомления</div>
                <div className={styles.settingRow}>
                  <span className={styles.settingIcon}>
                    <svg
                      width="18"
                      height="18"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
                      <path d="M13.73 21a2 2 0 0 1-3.46 0" />
                    </svg>
                  </span>
                  <span className={styles.settingLabel}>Уведомления</span>
                  <button
                    className={`${styles.toggle} ${notifications ? styles.on : styles.off}`}
                    onClick={() => setNotifications((v) => !v)}
                  >
                    <div className={styles.toggleKnob} />
                  </button>
                </div>
              </div>
              <div className={styles.fieldGroup}>
                <div className={styles.fieldLabel}>Язык</div>
                <div
                  className={styles.menuRow}
                  style={{ padding: '8px 0', borderRadius: 8 }}
                >
                  <span className={styles.settingIcon}>
                    <svg
                      width="18"
                      height="18"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <circle cx="12" cy="12" r="10" />
                      <line x1="2" y1="12" x2="22" y2="12" />
                      <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
                    </svg>
                  </span>
                  <span className={styles.settingLabel}>Русский</span>
                  <span className={styles.menuRowChevron}>
                    <ChevronRight />
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </aside>
    );
  }

  if (screen === 'privacy') {
    return (
      <aside className={`${styles.sidebar} sidebar`}>
        {renderHeader()}
        <div className={styles.panel}>
          <div className={styles.profileCard}>
            <div
              className={styles.profileAvatar}
              style={{ background: getAvatarColor(me?.username) }}
            >
              {initials(me?.username || '?')}
            </div>
            <div className={styles.profileName}>{me?.username}</div>
            <div className={styles.profileUsername}>@{me?.username}</div>
            <div className={styles.profileOnlineBadge}>В сети</div>
          </div>
          <div className={styles.subScreen}>
            <div
              className={styles.subHeader}
              onClick={() => setScreen('profile')}
            >
              <span className={styles.subHeaderBack}>
                <ChevronLeft />
              </span>
              <span className={styles.subHeaderTitle}>Конфиденциальность</span>
            </div>
            <div className={styles.subContent}>
              <div className={styles.fieldGroup}>
                <label className={styles.fieldLabel}>
                  Введите старый пароль
                </label>
                <div className={styles.passwordWrap}>
                  <input
                    className={styles.fieldInput}
                    type={showOld ? 'text' : 'password'}
                    value={oldPass}
                    onChange={(e) => setOldPass(e.target.value)}
                    placeholder="••••••"
                  />
                  <button
                    className={styles.eyeBtn}
                    onClick={() => setShowOld((v) => !v)}
                  >
                    {showOld ? '🙈' : '👁'}
                  </button>
                </div>
              </div>
              <div className={styles.fieldGroup}>
                <label className={styles.fieldLabel}>
                  Введите новый пароль
                </label>
                <div className={styles.passwordWrap}>
                  <input
                    className={styles.fieldInput}
                    type={showNew ? 'text' : 'password'}
                    value={newPass}
                    onChange={(e) => setNewPass(e.target.value)}
                    placeholder="••••••"
                  />
                  <button
                    className={styles.eyeBtn}
                    onClick={() => setShowNew((v) => !v)}
                  >
                    {showNew ? '🙈' : '👁'}
                  </button>
                </div>
              </div>
              <div className={styles.fieldGroup}>
                <label className={styles.fieldLabel}>
                  Повторите новый пароль
                </label>
                <div className={styles.passwordWrap}>
                  <input
                    className={styles.fieldInput}
                    type={showConfirm ? 'text' : 'password'}
                    value={confirmPass}
                    onChange={(e) => setConfirmPass(e.target.value)}
                    placeholder="••••••"
                  />
                  <button
                    className={styles.eyeBtn}
                    onClick={() => setShowConfirm((v) => !v)}
                  >
                    {showConfirm ? '🙈' : '👁'}
                  </button>
                </div>
              </div>
              <button className={styles.saveBtn} onClick={savePassword}>
                Сохранить
              </button>
            </div>
          </div>
        </div>
      </aside>
    );
  }

  if (screen === 'favorites') {
    return (
      <aside className={`${styles.sidebar} sidebar`}>
        {renderHeader()}
        <div className={styles.panel}>
          <div className={styles.profileCard}>
            <div
              className={styles.profileAvatar}
              style={{ background: getAvatarColor(me?.username) }}
            >
              {initials(me?.username || '?')}
            </div>
            <div className={styles.profileName}>{me?.username}</div>
            <div className={styles.profileUsername}>@{me?.username}</div>
            <div className={styles.profileOnlineBadge}>В сети</div>
          </div>
          <div className={styles.subScreen}>
            <div
              className={styles.subHeader}
              onClick={() => setScreen('profile')}
            >
              <span className={styles.subHeaderBack}>
                <ChevronLeft />
              </span>
              <span className={styles.subHeaderTitle}>Избранное</span>
            </div>
            <div className={styles.mediaGrid}>
              <div
                style={{
                  padding: '20px 16px',
                  color: 'var(--text2)',
                  fontSize: 13,
                }}
              >
                Нет сохранённых сообщений
              </div>
            </div>
          </div>
        </div>
      </aside>
    );
  }

  return null;
}
