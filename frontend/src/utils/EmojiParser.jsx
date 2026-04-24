export function formatMessageContent(text, customEmojis = []) {
  if (!text) return '';

  // Регулярка для поиска :shortcode:
  const parts = text.split(/(:[a-zA-Z0-9_]+:)/g);

  return parts.map((part, i) => {
    if (part.startsWith(':') && part.endsWith(':')) {
      const shortcode = part.slice(1, -1);
      const emoji = customEmojis.find((e) => e.shortcode === shortcode);

      if (emoji) {
        return (
          <img
            key={i}
            src={emoji.url}
            className={styles.inlineEmoji}
            alt={part}
            title={part}
          />
        );
      }
    }
    return part;
  });
}
