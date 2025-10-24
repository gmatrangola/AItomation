<template>
    <div class="ai-chat-container">
        <!-- Chat Messages -->
        <div ref="messagesContainer" class="messages-container">
            <template v-if="messages.length === 0 && !streamingMessage">
                <div class="empty-state">
                    <v-icon size="48" color="primary">mdi-chat-outline</v-icon>
                    <h3 class="mt-3">Start a Conversation</h3>
                    <p class="text-secondary mt-2">Describe the automation you'd like to create</p>
                    <div class="example-prompts mt-4">
                        <v-chip
                            v-for="example in examplePrompts"
                            :key="example"
                            size="small"
                            class="ma-1"
                            @click="selectExample(example)"
                        >
                            {{ example }}
                        </v-chip>
                    </div>
                </div>
            </template>

            <template v-else>
                <ChatMessage
                    v-for="message in messages"
                    :key="message.id"
                    :message="message"
                    :show-install-button="message.yaml === latestYaml"
                    @install="handleInstallAutomation"
                />

                <!-- Streaming message (real-time) -->
                <ChatMessage
                    v-if="streamingMessage"
                    :key="streamingMessage.id"
                    :message="streamingMessage"
                    :show-install-button="false"
                    class="streaming-message"
                />

                <!-- Loading indicator (only show before streaming starts) -->
                <div v-if="isGenerating && !streamingMessage" class="chat-message chat-message--assistant">
                    <div class="chat-message__header">
                        <v-avatar color="success" size="28">
                            <v-icon size="small">mdi-robot</v-icon>
                        </v-avatar>
                        <span class="chat-message__role">AI Assistant</span>
                    </div>
                    <div class="chat-message__content">
                        <v-progress-linear indeterminate color="primary" height="2"></v-progress-linear>
                        <p class="text-secondary mt-2 text-caption">Thinking...</p>
                    </div>
                </div>
            </template>
        </div>

        <!-- Compact Input Area -->
        <div class="chat-input-wrapper">
            <v-divider />
            <div class="chat-input">
                <v-textarea
                    v-model="internalPrompt"
                    :placeholder="
                        messages.length === 0
                            ? 'e.g., Turn on the porch light at sunset...'
                            : 'Refine or ask for changes...'
                    "
                    rows="1"
                    auto-grow
                    max-rows="3"
                    :disabled="isGenerating"
                    variant="outlined"
                    density="compact"
                    hide-details
                    class="compact-input"
                    @keydown.enter.exact.prevent="handleSend"
                    @keydown.enter.shift.exact="handleNewLine"
                >
                    <template #append-inner>
                        <v-btn
                            :disabled="!internalPrompt.trim() || isGenerating"
                            icon
                            size="small"
                            color="primary"
                            variant="flat"
                            @click="handleSend"
                        >
                            <v-icon size="small">mdi-send</v-icon>
                        </v-btn>
                    </template>
                </v-textarea>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue';
import { useChat } from '@/composables/useChat';
import ChatMessage from './ChatMessage.vue';
import type { APIError } from '@/types/errors';

const { messages, isGenerating, latestYaml, streamingMessage, currentError, sendMessage, clearChat, clearError } =
    useChat();

interface Props {
    modelValue?: string;
}

const props = withDefaults(defineProps<Props>(), {
    modelValue: '',
});

const emit = defineEmits<{
    'install-automation': [yaml: string];
    'update:modelValue': [value: string];
    'has-messages': [hasMessages: boolean];
    error: [error: APIError];
}>();

const internalPrompt = ref(props.modelValue);
const messagesContainer = ref<HTMLElement>();

const examplePrompts = ['Turn on lights at sunset', 'Notify me when door opens', 'Coffee maker on weekdays at 7am'];

// Emit whether we have messages
watch(
    messages,
    (newMessages) => {
        emit('has-messages', newMessages.length > 0);
    },
    { immediate: true, deep: true }
);

// Watch for errors and emit to parent
watch(
    currentError,
    (error) => {
        if (error) {
            emit('error', error);
            clearError(); // Clear from composable since Dashboard manages it now
        }
    },
    { immediate: true }
);

// Watch for external prompt changes
watch(
    () => props.modelValue,
    (newValue) => {
        internalPrompt.value = newValue;
    }
);

// Emit prompt changes
watch(internalPrompt, (newValue) => {
    emit('update:modelValue', newValue);
});

// Scroll to bottom when messages or streaming message changes
watch(
    [messages, streamingMessage],
    async () => {
        await nextTick();
        if (messagesContainer.value) {
            messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
        }
    },
    { deep: true }
);

const handleSend = async () => {
    if (!internalPrompt.value.trim() || isGenerating.value) return;

    const prompt = internalPrompt.value.trim();
    internalPrompt.value = '';
    await sendMessage(prompt);
};

const handleNewLine = () => {
    internalPrompt.value += '\n';
};

const selectExample = (example: string) => {
    internalPrompt.value = example;
    handleSend();
};

const handleInstallAutomation = (yaml: string) => {
    emit('install-automation', yaml);
};

// Expose clearChat for parent component
defineExpose({
    clearChat,
});
</script>

<style scoped>
.ai-chat-container {
    display: flex;
    flex-direction: column;
    height: 100%;
    max-height: 100%;
    overflow: hidden;
}

.messages-container {
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
    padding: 1rem;
    scroll-behavior: smooth;
    min-height: 0;
}

/* Custom scrollbar for messages */
.messages-container::-webkit-scrollbar {
    width: 8px;
}

.messages-container::-webkit-scrollbar-track {
    background: var(--ha-card-background);
}

.messages-container::-webkit-scrollbar-thumb {
    background: var(--ha-border);
    border-radius: 4px;
}

.messages-container::-webkit-scrollbar-thumb:hover {
    background: var(--ha-secondary-text);
}

.streaming-message {
    opacity: 1;
}

.streaming-message::after {
    content: '▋';
    animation: blink 1s step-end infinite;
    color: var(--ha-primary-color);
    margin-left: 2px;
}

@keyframes blink {
    0%,
    50% {
        opacity: 1;
    }

    51%,
    100% {
        opacity: 0;
    }
}

.empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 2rem 1rem;
    min-height: 300px;
    color: var(--ha-secondary-text);
}

.empty-state h3 {
    color: var(--ha-primary-text);
    font-size: 1.1rem;
    font-weight: 500;
}

.example-prompts {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 0.5rem;
    max-width: 500px;
}

.example-prompts .v-chip {
    cursor: pointer;
    text-transform: none;
}

.chat-input-wrapper {
    flex-shrink: 0;
    background: var(--ha-card-background);
}

.chat-input {
    padding: 0.5rem 1rem 0.75rem;
}

.compact-input {
    font-size: 0.875rem;
}

.compact-input :deep(.v-field) {
    border-radius: 20px;
    padding: 2px 10px;
}

.compact-input :deep(.v-field__input) {
    padding: 6px 0;
    min-height: 32px;
}

.compact-input :deep(.v-field__append-inner) {
    padding-top: 0;
    align-items: center;
}
</style>
