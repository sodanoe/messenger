import { useEffect, useRef, useState } from 'react';
import Picker from '@emoji-mart/react';
import emojiData from '@emoji-mart/data';
import { api } from '../../../../services/api';
import styles from './QuickEmojiBar.module.css';
import toast from 'react-hot-toast';

export default function QuickEmojiBar({ onSelect, onClose, position }) {
  const ref = useRef(null);
  const fileInputRef = useRef(null);
  const [customEmojis, setCustomEmojis] = useState([]);

  useEffect(() => {
    loadEmojis();
  }, []);

  async function loadEmojis() {
    try {
      const data = await api('/emojis/', 'GET');
      const emojis = data.emojis || [];
      setCustomEmojis([{
        id: 'custom',
        name: 'Стикеры',
        emojis: emojis.map((e) => ({
          id: e.shortcode,
          name: e.shortcode,
          keywords: [e.shortcode],
          skins: [{ src: e.url }],
        })),
      }]);
    } catch (e) {
      console.error(e);
    }
  }

  const handleUpload = async (ev) => {
    const file = ev.target.files[0];
    if (!file) return;
    const shortcode = prompt('Короткое имя (например: cat_dance):');
    if (!shortcode) return;
    const formData = new FormData();
    formData.append('file', file);
    formData.append('shortcode', shortcode);
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL || ''}/emojis/`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${localStorage.getItem('msng_token')}` },
        body: formData,
      });
      if (res.ok) { toast.success('Загружено!'); loadEmojis(); }
      else toast.error('Ошибка загрузки');
    } catch { toast.error('Ошибка сети'); }
  };

  useEffect(() => {
    const onClick = (e) => {
      if (ref.current && !ref.current.contains(e.target)) onClose();
    };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, [onClose]);

  const handleSelect = (emoji) => {
    // Вставляем в текст — для кастомных shortcode, для стандартных native
    if (emoji.src) {
      onSelect(`:${emoji.id}:`);
    } else {
      onSelect(emoji.native);
    }
    onClose();
  };

  return (
    <div
      ref={ref}
      style={{ position: 'fixed', top: position.top, left: position.left, zIndex: 1000 }}
    >
      <Picker
        data={emojiData}
        custom={customEmojis}
        onEmojiSelect={handleSelect}
        theme="dark"
        locale="ru"
        previewPosition="none"
        skinTonePosition="none"
        maxFrequentRows={1}
      />
      <div className={styles.uploadRow}>
        <button className={styles.uploadBtn} onClick={() => fileInputRef.current.click()}>
          ➕ Загрузить стикер
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