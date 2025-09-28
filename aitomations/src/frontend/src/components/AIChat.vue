<template>
    <div class="ai-chat-container">
        <!-- AI Response Display -->
        <v-card v-if="response" class="mb-4" elevation="2">
            <v-card-text>
                <!-- Success Response -->
                <template v-if="!response.error && response.full_response">
                    <AIResponse :response="response.full_response" @install-automation="handleInstallAutomation" />
                </template>

                <!-- Error Response -->
                <template v-else-if="response.error">
                    <v-alert type="error" class="mb-3" title="Failed to Generate Automation">
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
            </v-card-text>
        </v-card>

        <!-- Prompt Input -->
        <v-textarea v-model="internalPrompt" label="Your Prompt"
            placeholder="e.g., 'Turn on the porch light at sunset and turn it off at sunrise'" rows="3" auto-grow
            clearable :disabled="generating" variant="outlined" class="mb-4" />

        <!-- Generate Button -->
        <v-btn color="primary" :loading="generating" :disabled="!internalPrompt.trim()" @click="handleGenerate" block
            size="large">
            <v-icon start>mdi-magic-staff</v-icon>
            Generate Automation
        </v-btn>
    </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import AIResponse from './AIResponse.vue';

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

const handleGenerate = () => {
    if (!internalPrompt.value.trim()) return;
    emit('generate-prompt', internalPrompt.value.trim());
};

const handleInstallAutomation = (yaml: string) => {
    emit('install-automation', yaml);
};
</script>

<style scoped>
/* Only component-specific overrides needed here */
.debug-response {
    font-size: 0.75rem;
    white-space: pre-wrap;
    overflow-x: auto;
}

.error-message {
    font-family: 'Roboto Mono', Monaco, monospace;
    font-size: 0.9rem;
}
</style>