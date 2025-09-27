<template>
    <div class="ai-chat-container">
        <!-- AI Response Display -->
        <div v-if="response" class="ai-response-container mb-4 pa-3" :class="responseContainerClass">
            <div class="ai-response-header">
                <v-icon :color="headerIconColor" class="mr-2">
                    {{ headerIcon }}
                </v-icon>
                <span class="font-weight-bold">{{ headerText }}</span>
            </div>

            <!-- Success Response -->
            <template v-if="!response.error">
                <!-- Display the explanation with Markdown -->
                <div v-if="response.explanation" class="explanation-section mt-3">
                    <v-card variant="outlined" class="pa-3">
                        <v-card-title class="text-subtitle-2 py-2">
                            <v-icon class="mr-2">mdi-information</v-icon>
                            Explanation
                        </v-card-title>
                        <v-divider class="mb-3"></v-divider>
                        <div class="markdown-content" v-html="renderMarkdown(response.explanation)"></div>
                    </v-card>
                </div>

                <!-- Display the YAML with syntax highlighting -->
                <div v-if="response.automation_yaml" class="yaml-section mt-3">
                    <v-card variant="outlined">
                        <v-card-title class="text-subtitle-2 py-2">
                            <v-icon class="mr-2">mdi-code-braces</v-icon>
                            Generated Automation YAML
                            <v-spacer></v-spacer>
                            <v-btn icon="mdi-content-copy" size="small" variant="text" @click="copyYaml"
                                :disabled="copying" class="copy-button">
                                <v-icon>{{ copying ? 'mdi-check' : 'mdi-content-copy' }}</v-icon>
                            </v-btn>
                        </v-card-title>
                        <v-divider></v-divider>
                        <div class="code-container">
                            <pre><code 
                class="yaml-code language-yaml" 
                v-html="highlightYaml(response.automation_yaml)"
              ></code></pre>
                        </div>
                    </v-card>
                </div>

                <!-- Display full LLM response if available -->
                <div v-if="response.full_response && response.full_response !== response.explanation"
                    class="full-response-section mt-3">
                    <v-expansion-panels>
                        <v-expansion-panel>
                            <v-expansion-panel-title>
                                <v-icon class="mr-2">mdi-message-text</v-icon>
                                Full LLM Response
                            </v-expansion-panel-title>
                            <v-expansion-panel-text>
                                <div class="markdown-content" v-html="renderMarkdown(response.full_response)"></div>
                            </v-expansion-panel-text>
                        </v-expansion-panel>
                    </v-expansion-panels>
                </div>

                <!-- Install Button -->
                <div v-if="response.automation_yaml" class="action-section mt-4">
                    <v-btn color="success" variant="elevated" size="large" @click="handleInstallAutomation">
                        <v-icon left>mdi-download</v-icon>
                        Install Automation
                    </v-btn>
                </div>
            </template>

            <!-- Error Response -->
            <template v-else>
                <v-alert type="error" class="mt-3" :title="errorTitle">
                    <div class="error-message markdown-content" v-html="renderMarkdown(response.error)"></div>

                    <!-- Raw response for debugging -->
                    <v-expansion-panels v-if="response.rawResponse" class="mt-3">
                        <v-expansion-panel>
                            <v-expansion-panel-title>
                                <v-icon class="mr-2">mdi-bug</v-icon>
                                Debug Information
                            </v-expansion-panel-title>
                            <v-expansion-panel-text>
                                <pre class="debug-response">{{ response.rawResponse }}</pre>
                            </v-expansion-panel-text>
                        </v-expansion-panel>
                    </v-expansion-panels>
                </v-alert>
            </template>
        </div>

        <!-- Prompt Input -->
        <v-textarea v-model="internalPrompt" label="Your Prompt"
            placeholder="e.g., 'Turn on the porch light at sunset and turn it off at sunrise'" rows="3" auto-grow
            clearable :disabled="generating" />

        <!-- Generate Button -->
        <div class="mt-3">
            <v-btn color="primary" :loading="generating" :disabled="!internalPrompt.trim()" @click="handleGenerate"
                block size="large">
                <v-icon left>mdi-magic-staff</v-icon>
                Generate Automation
            </v-btn>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { useHATheme } from '@/composables/useHATheme';
import { useMarkdown } from '@/composables/useMarkdown';
import hljs from 'highlight.js/lib/core';
import yaml from 'highlight.js/lib/languages/yaml';

// Register YAML language for syntax highlighting
hljs.registerLanguage('yaml', yaml);

// Initialize HA theme and markdown
const { haTheme } = useHATheme()
const { renderMarkdown } = useMarkdown()

interface AiResponse {
    automation_yaml?: string;
    explanation?: string;
    full_response?: string;
    error?: string;
    rawResponse?: string;
}

interface Props {
    response: AiResponse | null;
    generating?: boolean;
    modelValue?: string;
}

const props = withDefaults(defineProps<Props>(), {
    generating: false,
    modelValue: '',
});

const emit = defineEmits<{
    'install-automation': [yaml: string];
    'generate-prompt': [prompt: string];
    'update:modelValue': [value: string];
}>();

const copying = ref(false);
const internalPrompt = ref(props.modelValue);

// Watch for external prompt changes (v-model)
watch(() => props.modelValue, (newValue) => {
    internalPrompt.value = newValue;
});

