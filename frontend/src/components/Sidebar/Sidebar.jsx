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

export default function Sidebar() {
  const { me, isAdmin, chats, logout, lastInvite, setLastInvite } =
    useAppStore();

  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);

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
    <aside className={styles.sidebar}>
      {/* HEADER */}
      <div className={styles.header}>
        <div className={styles.logo}>// msg</div>

        <div className={styles.headerRight} ref={menuRef}>
          <button
            className={`${styles.menuBtn} ${
              menuOpen ? styles.active : ''
            }`}
            onClick={() => setMenuOpen((v) => !v)}
          >
            <span />
            <span />
            <span />
          </button>

          {menuOpen && (
            <div className={styles.menu}>
              {/* PROFILE */}
              <div className={styles.menuProfile}>
                <div className={styles.menuAvatar}>
                  {getInitials(me?.username)}
                </div>

                <div className={styles.menuUserInfo}>
                  <div className={styles.menuUsername}>
                    {me?.username}
                  </div>

                  {isAdmin && (
                    <div className={styles.menuAdmin}>ADMIN</div>
                  )}
                </div>
              </div>

              {/* ADMIN */}
              {isAdmin && (
                <div className={styles.menuSection}>
                  <div
                    className={styles.menuItem}
                    onClick={genInvite}
                  >
                    Создать инвайт
                  </div>

                  {lastInvite && (
                    <div
                      className={styles.menuItem}
                      onClick={copyInvite}
                    >
                      {lastInvite}
                    </div>
                  )}
                </div>
              )}

              {/* LOGOUT */}
              <div className={styles.menuSection}>
                <div
                  className={`${styles.menuItem} ${styles.danger}`}
                  onClick={() => {
                    setMenuOpen(false);
                    logout();
                  }}
                >
                  Выйти
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* SEARCH */}
      <div className={styles.searchWrapper}>
        <SearchBar />
      </div>

      {/* CHAT LIST */}
      <div className={styles.chatListContainer}>
        <ChatList chats={chats || []} />
      </div>
    </aside>
  );
}