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
            
            return div.innerHTML;
        } catch (error) {
            console.error('Markdown rendering failed:', error);
            return content;
        }
    };

    return {
        renderMarkdown
    };
}