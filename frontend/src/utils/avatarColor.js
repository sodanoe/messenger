const COLORS = [
  '#E17076', // красный
  '#7BC862', // зелёный
  '#65AADD', // голубой
  '#A695E7', // фиолетовый
  '#EE7AAE', // розовый
  '#6EC9CB', // бирюзовый
  '#FAA774', // оранжевый
  '#5FADED', // синий
];

export function getAvatarColor(name) {
  if (!name) return COLORS[0];
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return COLORS[Math.abs(hash) % COLORS.length];
}