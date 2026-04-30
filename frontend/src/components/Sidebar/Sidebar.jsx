import { useEffect, useState, useRef } from 'react';
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

        {/* Поиск с аватаром внутри */}
        <div className={styles.searchWrap} ref={profileRef}>
          <div className={styles.searchInner}>
            <button
              className={styles.myAvatarBtn}
              onClick={() => { setProfileOpen((v) => !v); setActionsOpen(false); }}
            >
              {profileOpen ? (
                <div className={styles.myAvatarClose}>✕</div>
              ) : (
                <div
                  className={styles.myAvatar}
                  style={{ background: getAvatarColor(me?.username) }}
                >
                  {initials(me?.username || '?')}
                </div>
              )}
            </button>
            <SearchBar />
          </div>

          {profileOpen && (
            <div className={styles.menuProfile}>
              <div className={styles.menuProfileCard}>
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

        {/* Бургер в круге */}
        <div className={styles.actionsWrap} ref={actionsRef}>
          <button
            className={`${styles.menuBtn} ${actionsOpen ? styles.active : ''}`}
            onClick={() => { setActionsOpen((v) => !v); setProfileOpen(false); }}
          >
            {actionsOpen ? (
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M1 1L13 13M13 1L1 13" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
              </svg>
            ) : (
              <svg width="16" height="12" viewBox="0 0 16 12" fill="none">
                <path d="M0 1H16M0 6H16M0 11H16" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
              </svg>
            )}
          </button>

          {actionsOpen && (
            <div className={styles.menuActions}>
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

      <div className={styles.chatListContainer}>
        <ChatList chats={chats || []} />
      </div>
    </aside>
  );
}