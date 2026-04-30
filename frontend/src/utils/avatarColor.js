const COLORS = [
  '#E17076',
  '#7BC862',
  '#7da2c7',
  '#EE7AAE',
  '#6EC9CB',
  '#FAA774',
  '#e8e538',
  '#8c6161', 
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