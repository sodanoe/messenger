import { useState, useRef } from 'react';
import {
  searchUsers,
  addContact,
  getContacts,
} from '../../../services/contacts';
import useAppStore from '../../../store/useAppStore';
import { initials } from '../../../utils/format';
import toast from 'react-hot-toast';
import styles from './SearchBar.module.css';

export default function SearchBar() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState(null); // null = скрыто
  const timer = useRef(null);

  // Достаем данные из стора. Если contacts там нет, используем пустой массив по умолчанию
  const { contacts = [], setContacts, setCurrentChat } = useAppStore();

  function onInput(val) {
    setQuery(val);
    const trimmed = val.trim();
    clearTimeout(timer.current);
    if (!trimmed) {
      setResults(null);
      return;
    }
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
    setCurrentChat({
      type: 'dm',
      id: user.id,
      name: user.username,
      is_online: user.is_online,
    });
  }

  async function addAndChat(user) {
    try {
      await addContact(user.id);
      const updated = await getContacts();
      if (typeof setContacts === 'function') {
        setContacts(updated);
      }
      toast.success(`${user.username} добавлен`);
    } catch (e) {
      if (!e.message.includes('409') && !e.message.includes('already')) {
        toast.error(e.message);
        return;
      }
    }
    clearSearch();
    setCurrentChat({
      type: 'dm',
      id: user.id,
      name: user.username,
      is_online: user.is_online,
    });
  }

  // ЗАЩИТА: Добавлен (contacts || []), чтобы .map() не вызывался у undefined
  const contactIds = new Set((contacts || []).map((c) => c.contact_user_id));

  return (
    <div className={styles.wrap}>
      <div className={styles.inputRow}>
        <input
          className={styles.input}
          value={query}
          onChange={(e) => onInput(e.target.value)}
          placeholder="🔍 Найти пользователя…"
          autoComplete="off"
        />
        {query && (
          <button className={styles.clear} onClick={clearSearch}>
            ✕
          </button>
        )}
      </div>

      {results !== null && (
        <div className={styles.results}>
          {results.length === 0 ? (
            <div className={styles.empty}>Никого не найдено</div>
          ) : (
            results.map((u) => {
              const isContact = contactIds.has(u.id);
              return (
                <div key={u.id} className={styles.item}>
                  <div
                    className={styles.avatar}
                    style={{ position: 'relative' }}
                  >
                    {/* Защита на случай отсутствия username */}
                    {initials(u.username || '?')}
                    {u.is_online && <div className={styles.onlineDot} />}
                  </div>
                  <div className={styles.info}>
                    <div className={styles.name}>
                      {u.username || 'Без имени'}
                    </div>
                    <div
                      className={styles.status}
                      style={{
                        color: u.is_online ? 'var(--green)' : undefined,
                      }}
                    >
                      {u.is_online ? '● online' : 'offline'}
                    </div>
                  </div>
                  <div className={styles.actions}>
                    {isContact ? (
                      <>
                        <span className={styles.alreadyBtn}>✓ добавлен</span>
                        <button
                          className={styles.actionBtn}
                          onClick={() => openDM(u)}
                        >
                          💬
                        </button>
                      </>
                    ) : (
                      <>
                        <button
                          className={`${styles.actionBtn} ${styles.add}`}
                          onClick={() => addAndChat(u)}
                        >
                          ＋
                        </button>
                        <button
                          className={styles.actionBtn}
                          onClick={() => openDM(u)}
                        >
                          💬
                        </button>
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
