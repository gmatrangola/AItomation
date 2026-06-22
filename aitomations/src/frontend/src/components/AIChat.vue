<template>
    <div class="ai-chat-container">
        <!-- Chat Messages -->
        <div ref="messagesContainer" class="messages-container">
            <template v-if="messages.length === 0">
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
                    :show-install-button="message.id === lastArtifactMessageId"
                    @apply-artifact="handleApplyArtifact"
                />

                <!-- Connecting State - Show immediately while waiting for backend -->
                <div v-if="isSending || isConnecting" class="chat-message chat-message--assistant">
                    <div class="chat-message__header">
                        <v-avatar color="success" size="28">
                            <v-icon size="small">mdi-robot</v-icon>
                        </v-avatar>
                        <span class="chat-message__role">AI Assistant</span>
                    </div>
                    <div class="chat-message__content connecting-content">
                        <div class="connecting-animation">
                            <div class="pulse-container">
                                <div class="pulse pulse-1"></div>
                                <div class="pulse pulse-2"></div>
                                <div class="pulse pulse-3"></div>
                            </div>
                            <div class="connecting-text">
                                <div class="connecting-message">Connecting to AI assistant...</div>
                                <div class="connecting-submessage">Establishing secure connection</div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Progress Indicator - Show BEFORE streaming starts or during streaming -->
                <div
                    v-else-if="isGenerating && progressInfo && !streamingMessage"
                    class="chat-message chat-message--assistant"
                >
                    <div class="chat-message__header">
                        <v-avatar color="success" size="28">
                            <v-icon size="small">mdi-robot</v-icon>
                        </v-avatar>
                        <span class="chat-message__role">AI Assistant</span>
                    </div>
                    <div class="chat-message__content progress-content">
                        <div v-if="progressInfo.stage === 'initializing_context'" class="progress-stage">
                            <v-progress-circular indeterminate color="primary" size="20" class="mr-2" />
                            <span>Initializing context...</span>
                        </div>

                        <div v-else-if="progressInfo.stage === 'gathering_context'" class="progress-stage">
                            <v-progress-circular indeterminate color="primary" size="20" class="mr-2" />
                            <span>Gathering Home Assistant context...</span>
                        </div>

                        <div v-else-if="progressInfo.stage === 'context_ready'" class="progress-stage">
                            <v-icon color="success" size="small" class="mr-2">mdi-check-circle</v-icon>
                            <div class="context-stats">
                                <div class="stats-title">Context prepared:</div>
                                <div class="stats-grid">
                                    <span class="stat-item">
                                        <v-icon size="x-small">mdi-lightbulb-outline</v-icon>
                                        {{ progressInfo.stats?.entities }} entities
                                    </span>
                                    <span class="stat-item">
                                        <v-icon size="x-small">mdi-cog-outline</v-icon>
                                        {{ progressInfo.stats?.services }} services
                                    </span>
                                    <span class="stat-item">
                                        <v-icon size="x-small">mdi-robot-outline</v-icon>
                                        {{ progressInfo.stats?.automations }} automations
                                    </span>
                                </div>
                            </div>
                        </div>

                        <div v-else-if="progressInfo.stage === 'generating'" class="progress-stage">
                            <v-progress-circular indeterminate color="primary" size="20" class="mr-2" />
                            <span>Generating with {{ progressInfo.provider }}...</span>
                        </div>
                    </div>
                </div>

                <!-- Streaming message (real-time) with inline progress -->
                <div v-if="streamingMessage" class="chat-message chat-message--assistant">
                    <div class="chat-message__header">
                        <v-avatar color="success" size="28">
                            <v-icon size="small">mdi-robot</v-icon>
                        </v-avatar>
                        <span class="chat-message__role">AI Assistant</span>
                        <!-- Show progress in header while streaming -->
                        <span v-if="progressInfo && progressInfo.stage === 'generating'" class="streaming-status">
                            <v-icon size="x-small" class="mr-1">mdi-flash</v-icon>
                            {{ progressInfo.provider }}
                            <span v-if="progressInfo.chunks_received" class="chunks-badge">
                                {{ progressInfo.chunks_received }}
                            </span>
                        </span>
                    </div>
                    <div class="chat-message__content">
                        <div class="markdown-content" v-html="renderMarkdown(streamingMessage.content)"></div>
                        <span class="cursor-blink">▋</span>
                    </div>
                </div>

                <!-- Completion message - shown briefly after streaming -->
                <div
                    v-if="progressInfo && progressInfo.stage === 'complete' && !streamingMessage"
                    class="chat-message chat-message--assistant completion-message"
                >
                    <div class="chat-message__header">
                        <v-avatar color="success" size="28">
                            <v-icon size="small">mdi-robot</v-icon>
                        </v-avatar>
                        <span class="chat-message__role">AI Assistant</span>
                    </div>
                    <div class="chat-message__content progress-content">
                        <div class="progress-stage">
                            <v-icon color="success" size="small" class="mr-2">mdi-check-circle</v-icon>
                            <span>
                                Complete! Generated {{ progressInfo.response_length }} characters in
                                {{ progressInfo.total_chunks }} chunks
                            </span>
                        </div>
                    </div>
                </div>

                <!-- Fallback Loading indicator (only if no progress info yet and not connecting) -->
                <div
                    v-else-if="isGenerating && !streamingMessage && !progressInfo && !isConnecting"
                    class="chat-message chat-message--assistant"
                >
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
                    auto-grow
                    max-rows="8"
                    variant="outlined"
                    density="compact"
                    hide-details
                    class="compact-input growing-input"
                    :disabled="isGenerating"
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
import { ref, computed, watch, nextTick } from 'vue';
import { useChat } from '@/composables/useChat';
import ChatMessage from './ChatMessage.vue';
import type { Artifact } from '@/types/chat';
import type { APIError } from '@/types/errors';
import { marked } from 'marked';

