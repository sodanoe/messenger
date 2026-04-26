import useAppStore from '../../../store/useAppStore';
import ChatListItem from './ChatListItem/ChatListItem';
import styles from './ChatList.module.css';

export default function ChatList({ chats }) {
  const { setCurrentChat, currentChat } = useAppStore();

  const items = Array.isArray(chats) ? chats : [];

  if (items.length === 0) {
    return (
      <div className={styles.list}>
        <div className={styles.empty}>
          Чатов пока нет.<br />Найди кого-нибудь через поиск.
        </div>
      </div>
    );
  }

  return (
    <div className={styles.list}>
      {items.map((chat) => (
        <ChatListItem
          key={`${chat.type}-${chat.id}`}
          type={chat.type}
          id={chat.id}
          name={chat.name || (chat.type === 'group' ? 'Безымянная группа' : 'Пользователь')}
          isOnline={chat.is_online}
          lastMessage={chat.last_message}
          hasUnread={chat.has_unread}
          time={chat.updated_at}
          mediaId={chat.last_msg_media_id}
          isActive={current_chat_is_active(currentChat, chat)}
          onClick={() => setCurrentChat({
            type: chat.type,
            id: chat.id,
            name: chat.name,
            is_online: chat.is_online,
            other_user_id: chat.other_user_id,
          })}
        />
      ))}
    </div>
  );
}

function current_chat_is_active(current, chat) {
  return current?.id === chat.id && current?.type === chat.type;
}