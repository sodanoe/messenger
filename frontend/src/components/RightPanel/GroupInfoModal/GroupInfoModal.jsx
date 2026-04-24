import { useEffect, useState } from 'react';
import useAppStore from '../../../store/useAppStore';
import {
  getGroupMembers,
  inviteMember,
  removeMember,
  leaveGroup,
  deleteGroup,
  getGroups,
} from '../../../services/groups';
import { getContacts } from '../../../services/contacts';
import { initials } from '../../../utils/format';
import toast from 'react-hot-toast';
import styles from './GroupInfoModal.module.css';

export default function GroupInfoModal({ onClose }) {
  const {
    currentChat,
    me,
    contacts,
    setContacts,
    chats,
    setGroups,
    clearCurrentChat,
  } = useAppStore();
  const [members, setMembers] = useState([]);
  const [inviteInput, setInviteInput] = useState('');

  const groupId = currentChat?.id;

  useEffect(() => {
    if (groupId) {
      loadMembers();
      if (!contacts || contacts.length === 0) {
        getContacts()
          .then((data) => setContacts(data))
          .catch((e) => console.error('Ошибка загрузки контактов:', e));
      }
    }
  }, [groupId]);

  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose();
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onClose]);

  async function loadMembers() {
    try {
      const data = await getGroupMembers(groupId);
      const list = data?.members || (Array.isArray(data) ? data : []);
      setMembers(list);
    } catch (e) {
      setMembers([]);
      toast.error(e.message);
    }
  }

  // УНИВЕРСАЛЬНЫЙ ПОИСК ИМЕНИ
  const getName = (obj) => {
    // 1. Если имя есть в самом объекте
    if (obj?.username && obj.username !== 'Неизвестный') return obj.username;

    // 2. Если нет, ищем в списке чатов (Sidebar) по ID
    const userId = obj?.contact_user_id || obj?.user_id || obj?.id;
    const foundInChats = (chats || []).find((c) => c.other_user_id === userId);
    if (foundInChats?.name) return foundInChats.name;

    // 3. Крайний случай
    return userId ? `Юзер #${userId}` : 'Неизвестный';
  };

  const getUserId = (obj) => obj?.contact_user_id || obj?.user_id || obj?.id;

  async function doInvite(contact) {
    const userId = getUserId(contact);
    const username = getName(contact);

    if (!userId && !inviteInput) return;

    try {
      if (userId) {
        await inviteMember(groupId, userId);
      } else {
        const found = (contacts || []).find(
          (c) => getName(c).toLowerCase() === inviteInput.trim().toLowerCase(),
        );
        if (found) {
          await inviteMember(groupId, getUserId(found));
        } else {
          toast.error('Пользователь не найден');
          return;
        }
      }
      setInviteInput('');
      toast.success(`Добавлен`);
      await loadMembers();
    } catch (e) {
      toast.error(e.message);
    }
  }

  async function doRemove(uId, uName) {
    if (!confirm(`Удалить ${uName} из группы?`)) return;
    try {
      await removeMember(groupId, uId);
      toast.success(`${uName} удалён`);
      await loadMembers();
    } catch (e) {
      toast.error(e.message);
    }
  }

  async function doLeave() {
    if (!confirm(`Покинуть группу?`)) return;
    try {
      await leaveGroup(groupId, me?.id);
      const updated = await getGroups();
      setGroups(updated);
      clearCurrentChat();
      onClose();
    } catch (e) {
      toast.error(e.message);
    }
  }

  async function doDelete() {
    if (!confirm(`Удалить группу необратимо?`)) return;
    try {
      await deleteGroup(groupId);
      const updated = await getGroups();
      setGroups(updated);
      clearCurrentChat();
      onClose();
    } catch (e) {
      toast.error(e.message);
    }
  }

  const safeMembers = Array.isArray(members) ? members : [];
  const safeContacts = Array.isArray(contacts) ? contacts : [];
  const myMember = safeMembers.find((m) => getUserId(m) === me?.id);
  const isAdmin = myMember?.role === 'admin';
  const memberIds = new Set(safeMembers.map((m) => getUserId(m)));
  const available = safeContacts.filter((c) => !memberIds.has(getUserId(c)));

  return (
    <div
      className={styles.overlay}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className={styles.modal}>
        <div className={styles.header}>
          <span className={styles.title}>{currentChat?.name || 'Группа'}</span>
          <button className={styles.closeBtn} onClick={onClose}>
            ✕
          </button>
        </div>

        <div className={styles.sectionTitle}>
          Участники ({safeMembers.length})
        </div>
        <div className={styles.memberList}>
          {safeMembers.map((m) => {
            const uId = getUserId(m);
            const uName = getName(m);
            return (
              <div key={uId} className={styles.member}>
                <div className={styles.avatar}>{initials(uName)}</div>
                <span className={styles.memberName}>
                  {uName}
                  {m.role === 'admin' && (
                    <span className={styles.adminBadge}>admin</span>
                  )}
                </span>
                {uId === me?.id ? (
                  <span className={styles.youLabel}>вы</span>
                ) : (
                  isAdmin && (
                    <button
                      className={styles.removeBtn}
                      onClick={() => doRemove(uId, uName)}
                    >
                      ✕
                    </button>
                  )
                )}
              </div>
            );
          })}
        </div>

        {available.length > 0 && (
          <>
            <div className={styles.sectionTitle}>Добавить из контактов</div>
            <div className={styles.pickerList}>
              {available.map((c) => {
                const uName = getName(c);
                return (
                  <button
                    key={getUserId(c)}
                    className={styles.pickerItem}
                    onClick={() => doInvite(c)}
                  >
                    <div className={styles.avatar}>{initials(uName)}</div>
                    <span className={styles.pickerName}>{uName}</span>
                    <span className={styles.addLabel}>+ добавить</span>
                  </button>
                );
              })}
            </div>
          </>
        )}

        <div className={styles.footerActions}>
          <button className={styles.leaveBtn} onClick={doLeave}>
            Покинуть группу
          </button>
          {isAdmin && (
            <button className={styles.deleteBtn} onClick={doDelete}>
              🗑 Удалить
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
