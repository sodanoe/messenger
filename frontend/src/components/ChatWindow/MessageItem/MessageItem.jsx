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
  const { me, currentChat, setReplyTo, addToMsgStore, removeMessage, updateChatLastMessage, customEmojis } = useAppStore();
  const [pickerState, setPickerState] = useState({ open: false, top: 0, left: 0 });
  const [lightboxUrl, setLightboxUrl] = useState(null);
  const rowRef = useRef(null);

  const isMe = message.sender_id === me?.id;

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

  const trimmed = message.content?.trim() || '';
  const isSingleCustomEmoji = /^:[a-zA-Z0-9_]+:$/.test(trimmed);
  const isSingleUnicodeEmoji = trimmed.length > 0 && /^\p{Emoji}$/u.test(trimmed);
  const isSingleEmoji = (isSingleCustomEmoji || isSingleUnicodeEmoji) && !message.media_url;

  function handleReply() {
    setReplyTo({
      id: message.id,
      senderId: message.sender_id,
      senderName: isMe ? 'Вы' : message.sender_username || currentChat?.name,
      content: message.content || '',
      mediaUrl: message.media_url || null,
    });
  }

  function handleScrollToReply() {
    if (!replyTo?.id) return;
    const el = document.querySelector(`[data-msg-id="${replyTo.id}"]`);
    if (!el) return;
    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    el.classList.add(styles.highlight);
    setTimeout(() => el.classList.remove(styles.highlight), 1000);
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
    const pickerWidth = Math.min(320, window.innerWidth - 32);
    const margin = 12;
    const rect = e.currentTarget.getBoundingClientRect();
    let top = rect.top - pickerHeight - margin;
    if (top < margin) top = rect.bottom + margin;
    let left = rect.left + rect.width / 2 - pickerWidth / 2;
    if (left + pickerWidth > window.innerWidth - margin) left = window.innerWidth - pickerWidth - margin;
    if (left < margin) left = margin;
    setPickerState({ open: true, top, left });
  };

  const mediaUrl = message.media_url
    ? message.media_url.startsWith('http') ? message.media_url : API_BASE() + message.media_url
    : null;

  const replyTo = message.reply_to;
  const replyAuthor = replyTo
    ? replyTo.sender_id === me?.id ? 'Вы' : currentChat?.name || `#${replyTo.sender_id}`
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

  const mediaOnly = mediaUrl && !message.content && !replyTo;

  return (
    <>
      <div
        ref={rowRef}
        className={`${styles.row} ${isMe ? styles.me : styles.other}`}
        data-msg-id={message.id}
        onContextMenu={(e) => { e.preventDefault(); handleDelete(); }}
      >
        <div className={styles.bubbleWrap}>
          <div className={styles.bubbleRow}>
            {message.id && (
              <button className={styles.replyBtn} title="Ответить" onClick={handleReply}>↩</button>
            )}

            <div className={`${styles.bubble} ${isSingleEmoji ? styles.singleEmoji : ''} ${mediaOnly ? styles.mediaBubble : ''}`}>
              {!isMe && currentChat?.type === 'group' && (
                <div className={styles.senderName}>{message.sender_username || '?'}</div>
              )}

              {replyTo && (
                <div className={styles.replyQuote} onClick={handleScrollToReply}>
                  <div className={styles.replyInner}>
                    <span className={styles.replyAuthor}>{replyAuthor}</span>
                    <span className={styles.replyContent}>
                      {replyTo.content
                        ? formatContent(replyTo.content)
                        : replyTo.media_url ? '📷 Фото' : '—'}
                    </span>
                  </div>
                  {replyThumb && <img className={styles.replyThumb} src={replyThumb} alt="фото" />}
                </div>
              )}

              {mediaUrl && (
                <div className={`${styles.media} ${mediaOnly ? styles.mediaOnly : ''}`}>
                  <div className={styles.mediaBlur} style={{ backgroundImage: `url(${mediaUrl})` }} />
                  <img src={mediaUrl} alt="photo" loading="lazy" onClick={() => setLightboxUrl(mediaUrl)} />
                </div>
              )}

              {message.content && (
                <div className={styles.text}>{formatContent(message.content)}</div>
              )}

              <div className={`${styles.meta} ${mediaOnly ? styles.metaOverlay : ''}`}>
                <span className={styles.time}>{fmtTime(message.created_at)}</span>
                {isMe && currentChat?.type === 'direct' && (
                  <span className={`${styles.status} ${message.read_at ? styles.read : ''}`}>
                    {message.read_at ? '✓✓' : '✓'}
                  </span>
                )}
              </div>
            </div>

            {message.id && (
              <button className={styles.reactBtn} onClick={handleOpenPicker}>+</button>
            )}
          </div>

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