// Emit prompt changes for v-model
watch(internalPrompt, (newValue) => {
    emit('update:modelValue', newValue);
});

const responseContainerClass = computed(() => ({
    'success-response': !props.response?.error,
    'error-response': !!props.response?.error,
}));

const headerIcon = computed(() =>
    props.response?.error ? 'mdi-alert-circle' : 'mdi-robot'
);

const headerIconColor = computed(() =>
    props.response?.error ? 'error' : 'primary'
);

const headerText = computed(() =>
    props.response?.error ? 'AItomations Assistant - Error' : 'AItomations Assistant'
);

const errorTitle = computed(() =>
    'Failed to Generate Automation'
);

const highlightYaml = (code: string) => {
    try {
        return hljs.highlight(code, { language: 'yaml' }).value;
    } catch (error) {
        console.warn('YAML highlighting failed:', error);
        return code;
    }
};

const handleGenerate = () => {
    if (!internalPrompt.value.trim()) return;
    emit('generate-prompt', internalPrompt.value.trim());
};

const handleInstallAutomation = () => {
    if (props.response?.automation_yaml) {
        emit('install-automation', props.response.automation_yaml);
    }
};

const copyYaml = async () => {
    if (!props.response?.automation_yaml) return;

    try {
        copying.value = true;
        await navigator.clipboard.writeText(props.response.automation_yaml);

        setTimeout(() => {
            copying.value = false;
        }, 2000);
    } catch (error) {
        console.error('Failed to copy YAML:', error);
        copying.value = false;
    }
};
</script>

<style scoped>
/* Component-specific styles that enhance the global theme */
.ai-response-header {
    display: flex;
    align-items: center;
    font-size: 1.1rem;
}

.explanation-section,
.yaml-section,
.full-response-section,
.action-section {
    margin-bottom: 1rem;
}

.code-container {
    position: relative;
    background-color: var(--ha-card-background-color);
    border-radius: 4px;
    overflow: visible;
    /* Changed from hidden to visible */
}

.yaml-code {
    margin: 0 !important;
    padding: 16px !important;
    background-color: var(--ha-card-background-color) !important;
    color: var(--ha-primary-text-color) !important;
    border: none !important;
    border-radius: 4px !important;
    overflow-x: auto;
    overflow-y: visible !important;
    /* Ensure vertical content is not clipped */
    font-size: 0.875rem;
    line-height: 1.4;
    filter: brightness(0.95);
    white-space: pre-wrap;
    /* Ensure proper line wrapping */
    word-wrap: break-word;
    min-height: auto !important;
    /* Remove any min-height constraints */
    max-height: none !important;
    /* Remove any max-height constraints */
    display: block !important;
    /* Ensure proper block display */
}

/* Fix any potential masking issues */
.yaml-code,
.yaml-code * {
    -webkit-mask-image: none !important;
    mask-image: none !important;
    -webkit-mask: none !important;
    mask: none !important;
}

/* Ensure the pre element doesn't clip content */
.code-container pre {
    margin: 0 !important;
    padding: 0 !important;
    overflow: visible !important;
    white-space: pre-wrap !important;
    word-wrap: break-word !important;
}

.copy-button {
    opacity: 0.7;
    transition: opacity 0.2s;
}

.copy-button:hover {
    opacity: 1;
}

.markdown-content {
    font-size: 0.95rem;
    line-height: 1.6;
}

/* Style markdown elements to match HA theme */
.markdown-content :deep(h1),
.markdown-content :deep(h2),
.markdown-content :deep(h3),
.markdown-content :deep(h4),
.markdown-content :deep(h5),
.markdown-content :deep(h6) {
    color: var(--ha-primary-text-color);
    margin-top: 1.5rem;
    margin-bottom: 0.5rem;
}

.markdown-content :deep(p) {
    margin-bottom: 1rem;
    color: var(--ha-primary-text-color);
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
    margin-bottom: 1rem;
    padding-left: 1.5rem;
    color: var(--ha-primary-text-color);
}

.markdown-content :deep(code) {
    background-color: var(--ha-card-background-color);
    color: var(--ha-primary-text-color);
    padding: 0.2rem 0.4rem;
    border-radius: 3px;
    font-size: 0.9em;
    border: 1px solid var(--ha-divider-color);
    filter: brightness(0.95);
}

.markdown-content :deep(pre) {
    background-color: var(--ha-card-background-color);
    color: var(--ha-primary-text-color);
    padding: 1rem;
    border-radius: 4px;
    overflow-x: auto;
    overflow-y: visible !important;
    /* Ensure vertical scrolling works */
    border: 1px solid var(--ha-divider-color);
    filter: brightness(0.95);
}

.markdown-content :deep(blockquote) {
    border-left: 4px solid var(--ha-primary-color);
    margin: 1rem 0;
    padding-left: 1rem;
    color: var(--ha-secondary-text-color);
    font-style: italic;
}

.debug-response {
    font-size: 0.75rem;
    margin: 0;
    white-space: pre-wrap;
    color: var(--ha-secondary-text-color);
    overflow: visible !important;
    /* Ensure debug content isn't clipped */
}

.error-message {
    font-family: 'Roboto Mono', Monaco, monospace;
    font-size: 0.9rem;
}
</style>