import { useEffect, useRef, useState } from 'react';
import { api } from '../../../../services/api';
import styles from './ReactionPicker.module.css';
import toast from 'react-hot-toast';

const STANDART_EMOJIS = ['👍', '❤️', '😂', '😮', '😢', '😡'];

export default function ReactionPicker({ onReact, onClose, position }) {
  const ref = useRef(null);
  const fileInputRef = useRef(null);
  const [customEmojis, setCustomEmojis] = useState([]);

  useEffect(() => {
    loadEmojis();
  }, []);

  async function loadEmojis() {
    try {
      const data = await api('/emojis/', 'GET');
      setCustomEmojis(data.emojis || []);
    } catch (e) {
      console.error(e);
    }
  }

  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const shortcode = prompt("Введите короткое имя для эмодзи (например: cat_dance):");
    if (!shortcode) return;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('shortcode', shortcode);

    try {
      // Используем fetch напрямую для FormData, если обертка api не настроена на multipart
      const response = await fetch(`${import.meta.env.VITE_API_URL || ''}/emojis/`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}` // Укажи свой способ получения токена
        },
        body: formData
      });

      if (response.ok) {
        toast.success("Эмодзи загружен!");
        loadEmojis(); // Перезагружаем список
      } else {
        toast.error("Ошибка при загрузке");
      }
    } catch (err) {
      toast.error("Ошибка сети");
    }
  };

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
      style={{
        position: 'fixed',
        top: position.top,
        left: position.left,
        zIndex: 1000,
      }}
    >
      <div className={styles.section}>
        {STANDART_EMOJIS.map((emoji) => (
          <button key={emoji} className={styles.btn} onClick={() => onReact(emoji)}>
            {emoji}
          </button>
        ))}
      </div>

      <div className={styles.customSection}>
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
        
        {/* Кнопка добавления */}
        <button 
          className={styles.addBtn} 
          onClick={() => fileInputRef.current.click()}
          title="Загрузить свой эмодзи"
        >
          ➕
        </button>
        <input 
          type="file" 
          ref={fileInputRef} 
          onChange={handleUpload} 
          style={{ display: 'none' }} 
          accept="image/*"
        />
      </div>
    </div>
  );
}
