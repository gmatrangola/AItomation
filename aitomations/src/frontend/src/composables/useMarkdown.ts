import { marked } from 'marked';
import hljs from 'highlight.js/lib/core';
import yaml from 'highlight.js/lib/languages/yaml';

// Register only the YAML language
hljs.registerLanguage('yaml', yaml);

export function useMarkdown() {
    const renderMarkdown = (content: string): string => {
        if (!content) return '';

        try {
            // First render markdown to HTML
            const html = marked(content) as string;

            // Then apply syntax highlighting to code blocks
            const div = document.createElement('div');
            div.innerHTML = html;

            // Find all code blocks and highlight them
            div.querySelectorAll('pre code').forEach((block) => {
                const codeElement = block as HTMLElement;
                // Check if it has a language class
                const langMatch = codeElement.className.match(/language-(\w+)/);
                if (langMatch && langMatch[1] === 'yaml') {
                    hljs.highlightElement(codeElement);
                }
            });

            // Wrap each code block and add a copy-to-clipboard button. The click is handled
            // via event delegation in the component (the injected HTML isn't reactive).
            div.querySelectorAll('pre').forEach((pre) => {
                if (!pre.querySelector('code')) return;
                const wrapper = document.createElement('div');
                wrapper.className = 'code-block';
                pre.parentNode?.insertBefore(wrapper, pre);
                wrapper.appendChild(pre);

                const button = document.createElement('button');
                button.type = 'button';
                button.className = 'copy-code-btn';
                button.title = 'Copy to clipboard';
                button.setAttribute('aria-label', 'Copy code to clipboard');
                button.innerHTML = '<i class="mdi mdi-content-copy"></i>';
                wrapper.appendChild(button);
            });

            return div.innerHTML;
        } catch (error) {
            console.error('Markdown rendering failed:', error);
            return content;
        }
    };

    return {
        renderMarkdown,
    };
}
