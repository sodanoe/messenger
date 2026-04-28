import { useRef } from 'react';
import useAppStore from '../../../store/useAppStore';
import { sendDM } from '../../../services/contacts';
import { sendGroupMessage } from '../../../services/groups';
import { useMediaUpload } from '../../../hooks/useMediaUpload';
import toast from 'react-hot-toast';
import styles from './MessageInput.module.css';

export default function MessageInput() {
  const inputRef = useRef(null);
  const { currentChat, me, replyTo, clearReplyTo, addMessage, updateChatLastMessage } = useAppStore();
  const { pendingMedia, handleFile, removePending } = useMediaUpload();

  function autoGrow() {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 120) + 'px';
  }

  async function sendMessage() {
    if (!currentChat) return;
    const content = inputRef.current?.value.trim() || '';
    if (!content && !pendingMedia) return;

    if (inputRef.current) inputRef.current.value = '';
    autoGrow();

    const sentReplyTo = replyTo ? { ...replyTo } : null;
    const sentMedia = pendingMedia ? { ...pendingMedia } : null;
    clearReplyTo();
    removePending();

    try {
      let result;
      if (currentChat.type === 'dm') {
        result = await sendDM(
          currentChat.id,
          content,
          sentMedia?.id || null,
          sentReplyTo?.id || null,
        );
      } else {
        result = await sendGroupMessage(
          currentChat.id,
          content,
          sentMedia?.id || null,
          sentReplyTo?.id || null,
        );
      }

      if (result) {
        addMessage({
          id: result.id,
          content: result.content || result.content_encrypted || content,
          content_encrypted: result.content_encrypted || null,
          sender_id: me?.id,
          created_at: result.created_at || new Date().toISOString(),
          media_url: result.media_url || sentMedia?.url || null,
          // берём reply_to прямо из ответа бэкенда — там уже правильный объект
          reply_to: result.reply_to || null,
          reactions: [],
          read_at: null,
        });

        // Обновляем последнее сообщение в chat-листе
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
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
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

  const replySnippet = replyTo
    ? replyTo.content
      ? replyTo.content.slice(0, 60)
      : replyTo.mediaUrl
        ? '📷 Фото'
        : '—'
    : '';

  const previewUrl = pendingMedia?.previewUrl;

  return (
    <div className={styles.wrap}>
      {replyTo && (
        <div className={styles.replyPreview}>
          <span className={styles.replyIcon}>↩</span>
          <span className={styles.replyText}>
            {replyTo.senderName}: {replySnippet}
          </span>
          <button className={styles.replyClose} onClick={clearReplyTo}>
            ✕
          </button>
        </div>
      )}

      {previewUrl && (
        <div className={styles.mediaPreview}>
          <img src={previewUrl} alt="preview" />
          <button className={styles.removeMedia} onClick={removePending}>
            ✕
          </button>
        </div>
      )}

      <div
        className={styles.inputArea}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
      >
        <label className={styles.attachBtn} title="Прикрепить картинку">
          📎
          <input
            type="file"
            accept="image/jpeg,image/png,image/gif,image/webp"
            style={{ display: 'none' }}
            onChange={onFileChange}
          />
        </label>

        <textarea
          ref={inputRef}
          className={styles.textarea}
          rows={1}
          placeholder="Сообщение… (Enter — отправить)"
          onKeyDown={handleKey}
          onInput={autoGrow}
        />

        <button className={styles.sendBtn} onClick={sendMessage}>
          ➤
        </button>
      </div>
    </div>
  );
}