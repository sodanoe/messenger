import { useEffect, useRef, useState } from 'react';
import { api } from '../../../../services/api';
import styles from './ReactionPicker.module.css';

const STANDARD_EMOJIS = ['👍', '❤️', '😂', '😮', '😢', '😡'];

export default function ReactionPicker({ onReact, onClose, position }) {
  const ref = useRef(null);
  const [customEmojis, setCustomEmojis] = useState([]);

  useEffect(() => {
    api('/emojis/', 'GET')
      .then((data) => setCustomEmojis(data.emojis || []))
      .catch(console.error);
  }, []);

  useEffect(() => {
    const onClick = (e) => {
      if (ref.current && !ref.current.contains(e.target)) onClose();
    };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, [onClose]);

  return (
    <div
      ref={ref}
      className={styles.picker}
      style={{ position: 'fixed', top: position.top, left: position.left, zIndex: 1000 }}
    >
      <div className={styles.row}>
        {STANDARD_EMOJIS.map((emoji) => (
          <button key={emoji} className={styles.btn} onClick={() => onReact(emoji)}>
            {emoji}
          </button>
        ))}
        {customEmojis.map((e) => (
          <button
            key={e.id}
            className={styles.btn}
            title={`:${e.shortcode}:`}
            onClick={() => onReact(`:${e.shortcode}:`)}
          >
            <img src={e.url} alt={e.shortcode} className={styles.customImg} />
          </button>
        ))}
      </div>
    </div>
  );
}