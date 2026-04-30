import { useEffect, useRef, useState } from 'react';
import useAppStore from '../../store/useAppStore';
import { getMessages } from '../../services/contacts';
import { getGroupMessages } from '../../services/groups';
import { api } from '../../services/api';
import { initials } from '../../utils/format';
import { getAvatarColor } from '../../utils/avatarColor';
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
  const { currentChat, clearCurrentChat, setMessages, me, chats, setCustomEmojis } = useAppStore();
  const [showGroupInfo, setShowGroupInfo] = useState(false);
  const loadedChatId = useRef(null);
  const touchStartX = useRef(null);
  const touchStartY = useRef(null);

  const isOnline = currentChat?.type === 'direct'
    ? chats?.find(c => c.id === currentChat.id)?.is_online ?? currentChat.is_online
    : false;

  useEffect(() => {
    api('/emojis/', 'GET')
      .then((data) => setCustomEmojis(data.emojis || []))
      .catch(() => {});
  }, []);

  function goBack() {
    clearCurrentChat();
  }

  function handleTouchStart(e) {
    touchStartX.current = e.touches[0].clientX;
    touchStartY.current = e.touches[0].clientY;
  }

  function handleTouchEnd(e) {
    if (touchStartX.current === null) return;
    const dx = e.changedTouches[0].clientX - touchStartX.current;
    const dy = Math.abs(e.changedTouches[0].clientY - touchStartY.current);
    if (dx > 80 && dy < 60) goBack();
    touchStartX.current = null;
    touchStartY.current = null;
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
        let data;
        if (currentChat.type === 'direct') {
          data = await getMessages(currentChat.id);
        } else {
          data = await getGroupMessages(currentChat.id);
        }
        setMessages([...data.messages].reverse(), data.next_cursor);
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
    <div
      className={`${styles.area} chat-area`}
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
    >
      <div className={styles.header}>
        <button className={styles.backBtn} onClick={goBack}>‹</button>
        <div
          className={`${styles.avatar} ${currentChat.type === 'group' ? styles.groupAvatar : ''}`}
          style={currentChat.type !== 'group' ? { background: getAvatarColor(currentChat.name) } : {}}
        >
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
          <button className={styles.membersBtn} onClick={() => setShowGroupInfo(true)} title="Участники">
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