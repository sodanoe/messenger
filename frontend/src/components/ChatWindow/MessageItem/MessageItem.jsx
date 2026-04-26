import { useState, useRef, useEffect } from 'react';
import useAppStore from '../../../store/useAppStore';
import { reactDM, deleteDM } from '../../../services/contacts';
import { reactGroup, deleteGroupMessage } from '../../../services/groups';
import { api } from '../../../services/api';
import { fmtTime } from '../../../utils/format';
import { API_BASE } from '../../../config';
import ReactionPicker from './ReactionPicker/ReactionPicker';
import toast from 'react-hot-toast';
import styles from './MessageItem.module.css';

export default function MessageItem({ message }) {
  const { me, currentChat, setReplyTo, addToMsgStore, removeMessage } = useAppStore();
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
        senderName: isMe
          ? 'Вы'
          : message.sender_username || currentChat?.name || `#${message.sender_id}`,
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

  const myReaction = Object.keys(grouped).find((e) => grouped[e].mine);
  const reactBtnLabel = myReaction || '+';

  const handleOpenPicker = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const pickerHeight = 350;
    const pickerWidth = 260;
    const margin = 8;
    let top = rect.top - pickerHeight - margin;
    if (top < margin) top = rect.bottom + margin;
    let left = rect.left;
    if (left + pickerWidth > window.innerWidth) left = window.innerWidth - pickerWidth - margin;
    setPickerState({ open: true, top, left });
  };

  return (
    <>
      <div
        ref={rowRef}
        className={`${styles.row} ${isMe ? styles.me : styles.other}`}
        data-msg-id={message.id}
        onContextMenu={(e) => { e.preventDefault(); handleDelete(); }}
      >
        <div className={styles.bubbleWrap}>
          {/* bubbleRow — содержит только пузырь и кнопки позиционирования */}
          <div className={styles.bubbleRow}>
            {message.id && (
              <button className={styles.replyBtn} title="Ответить" onClick={handleReply}>
                ↩
              </button>
            )}

            <div className={styles.bubble}>
              {!isMe && currentChat?.type === 'group' && (
                <div className={styles.senderName}>{message.sender_username || '?'}</div>
              )}

              {replyTo && (
                <div className={styles.replyQuote}>
                  <div className={styles.replyInner}>
                    <span className={styles.replyAuthor}>{replyAuthor}</span>
                    <span className={styles.replyContent}>{replySnippet}</span>
                  </div>
                  {replyThumb && <img className={styles.replyThumb} src={replyThumb} alt="фото" />}
                </div>
              )}

              {mediaUrl && (
                <div className={styles.media}>
                  <img src={mediaUrl} alt="photo" loading="lazy" onClick={() => setLightboxUrl(mediaUrl)} />
                </div>
              )}

              {message.content && (
                <div className={styles.text}>{formatContent(message.content)}</div>
              )}

              <div className={styles.meta}>
                <span className={styles.time}>{fmtTime(message.created_at)}</span>
                {isMe && currentChat?.type === 'direct' && (
                  <span className={`${styles.status} ${message.read_at ? styles.read : ''}`}>
                    {message.read_at ? '✓✓' : '✓'}
                  </span>
                )}
              </div>
            </div>

            {message.id && (
              <button className={styles.reactBtn} title="Реакция" onClick={handleOpenPicker}>
                {reactBtnLabel}
              </button>
            )}
          </div>

          {/* Реакции снаружи пузыря */}
          {Object.keys(grouped).length > 0 && (
            <div className={styles.reactions}>
              {Object.entries(grouped).map(([emoji, { count, mine }]) => {
                const found = customEmojis.find((e) => `:${e.shortcode}:` === emoji);
                return (
                  <span
                    key={emoji}
                    className={`${styles.pill} ${mine ? styles.mine : ''}`}
                    onClick={() => handleReact(emoji)}
                  >
                    {found ? <img src={found.url} className={styles.pillImg} alt={emoji} /> : emoji}
                    {count > 1 && <span className={styles.count}>{count}</span>}
                  </span>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {pickerState.open && (
        <ReactionPicker
          position={{ top: pickerState.top, left: pickerState.left }}
          onReact={handleReact}
          onClose={() => setPickerState((prev) => ({ ...prev, open: false }))}
        />
      )}

      {lightboxUrl && (
        <div className={styles.lightbox} onClick={() => setLightboxUrl(null)}>
          <button className={styles.lightboxClose} onClick={() => setLightboxUrl(null)}>✕</button>
          <img src={lightboxUrl} alt="" onClick={(e) => e.stopPropagation()} />
        </div>
      )}
    </>
  );
}