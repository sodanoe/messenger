import { useState, useRef, useEffect } from "react";
import useAppStore from "../../../store/useAppStore";
import { reactDM, deleteDM } from "../../../services/contacts";
import { reactGroup, deleteGroupMessage } from "../../../services/groups";
import { fmtTime } from "../../../utils/format";
import { API_BASE } from "../../../config";
import ReactionPicker from "./ReactionPicker/ReactionPicker";
import toast from "react-hot-toast";
import styles from "./MessageItem.module.css";

export default function MessageItem({ message }) {
  const { me, currentChat, setReplyTo, addToMsgStore, removeMessage } = useAppStore();
  const [pickerOpen, setPickerOpen] = useState(false);
  const [lightboxUrl, setLightboxUrl] = useState(null);
  const rowRef = useRef(null);

  const isMe = message.sender_id === me?.id;

  useEffect(() => {
    if (message.id) {
      addToMsgStore(message.id, {
        id: message.id,
        senderName: isMe
          ? "Вы"
          : message.sender_username || currentChat?.name || `#${message.sender_id}`,
        content: message.content || "",
        mediaUrl: message.media_url || null,
      });
    }
  }, [message.id]);

  function handleReply() {
    setReplyTo({
      id: message.id,
      senderName: isMe ? "Вы" : message.sender_username || currentChat?.name,
      content: message.content || "",
      mediaUrl: message.media_url || null,
    });
  }

  async function handleDelete() {
    if (!confirm("Удалить сообщение?")) return;
    try {
      if (currentChat.type === "dm") {
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
    setPickerOpen(false);
    try {
      if (currentChat.type === "dm") {
        await reactDM(currentChat.id, message.id, emoji);
      } else {
        await reactGroup(currentChat.id, message.id, emoji);
      }
    } catch (e) {
      toast.error(e.message);
    }
  }

  const mediaUrl = message.media_url
    ? message.media_url.startsWith("http")
      ? message.media_url
      : API_BASE() + message.media_url
    : null;

  const replyTo = message.reply_to;
  const replyAuthor = replyTo
    ? replyTo.sender_id === me?.id ? "Вы" : currentChat?.name || `#${replyTo.sender_id}`
    : null;
  const replySnippet = replyTo
    ? replyTo.content?.trim()
      ? replyTo.content.slice(0, 80)
      : replyTo.media_url ? "📷 Фото" : "—"
    : null;
  const replyThumb = replyTo?.media_url
    ? replyTo.media_url.startsWith("http") ? replyTo.media_url : API_BASE() + replyTo.media_url
    : null;

  const reactions = message.reactions || [];
  const grouped = {};
  reactions.forEach((r) => {
    if (!grouped[r.emoji]) grouped[r.emoji] = { count: 0, mine: false };
    grouped[r.emoji].count++;
    if (r.user_id === me?.id) grouped[r.emoji].mine = true;
  });

  const myReaction = Object.keys(grouped).find((e) => grouped[e].mine);
  const reactBtnLabel = myReaction || "+";

  return (
    <>
      <div
        ref={rowRef}
        className={`${styles.row} ${isMe ? styles.me : styles.other}`}
        data-msg-id={message.id}
        onContextMenu={(e) => { e.preventDefault(); handleDelete(); }}
      >
        <div className={styles.bubbleWrap}>
          {message.id && (
            <button className={styles.replyBtn} title="Ответить" onClick={handleReply}>
              ↩
            </button>
          )}

          <div className={styles.bubble}>
            {!isMe && currentChat?.type === "group" && (
              <div className={styles.senderName}>{message.sender_username || "?"}</div>
            )}

            {replyTo && (
              <div className={styles.replyQuote}>
                <div className={styles.replyInner}>
                  <span className={styles.replyAuthor}>{replyAuthor}</span>
                  <span className={styles.replyContent}>{replySnippet}</span>
                </div>
                {replyThumb && (
                  <img className={styles.replyThumb} src={replyThumb} alt="фото" />
                )}
              </div>
            )}

            {mediaUrl && (
              <div className={styles.media}>
                <img src={mediaUrl} alt="photo" loading="lazy" onClick={() => setLightboxUrl(mediaUrl)} />
              </div>
            )}

            {message.content && (
              <div className={styles.text}>{message.content}</div>
            )}

            {Object.keys(grouped).length > 0 && (
              <div className={styles.reactions}>
                {Object.entries(grouped).map(([emoji, { count, mine }]) => (
                  <span
                    key={emoji}
                    className={`${styles.pill} ${mine ? styles.mine : ""}`}
                    onClick={() => handleReact(emoji)}
                  >
                    {emoji}
                    {count > 1 && <span className={styles.count}>{count}</span>}
                  </span>
                ))}
              </div>
            )}

            <div className={styles.meta}>
              <span className={styles.time}>{fmtTime(message.created_at)}</span>
              {isMe && currentChat?.type === "dm" && (
                <span className={`${styles.status} ${message.read_at ? styles.read : ""}`}>
                  {message.read_at ? "✓✓" : "✓"}
                </span>
              )}
            </div>
          </div>

          {message.id && (
            <button className={styles.reactBtn} title="Реакция" onClick={() => setPickerOpen(true)}>
              {reactBtnLabel}
            </button>
          )}
        </div>
      </div>

      {pickerOpen && (
        <ReactionPicker
          onReact={handleReact}
          onClose={() => setPickerOpen(false)}
          anchorRef={rowRef}
          isMe={isMe}
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