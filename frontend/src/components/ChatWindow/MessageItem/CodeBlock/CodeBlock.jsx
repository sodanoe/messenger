import { useState } from 'react';
import { PrismLight as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

import javascript from 'react-syntax-highlighter/dist/esm/languages/prism/javascript';
import jsx from 'react-syntax-highlighter/dist/esm/languages/prism/jsx';
import typescript from 'react-syntax-highlighter/dist/esm/languages/prism/typescript';
import tsx from 'react-syntax-highlighter/dist/esm/languages/prism/tsx';
import python from 'react-syntax-highlighter/dist/esm/languages/prism/python';
import bash from 'react-syntax-highlighter/dist/esm/languages/prism/bash';
import json from 'react-syntax-highlighter/dist/esm/languages/prism/json';
import yaml from 'react-syntax-highlighter/dist/esm/languages/prism/yaml';
import docker from 'react-syntax-highlighter/dist/esm/languages/prism/docker';
import sql from 'react-syntax-highlighter/dist/esm/languages/prism/sql';
import css from 'react-syntax-highlighter/dist/esm/languages/prism/css';
import markup from 'react-syntax-highlighter/dist/esm/languages/prism/markup';
import markdown from 'react-syntax-highlighter/dist/esm/languages/prism/markdown';
import kotlin from 'react-syntax-highlighter/dist/esm/languages/prism/kotlin';
import diff from 'react-syntax-highlighter/dist/esm/languages/prism/diff';

import styles from './CodeBlock.module.css';

// Регистрируем только то, что реально нужно — не весь Prism
SyntaxHighlighter.registerLanguage('javascript', javascript);
SyntaxHighlighter.registerLanguage('js', javascript);
SyntaxHighlighter.registerLanguage('jsx', jsx);
SyntaxHighlighter.registerLanguage('typescript', typescript);
SyntaxHighlighter.registerLanguage('ts', typescript);
SyntaxHighlighter.registerLanguage('tsx', tsx);
SyntaxHighlighter.registerLanguage('python', python);
SyntaxHighlighter.registerLanguage('py', python);
SyntaxHighlighter.registerLanguage('bash', bash);
SyntaxHighlighter.registerLanguage('sh', bash);
SyntaxHighlighter.registerLanguage('shell', bash);
SyntaxHighlighter.registerLanguage('json', json);
SyntaxHighlighter.registerLanguage('yaml', yaml);
SyntaxHighlighter.registerLanguage('yml', yaml);
SyntaxHighlighter.registerLanguage('docker', docker);
SyntaxHighlighter.registerLanguage('dockerfile', docker);
SyntaxHighlighter.registerLanguage('sql', sql);
SyntaxHighlighter.registerLanguage('css', css);
SyntaxHighlighter.registerLanguage('markup', markup);
SyntaxHighlighter.registerLanguage('html', markup);
SyntaxHighlighter.registerLanguage('xml', markup);
SyntaxHighlighter.registerLanguage('markdown', markdown);
SyntaxHighlighter.registerLanguage('md', markdown);
SyntaxHighlighter.registerLanguage('kotlin', kotlin);
SyntaxHighlighter.registerLanguage('diff', diff);

const SUPPORTED = new Set([
  'javascript', 'js', 'jsx', 'typescript', 'ts', 'tsx',
  'python', 'py', 'bash', 'sh', 'shell',
  'json', 'yaml', 'yml', 'docker', 'dockerfile',
  'sql', 'css', 'markup', 'html', 'xml',
  'markdown', 'md', 'kotlin', 'diff',
]);

function CopyIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
  );
}

export default function CodeBlock({ lang, code }) {
  const [copied, setCopied] = useState(false);
  const normalizedLang = (lang || '').toLowerCase();
  const isSupported = SUPPORTED.has(normalizedLang);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // intentional
    }
  }

  return (
    <div className={styles.wrap} onClick={(e) => e.stopPropagation()}>
      <div className={styles.header}>
        <span className={styles.lang}>{normalizedLang || 'код'}</span>
        <button className={styles.copyBtn} onClick={handleCopy}>
          {copied ? (
            <>✓ Скопировано</>
          ) : (
            <>
              <CopyIcon />
              Копировать
            </>
          )}
        </button>
      </div>

      {isSupported ? (
        <SyntaxHighlighter
          language={normalizedLang}
          style={oneDark}
          customStyle={{
            margin: 0,
            padding: '12px 14px',
            background: 'transparent',
            fontSize: 13,
            lineHeight: 1.5,
          }}
          codeTagProps={{ style: { fontFamily: 'var(--mono, monospace)' } }}
          wrapLongLines
        >
          {code}
        </SyntaxHighlighter>
      ) : (
        <pre className={styles.plain}><code>{code}</code></pre>
      )}
    </div>
  );
}