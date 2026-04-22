import useAppStore from '../../../store/useAppStore'
import ChatListItem from './ChatListItem/ChatListItem'
import { createGroup, getGroups } from '../../../services/groups'
import toast from 'react-hot-toast'
import styles from './ChatList.module.css'

export default function ChatList() {
  const { activeTab, contacts, groups, setGroups, setCurrentChat, currentChat } = useAppStore()

  async function promptCreateGroup() {
    const name = prompt('Название группы:')
    if (!name?.trim()) return
    try {
      await createGroup(name.trim())
      const updated = await getGroups()
      setGroups(updated)
      toast.success('Группа создана')
    } catch (e) {
      toast.error(e.message)
    }
  }

  if (activeTab === 'dm') {
    if (!contacts.length) {
      return (
        <div className={styles.empty}>
          Нет контактов.<br />Найди пользователя через поиск.
        </div>
      )
    }
    return (
      <div className={styles.list}>
        {contacts.map((c) => (
          <ChatListItem
            key={c.contact_user_id}
            type="dm"
            id={c.chat_id || c.contact_user_id}
            name={c.username || String(c.contact_user_id)}
            isOnline={c.is_online}
            lastMessage={c.last_message}
            hasUnread={c.has_unread}
            isActive={currentChat?.type === 'dm' && currentChat?.id === (c.chat_id || c.contact_user_id)}
            onClick={() => setCurrentChat({
              type: 'dm',
              id: c.chat_id || c.contact_user_id,
              name: c.username,
              is_online: c.is_online,
            })}
          />
        ))}
      </div>
    )
  }

  return (
    <div className={styles.list}>
      <button className={styles.createBtn} onClick={promptCreateGroup}>
        ＋ Создать группу
      </button>
      {!groups.length && <div className={styles.empty}>Нет групп.</div>}
      {groups.map((g) => (
        <ChatListItem
          key={g.id}
          type="group"
          id={g.id}
          name={g.name}
          isActive={currentChat?.type === 'group' && currentChat?.id === g.id}
          onClick={() => setCurrentChat({ type: 'group', id: g.id, name: g.name })}
        />
      ))}
    </div>
  )
}