const {
    messages,
    isGenerating,
    isConnecting,
    streamingMessage,
    currentError,
    progressInfo,
    sendMessage,
    clearChat,
    clearError,
} = useChat();

// ID of the most recent assistant message that has artifacts — only that one shows apply buttons
const lastArtifactMessageId = computed(() => {
    const withArtifacts = messages.value.filter((m) => m.role === 'assistant' && (m.artifacts?.length || m.yaml));
    return withArtifacts[withArtifacts.length - 1]?.id;
});

interface Props {
    modelValue?: string;
}

const props = withDefaults(defineProps<Props>(), {
    modelValue: '',
});

const emit = defineEmits<{
    'apply-artifact': [artifact: Artifact];
    'update:modelValue': [value: string];
    'has-messages': [hasMessages: boolean];
    error: [error: APIError];
}>();

const internalPrompt = ref(props.modelValue);
const messagesContainer = ref<HTMLElement>();
const isSending = ref(false); // Add local sending state

const examplePrompts = [
    'Turn on lights at sunset',
    'Notify me when door opens',
    'Create a dashboard for the living room',
    'Add a weather card to my dashboard',
];

// Simple markdown renderer for streaming content
const renderMarkdown = (content: string): string => {
    if (!content) return '';
    try {
        return marked.parse(content) as string;
    } catch {
        return content;
    }
};

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

// Scroll to bottom when messages, streaming message, connecting state, or progress changes
watch(
    [messages, streamingMessage, progressInfo, isConnecting],
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

    isSending.value = true; // Set immediately
    try {
        await sendMessage(prompt);
    } finally {
        isSending.value = false; // Clear after send completes
    }
};

const handleNewLine = () => {
    internalPrompt.value += '\n';
};

const selectExample = (example: string) => {
    internalPrompt.value = example;
    handleSend();
};

const handleApplyArtifact = (artifact: Artifact) => {
    emit('apply-artifact', artifact);
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

.chat-message {
    margin-bottom: 1rem;
}

.chat-message__header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
}

.chat-message__role {
    font-weight: 500;
    font-size: 0.875rem;
}

