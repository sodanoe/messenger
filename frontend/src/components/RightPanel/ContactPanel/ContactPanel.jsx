import { useEffect, useState } from 'react';
import useAppStore from '../../../store/useAppStore';
import { api } from '../../../services/api';
import { initials } from '../../../utils/format';
import { getAvatarColor } from '../../../utils/avatarColor';
import { API_BASE } from '../../../config';
import toast from 'react-hot-toast';
import styles from './ContactPanel.module.css';

// ─── Иконки ───────────────────────────────────────────────
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

function BlockIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10"/>
      <line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/>
    </svg>
  );
}

export default function ContactPanel({ onClose, onOpenSearch }) {
  const { currentChat, chats, me } = useAppStore();
  const [media, setMedia] = useState([]);
  const [muted, setMuted] = useState(false);

  const isOnline = chats?.find((c) => c.id === currentChat?.id)?.is_online
    ?? currentChat?.is_online
    ?? false;

  // Загрузка медиа контакта
  useEffect(() => {
    if (!currentChat?.id) return;
    api(`/chats/${currentChat.id}/media`, 'GET')
      .then((data) => setMedia(data?.media || []))
      .catch(() => setMedia([]));
  }, [currentChat?.id]);

  // Esc закрывает панель
  useEffect(() => {
    function onKey(e) {
      if (e.key === 'Escape') onClose();
    }
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onClose]);

  async function handleMute() {
    setMuted((v) => !v);
    toast.success(muted ? 'Уведомления включены' : 'Уведомления отключены');
  }

  async function handleBlock() {
    if (!confirm(`Заблокировать ${currentChat?.name}?`)) return;
    try {
      await api(`/contacts/${currentChat?.other_user_id}/block`, 'POST');
      toast.success(`${currentChat?.name} заблокирован`);
      onClose();
    } catch (e) {
      toast.error(e.message);
    }
  }

  if (!currentChat) return null;

  return (
    <div className={styles.panel}>
      {/* ─── Кнопка закрытия ─── */}
      <button className={styles.closeBtn} onClick={onClose} title="Закрыть (Esc)">
        ✕
      </button>

      {/* ─── Карточка контакта ─── */}
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

      {/* ─── Быстрые действия ─── */}
      <div className={styles.actions}>
        <button
          className={styles.actionItem}
          onClick={onOpenSearch}
          title="Поиск по сообщениям"
        >
          <div className={styles.actionIcon}>
            <SearchIcon />
          </div>
          <span className={styles.actionLabel}>Поиск</span>
        </button>

        <button
          className={styles.actionItem}
          onClick={handleMute}
          title={muted ? 'Включить уведомления' : 'Отключить уведомления'}
        >
          <div className={styles.actionIcon} style={{ opacity: muted ? 0.5 : 1 }}>
            <MuteIcon />
          </div>
          <span className={styles.actionLabel}>
            {muted ? 'Включить' : 'Без звука'}
          </span>
        </button>

        <button
          className={styles.actionItem}
          onClick={handleBlock}
          title="Заблокировать"
        >
          <div className={`${styles.actionIcon} ${styles.actionDanger}`}>
            <BlockIcon />
          </div>
          <span className={`${styles.actionLabel} ${styles.actionDanger}`}>
            Заблокировать
          </span>
        </button>
      </div>

      {/* ─── Медиа ─── */}
      <div className={styles.mediaSection}>
        <div className={styles.mediaSectionHeader}>Медиа</div>
        {media.length === 0 ? (
          <div className={styles.mediaEmpty}>Нет общих медиафайлов</div>
        ) : (
          <div className={styles.mediaGrid}>
            {media.map((item, i) => {
              const url = item.url?.startsWith('http')
                ? item.url
                : API_BASE() + item.url;
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