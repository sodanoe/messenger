import { useEffect, useRef } from "react";
import styles from "./ReactionPicker.module.css";

const EMOJIS = ["❤️", "😂", "😮", "😢", "😡", "👍"];

export default function ReactionPicker({ onReact, onClose, isMe }) {
  const ref = useRef(null);

  useEffect(() => {
    function onKey(e) {
      if (e.key === "Escape") onClose();
    }
    function onClick(e) {
      if (ref.current && !ref.current.contains(e.target)) onClose();
    }
    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onClick);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onClick);
    };
  }, []);

  return (
    <div
      ref={ref}
      className={`${styles.picker} ${isMe ? styles.right : styles.left}`}
    >
      {EMOJIS.map((e) => (
        <button key={e} className={styles.btn} onClick={() => onReact(e)}>
          {e}
        </button>
      ))}
    </div>
  );
}
