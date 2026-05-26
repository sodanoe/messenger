import { useEffect, useRef, useState } from 'react';
import useAppStore from '../../store/useAppStore';
import { getMessages } from '../../services/contacts';
import { getGroupMessages } from '../../services/groups';
import { api } from '../../services/api';
import { initials } from '../../utils/format';
import { getAvatarColor } from '../../utils/avatarColor';
import { useMediaUpload } from '../../hooks/useMediaUpload';
import MessageList from './MessageList/MessageList';
import MessageInput from './MessageInput/MessageInput';
import GroupInfoModal from '../RightPanel/GroupInfoModal/GroupInfoModal';
import styles from './ChatWindow.module.css';

function SearchIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  );
}

function DotsIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="5" r="1" fill="currentColor" />
      <circle cx="12" cy="12" r="1" fill="currentColor" />
      <circle cx="12" cy="19" r="1" fill="currentColor" />
    </svg>
  );
}

function MembersIcon({ size = 18 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 20 20" fill="none">
      <circle cx="7" cy="7" r="2.8" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="13" cy="7" r="2.8" stroke="currentColor" strokeWidth="1.5" />
      <path d="M1 17c0-3 2.5-4.8 6-4.8h6c3.5 0 6 1.8 6 4.8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

function ChevronUp() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="18 15 12 9 6 15" />
    </svg>
  );
}

function ChevronDown() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}

