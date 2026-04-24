import { useEffect, useState } from 'react';
import useAppStore from '../../store/useAppStore';
import { api } from '../../services/api';
import SearchBar from './SearchBar/SearchBar';
import ChatList from './ChatList/ChatList';
import styles from './Sidebar.module.css';

export default function Sidebar() {
  const { me, isAdmin, chats, setChats, logout, lastInvite, setLastInvite } =
    useAppStore();

  const [inviteHint, setInviteHint] = useState(
    'Создай код и отправь новому пользователю',
  );

  useEffect(() => {
    const fetchChats = async () => {
      try {
        const data = await api('/chats/', 'GET');

        // ЗАЩИТА: Если бэкенд прислал что-то не то, ставим пустой массив вместо undefined
        setChats(data?.chats || []);
      } catch (err) {
        console.error('Ошибка загрузки чатов:', err);
        // В случае ошибки тоже гарантируем, что chats будет массивом
        setChats([]);
      }
    };
    fetchChats();
  }, [setChats]);

  function doLogout() {
    logout();
  }

  async function genInvite() {
    try {
      const r = await api('/auth/invite', 'POST');
      setLastInvite(r.code);
      setInviteHint('Нажми на код чтобы скопировать');
    } catch {
      // silent
    }
  }

  function copyInvite() {
    if (!lastInvite) return;
    navigator.clipboard
      .writeText(lastInvite)
      .then(() => setInviteHint('✓ Скопировано'))
      .catch(() => prompt('Скопируй код:', lastInvite));
  }

  return (
    <aside className={`${styles.sidebar} sidebar`}>
      <div className={styles.header}>
        <div className={styles.logo}>// msg</div>
        <div className={styles.meBadge}>{me?.username}</div>
        {isAdmin && <span className={styles.adminBadge}>ADMIN</span>}
        <button className={styles.logoutBtn} onClick={doLogout} title="Выйти">
          ⏏
        </button>
      </div>

      <SearchBar />

      <div className={styles.chatListContainer}>
        {/* Передаем chats, который теперь гарантированно массив или пустой список */}
        <ChatList chats={chats || []} />
      </div>

      {isAdmin && (
        <div className={styles.adminPanel}>
          <div className={styles.adminTitle}>⚡ Инвайты</div>
          <div className={styles.inviteRow}>
            <div
              className={`${styles.inviteCode} ${!lastInvite ? styles.empty : ''}`}
              onClick={copyInvite}
              title="Нажми чтобы скопировать"
            >
              {lastInvite || 'нет кода'}
            </div>
            <button className={styles.smallBtn} onClick={genInvite}>
              + Создать
            </button>
          </div>
          <div className={styles.inviteHint}>{inviteHint}</div>
        </div>
      )}
    </aside>
  );
}
