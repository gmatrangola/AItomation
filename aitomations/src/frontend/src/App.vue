<template>
    <v-app>
        <v-main>
            <v-container fluid class="pa-4">
                <Dashboard />
            </v-container>
        </v-main>
    </v-app>
</template>

<script setup lang="ts">
import Dashboard from '@/views/Dashboard.vue';
</script>

<style>
/* HA-inspired color variables */
:root {
    --ha-primary-color: #03a9f4;
    --ha-primary-text: #e1e1e1;
    --ha-secondary-text: #9e9e9e;
    --ha-background: #111111;
    --ha-card-background: #1c1c1c;
    --ha-border: rgba(225, 225, 225, 0.12);
    --ha-success: #4caf50;
    --ha-error: #f44336;
    --ha-warning: #ff9800;
}

html,
body,
#app {
    height: 100%;
    margin: 0;
    padding: 0;
    background-color: var(--ha-background);
    color: var(--ha-primary-text);
}

.v-application {
    background-color: var(--ha-background) !important;
}

/* Vuetify component overrides for HA theme */
.v-card {
    background-color: var(--ha-card-background) !important;
    border: 1px solid var(--ha-border);
}

.v-textarea .v-field {
    background-color: var(--ha-card-background);
    border: 1px solid var(--ha-border);
}

.v-textarea textarea {
    color: var(--ha-primary-text) !important;
}

.v-textarea :deep(.v-field-label) {
    color: var(--ha-secondary-text) !important;
}

.v-textarea :deep(.v-field-label--floating) {
    color: var(--ha-primary-color) !important;
}

.v-data-table-footer {
    color: var(--ha-primary-text) !important;
}

.v-data-table-footer .v-pagination button {
    color: var(--ha-primary-text) !important;
}

.v-pagination .v-pagination__item,
.v-pagination .v-pagination__navigation {
    color: var(--ha-primary-text) !important;
}

.v-btn--variant-elevated {
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.v-alert {
    border: 1px solid var(--ha-border);
}

.v-data-table {
    background-color: var(--ha-card-background) !important;
}

.v-data-table__td,
.v-data-table__th {
    border-bottom: 1px solid var(--ha-border) !important;
    color: var(--ha-primary-text) !important;
}

.v-divider {
    border-color: var(--ha-border) !important;
}

/* Markdown content base styling - displayed within Home Assistant iframe */
.markdown-content {
    color: var(--ha-primary-text) !important;
}

.markdown-content h1,
.markdown-content h2,
.markdown-content h3,
.markdown-content h4,
.markdown-content h5,
.markdown-content h6 {
    color: var(--ha-primary-text) !important;
    margin: 1rem 0 0.5rem 0;
}

.markdown-content p {
    color: var(--ha-primary-text) !important;
    margin: 0.5rem 0;
}

.markdown-content strong,
.markdown-content b {
    font-weight: bold;
}

.markdown-content em,
.markdown-content i {
    font-style: italic;
}

.markdown-content ul,
.markdown-content ol {
    margin: 0.5rem 0;
    padding-left: 1.5rem;
}

.markdown-content a {
    color: var(--ha-primary-color) !important;
    text-decoration: underline;
}

.markdown-content a:hover {
    opacity: 0.8;
}

.markdown-content blockquote {
    color: var(--ha-secondary-text) !important;
    border-left: 4px solid var(--ha-primary-color) !important;
    padding-left: 1rem;
    margin: 1rem 0;
    font-style: italic;
}

/* Code blocks - integrate with github-dark.css theme from highlight.js */
.markdown-content pre {
    background-color: var(--ha-card-background) !important;
    border: 1px solid var(--ha-border) !important;
    border-radius: 4px;
    padding: 12px;
    overflow-x: auto;
    margin: 0.5rem 0;
}

.markdown-content pre code {
    font-family: 'Roboto Mono', Monaco, 'Cascadia Code', 'Segoe UI Mono', Consolas, 'Courier New', monospace !important;
    font-size: 0.9em;
}

.markdown-content code:not(pre code) {
    background-color: var(--ha-card-background) !important;
    color: var(--ha-primary-text) !important;
    border: 1px solid var(--ha-border) !important;
    border-radius: 4px;
    padding: 2px 6px;
    font-family: 'Roboto Mono', Monaco, 'Cascadia Code', 'Segoe UI Mono', Consolas, 'Courier New', monospace !important;
    font-size: 0.9em;
}
</style>
