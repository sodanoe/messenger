import { initials } from '../../../../utils/format';
import styles from './ChatListItem.module.css';

/**
 * @param {{
 *   type: 'direct'|'group',
 *   id: number,
 *   name: string,
 *   isOnline?: boolean,
 *   lastMessage?: string,
 *   mediaId?: number | null, // Добавили поле для медиа
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
  hasUnread,
  isActive,
  onClick,
}) {
  // Логика выбора текста подзаголовка
  const renderSubText = () => {
    // 1. Если есть текст сообщения (даже если там просто эмодзи)
    if (lastMessage && lastMessage.trim() !== '') {
      return lastMessage;
    }

    // 2. Если текста нет, но есть ID медиафайла
    if (mediaId) {
      return '🖼 Фотография';
    }

    // 3. Если совсем ничего нет — стандартные заглушки
    return type === 'group' ? 'Групповой чат' : 'Напишите первым...';
  };

  return (
    <div
      className={`${styles.item} ${isActive ? styles.active : ''}`}
      onClick={onClick}
    >
      <div className={styles.avatarWrap}>
        <div
          className={`${styles.avatar} ${type === 'group' ? styles.group : ''}`}
        >
          {type === 'group' ? '#' : initials(name)}
        </div>
        {isOnline && <div className={styles.onlineDot} />}
      </div>

      <div className={styles.info}>
        <div className={styles.name}>{name}</div>
        <div className={styles.sub}>{renderSubText()}</div>
      </div>

      {hasUnread && <div className={styles.unreadDot} />}
    </div>
  );
}
