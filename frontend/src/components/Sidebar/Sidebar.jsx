import { useEffect, useState, useRef } from 'react';
import useAppStore from '../../store/useAppStore';
import { api } from '../../services/api';
import SearchBar from './SearchBar/SearchBar';
import ChatList from './ChatList/ChatList';
import styles from './Sidebar.module.css';

function getInitials(username) {
  if (!username) return '?';
  return username.slice(0, 2).toUpperCase();
}

function Logo() {
  return (
    <svg width="28" height="28" viewBox="0 0 35 35" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <clipPath id="logo_clip">
          <rect width="35" height="35" rx="10" fill="white"/>
        </clipPath>
        <linearGradient id="logo_stroke" x1="0" y1="0" x2="35" y2="35" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="white" stopOpacity="0.4"/>
          <stop offset="100%" stopColor="white" stopOpacity="0.05"/>
        </linearGradient>
        <linearGradient id="logo_shine" x1="0" y1="0" x2="0" y2="14" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="white" stopOpacity="0.18"/>
          <stop offset="100%" stopColor="white" stopOpacity="0"/>
        </linearGradient>
      </defs>
      <g clipPath="url(#logo_clip)">
        <path d="M28.4375 0H6.5625C2.93813 0 0 2.93813 0 6.5625V28.4375C0 32.0619 2.93813 35 6.5625 35H28.4375C32.0619 35 35 32.0619 35 28.4375V6.5625C35 2.93813 32.0619 0 28.4375 0Z" fill="#081826"/>
        <path d="M0 16.4062C8.20312 13.6719 16.4062 19.1406 35 15.0391V35H0V16.4062Z" fill="#0E2F4A"/>
        <path d="M0 20.5078C10.9375 17.7734 21.875 23.2422 35 19.1406V35H0V20.5078Z" fill="#123A5A"/>
        <path d="M0 24.6094C13.6719 21.875 27.3438 27.3438 35 23.2422V35H0V24.6094Z" fill="#1B4F72"/>
        <rect width="35" height="14" fill="url(#logo_shine)"/>
      </g>
      <rect x="0.5" y="0.5" width="34" height="34" rx="9.5" stroke="url(#logo_stroke)" strokeWidth="1"/>
    </svg>
  );
}

export default function Sidebar() {
  const { me, isAdmin, chats, setChats, logout, lastInvite, setLastInvite } = useAppStore();

  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);

  useEffect(() => {
    const fetchChats = async () => {
      try {
        const data = await api('/chats/', 'GET');
        setChats(data?.chats || []);
      } catch {
        setChats([]);
      }
    };
    fetchChats();
  }, [setChats]);

  useEffect(() => {
    function handleClickOutside(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setMenuOpen(false);
      }
    }
    if (menuOpen) document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [menuOpen]);

  async function genInvite() {
    try {
      const r = await api('/auth/invite', 'POST');
      setLastInvite(r.code);
    } catch {}
  }

  function copyInvite() {
    if (!lastInvite) return;
    navigator.clipboard.writeText(lastInvite).catch(() => {
      prompt('Скопируй код:', lastInvite);
    });
  }

  return (
    <aside className={`${styles.sidebar} sidebar`}>
      <div className={styles.header}>
        <div className={styles.logo}>
          <Logo />
        </div>

        <div className={styles.headerRight} ref={menuRef}>
          <button
            className={`${styles.menuBtn} ${menuOpen ? styles.active : ''}`}
            onClick={() => setMenuOpen((v) => !v)}
          >
            <span />
            <span />
            <span />
          </button>

          {menuOpen && (
            <div className={styles.menu}>
              <div className={styles.menuProfile}>
                <div className={styles.menuAvatar}>
                  {getInitials(me?.username)}
                </div>
                <div className={styles.menuUserInfo}>
                  <div className={styles.menuUsername}>{me?.username}</div>
                  {isAdmin && <div className={styles.menuAdmin}>ADMIN</div>}
                </div>
              </div>

              {isAdmin && (
                <div className={styles.menuSection}>
                  <div className={styles.menuItem} onClick={genInvite}>
                    Создать инвайт
                  </div>
                  {lastInvite && (
                    <div className={styles.menuItem} onClick={copyInvite}>
                      {lastInvite}
                    </div>
                  )}
                </div>
              )}

              <div className={styles.menuSection}>
                <div
                  className={`${styles.menuItem} ${styles.danger}`}
                  onClick={() => { setMenuOpen(false); logout(); }}
                >
                  Выйти
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className={styles.searchWrapper}>
        <SearchBar />
      </div>

      <div className={styles.chatListContainer}>
        <ChatList chats={chats || []} />
      </div>
    </aside>
  );
}