.chat-message__content {
    padding: 0.75rem 1rem;
    background: var(--ha-card-background);
    border-radius: 8px;
    border: 1px solid var(--ha-border);
}

/* Connecting Animation */
.connecting-content {
    padding: 1.5rem 1rem;
}

.connecting-animation {
    display: flex;
    align-items: center;
    gap: 1rem;
}

.pulse-container {
    display: flex;
    gap: 0.5rem;
    align-items: center;
}

.pulse {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: var(--ha-primary-color);
    animation: pulse 1.5s ease-in-out infinite;
}

.pulse-1 {
    animation-delay: 0s;
}

.pulse-2 {
    animation-delay: 0.2s;
}

.pulse-3 {
    animation-delay: 0.4s;
}

@keyframes pulse {
    0%,
    100% {
        opacity: 0.3;
        transform: scale(0.8);
    }

    50% {
        opacity: 1;
        transform: scale(1.2);
    }
}

.connecting-text {
    flex: 1;
}

.connecting-message {
    font-weight: 500;
    color: var(--ha-primary-text);
    margin-bottom: 0.25rem;
}

.connecting-submessage {
    font-size: 0.8rem;
    color: var(--ha-secondary-text);
    font-style: italic;
}

.streaming-status {
    margin-left: auto;
    font-size: 0.75rem;
    color: var(--ha-secondary-text);
    display: flex;
    align-items: center;
    gap: 0.25rem;
}

.chunks-badge {
    background: rgba(var(--v-theme-primary), 0.2);
    padding: 0.125rem 0.375rem;
    border-radius: 10px;
    font-weight: 500;
    font-size: 0.7rem;
    margin-left: 0.25rem;
}

.cursor-blink {
    animation: blink 1s step-end infinite;
    color: var(--ha-primary-color);
    margin-left: 2px;
    font-weight: bold;
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

.completion-message {
    animation: fadeOut 2s ease-in-out 1s forwards;
}

@keyframes fadeOut {
    to {
        opacity: 0;
        height: 0;
        margin: 0;
        overflow: hidden;
    }
}

.progress-content {
    padding: 1rem;
}

.progress-stage {
    display: flex;
    align-items: flex-start;
    gap: 0.5rem;
    font-size: 0.875rem;
    color: var(--ha-primary-text);
}

.context-stats {
    flex: 1;
}

.stats-title {
    font-weight: 500;
    margin-bottom: 0.5rem;
}

.stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 0.5rem;
}

.stat-item {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    font-size: 0.8rem;
    color: var(--ha-secondary-text);
    padding: 0.25rem 0.5rem;
    background: rgba(var(--v-theme-primary), 0.1);
    border-radius: 4px;
}

.markdown-content {
    line-height: 1.6;
}

.markdown-content :deep(code) {
    background: rgba(var(--v-theme-surface-variant), 0.5);
    padding: 0.125rem 0.25rem;
    border-radius: 3px;
    font-size: 0.875em;
}

.markdown-content :deep(pre) {
    background: rgba(var(--v-theme-surface-variant), 0.5);
    padding: 0.75rem;
    border-radius: 6px;
    overflow-x: auto;
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

/* NEW: allow v-textarea to grow with content */
.compact-input {
    font-size: 0.875rem;
    max-height: none;
}

.compact-input :deep(textarea) {
    /* let Vuetify auto-grow work; allow scroll when reaching max-rows */
    overflow-y: auto;
    resize: none;
}

/* keep existing field styling */
.compact-input :deep(.v-field) {
    border-radius: 20px;
    padding: 2px 10px;
}

.compact-input :deep(.v-field__input) {
    padding: 6px 0;
    min-height: 32px;

    /* ADD THESE LINES */
    max-height: none;
    align-items: stretch;
}

.compact-input :deep(.v-field__append-inner) {
    padding-top: 0;
    align-items: center;
}

/* you can keep or remove this, but it must not force hidden after our override */
.growing-input :deep(textarea) {
    /* remove overflow-y: hidden; or let compact-input override it */
    /* overflow-y: hidden; */
}
</style>
