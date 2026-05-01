import { useState, useEffect } from 'react';
import { uploadMedia } from '../services/api';
import useAppStore from '../store/useAppStore';
import toast from 'react-hot-toast';

export function useMediaUpload() {
  const [pendingMedia, setPendingMedia] = useState(null);
  const [isUploading, setIsUploading] = useState(false);

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

    setIsUploading(true);
    setPendingMedia({ id: null, url: null, previewUrl });

    try {
      const data = await uploadMedia(file);
      setPendingMedia({ id: data.id, url: data.url, previewUrl });
    } catch (e) {
      toast.error('Ошибка загрузки: ' + e.message);
      setPendingMedia(null);
    } finally {
      setIsUploading(false);
    }
  }

  function removePending() {
    setPendingMedia(null);
    setIsUploading(false);
  }

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

  return { pendingMedia, isUploading, handleFile, removePending };
}