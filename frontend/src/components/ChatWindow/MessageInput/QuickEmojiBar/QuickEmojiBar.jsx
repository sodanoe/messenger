import { useEffect, useRef, useState } from 'react';
import Picker from '@emoji-mart/react';
import emojiData from '@emoji-mart/data';
import { api } from '../../../../services/api';
import styles from './QuickEmojiBar.module.css';
import toast from 'react-hot-toast';

export default function QuickEmojiBar({ onSelect, onClose, position }) {
  const ref = useRef(null);
  const fileInputRef = useRef(null);
  const [rawEmojis, setRawEmojis] = useState([]);
  const [customEmojis, setCustomEmojis] = useState([]);
  const [showManager, setShowManager] = useState(false);
  const [shortcode, setShortcode] = useState('');
  const [pendingFile, setPendingFile] = useState(null);
  const [pendingPreview, setPendingPreview] = useState(null);
  const [isDragging, setIsDragging] = useState(false);

  useEffect(() => { loadEmojis(); }, []);

  async function loadEmojis() {
    try {
      const data = await api('/emojis/', 'GET');
      const emojis = data.emojis || [];
      setRawEmojis(emojis);
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

  async function handleDelete(shortcodeToDelete) {
    try {
      await api(`/emojis/${shortcodeToDelete}`, 'DELETE');
      toast.success('Удалено');
      loadEmojis();
    } catch {
      toast.error('Ошибка удаления');
    }
  }

  function handleFileSelect(file) {
    if (!file) return;
    setPendingFile(file);
    const reader = new FileReader();
    reader.onload = (e) => setPendingPreview(e.target.result);
    reader.readAsDataURL(file);
  }

  async function handleUpload() {
    if (!pendingFile || !shortcode.trim()) {
      toast.error('Выбери файл и введи название');
      return;
    }
    const formData = new FormData();
    formData.append('file', pendingFile);
    formData.append('shortcode', shortcode.trim());
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL || ''}/emojis/`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${localStorage.getItem('msng_token')}` },
        body: formData,
      });
      if (res.ok) {
        toast.success('Загружено!');
        setPendingFile(null);
        setPendingPreview(null);
        setShortcode('');
        loadEmojis();
      } else {
        toast.error('Ошибка загрузки');
      }
    } catch {
      toast.error('Ошибка сети');
    }
  }

  useEffect(() => {
    const onClick = (e) => {
      if (ref.current && !ref.current.contains(e.target)) onClose();
    };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, [onClose]);

  const handleSelect = (emoji) => {
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
      {!showManager ? (
        <>
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
            <button className={styles.uploadBtn} onClick={() => setShowManager(true)}>
              + Управление стикерами
            </button>
          </div>
        </>
      ) : (
        <div className={styles.manager}>
          {/* Шапка */}
          <div className={styles.managerHeader}>
            <button className={styles.backBtn} onClick={() => setShowManager(false)}>
              ←
            </button>
            <span>Мои стикеры</span>
          </div>

          {/* Список стикеров */}
          <div className={styles.stickerGrid}>
            {rawEmojis.length === 0 && (
              <div className={styles.empty}>Стикеров пока нет</div>
            )}
            {rawEmojis.map((e) => (
              <div key={e.shortcode} className={styles.stickerItem}>
                <img src={e.url} alt={e.shortcode} className={styles.stickerThumb} />
                <div className={styles.stickerName}>{e.shortcode}</div>
                <button
                  className={styles.deleteBtn}
                  onClick={() => handleDelete(e.shortcode)}
                  title="Удалить"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>

          {/* Разделитель */}
          <div className={styles.divider} />

          {/* Форма добавления */}
          <div className={styles.addSection}>
            <div className={styles.addLabel}>Добавить стикер</div>

            {/* Drag & drop зона */}
            <div
              className={`${styles.dropZone} ${isDragging ? styles.dragging : ''} ${pendingPreview ? styles.hasPreview : ''}`}
              onClick={() => fileInputRef.current.click()}
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setIsDragging(false);
                const f = e.dataTransfer.files[0];
                if (f) handleFileSelect(f);
              }}
            >
              {pendingPreview ? (
                <img src={pendingPreview} alt="preview" className={styles.dropPreview} />
              ) : (
                <>
                  <div className={styles.dropIcon}>
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
                      <polyline points="17 8 12 3 7 8"/>
                      <line x1="12" y1="3" x2="12" y2="15"/>
                    </svg>
                  </div>
                  <div className={styles.dropText}>Нажми или перетащи файл</div>
                  <div className={styles.dropHint}>PNG, JPG, GIF, WebP</div>
                </>
              )}
            </div>
            <input
              type="file"
              ref={fileInputRef}
              onChange={(e) => handleFileSelect(e.target.files[0])}
              style={{ display: 'none' }}
              accept="image/*"
            />

            {/* Поле названия */}
            <input
              type="text"
              className={styles.nameInput}
              placeholder="Название (например: cat_dance)"
              value={shortcode}
              onChange={(e) => setShortcode(e.target.value.replace(/[^a-zA-Z0-9_]/g, ''))}
              onKeyDown={(e) => { if (e.key === 'Enter') handleUpload(); }}
            />

            <button
              className={styles.uploadSubmitBtn}
              onClick={handleUpload}
              disabled={!pendingFile || !shortcode.trim()}
            >
              Загрузить
            </button>
          </div>
        </div>
      )}
    </div>
  );
}