import { marked } from 'marked';
import hljs from 'highlight.js';

// Define the extension for syntax highlighting
const highlightExtension = {
  name: 'highlight',
  level: 'block' as const, // This is a block-level extension
  start(src: string) {
    return src.match(/```(\w+)?\n/)?.index; // Find the start of a code block
  },
  tokenizer(src: string) {
    const match = src.match(/^```(\w+)?\n([\s\S]+?)\n```\n?/);
    if (match) {
      const lang = match[1] || 'plaintext';
      const code = match[2];
      const token = {
        type: 'highlight', // Custom token type
        raw: match[0],
        lang,
        code,
      };
      return token;
    }
  },
  renderer(token: any) {
    const language = hljs.getLanguage(token.lang) ? token.lang : 'plaintext';
    const highlightedCode = hljs.highlight(token.code, { language }).value;
    return `<pre><code class="hljs language-${language}">${highlightedCode}</code></pre>`;
  },
};

// Use the extension and set other global options
marked.use({
  extensions: [highlightExtension],
  gfm: true, // Enable GitHub Flavored Markdown
  breaks: true, // Convert single line breaks to <br>
});

export function useMarkdown() {
  /**
   * Renders a Markdown string to an HTML string.
   * @param markdownString The string to render.
   * @returns The rendered HTML string.
   */
  const renderMarkdown = (markdownString: string | undefined | null): string => {
    if (!markdownString) {
      return '';
    }
    // The 'marked' function can return a Promise, so we handle it asynchronously.
    // However, with the current setup, it behaves synchronously. We cast to be safe.
    return marked.parse(markdownString) as string;
  };

  return {
    renderMarkdown,
  };
}