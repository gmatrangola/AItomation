import { computed } from 'vue'
import { marked } from 'marked'
import hljs from 'highlight.js/lib/core'
import yaml from 'highlight.js/lib/languages/yaml'
import python from 'highlight.js/lib/languages/python'
import javascript from 'highlight.js/lib/languages/javascript'
import json from 'highlight.js/lib/languages/json'

// Register languages
hljs.registerLanguage('yaml', yaml)
hljs.registerLanguage('python', python)
hljs.registerLanguage('javascript', javascript)
hljs.registerLanguage('json', json)

export function useMarkdown() {
  // Configure marked with syntax highlighting
  marked.setOptions({
    highlight: (code: string, lang: string) => {
      if (lang && hljs.getLanguage(lang)) {
        try {
          return hljs.highlight(code, { language: lang }).value
        } catch (err) {
          console.warn('Syntax highlighting failed:', err)
        }
      }
      // Auto-detect if no language specified
      try {
        return hljs.highlightAuto(code).value
      } catch (err) {
        return code
      }
    },
    breaks: true,
    gfm: true,
  })

  const renderMarkdown = (content: string): string => {
    if (!content) return ''
    
    try {
      return marked(content)
    } catch (error) {
      console.error('Markdown rendering failed:', error)
      return content
    }
  }

  const renderMarkdownSafe = computed(() => renderMarkdown)

  return {
    renderMarkdown,
    renderMarkdownSafe
  }
}