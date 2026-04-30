const COLORS = [
  '#E17076', // красный
  '#7BC862', // зелёный
  '#A695E7', // фиолетовый
  '#EE7AAE', // розовый
  '#6EC9CB', // бирюзовый
  '#FAA774', // оранжевый
  '#E8A838', // жёлтый
  '#8B6FBF', // тёмно-фиолетовый
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