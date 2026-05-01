import { useEffect, useRef, useCallback } from 'react';
import useAppStore from '../../../store/useAppStore';
import { getMessages } from '../../../services/contacts';
import { getGroupMessages } from '../../../services/groups';
import MessageItem from '../MessageItem/MessageItem';
import { fmtDay } from '../../../utils/format';
import styles from './MessageList.module.css';

export default function MessageList() {
  const messages = useAppStore((s) => s.messages);
  const nextCursor = useAppStore((s) => s.nextCursor);
  const hasMore = useAppStore((s) => s.hasMore);
  const currentChat = useAppStore((s) => s.currentChat);
  const prependMessages = useAppStore((s) => s.prependMessages);
  const bottomRef = useRef(null);
  const wrapRef = useRef(null);
  const isLoadingRef = useRef(false);
  const prevLengthRef = useRef(0);

  // Сброс prevLength при смене чата
  useEffect(() => {
    prevLengthRef.current = 0;
  }, [currentChat?.id]);

  // Скролл вниз только при новых сообщениях в конце (не при prepend)
  useEffect(() => {
    const prevLength = prevLengthRef.current;
    prevLengthRef.current = messages.length;
    if (messages.length > prevLength && !isLoadingRef.current) {
      requestAnimationFrame(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'instant' });
        setTimeout(() => {
          bottomRef.current?.scrollIntoView({ behavior: 'instant' });
        }, 100);
      });
    }
  }, [messages.length]);

  const loadMore = useCallback(async () => {
    if (!hasMore || !nextCursor || !currentChat || isLoadingRef.current) return;
    isLoadingRef.current = true;

    const wrap = wrapRef.current;
    const prevScrollHeight = wrap?.scrollHeight ?? 0;

    try {
      let data;
      if (currentChat.type === 'direct') {
        data = await getMessages(currentChat.id, nextCursor);
      } else {
        data = await getGroupMessages(currentChat.id, nextCursor);
      }

      prependMessages([...data.messages].reverse(), data.next_cursor);

      requestAnimationFrame(() => {
        if (wrap) {
          wrap.scrollTop = wrap.scrollHeight - prevScrollHeight;
        }
      });
    } catch {
      // silent
    } finally {
      isLoadingRef.current = false;
    }
  }, [hasMore, nextCursor, currentChat, prependMessages]);

  useEffect(() => {
    const wrap = wrapRef.current;
    if (!wrap) return;
    const onScroll = () => {
      if (wrap.scrollTop < 80) {
        loadMore();
      }
    };
    wrap.addEventListener('scroll', onScroll);
    return () => wrap.removeEventListener('scroll', onScroll);
  }, [loadMore]);

  const grouped = [];
  let lastDay = null;
  for (const m of messages) {
    const day = fmtDay(m.created_at);
    if (day !== lastDay) {
      grouped.push({ type: 'divider', day, key: `d-${m.created_at}` });
      lastDay = day;
    }
    grouped.push({
      type: 'message',
      msg: m,
      key: m.id ?? `tmp-${m.created_at}`,
    });
  }

  return (
    <div ref={wrapRef} className={styles.wrap}>
      {hasMore && (
        <div className={styles.loadingMore}>Загрузка...</div>
      )}
      {grouped.map((item) =>
        item.type === 'divider' ? (
          <div key={item.key} className={styles.dayDivider}>
            {item.day}
          </div>
        ) : (
          <MessageItem key={item.key} message={item.msg} />
        ),
      )}
      <div ref={bottomRef} />
    </div>
  );
}