// Ссылки вида http(s)://... или www....
const URL_REGEX = /((?:https?:\/\/|www\.)[^\s<]+)/gi;

// Хвостовая пунктуация, которую не включаем в ссылку (типа "зайди на ya.ru.")
const TRAILING_PUNCTUATION = /[.,!?:;'"]+$/;

/**
 * Превращает текст сообщения в массив строк/React-элементов:
 * - :shortcode: заменяется на кастомный эмодзи (img), если он есть в customEmojis
 * - URL (http(s):// или www.) превращается в кликабельную ссылку
 *
 * @param {string} text
 * @param {Array<{shortcode: string, url: string}>} customEmojis
 * @param {{ emoji?: string, link?: string }} classNames - css-классы для img/a
 * @returns {Array<string|JSX.Element>}
 */
export function formatMessageContent(text, customEmojis = [], classNames = {}) {
  if (!text) return '';

  const { emoji: emojiClassName, link: linkClassName } = classNames;

  // Сначала разбиваем по кастомным эмодзи :shortcode:
  const emojiParts = text.split(/(:[a-zA-Z0-9_]+:)/g);

  const result = [];

  emojiParts.forEach((part, pi) => {
    if (part.startsWith(':') && part.endsWith(':')) {
      const shortcode = part.slice(1, -1);
      const emoji = customEmojis.find((e) => e.shortcode === shortcode);

      if (emoji) {
        result.push(
          <img
            key={`emoji-${pi}`}
            src={emoji.url}
            className={emojiClassName}
            alt={part}
            title={part}
          />
        );
        return;
      }
    }

    // В обычном тексте ищем ссылки
    const linkParts = part.split(URL_REGEX);

    linkParts.forEach((chunk, ci) => {
      if (!chunk) return;

      // При split с захватывающей группой нечётные индексы — это совпадения URL_REGEX
      if (ci % 2 === 1) {
        let url = chunk;
        let trailing = '';

        const match = url.match(TRAILING_PUNCTUATION);
        if (match) {
          trailing = match[0];
          url = url.slice(0, -trailing.length);
        }

        const href = /^https?:\/\//i.test(url) ? url : `https://${url}`;

        result.push(
          <a
            key={`link-${pi}-${ci}`}
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className={linkClassName}
            onClick={(e) => e.stopPropagation()}
          >
            {url}
          </a>
        );

        if (trailing) result.push(trailing);
      } else {
        result.push(chunk);
      }
    });
  });

  return result;
}

// ```lang\n...код...\n```  (lang опционален)
const CODE_BLOCK_REGEX = /```(\w*)\n?([\s\S]*?)```/g;

/**
 * Разбивает текст сообщения на сегменты:
 * { type: 'text', content } — обычный текст (дальше через formatMessageContent)
 * { type: 'code', lang, content } — содержимое ```fenced``` блока
 *
 * @param {string} text
 * @returns {Array<{type: 'text'|'code', content: string, lang?: string}>}
 */
export function splitCodeBlocks(text) {
  if (!text) return [];

  const segments = [];
  let lastIndex = 0;
  let match;

  CODE_BLOCK_REGEX.lastIndex = 0;
  while ((match = CODE_BLOCK_REGEX.exec(text)) !== null) {
    if (match.index > lastIndex) {
      segments.push({ type: 'text', content: text.slice(lastIndex, match.index) });
    }
    segments.push({
      type: 'code',
      lang: (match[1] || '').toLowerCase(),
      content: match[2].replace(/\n$/, ''),
    });
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    segments.push({ type: 'text', content: text.slice(lastIndex) });
  }

  return segments;
}