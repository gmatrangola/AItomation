<template>
    <div :class="['chat-message', `chat-message--${message.role}`]">
        <div class="chat-message__header">
            <v-avatar :color="message.role === 'user' ? 'primary' : 'success'" size="24">
                <v-icon size="x-small">{{ message.role === 'user' ? 'mdi-account' : 'mdi-robot' }}</v-icon>
            </v-avatar>
            <span class="chat-message__role">
                {{ message.role === 'user' ? 'You' : 'Assistant' }}
            </span>
            <span class="chat-message__time">
                {{ formatTime(message.timestamp) }}
            </span>
        </div>

        <div class="chat-message__content">
            <!-- User messages - plain text -->
            <div v-if="message.role === 'user'" class="chat-message__text">
                {{ message.content }}
            </div>

            <!-- Assistant messages - markdown with syntax highlighting -->
            <div v-else class="markdown-content" v-html="renderMarkdown(message.content)"></div>

            <!-- Install button for messages with YAML -->
            <div v-if="message.yaml && showInstallButton" class="chat-message__actions mt-2">
                <v-btn color="success" variant="elevated" size="small" @click="$emit('install', message.yaml)">
                    <v-icon start size="small">mdi-download</v-icon>
                    Install
                </v-btn>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { useMarkdown } from '@/composables/useMarkdown';
import type { ChatMessage } from '@/types/chat';

const { renderMarkdown } = useMarkdown();

interface Props {
    message: ChatMessage;
    showInstallButton?: boolean;
}

withDefaults(defineProps<Props>(), {
    showInstallButton: true
});

defineEmits<{
    'install': [yaml: string];
}>();

const formatTime = (date: Date): string => {
    return new Intl.DateTimeFormat('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
    }).format(date);
};
</script>

<style scoped>
.chat-message {
    margin-bottom: 0.875rem;
    animation: slideIn 0.2s ease-out;
}

@keyframes slideIn {
    from {
        opacity: 0;
        transform: translateY(6px);
    }

    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.chat-message__header {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    margin-bottom: 0.4rem;
}

.chat-message__role {
    font-weight: 600;
    font-size: 0.8rem;
    color: var(--ha-primary-text);
}

.chat-message__time {
    font-size: 0.7rem;
    color: var(--ha-secondary-text);
    margin-left: auto;
}

.chat-message__content {
    margin-left: 1.75rem;
    padding: 0.65rem 0.875rem;
    border-radius: 10px;
}

.chat-message--user .chat-message__content {
    background-color: var(--ha-card-background);
    border: 1px solid var(--ha-border);
}

.chat-message--assistant .chat-message__content {
    background-color: var(--ha-card-background);
    border: 1px solid var(--ha-primary-color);
    border-left-width: 3px;
}

.chat-message__text {
    color: var(--ha-primary-text);
    white-space: pre-wrap;
    word-wrap: break-word;
    font-size: 0.875rem;
}

.chat-message__actions {
    display: flex;
    justify-content: flex-start;
    padding-top: 0.5rem;
    border-top: 1px solid var(--ha-border);
}
</style>