import useAppStore from '../../../store/useAppStore';
import ChatListItem from './ChatListItem/ChatListItem';
import { createGroup } from '../../../services/groups';
import { api } from '../../../services/api';
import toast from 'react-hot-toast';
import styles from './ChatList.module.css';

export default function ChatList({ chats }) {
  const { setCurrentChat, currentChat, setChats } = useAppStore();

  const items = Array.isArray(chats) ? chats : [];

  async function promptCreateGroup() {
    const name = prompt('Название группы:');
    if (!name?.trim()) return;
    try {
      await createGroup(name.trim());
      const data = await api('/chats/', 'GET');
      if (data?.chats) {
        setChats(data.chats);
      }
      toast.success('Группа создана');
    } catch (e) {
      toast.error(e.message);
    }
  }

  if (items.length === 0) {
    return (
      <div className={styles.list}>
        <button className={styles.createBtn} onClick={promptCreateGroup}>
          ＋ Создать группу
        </button>
        <div className={styles.empty}>
          Чатов пока нет.
          <br />
          Найди кого-нибудь через поиск.
        </div>
      </div>
    );
  }

  return (
    <div className={styles.list}>
      <button className={styles.createBtn} onClick={promptCreateGroup}>
        ＋ Создать группу
      </button>

      {items.map((chat) => (
        <ChatListItem
          key={`${chat.type}-${chat.id}`}
          type={chat.type}
          id={chat.id}
          name={
            chat.name ||
            (chat.type === 'group' ? 'Безымянная группа' : 'Пользователь')
          }
          isOnline={chat.is_online}
          lastMessage={chat.last_message}
          // ПЕРЕДАЕМ ID МЕДИА: чтобы компонент знал, что там картинка
          mediaId={chat.last_msg_media_id}
          isActive={current_chat_is_active(currentChat, chat)}
          onClick={() =>
            setCurrentChat({
              type: chat.type,
              id: chat.id,
              name: chat.name,
              is_online: chat.is_online,
              other_user_id: chat.other_user_id,
            })
          }
        />
      ))}
    </div>
  );
}

// Вспомогательная функция для чистоты кода
function current_chat_is_active(current, chat) {
  return current?.id === chat.id && current?.type === chat.type;
}
