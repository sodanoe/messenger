import { useEffect, useState } from 'react';
import useAppStore from '../../../store/useAppStore';
import { api } from '../../../services/api';
import { initials } from '../../../utils/format';
import { getAvatarColor } from '../../../utils/avatarColor';
import { API_BASE } from '../../../config';
import toast from 'react-hot-toast';
import styles from './ContactPanel.module.css';

function SearchIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  );
}

function MuteIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
      <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
      <line x1="1" y1="1" x2="23" y2="23"/>
    </svg>
  );
}

function BellIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
      <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
    </svg>
  );
}

function BlockIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10"/>
      <line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/>
    </svg>
  );
}

export default function ContactPanel({ onClose, onOpenSearch }) {
  const { currentChat, chats } = useAppStore();
  const [media, setMedia] = useState([]);
  const [muted, setMuted] = useState(false);
  const [blocked, setBlocked] = useState(false); // баг 6

  const isOnline = chats?.find((c) => c.id === currentChat?.id)?.is_online
    ?? currentChat?.is_online
    ?? false;

  useEffect(() => {
    if (!currentChat?.id) return;
    api(`/chats/${currentChat.id}/media`, 'GET')
      .then((data) => setMedia(data?.media || []))
      .catch(() => setMedia([]));
  }, [currentChat?.id]);

  useEffect(() => {
    function onKey(e) { if (e.key === 'Escape') onClose(); }
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onClose]);

  async function handleMute() {
    setMuted((v) => !v);
    toast.success(muted ? 'Уведомления включены' : 'Уведомления отключены');
  }

  // Баг 6 — тоггл блокировки/разблокировки
  async function handleBlock() {
    if (blocked) {
      // Разблокировать
      if (!confirm(`Разблокировать ${currentChat?.name}?`)) return;
      try {
        await api(`/contacts/${currentChat?.other_user_id}/unblock`, 'POST');
        setBlocked(false);
        toast.success(`${currentChat?.name} разблокирован`);
      } catch (e) {
        toast.error(e.message);
      }
    } else {
      // Заблокировать
      if (!confirm(`Заблокировать ${currentChat?.name}?`)) return;
      try {
        await api(`/contacts/${currentChat?.other_user_id}/block`, 'POST');
        setBlocked(true);
        toast.success(`${currentChat?.name} заблокирован`);
      } catch (e) {
        toast.error(e.message);
      }
    }
  }

  if (!currentChat) return null;

  return (
    <div className={styles.panel}>
      <button className={styles.closeBtn} onClick={onClose} title="Закрыть (Esc)">✕</button>

      <div className={styles.profileCard}>
        <div
          className={styles.avatar}
          style={{ background: getAvatarColor(currentChat.name) }}
        >
          {initials(currentChat.name)}
          {isOnline && <div className={styles.onlineDot} />}
        </div>
        <div className={styles.name}>{currentChat.name}</div>
        <div className={styles.username}>@{currentChat.name}</div>
        {isOnline && <div className={styles.onlineBadge}>В сети</div>}
      </div>

      <div className={styles.actions}>
        <button className={styles.actionItem} onClick={onOpenSearch} title="Поиск по сообщениям">
          <div className={styles.actionIcon}><SearchIcon /></div>
          <span className={styles.actionLabel}>Поиск</span>
        </button>

        <button className={styles.actionItem} onClick={handleMute}>
          <div className={styles.actionIcon}>
            {muted ? <BellIcon /> : <MuteIcon />}
          </div>
          <span className={styles.actionLabel}>{muted ? 'Включить' : 'Без звука'}</span>
        </button>

        <button className={styles.actionItem} onClick={handleBlock}>
          <div className={`${styles.actionIcon} ${styles.actionDanger}`}>
            <BlockIcon />
          </div>
          <span className={`${styles.actionLabel} ${styles.actionDanger}`}>
            {blocked ? 'Разблокировать' : 'Заблокировать'}
          </span>
        </button>
      </div>

      <div className={styles.mediaSection}>
        <div className={styles.mediaSectionHeader}>Медиа</div>
        {media.length === 0 ? (
          <div className={styles.mediaEmpty}>Нет общих медиафайлов</div>
        ) : (
          <div className={styles.mediaGrid}>
            {media.map((item, i) => {
              const url = item.url?.startsWith('http') ? item.url : API_BASE() + item.url;
              return (
                <div key={i} className={styles.mediaCell}>
                  <img src={url} alt="" loading="lazy" />
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}