import js from '@eslint/js'
import vue from 'eslint-plugin-vue'
import typescript from 'typescript-eslint'
import prettier from 'eslint-plugin-prettier'
import prettierConfig from 'eslint-config-prettier'

export default [
  // Base configs
  js.configs.recommended,
  ...typescript.configs.recommended,
  ...vue.configs['flat/recommended'],
  prettierConfig,
  
  // Files to lint
  {
    files: ['**/*.{js,ts,vue}'],
    plugins: {
      prettier
    },
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      parserOptions: {
        parser: typescript.parser
      }
    },
    rules: {
      // Prettier integration
      'prettier/prettier': 'error',
      
      // Vue-specific rules
      'vue/multi-word-component-names': 'off',
      'vue/no-v-html': 'off', // We use v-html with sanitized markdown rendering
      
      // TypeScript rules
      '@typescript-eslint/no-explicit-any': 'warn',
      '@typescript-eslint/no-unused-vars': ['error', { 
        argsIgnorePattern: '^_',
        varsIgnorePattern: '^_' 
      }],
      
      // General rules
      'no-console': 'off', // Allow console messages
      'no-debugger': 'warn'
    }
  },
  
  // Ignore patterns
  {
    ignores: [
      'dist/**',
      'node_modules/**',
      '*.config.js',
      '*.config.ts',
      '.vite/**'
    ]
  }
]