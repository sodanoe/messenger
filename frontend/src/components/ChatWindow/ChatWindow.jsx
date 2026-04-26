import { useEffect, useRef, useState } from 'react';
import useAppStore from '../../store/useAppStore';
import { getMessages, markRead } from '../../services/contacts';
import { getGroupMessages } from '../../services/groups';
import { initials } from '../../utils/format';
import MessageList from './MessageList/MessageList';
import MessageInput from './MessageInput/MessageInput';
import GroupInfoModal from '../RightPanel/GroupInfoModal/GroupInfoModal';
import styles from './ChatWindow.module.css';

export default function ChatWindow() {
  const { currentChat, clearCurrentChat, setMessages, me } = useAppStore();
  const [showGroupInfo, setShowGroupInfo] = useState(false);
  const loadedChatId = useRef(null);

  function goBack() {
    clearCurrentChat();
  }

  // Сброс при смене чата
  useEffect(() => {
    loadedChatId.current = null;
  }, [currentChat?.type, currentChat?.id]);

  // Загрузка сообщений
  useEffect(() => {
    if (!currentChat) return;
    if (!me) return;
    if (loadedChatId.current === `${currentChat.type}-${currentChat.id}`)
      return;

    loadedChatId.current = `${currentChat.type}-${currentChat.id}`;

    async function loadMessages() {
      try {
        // if (currentChat.type === 'dm') {
        if (currentChat.type === 'direct') {
          const data = await getMessages(currentChat.id);
          setMessages([...data.messages].reverse());
          markRead(currentChat.id).catch(() => {});
        } else {
          const data = await getGroupMessages(currentChat.id);
          setMessages([...data.messages].reverse());
        }
      } catch {
        // silent
      }
    }
    loadMessages();
  }, [currentChat?.type, currentChat?.id, me?.id]);

  if (!currentChat) {
    return (
      <div className={`${styles.area} chat-area`}>
        <div className={styles.placeholder}>
          <div className={styles.placeholderIcon}>💬</div>
          <div>Выбери контакт или найди пользователя</div>
        </div>
      </div>
    );
  }

  return (
    <div className={`${styles.area} chat-area`}>
      <div className={styles.header}>
        <button className={styles.backBtn} onClick={goBack}>
          ‹
        </button>
        <div
          className={`${styles.avatar} ${currentChat.type === 'group' ? styles.groupAvatar : ''}`}
        >
          {currentChat.type === 'group' ? '#' : initials(currentChat.name)}
        </div>
        <div className={styles.headerInfo}>
          <div className={styles.chatName}>{currentChat.name}</div>
          {/* {currentChat.type === 'dm' && ( */}
          {currentChat.type === 'direct' && (
            <div
              className={`${styles.status} ${currentChat.is_online ? styles.online : ''}`}
            >
              {currentChat.is_online ? 'online' : 'offline'}
            </div>
          )}
          {currentChat.type === 'group' && (
            <div className={styles.status}>group chat</div>
          )}
        </div>
        {currentChat.type === 'group' && (
          <button
            className={styles.membersBtn}
            onClick={() => setShowGroupInfo(true)}
            title="Участники"
          >
            👥
          </button>
        )}
      </div>

      <MessageList />
      <MessageInput />

      {showGroupInfo && (
        <GroupInfoModal onClose={() => setShowGroupInfo(false)} />
      )}
    </div>
  );
}
