// ─────────────────────────────────────────────────────────
//  Media upload
// ─────────────────────────────────────────────────────────

async function onMediaSelected(input) {
  const file = input.files[0]; if (!file) return; input.value = '';
  await uploadMediaFile(file);
}

document.addEventListener('paste', e => {
  if (!currentChat) return;
  const items = e.clipboardData?.items; if (!items) return;
  for (const item of items) {
    if (item.type.startsWith('image/')) { e.preventDefault(); const f = item.getAsFile(); if (f) uploadMediaFile(f); break; }
  }
});

function onDragOver(e)  { e.preventDefault(); if (!currentChat) return; if ([...(e.dataTransfer?.types||[])].includes('Files')) el('chat-input-area').classList.add('drag-over'); }
function onDragLeave(e) { if (el('chat-input-area').contains(e.relatedTarget)) return; el('chat-input-area').classList.remove('drag-over'); }
function onDrop(e)      { e.preventDefault(); el('chat-input-area').classList.remove('drag-over'); if (!currentChat) return; const f = e.dataTransfer?.files?.[0]; if (f && f.type.startsWith('image/')) uploadMediaFile(f); }

async function uploadMediaFile(file) {
  if (file.size > 20 * 1024 * 1024) { toast('Файл слишком большой (макс 20MB)', 'err'); return; }
  const btn = el('attach-btn'); btn.disabled = true; btn.textContent = '⏳';
  try {
    const fd = new FormData(); fd.append('file', file);
    const resp = await fetch(API_BASE() + '/media/upload', { method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: fd });
    if (!resp.ok) { const err = await resp.json(); throw new Error(err.detail || 'Upload failed'); }
    const data = await resp.json();
    pendingMediaId = data.id; pendingMediaUrl = data.url;
    const reader = new FileReader();
    reader.onload = e => {
      const c = el('media-preview-container'); c.style.display = 'block';
      c.innerHTML = `<div class="media-preview"><img src="${e.target.result}" alt="preview"><button class="remove-media" onclick="removePendingMedia()">✕</button></div>`;
    };
    reader.readAsDataURL(file);
    toast('Картинка готова — нажми отправить', 'ok');
  } catch(e) { toast('Ошибка загрузки: ' + e.message, 'err'); }
  finally { btn.disabled = false; btn.textContent = '📎'; }
}

function removePendingMedia() {
  pendingMediaId = null; pendingMediaUrl = null;
  el('media-preview-container').style.display = 'none';
  el('media-preview-container').innerHTML = '';
}
