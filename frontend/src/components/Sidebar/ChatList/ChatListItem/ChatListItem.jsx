import { initials } from '../../../../utils/format';
import { getAvatarColor } from '../../../../utils/avatarColor';
import useAppStore from '../../../../store/useAppStore';
import styles from './ChatListItem.module.css';

export default function ChatListItem({
  type, name, isOnline, lastMessage, mediaId, time, hasUnread, isActive, onClick,
}) {
  const { customEmojis } = useAppStore();

  const formatLastMessage = (text) => {
    if (!text || !text.trim()) return null;
    const parts = text.split(/(:[a-zA-Z0-9_]+:)/g);
    return parts.map((part, i) => {
      if (part.startsWith(':') && part.endsWith(':')) {
        const code = part.slice(1, -1);
        const found = customEmojis.find((e) => e.shortcode === code);
        if (found) {
          return <img key={i} src={found.url} style={{ height: 16, width: 16, verticalAlign: 'middle', objectFit: 'contain', margin: '0 1px' }} alt={part} />;
        }
      }
      return part;
    });
  };

  const renderSubText = () => {
    if (lastMessage && lastMessage.trim() !== '') {
      return formatLastMessage(lastMessage);
    }
    if (mediaId) return '🖼 Фотография';
    return type === 'group' ? 'Групповой чат' : 'Напишите первым...';
  };

  function formatTime(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    const now = new Date();
    const isToday = date.toDateString() === now.toDateString();
    if (isToday) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    return date.toLocaleDateString([], { day: '2-digit', month: '2-digit' });
  }

  return (
    <div
      className={`${styles.item} ${isActive ? styles.active : ''} ${hasUnread ? styles.unread : ''}`}
      onClick={onClick}
    >
      <div className={styles.avatarWrap}>
        <div
          className={`${styles.avatar} ${type === 'group' ? styles.group : ''}`}
          style={type !== 'group' ? { background: getAvatarColor(name) } : {}}
        >
          {type === 'group' ? '#' : initials(name)}
        </div>
        {isOnline && <div className={styles.onlineDot} />}
      </div>

      <div className={styles.info}>
        <div className={styles.top}>
          <div className={styles.name}>{name}</div>
          <div className={styles.meta}>
            {hasUnread && <div className={styles.unreadDot} />}
            <div className={styles.time}>{formatTime(time)}</div>
          </div>
        </div>
        <div className={styles.sub}>{renderSubText()}</div>
      </div>
    </div>
  );
}