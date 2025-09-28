<template>
    <div class="ai-chat-container">
        <!-- AI Response Display -->
        <div v-if="response" class="ai-response-container mb-4 pa-3" :class="responseContainerClass">
            <!-- Success Response -->
            <template v-if="!response.error && response.full_response">
                <!-- Display the full response with Markdown rendering -->
                <div class="markdown-content mt-3" v-html="renderMarkdown(response.full_response)"></div>

                <!-- Install Button -->
                <div v-if="extractedYaml" class="action-section mt-4">
                    <v-btn color="success" variant="elevated" size="large" @click="handleInstallAutomation">
                        <v-icon left>mdi-download</v-icon>
                        Install Automation
                    </v-btn>
                </div>
            </template>

            <!-- Error Response -->
            <template v-else-if="response.error">
                <v-alert type="error" class="mt-3" :title="errorTitle">
                    <div class="error-message">{{ response.error }}</div>
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

// Initialize HA theme and markdown
useHATheme();
const { renderMarkdown } = useMarkdown();

interface AiResponse {
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

const internalPrompt = ref(props.modelValue);

// Watch for external prompt changes (v-model)
watch(
    () => props.modelValue,
    (newValue) => {
        internalPrompt.value = newValue;
    }
);

// Emit prompt changes for v-model
watch(internalPrompt, (newValue) => {
    emit('update:modelValue', newValue);
});

const responseContainerClass = computed(() => ({
    'success-response': !props.response?.error,
    'error-response': !!props.response?.error,
}));

const headerIcon = computed(() => (props.response?.error ? 'mdi-alert-circle' : 'mdi-robot'));
const headerIconColor = computed(() => (props.response?.error ? 'error' : 'primary'));
const headerText = computed(() => (props.response?.error ? 'AItomations Assistant - Error' : 'AItomations Assistant'));
const errorTitle = computed(() => 'Failed to Generate Automation');

const extractYamlFromMarkdown = (markdown: string | undefined): string | null => {
    if (!markdown) return null;
    const match = markdown.match(/```yaml\n([\s\S]*?)\n```/);
    return match ? match[1].trim() : null;
};

const extractedYaml = computed(() => extractYamlFromMarkdown(props.response?.full_response));

const handleGenerate = () => {
    if (!internalPrompt.value.trim()) return;
    emit('generate-prompt', internalPrompt.value.trim());
};

const handleInstallAutomation = () => {
    if (extractedYaml.value) {
        emit('install-automation', extractedYaml.value);
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

.action-section {
    margin-bottom: 1rem;
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
    border: 1px solid var(--ha-divider-color);
    filter: brightness(0.95);
}

.markdown-content :deep(pre code) {
    border: none;
    padding: 0;
    filter: none;
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