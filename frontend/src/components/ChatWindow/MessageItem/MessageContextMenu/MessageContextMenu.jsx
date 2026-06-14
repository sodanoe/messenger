import { useEffect, useRef } from 'react';
import styles from './MessageContextMenu.module.css';

function CopyIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="3 6 5 6 21 6" />
      <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
      <path d="M10 11v6M14 11v6" />
      <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
    </svg>
  );
}

export default function MessageContextMenu({ position, onCopy, onDelete, canCopy = true, onClose }) {
  const ref = useRef(null);

  useEffect(() => {
    const handleOutside = (e) => {
      if (ref.current && !ref.current.contains(e.target)) onClose();
    };
    const handleKey = (e) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('click', handleOutside);
    document.addEventListener('contextmenu', handleOutside);
    document.addEventListener('keydown', handleKey);
    return () => {
      document.removeEventListener('click', handleOutside);
      document.removeEventListener('contextmenu', handleOutside);
      document.removeEventListener('keydown', handleKey);
    };
  }, [onClose]);

  return (
    <div
      ref={ref}
      className={styles.menu}
      style={{ position: 'fixed', top: position.top, left: position.left, zIndex: 1000 }}
    >
      {canCopy && (
        <button className={styles.item} onClick={onCopy}>
          <CopyIcon />
          <span>Скопировать</span>
        </button>
      )}
      <button className={`${styles.item} ${styles.danger}`} onClick={onDelete}>
        <TrashIcon />
        <span>Удалить</span>
      </button>
    </div>
  );
}