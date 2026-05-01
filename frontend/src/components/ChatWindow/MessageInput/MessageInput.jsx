import { useRef, useState, useEffect } from 'react';
import useAppStore from '../../../store/useAppStore';
import { sendDM } from '../../../services/contacts';
import { sendGroupMessage } from '../../../services/groups';
import { useMediaUpload } from '../../../hooks/useMediaUpload';
import QuickEmojiBar from './QuickEmojiBar/QuickEmojiBar';
import toast from 'react-hot-toast';
import styles from './MessageInput.module.css';

export default function MessageInput() {
  const inputRef = useRef(null);
  const { currentChat, me, replyTo, clearReplyTo, addMessage, updateChatLastMessage, customEmojis, setInputRef } = useAppStore();
  const { pendingMedia, isUploading, handleFile, removePending } = useMediaUpload();
  const [emojiBarOpen, setEmojiBarOpen] = useState(false);
  const [emojiBarPos, setEmojiBarPos] = useState({ top: 0, left: 0 });

  useEffect(() => {
    setInputRef(inputRef);
    return () => setInputRef(null);
  }, []);

  function autoGrow() {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 120) + 'px';
  }

  const formatSnippet = (text) => {
    if (!text) return '';
    const parts = text.split(/(:[a-zA-Z0-9_]+:)/g);
    return parts.map((part, i) => {
      if (part.startsWith(':') && part.endsWith(':')) {
        const code = part.slice(1, -1);
        const found = customEmojis.find((e) => e.shortcode === code);
        if (found) {
          return <img key={i} src={found.url} style={{ height: 16, width: 16, verticalAlign: 'middle', objectFit: 'contain', margin: '0 1px' }} alt={part} />;
        }
      }
      return part;
    });
  };

  function handleEmojiBtn(e) {
    const pickerHeight = 450;
    const pickerWidth = 352;
    const margin = 16;
    const isMobile = window.innerWidth < 768;

    if (isMobile) {
      setEmojiBarPos({
        top: (window.innerHeight - pickerHeight) / 2,
        left: (window.innerWidth - pickerWidth) / 2,
      });
    } else {
      const rect = e.currentTarget.getBoundingClientRect();
      let top = rect.top - pickerHeight - margin;
      let left = rect.left + rect.width / 2 - pickerWidth / 2;
      if (left + pickerWidth > window.innerWidth - margin) left = window.innerWidth - pickerWidth - margin;
      if (left < margin) left = margin;
      setEmojiBarPos({ top, left });
    }
    setEmojiBarOpen(true);
  }

  function handleEmojiSelect(emoji) {
    const el = inputRef.current;
    if (!el) return;
    const start = el.selectionStart;
    const end = el.selectionEnd;
    el.value = el.value.slice(0, start) + emoji + el.value.slice(end);
    el.selectionStart = el.selectionEnd = start + emoji.length;
    el.focus();
    autoGrow();
  }

  async function sendMessage() {
    if (!currentChat) return;
    if (isUploading) return;
    const content = inputRef.current?.value.trim() || '';
    if (!content && !pendingMedia) return;

    if (inputRef.current) {
      inputRef.current.value = '';
      autoGrow();
      inputRef.current.focus();
    }

    const sentReplyTo = replyTo ? { ...replyTo } : null;
    const sentMedia = pendingMedia ? { ...pendingMedia } : null;
    clearReplyTo();
    removePending();

    try {
      let result;
      if (currentChat.type === 'dm') {
        result = await sendDM(currentChat.id, content, sentMedia?.id || null, sentReplyTo?.id || null);
      } else {
        result = await sendGroupMessage(currentChat.id, content, sentMedia?.id || null, sentReplyTo?.id || null);
      }

      if (result) {
        addMessage({
          id: result.id,
          content: result.content || result.content_encrypted || content,
          content_encrypted: result.content_encrypted || null,
          sender_id: me?.id,
          created_at: result.created_at || new Date().toISOString(),
          media_url: result.media_url || sentMedia?.url || null,
          reply_to: result.reply_to || null,
          reactions: [],
          read_at: null,
        });
        updateChatLastMessage(
          currentChat.id,
          sentMedia && !content ? '🖼 Фотография' : content,
          result.created_at || new Date().toISOString(),
        );
      }
    } catch (e) {
      toast.error(e.message + ' (сообщение не доставлено)');
      if (inputRef.current) inputRef.current.value = content;
    }
  }

  function handleKey(e) {
    const isMobile = window.innerWidth < 768;
    if (e.key === 'Enter') {
      if (!isMobile && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    }
  }

  function onFileChange(e) {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
    e.target.value = '';
  }

  function onDragOver(e) {
    e.preventDefault();
    if ([...(e.dataTransfer?.types || [])].includes('Files'))
      e.currentTarget.classList.add(styles.dragOver);
  }
  function onDragLeave(e) {
    if (e.currentTarget.contains(e.relatedTarget)) return;
    e.currentTarget.classList.remove(styles.dragOver);
  }
  function onDrop(e) {
    e.preventDefault();
    e.currentTarget.classList.remove(styles.dragOver);
    const f = e.dataTransfer?.files?.[0];
    if (f && f.type.startsWith('image/')) handleFile(f);
  }

  return (
    <div className={styles.wrap} onDragOver={onDragOver} onDragLeave={onDragLeave} onDrop={onDrop}>
      {replyTo && (
        <div className={styles.replyPreview}>
          <span className={styles.replyIcon}>↩</span>
          <span className={styles.replyText}>
            {replyTo.senderName}: {replyTo.content ? formatSnippet(replyTo.content) : replyTo.mediaUrl ? '📷 Фото' : '—'}
          </span>
          <button className={styles.replyClose} onClick={clearReplyTo}>✕</button>
        </div>
      )}

      {pendingMedia?.previewUrl && (
        <div className={styles.mediaPreview}>
          <img
            src={pendingMedia.previewUrl}
            alt="preview"
            style={{ opacity: isUploading ? 0.5 : 1 }}
          />
          {isUploading ? (
            <div className={styles.uploadingOverlay}>
              <div className={styles.spinner} />
            </div>
          ) : (
            <button className={styles.removeMedia} onClick={removePending}>✕</button>
          )}
        </div>
      )}

      <div className={styles.row}>
        <label className={styles.attachBtn} title="Прикрепить картинку">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66L9.41 17.41a2 2 0 01-2.83-2.83l8.49-8.48"/>
          </svg>
          <input type="file" accept="image/jpeg,image/png,image/gif,image/webp" style={{ display: 'none' }} onChange={onFileChange} />
        </label>

        <div className={`${styles.inputArea} ${styles.dragOver}`}>
          <textarea
            ref={inputRef}
            className={styles.textarea}
            rows={1}
            placeholder="Сообщение…"
            onKeyDown={handleKey}
            onInput={autoGrow}
          />
          <button className={styles.emojiBtn} onClick={handleEmojiBtn} title="Эмодзи">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10"/>
              <path d="M8 14s1.5 2 4 2 4-2 4-2"/>
              <line x1="9" y1="9" x2="9.01" y2="9"/>
              <line x1="15" y1="9" x2="15.01" y2="9"/>
            </svg>
          </button>
        </div>

        <button className={styles.sendBtn} onClick={sendMessage} disabled={isUploading}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M5 12h14M12 5l7 7-7 7"/>
          </svg>
        </button>
      </div>

      {emojiBarOpen && (
        <QuickEmojiBar
          position={emojiBarPos}
          onSelect={handleEmojiSelect}
          onClose={() => setEmojiBarOpen(false)}
        />
      )}
    </div>
  );
}