export default function ChatWindow({
  showContactPanel,
  setShowContactPanel,
  searchOpen,
  setSearchOpen,
}) {
  const {
    currentChat,
    clearCurrentChat,
    setMessages,
    messages,
    me,
    chats,
    setCustomEmojis,
  } = useAppStore();

  const { handleFile } = useMediaUpload();

  const [showGroupInfo, setShowGroupInfo] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searchIndex, setSearchIndex] = useState(0);

  const loadedChatId = useRef(null);
  const touchStartX = useRef(null);
  const touchStartY = useRef(null);
  const dragCounterRef = useRef(0);
  const searchInputRef = useRef(null);

  const isOnline =
    currentChat?.type === 'direct'
      ? (chats?.find((c) => c.id === currentChat.id)?.is_online ?? currentChat.is_online)
      : false;

  useEffect(() => {
    api('/emojis/', 'GET')
      .then((data) => setCustomEmojis(data.emojis || []))
      .catch(() => {});
  }, []);

  useEffect(() => {
    loadedChatId.current = null;
    setSearchOpen(false);
    setSearchQuery('');
    setSearchResults([]);
    setShowContactPanel(false);
    setShowGroupInfo(false);
  }, [currentChat?.type, currentChat?.id]);

  useEffect(() => {
    if (!currentChat || !me) return;
    if (loadedChatId.current === `${currentChat.type}-${currentChat.id}`) return;
    loadedChatId.current = `${currentChat.type}-${currentChat.id}`;
    async function loadMessages() {
      try {
        const data = currentChat.type === 'direct'
          ? await getMessages(currentChat.id)
          : await getGroupMessages(currentChat.id);
        setMessages([...data.messages].reverse(), data.next_cursor);
      } catch { /* silent */ }
    }
    loadMessages();
  }, [currentChat?.type, currentChat?.id, me?.id]);

  useEffect(() => {
    if (!searchQuery.trim()) { setSearchResults([]); setSearchIndex(0); return; }
    const q = searchQuery.toLowerCase();
    const found = (messages || [])
      .map((m, i) => ({ ...m, _idx: i }))
      .filter((m) => m.content?.toLowerCase().includes(q));
    setSearchResults(found);
    setSearchIndex(0);
  }, [searchQuery, messages]);

  useEffect(() => {
    if (!searchResults.length) return;
    const msg = searchResults[searchIndex];
    if (!msg) return;
    const el = document.querySelector(`[data-msg-id="${msg.id}"]`);
    if (!el) return;
    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    el.classList.add(styles.highlight);
    setTimeout(() => el.classList.remove(styles.highlight), 1000);
  }, [searchIndex, searchResults]);

  useEffect(() => {
    if (searchOpen) setTimeout(() => searchInputRef.current?.focus(), 50);
  }, [searchOpen]);

  useEffect(() => {
    function onKey(e) {
      if (e.key === 'Escape' && searchOpen) closeSearch();
    }
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [searchOpen]);

  function closeSearch() {
    setSearchOpen(false);
    setSearchQuery('');
    setSearchResults([]);
  }

  function handleDotsClick() {
    if (showContactPanel) {
      setShowContactPanel(false);
    } else {
      closeSearch();
      setShowContactPanel(true);
    }
  }

  function handleSearchClick() {
    if (searchOpen) {
      closeSearch();
    } else {
      setShowContactPanel(false);
      setSearchOpen(true);
    }
  }

  function goBack() { clearCurrentChat(); }

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

  function onDragEnter(e) {
    e.preventDefault();
    if ([...(e.dataTransfer?.types || [])].includes('Files')) {
      dragCounterRef.current++;
      setIsDragging(true);
    }
  }

  function onDragLeave(e) {
    e.preventDefault();
    dragCounterRef.current--;
    if (dragCounterRef.current === 0) setIsDragging(false);
  }

  function onDragOver(e) { e.preventDefault(); }

  function onDrop(e) {
    e.preventDefault();
    dragCounterRef.current = 0;
    setIsDragging(false);
    const f = e.dataTransfer?.files?.[0];
    if (f && (f.type.startsWith('image/') || f.name.match(/\.(heic|heif)$/i)))
      handleFile(f);
  }

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
      onDragEnter={onDragEnter}
      onDragLeave={onDragLeave}
      onDragOver={onDragOver}
      onDrop={onDrop}
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
              {isOnline ? 'в сети' : 'не в сети'}
            </div>
          )}
          {currentChat.type === 'group' && (
            <div className={styles.status}>групповой чат</div>
          )}
        </div>
        <div className={styles.headerActions}>
          <button
            className={`${styles.headerBtn} ${searchOpen ? styles.active : ''}`}
            onClick={handleSearchClick}
            title="Поиск по сообщениям"
          >
            <SearchIcon />
          </button>
          {currentChat.type === 'group' ? (
            <button
              className={`${styles.headerBtn} ${showGroupInfo ? styles.active : ''}`}
              onClick={() => setShowGroupInfo((v) => !v)}
              title="Участники"
            >
              <MembersIcon />
            </button>
          ) : (
            <button
              className={`${styles.headerBtn} ${showContactPanel ? styles.menuActive : ''}`}
              onClick={handleDotsClick}
              title="Профиль контакта"
            >
              <DotsIcon />
            </button>
          )}
        </div>
      </div>

      {searchOpen && (
        <div className={styles.searchBar}>
          <input
            ref={searchInputRef}
            className={styles.searchBarInput}
            placeholder="Поиск по сообщениям..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          {searchResults.length > 0 && (
            <span className={styles.searchBarCount}>
              {searchIndex + 1}/{searchResults.length}
            </span>
          )}
          <div className={styles.searchBarNav}>
            <button
              className={styles.searchNavBtn}
              onClick={() => setSearchIndex((i) => Math.max(0, i - 1))}
              disabled={searchIndex === 0}
            >
              <ChevronUp />
            </button>
            <button
              className={styles.searchNavBtn}
              onClick={() => setSearchIndex((i) => Math.min(searchResults.length - 1, i + 1))}
              disabled={searchIndex >= searchResults.length - 1}
            >
              <ChevronDown />
            </button>
          </div>
          <button className={styles.searchCloseBtn} onClick={closeSearch}>✕</button>
        </div>
      )}

      <MessageList />
      <MessageInput />

      {isDragging && (
        <div className={styles.dropOverlay}>
          <div className={styles.dropBox}>
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66L9.41 17.41a2 2 0 01-2.83-2.83l8.49-8.48" />
            </svg>
            <div className={styles.dropTitle}>Отпустите файл</div>
            <div className={styles.dropSub}>Изображение будет прикреплено к сообщению</div>
          </div>
        </div>
      )}

      {showGroupInfo && (
        <GroupInfoModal onClose={() => setShowGroupInfo(false)} />
      )}
    </div>
  );
}