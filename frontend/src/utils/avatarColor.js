const COLORS = [
  '#E17076',
  '#7BC862',
  '#65AADD',
  '#A695E7',
  '#EE7AAE',
  '#6EC9CB',
  '#FAA774',
  '#5FADED',
];

export function getAvatarColor(name) {
  if (!name) return COLORS[0];
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = (hash * 31 + name.charCodeAt(i)) >>> 0;
  }
  const color = COLORS[hash % COLORS.length];
  console.log(name, hash, hash % COLORS.length, color);
  return color;
}