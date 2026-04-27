import { useState, useRef } from 'react';
import { searchUsers } from '../../../services/contacts';
import { createGroup } from '../../../services/groups';
import { api } from '../../../services/api';
import useAppStore from '../../../store/useAppStore';
import { initials } from '../../../utils/format';
import toast from 'react-hot-toast';
import styles from './SearchBar.module.css';

function GroupPlusIcon({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 20 20" fill="none">
      <circle cx="7" cy="7" r="2.8" stroke="currentColor" strokeWidth="1.5" />
      <circle cx="13" cy="7" r="2.8" stroke="currentColor" strokeWidth="1.5" />
      <path d="M1 17c0-3 2.5-4.8 6-4.8h2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <path d="M14 12.5v4M12 14.5h4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

export default function SearchBar() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState(null);
  const timer = useRef(null);

  const { setCurrentChat, setChats, chats } = useAppStore();

  const existingDMUserIds = new Set(
    (chats || []).filter(c => c.type === 'direct').map(c => c.other_user_id)
  );

  function onInput(val) {
    setQuery(val);
    const trimmed = val.trim();
    clearTimeout(timer.current);
    if (!trimmed) { setResults(null); return; }
    timer.current = setTimeout(() => doSearch(trimmed), 280);
  }

  async function doSearch(q) {
    try {
      const users = await searchUsers(q);
      setResults(users || []);
    } catch {
      setResults([]);
    }
  }

  function clearSearch() {
    setQuery('');
    setResults(null);
    clearTimeout(timer.current);
  }

  async function openDM(user) {
    clearSearch();
    try {
      const chat = await api('/chats/direct', 'POST', { user_id: user.id });
      setCurrentChat({
        type: 'direct',
        id: chat.id,
        name: user.username,
        is_online: user.is_online,
      });
      const data = await api('/chats/', 'GET');
      if (data?.chats) setChats(data.chats);
    } catch (e) {
      toast.error(e.message);
    }
  }

  async function addAndChat(user) {
    // Сначала добавляем в контакты (создаёт двустороннюю запись)
    try {
      await api('/contacts', 'POST', { username: user.username });
    } catch (e) {
      if (!e.message.includes('409') && !e.message.includes('already')) {
        toast.error(e.message);
        return;
      }
    }
    // Потом создаём или открываем DM чат
    try {
      const chat = await api('/chats/direct', 'POST', { user_id: user.id });
      toast.success(`${user.username} добавлен`);
      const data = await api('/chats/', 'GET');
      if (data?.chats) setChats(data.chats);
      clearSearch();
      setCurrentChat({
        type: 'direct',
        id: chat.id,
        name: user.username,
        is_online: user.is_online,
      });
    } catch (e) {
      toast.error(e.message);
    }
  }

  async function handleCreateGroup() {
    const name = prompt('Название группы:');
    if (!name?.trim()) return;
    try {
      await createGroup(name.trim());
      const data = await api('/chats/', 'GET');
      if (data?.chats) setChats(data.chats);
      toast.success('Группа создана');
    } catch (e) {
      toast.error(e.message);
    }
  }

  return (
    <div className={styles.wrap}>
      <div className={styles.row}>
        <div className={styles.inputRow}>
          <input
            className={styles.input}
            value={query}
            onChange={(e) => onInput(e.target.value)}
            placeholder="Найти пользователя…"
            autoComplete="off"
          />
          {query && (
            <button className={styles.clear} onClick={clearSearch}>✕</button>
          )}
        </div>

        <button
          className={styles.createGroupBtn}
          onClick={handleCreateGroup}
          aria-label="Создать группу"
        >
          <GroupPlusIcon />
          <span className={styles.tooltip}>Создать группу</span>
        </button>
      </div>

      {results !== null && (
        <div className={styles.results}>
          {results.length === 0 ? (
            <div className={styles.empty}>Никого не найдено</div>
          ) : (
            results.map((u) => {
              const isContact = existingDMUserIds.has(u.id);
              return (
                <div key={u.id} className={styles.item}>
                  <div className={styles.avatar}>
                    {initials(u.username || '?')}
                    {u.is_online && <div className={styles.onlineDot} />}
                  </div>
                  <div className={styles.info}>
                    <div className={styles.name}>{u.username || 'Без имени'}</div>
                    <div
                      className={styles.status}
                      style={{ color: u.is_online ? 'var(--green)' : undefined }}
                    >
                      {u.is_online ? '● online' : 'offline'}
                    </div>
                  </div>
                  <div className={styles.actions}>
                    {isContact ? (
                      <>
                        <span className={styles.alreadyBtn}>✓ добавлен</span>
                        <button className={styles.actionBtn} onClick={() => openDM(u)}>💬</button>
                      </>
                    ) : (
                      <>
                        <button
                          className={`${styles.actionBtn} ${styles.add}`}
                          onClick={() => addAndChat(u)}
                        >
                          ＋
                        </button>
                        <button className={styles.actionBtn} onClick={() => openDM(u)}>💬</button>
                      </>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}