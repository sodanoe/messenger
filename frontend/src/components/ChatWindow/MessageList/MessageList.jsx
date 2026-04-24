import { useEffect, useRef } from 'react';
import useAppStore from '../../../store/useAppStore';
import MessageItem from '../MessageItem/MessageItem';
import { fmtDay } from '../../../utils/format';
import styles from './MessageList.module.css';

export default function MessageList() {
  const messages = useAppStore((s) => s.messages);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'instant' });
  }, [messages.length]);

  // Group messages by day
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
    <div className={styles.wrap}>
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
