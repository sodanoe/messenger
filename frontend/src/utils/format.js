export function initials(name) {
  return name ? name[0].toUpperCase() : '?';
}

export function normalizeDate(iso) {
  if (!iso) return iso;
  return iso.endsWith('Z') || /[+-]\d{2}:\d{2}$/.test(iso) ? iso : iso + 'Z';
}

export function fmtTime(iso) {
  return new Date(normalizeDate(iso)).toLocaleTimeString('ru', {
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function fmtDay(iso) {
  const d = new Date(normalizeDate(iso));
  const now = new Date();
  if (d.toDateString() === now.toDateString()) return 'Сегодня';
  const y = new Date(now);
  y.setDate(y.getDate() - 1);
  if (d.toDateString() === y.toDateString()) return 'Вчера';
  return d.toLocaleDateString('ru', { day: 'numeric', month: 'long' });
}
