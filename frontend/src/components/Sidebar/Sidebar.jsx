import { useEffect, useState, useRef, useCallback } from 'react';
import useAppStore from '../../store/useAppStore';
import { api } from '../../services/api';
import SearchBar from './SearchBar/SearchBar';
import ChatList from './ChatList/ChatList';
import { initials } from '../../utils/format';
import { getAvatarColor } from '../../utils/avatarColor';
import { createGroup } from '../../services/groups';
import toast from 'react-hot-toast';
import styles from './Sidebar.module.css';

export default function Sidebar() {
  const { me, isAdmin, chats, setChats, logout, lastInvite, setLastInvite } = useAppStore();

  const [profileOpen, setProfileOpen] = useState(false);
  const [actionsOpen, setActionsOpen] = useState(false);
  const profileRef = useRef(null);
  const actionsRef = useRef(null);

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

  // Закрытие по клику снаружи
  useEffect(() => {
    function handleClickOutside(e) {
      if (profileRef.current && !profileRef.current.contains(e.target)) {
        setProfileOpen(false);
      }
      if (actionsRef.current && !actionsRef.current.contains(e.target)) {
        setActionsOpen(false);
      }
    }
    if (profileOpen || actionsOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [profileOpen, actionsOpen]);

  // Закрытие по Esc
  useEffect(() => {
    function handleEsc(e) {
      if (e.key === 'Escape') {
        setProfileOpen(false);
        setActionsOpen(false);
      }
    }
    document.addEventListener('keydown', handleEsc);
    return () => document.removeEventListener('keydown', handleEsc);
  }, []);

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

  async function handleCreateGroup() {
    const name = prompt('Название группы:');
    if (!name?.trim()) return;
    try {
      await createGroup(name.trim());
      const data = await api('/chats/', 'GET');
      if (data?.chats) setChats(data.chats);
      toast.success('Группа создана');
      setActionsOpen(false);
    } catch (e) {
      toast.error(e.message);
    }
  }

  return (
    <aside className={`${styles.sidebar} sidebar`}>
      <div className={styles.header}>

        {/* Аватар текущего пользователя — меню профиля */}
        <div className={styles.avatarWrap} ref={profileRef}>
          <button
            className={styles.myAvatarBtn}
            onClick={() => { setProfileOpen((v) => !v); setActionsOpen(false); }}
            title="Профиль"
          >
            {profileOpen ? (
              <span className={styles.closeIcon}>✕</span>
            ) : (
              <div
                className={styles.myAvatar}
                style={{ background: getAvatarColor(me?.username) }}
              >
                {initials(me?.username || '?')}
              </div>
            )}
          </button>

          {profileOpen && (
            <div className={styles.menu}>
              <div className={styles.menuProfile}>
                <div
                  className={styles.menuAvatar}
                  style={{ background: getAvatarColor(me?.username) }}
                >
                  {initials(me?.username || '?')}
                </div>
                <div className={styles.menuUserInfo}>
                  <div className={styles.menuUsername}>{me?.username}</div>
                  <div className={styles.menuSubtext}>@{me?.username}</div>
                  {isAdmin && <div className={styles.menuAdmin}>ADMIN</div>}
                </div>
              </div>

              <div className={styles.menuDivider} />

              <div
                className={`${styles.menuItem} ${styles.danger}`}
                onClick={() => { setProfileOpen(false); logout(); }}
              >
                Выйти
              </div>
            </div>
          )}
        </div>

        {/* Заголовок */}
        <div className={styles.headerTitle}>Чаты</div>

        {/* Бургер — меню действий */}
        <div className={styles.actionsWrap} ref={actionsRef}>
          <button
            className={`${styles.menuBtn} ${actionsOpen ? styles.active : ''}`}
            onClick={() => { setActionsOpen((v) => !v); setProfileOpen(false); }}
            title="Действия"
          >
            {actionsOpen ? (
              <span className={styles.closeIcon}>✕</span>
            ) : (
              <>
                <span />
                <span />
                <span />
              </>
            )}
          </button>

          {actionsOpen && (
            <div className={styles.menuRight}>
              <div className={styles.menuItem} onClick={handleCreateGroup}>
                Создать группу
              </div>

              {isAdmin && (
                <>
                  <div className={styles.menuDivider} />
                  <div className={styles.menuItem} onClick={genInvite}>
                    Создать инвайт
                  </div>
                  {lastInvite && (
                    <div className={styles.menuItem} onClick={copyInvite}>
                      Скопировать: {lastInvite}
                    </div>
                  )}
                </>
              )}
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