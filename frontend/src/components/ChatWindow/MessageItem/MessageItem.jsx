import { useState, useRef, useEffect } from 'react';
import useAppStore from '../../../store/useAppStore';
import { deleteDM } from '../../../services/contacts';
import { deleteGroupMessage } from '../../../services/groups';
import { api } from '../../../services/api';
import { fmtTime } from '../../../utils/format';
import { API_BASE } from '../../../config';
import ReactionPicker from './ReactionPicker/ReactionPicker';
import toast from 'react-hot-toast';
import styles from './MessageItem.module.css';

export default function MessageItem({ message }) {
  const { me, currentChat, setReplyTo, addToMsgStore, removeMessage, updateChatLastMessage } = useAppStore();
  const [pickerState, setPickerState] = useState({ open: false, top: 0, left: 0 });
  const [lightboxUrl, setLightboxUrl] = useState(null);
  const [customEmojis, setCustomEmojis] = useState([]);
  const rowRef = useRef(null);

  const isMe = message.sender_id === me?.id;

  useEffect(() => {
    api('/emojis/', 'GET')
      .then((data) => setCustomEmojis(data.emojis || []))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (message.id) {
      addToMsgStore(message.id, {
        id: message.id,
        senderName: isMe ? 'Вы' : message.sender_username || currentChat?.name || `#${message.sender_id}`,
        content: message.content || '',
        mediaUrl: message.media_url || null,
      });
    }
  }, [message.id, isMe, currentChat, addToMsgStore]);

  const formatContent = (text) => {
    if (!text) return '';
    const parts = text.split(/(:[a-zA-Z0-9_]+:)/g);
    return parts.map((part, i) => {
      if (part.startsWith(':') && part.endsWith(':')) {
        const code = part.slice(1, -1);
        const found = customEmojis.find((e) => e.shortcode === code);
        if (found) {
          return <img key={i} src={found.url} className={styles.inlineEmoji} alt={part} title={part} />;
        }
      }
      return part;
    });
  };

  function handleReply() {
    setReplyTo({
      id: message.id,
      senderId: message.sender_id,
      senderName: isMe ? 'Вы' : message.sender_username || currentChat?.name,
      content: message.content || '',
      mediaUrl: message.media_url || null,
    });
  }

  async function handleDelete() {
    if (!confirm('Удалить сообщение?')) return;
    try {
      if (currentChat.type === 'direct') {
        await deleteDM(currentChat.id, message.id);
      } else {
        await deleteGroupMessage(currentChat.id, message.id);
      }
      removeMessage(message.id);
      const remaining = useAppStore.getState().messages.filter((m) => m.id !== message.id);
      const lastMsg = remaining[remaining.length - 1];
      updateChatLastMessage(
        currentChat.id,
        lastMsg ? (lastMsg.media_url && !lastMsg.content ? '🖼 Фотография' : lastMsg.content || '') : '',
        lastMsg?.created_at || new Date().toISOString(),
      );
    } catch (e) {
      toast.error(e.message);
    }
  }

  async function handleReact(emoji) {
    setPickerState((prev) => ({ ...prev, open: false }));
    const isAlreadySet = (message.reactions || []).some(
      (r) => r.emoji === emoji && r.user_id === me?.id,
    );
    try {
      const baseUrl = `/chats/${currentChat.id}/messages/${message.id}/reactions`;
      if (isAlreadySet) {
        await api(`${baseUrl}/${encodeURIComponent(emoji)}`, 'DELETE');
      } else {
        await api(baseUrl, 'POST', { emoji });
      }
    } catch (e) {
      toast.error(e.message);
    }
  }

  const handleOpenPicker = (e) => {
    const pickerHeight = 60;
    const pickerWidth = 320;
    const margin = 8;
    const isMobile = window.innerWidth < 768;

    if (isMobile) {
      setPickerState({
        open: true,
        top: (window.innerHeight - pickerHeight) / 2,
        left: (window.innerWidth - pickerWidth) / 2,
      });
    } else {
      const rect = e.currentTarget.getBoundingClientRect();
      let top = rect.top - pickerHeight - margin;
      if (top < margin) top = rect.bottom + margin;
      let left = rect.left + rect.width / 2 - pickerWidth / 2;
      if (left + pickerWidth > window.innerWidth - margin) left = window.innerWidth - pickerWidth - margin;
      if (left < margin) left = margin;
      setPickerState({ open: true, top, left });
    }
  };

  const mediaUrl = message.media_url
    ? message.media_url.startsWith('http') ? message.media_url : API_BASE() + message.media_url
    : null;

  const replyTo = message.reply_to;
  const replyAuthor = replyTo
    ? replyTo.sender_id === me?.id ? 'Вы' : currentChat?.name || `#${replyTo.sender_id}`
    : null;
  const replySnippet = replyTo
    ? replyTo.content?.trim() ? replyTo.content.slice(0, 80) : replyTo.media_url ? '📷 Фото' : '—'
    : null;
  const replyThumb = replyTo?.media_url
    ? replyTo.media_url.startsWith('http') ? replyTo.media_url : API_BASE() + replyTo.media_url
    : null;

  const reactions = message.reactions || [];
  const grouped = {};
  reactions.forEach((r) => {
    if (!grouped[r.emoji]) grouped[r.emoji] = { count: 0, mine: false };
    grouped[r.emoji].count++;
    if (r.user_id === me?.id) grouped[r.emoji].mine = true;
  });

  return (
    <>
      <div
        ref={rowRef}
        className={`${styles.row} ${isMe ? styles.me : styles.other}`}
        data-msg-id={message.id}
        onContextMenu={(e) => { e.preventDefault(); handle