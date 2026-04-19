// ─────────────────────────────────────────────────────────
//  Custom Emoji
// ─────────────────────────────────────────────────────────

let customEmojis = [];

// Загрузить кастомные эмодзи с сервера
async function loadCustomEmojis() {
    try {
        const data = await api('/emojis/');
        customEmojis = data.emojis || [];
        renderCustomEmojiButtons();
    } catch (e) {
        console.error('Failed to load custom emojis:', e);
    }
}

// Отрисовать кнопки кастомных эмодзи в пикере
function renderCustomEmojiButtons() {
    const container = el('custom-emoji-btns');
    if (!container) return;

    if (!customEmojis.length) {
        container.innerHTML = '';
        return;
    }

    container.innerHTML = customEmojis
        .map(
            (e) =>
                `<button class="react-btn custom-emoji-btn" title=":${e.shortcode}:"
             onclick="doReact(':${e.shortcode}:')">
            <img src="${e.url}" alt=":${e.shortcode}:" style="width:20px;height:20px;object-fit:contain;">
        </button>`,
        )
        .join('');
}

// ── Менеджер эмодзи ───────────────────────────────────────

function openEmojiManager() {
    el('emoji-manager').style.display = 'flex';
    renderEmojiManagerList();
}

function closeEmojiManager() {
    el('emoji-manager').style.display = 'none';
    el('emoji-shortcode-input').value = '';
    el('emoji-file-input').value = '';
    el('emoji-preview').style.display = 'none';
    el('emoji-preview-img').src = '';
}

function renderEmojiManagerList() {
    const wrap = el('emoji-manager-list');
    if (!customEmojis.length) {
        wrap.innerHTML =
            '<div style="color:var(--text2);font-size:13px;text-align:center;padding:8px 0">Нет кастомных эмодзи</div>';
        return;
    }
    wrap.innerHTML = customEmojis
        .map(
            (e) => `
        <div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid var(--border)">
            <img src="${e.url}" alt=":${e.shortcode}:" style="width:28px;height:28px;object-fit:contain;border-radius:4px;">
            <span style="flex:1;font-size:13px;color:var(--text)">:${e.shortcode}:</span>
            <button onclick="deleteCustomEmoji(${e.id}, ':${e.shortcode}:')"
                style="background:none;border:none;color:var(--text2);cursor:pointer;font-size:14px;padding:2px 4px;border-radius:4px;transition:color .15s"
                onmouseover="this.style.color='var(--danger,#e55)'"
                onmouseout="this.style.color='var(--text2)'">✕</button>
        </div>`,
        )
        .join('');
}

function onEmojiFileSelected(input) {
    const file = input.files[0];
    if (!file) return;

    if (file.size > 512 * 1024) {
        toast('Файл слишком большой (макс 512KB)', 'err');
        input.value = '';
        return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
        el('emoji-preview-img').src = e.target.result;
        el('emoji-preview').style.display = 'block';
    };
    reader.readAsDataURL(file);
}

async function uploadCustomEmoji() {
    const shortcode = el('emoji-shortcode-input').value.trim().replace(/:/g, '');
    const fileInput = el('emoji-file-input');
    const file = fileInput.files[0];

    if (!shortcode) {
        toast('Введи shortcode', 'err');
        return;
    }
    if (!file) {
        toast('Выбери файл', 'err');
        return;
    }

    const btn = el('emoji-upload-btn');
    btn.disabled = true;
    btn.textContent = '⏳';

    try {
        const fd = new FormData();
        fd.append('shortcode', shortcode);
        fd.append('file', file);

        const resp = await fetch(API_BASE() + '/emojis/', {
            method: 'POST',
            headers: { Authorization: `Bearer ${token}` },
            body: fd,
        });

        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || 'Upload failed');
        }

        const data = await resp.json();
        customEmojis.push(data);
        renderCustomEmojiButtons();
        renderEmojiManagerList();

        el('emoji-shortcode-input').value = '';
        fileInput.value = '';
        el('emoji-preview').style.display = 'none';
        el('emoji-preview-img').src = '';

        toast(`✅ :${shortcode}: добавлен!`, 'ok');
    } catch (e) {
        toast('Ошибка: ' + e.message, 'err');
    } finally {
        btn.disabled = false;
        btn.textContent = 'Загрузить';
    }
}

async function deleteCustomEmoji(emojiId, label) {
    if (!confirm(`Удалить ${label}?`)) return;
    try {
        await api(`/emojis/${emojiId}`, 'DELETE');
        customEmojis = customEmojis.filter((e) => e.id !== emojiId);
        renderCustomEmojiButtons();
        renderEmojiManagerList();
        toast(`${label} удалён`, 'ok');
    } catch (e) {
        toast(e.message, 'err');
    }
}

// Закрытие по Escape
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && el('emoji-manager').style.display === 'flex') {
        closeEmojiManager();
    }
});
