const COLORS = [
  '#5B8DEF',
  '#4DAA8A',
  '#6C8AE4',
  '#5FA8D3',
  '#7C9CBF',
  '#4C7A96',
  '#6FAED9',
  '#7289AB',
  '#E07A7A',
];

export function getAvatarColor(name) {
  if (!name) return COLORS[0];
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = (hash * 31 + name.charCodeAt(i)) >>> 0;
  }
  const color = COLORS[hash % COLORS.length];
  return color;
}