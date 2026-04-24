import { useState, useEffect } from 'react';
import { uploadMedia } from '../services/api';
import useAppStore from '../store/useAppStore';
import toast from 'react-hot-toast';

export function useMediaUpload() {
  const [pendingMedia, setPendingMedia] = useState(null);
  // pendingMedia: { id, url, previewUrl } | null

  const currentChat = useAppStore((s) => s.currentChat);

  async function handleFile(file) {
    if (!file) return;
    if (file.size > 20 * 1024 * 1024) {
      toast.error('Файл слишком большой (макс 20MB)');
      return;
    }
    const previewUrl = await new Promise((res) => {
      const r = new FileReader();
      r.onload = (e) => res(e.target.result);
      r.readAsDataURL(file);
    });
    try {
      const data = await uploadMedia(file);
      setPendingMedia({ id: data.id, url: data.url, previewUrl });
      toast.success('Картинка готова — нажми отправить');
    } catch (e) {
      toast.error('Ошибка загрузки: ' + e.message);
    }
  }

  function removePending() {
    setPendingMedia(null);
  }

  // Paste
  useEffect(() => {
    function onPaste(e) {
      if (!currentChat) return;
      const items = e.clipboardData?.items;
      if (!items) return;
      for (const item of items) {
        if (item.type.startsWith('image/')) {
          e.preventDefault();
          const f = item.getAsFile();
          if (f) handleFile(f);
          break;
        }
      }
    }
    document.addEventListener('paste', onPaste);
    return () => document.removeEventListener('paste', onPaste);
  }, [currentChat]);

  return { pendingMedia, handleFile, removePending };
}
