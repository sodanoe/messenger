import { initials } from "../../../../utils/format";
import styles from "./ChatListItem.module.css";

/**
 * @param {{
 *   type: 'dm'|'group',
 *   id: number,
 *   name: string,
 *   isOnline?: boolean,
 *   lastMessage?: string,
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
  hasUnread,
  isActive,
  onClick,
}) {
  return (
    <div
      className={`${styles.item} ${isActive ? styles.active : ""}`}
      onClick={onClick}
    >
      <div className={styles.avatarWrap}>
        <div
          className={`${styles.avatar} ${type === "group" ? styles.group : ""}`}
        >
          {type === "group" ? "#" : initials(name)}
        </div>
        {isOnline && <div className={styles.onlineDot} />}
      </div>

      <div className={styles.info}>
        <div className={styles.name}>{name}</div>
        <div className={styles.sub}>
          {type === "group"
            ? "group"
            : lastMessage
              ? typeof lastMessage === "string"
                ? lastMessage
                : "нет сообщений"
              : "нет сообщений"}
        </div>
      </div>

      {hasUnread && <div className={styles.unreadDot} />}
    </div>
  );
}
