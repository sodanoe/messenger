import { initials } from '../../../../utils/format';
import styles from './ChatListItem.module.css';

/**
 * @param {{
 *   type: 'direct'|'group',
 *   id: number,
 *   name: string,
 *   isOnline?: boolean,
 *   lastMessage?: string,
 *   mediaId?: number | null,
 *   time?: string,
 *   hasUnread?: boolean,
 *   isActive: boolean,
 *   onClick: () => void
 * }} props
 */
export default function ChatListItem({
  type,
  name,
  isOnline,
  lastMessage,
  mediaId,
  time,
  hasUnread,
  isActive,
  onClick,
}) {
  const renderSubText = () => {
    if (lastMessage && lastMessage.trim() !== '') {
      return lastMessage;
    }

    if (mediaId) {
      return '🖼 Фотография';
    }

    return type === 'group'
      ? 'Групповой чат'
      : 'Напишите первым...';
  };

  function formatTime(dateString) {
    if (!dateString) return '';

    const date = new Date(dateString);
    const now = new Date();

    const isToday = date.toDateString() === now.toDateString();

    if (isToday) {
      return date.toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
      });
    }

    return date.toLocaleDateString([], {
      day: '2-digit',
      month: '2-digit',
    });
  }

  return (
    <div
      className={`
        ${styles.item}
        ${isActive ? styles.active : ''}
        ${hasUnread ? styles.unread : ''}
      `}
      onClick={onClick}
    >
      {/* AVATAR */}
      <div className={styles.avatarWrap}>
        <div
          className={`
            ${styles.avatar}
            ${type === 'group' ? styles.group : ''}
          `}
        >
          {type === 'group' ? '#' : initials(name)}
        </div>

        {isOnline && <div className={styles.onlineDot} />}
      </div>

      {/* INFO */}
      <div className={styles.info}>
        <div className={styles.top}>
          <div className={styles.name}>{name}</div>

          {/* META BLOCK */}
          <div className={styles.meta}>
            {hasUnread && <div className={styles.unreadDot} />}

            <div className={styles.time}>
              {formatTime(time)}
            </div>
          </div>
        </div>

        <div className={styles.sub}>
          {renderSubText()}
        </div>
      </div>
    </div>
  );
}