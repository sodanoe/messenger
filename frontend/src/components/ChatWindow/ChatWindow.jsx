import { useEffect, useRef, useState } from 'react';
import useAppStore from '../../store/useAppStore';
import { getMessages, 
  // markRead 
} from '../../services/contacts';
import { getGroupMessages } from '../../services/groups';
import { initials } from '../../utils/format';
import MessageList from './MessageList/MessageList';
import MessageInput from './MessageInput/MessageInput';
import GroupInfoModal from '../RightPanel/GroupInfoModal/GroupInfoModal';
import styles from './ChatWindow.module.css';

function MembersIcon({ size = 18 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 20 20" fill="none">
      <circle cx="7" cy="7" r="2.8" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="13" cy="7" r="2.8" stroke="currentColor" strokeWidth="1.5" />
      <path d="M1 17c0-3 2.5-4.8 6-4.8h6c3.5 0 6 1.8 6 4.8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

export default function ChatWindow() {
  const { currentChat, clearCurrentChat, setMessages, me, chats } = useAppStore();
  const [showGroupInfo, setShowGroupInfo] = useState(false);
  const loadedChatId = useRef(null);

  // берём актуальный онлайн-статус из chats, а не из currentChat
  const isOnline = currentChat?.type === 'direct'
    ? chats?.find(c => c.id === currentChat.id)?.is_online ?? currentChat.is_online
    : false;

  function goBack() {
    clearCurrentChat();
  }

  useEffect(() => {
    loadedChatId.current = null;
  }, [currentChat?.type, currentChat?.id]);

  useEffect(() => {
    if (!currentChat) return;
    if (!me) return;
    if (loadedChatId.current === `${currentChat.type}-${currentChat.id}`) return;

    loadedChatId.current = `${currentChat.type}-${currentChat.id}`;

    async function loadMessages() {
      try {
        if (currentChat.type === 'direct') {
          const data = await getMessages(currentChat.id);
          setMessages([...data.messages].reverse());
          // markRead(currentChat.id).catch(() => {});
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
        <button className={styles.backBtn} onClick={goBack}>‹</button>
        <div className={`${styles.avatar} ${currentChat.type === 'group' ? styles.groupAvatar : ''}`}>
          {currentChat.type === 'group' ? '#' : initials(currentChat.name)}
        </div>
        <div className={styles.headerInfo}>
          <div className={styles.chatName}>{currentChat.name}</div>
          {currentChat.type === 'direct' && (
            <div className={`${styles.status} ${isOnline ? styles.online : ''}`}>
              {isOnline ? 'online' : 'offline'}
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
            <MembersIcon />
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