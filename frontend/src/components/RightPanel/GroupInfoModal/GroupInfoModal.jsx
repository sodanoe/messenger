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
import { initials } from '../../../utils/format';
import toast from 'react-hot-toast';
import styles from './GroupInfoModal.module.css';

export default function GroupInfoModal({ onClose }) {
  const { currentChat, me, contacts, setGroups, clearCurrentChat } =
    useAppStore();
  const [members, setMembers] = useState([]);
  const [inviteInput, setInviteInput] = useState('');

  const groupId = currentChat?.id;

  useEffect(() => {
    loadMembers();
  }, []);

  useEffect(() => {
    function onKey(e) {
      if (e.key === 'Escape') onClose();
    }
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, []);

  async function loadMembers() {
    try {
      const data = await getGroupMembers(groupId);
      setMembers(data);
    } catch (e) {
      toast.error(e.message);
    }
  }

  async function doInvite(contact) {
    // contact может быть объектом контакта или строкой username
    const userId = contact?.contact_user_id || null;
    const username = contact?.username || contact;
    if (!username && !userId) return;
    try {
      if (userId) {
        await inviteMember(groupId, userId);
      } else {
        // fallback: ищем по username в contacts
        const found = contacts.find((c) => c.username === username.trim());
        if (found) {
          await inviteMember(groupId, found.contact_user_id);
        } else {
          toast.error('Пользователь не найден в контактах');
          return;
        }
      }
      setInviteInput('');
      toast.success(`${username} добавлен`);
      loadMembers();
    } catch (e) {
      toast.error(e.message);
    }
  }

  async function doRemove(userId, username) {
    if (!confirm(`Удалить ${username} из группы?`)) return;
    try {
      await removeMember(groupId, userId);
      toast.success(`${username} удалён`);
      loadMembers();
    } catch (e) {
      toast.error(e.message);
    }
  }

  async function doLeave() {
    if (!confirm(`Покинуть группу «${currentChat?.name}»?`)) return;
    try {
      await leaveGroup(groupId, me?.id);
      const updated = await getGroups();
      setGroups(updated);
      clearCurrentChat();
      onClose();
      toast.success('Вы покинули группу');
    } catch (e) {
      toast.error(e.message);
    }
  }

  async function doDelete() {
    if (!confirm(`Удалить группу «${currentChat?.name}»? Необратимо.`)) return;
    try {
      await deleteGroup(groupId);
      const updated = await getGroups();
      setGroups(updated);
      clearCurrentChat();
      onClose();
      toast.success('Группа удалена');
    } catch (e) {
      toast.error(e.message);
    }
  }

  const myRole = members.find((m) => m.user_id === me?.id)?.role;
  const isAdmin = myRole === 'admin';
  const memberIds = new Set(members.map((m) => m.user_id));
  const available = contacts.filter((c) => !memberIds.has(c.contact_user_id));

  return (
    <div
      className={styles.overlay}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className={styles.modal}>
        <div className={styles.header}>
          <span className={styles.title}>{currentChat?.name}</span>
          <button className={styles.closeBtn} onClick={onClose}>
            ✕
          </button>
        </div>

        <div className={styles.sectionTitle}>Участники</div>
        <div className={styles.memberList}>
          {members.map((m) => (
            <div key={m.user_id} className={styles.member}>
              <div className={styles.avatar}>{initials(m.username)}</div>
              <span className={styles.memberName}>
                {m.username}
                {m.role === 'admin' && (
                  <span className={styles.adminBadge}>admin</span>
                )}
              </span>
              {m.user_id === me?.id ? (
                <span className={styles.youLabel}>вы</span>
              ) : (
                isAdmin && (
                  <button
                    className={styles.removeBtn}
                    onClick={() => doRemove(m.user_id, m.username)}
                  >
                    ✕
                  </button>
                )
              )}
            </div>
          ))}
        </div>

        {available.length > 0 && (
          <>
            <div className={styles.sectionTitle}>Добавить из контактов</div>
            <div className={styles.pickerList}>
              {available.map((c) => (
                <button
                  key={c.contact_user_id}
                  className={styles.pickerItem}
                  onClick={() => doInvite(c)}
                >
                  <div className={styles.avatar}>{initials(c.username)}</div>
                  <span className={styles.pickerName}>{c.username}</span>
                  <span className={styles.addLabel}>+ добавить</span>
                </button>
              ))}
            </div>
          </>
        )}

        <div className={styles.inviteRow}>
          <input
            className={styles.inviteInput}
            value={inviteInput}
            onChange={(e) => setInviteInput(e.target.value)}
            placeholder="Или введи username"
            onKeyDown={(e) => e.key === 'Enter' && doInvite(inviteInput)}
          />
          <button
            className={styles.inviteBtn}
            onClick={() => doInvite(inviteInput)}
          >
            + Добавить
          </button>
        </div>

        <button className={styles.leaveBtn} onClick={doLeave}>
          Покинуть группу
        </button>
        {isAdmin && (
          <button className={styles.deleteBtn} onClick={doDelete}>
            🗑 Удалить группу
          </button>
        )}
      </div>
    </div>
  );
}
