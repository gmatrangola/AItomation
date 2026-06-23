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

            <!-- Per-artifact action buttons -->
            <div v-if="messageArtifacts.length && showInstallButton" class="chat-message__actions mt-2">
                <v-btn
                    v-for="(artifact, i) in messageArtifacts"
                    :key="i"
                    :color="artifactColor(artifact.kind)"
                    variant="elevated"
                    size="small"
                    class="mr-2"
                    @click="$emit('apply-artifact', artifact)"
                >
                    <v-icon start size="small">{{ artifactIcon(artifact.kind) }}</v-icon>
                    {{ artifactLabel(artifact.kind) }}
                </v-btn>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useMarkdown } from '@/composables/useMarkdown';
import { HELPER_KINDS, type Artifact, type ArtifactKind, type ChatMessage } from '@/types/chat';

const { renderMarkdown } = useMarkdown();

interface Props {
    message: ChatMessage;
    showInstallButton?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    showInstallButton: true,
});

defineEmits<{
    'apply-artifact': [artifact: Artifact];
}>();

// Normalize to Artifact[] — supports new messages (artifacts[]) and legacy (yaml/artifactKind)
const messageArtifacts = computed((): Artifact[] => {
    if (props.message.artifacts?.length) return props.message.artifacts;
    if (props.message.yaml) {
        return [{ yaml: props.message.yaml, kind: props.message.artifactKind ?? 'automation' }];
    }
    return [];
});

// Turn a helper domain like `input_boolean` into a friendly name like "Input Boolean".
const prettyKind = (kind: ArtifactKind): string =>
    kind
        .split('_')
        .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
        .join(' ');

const artifactLabel = (kind: ArtifactKind): string => {
    if (HELPER_KINDS.has(kind)) return `Create ${prettyKind(kind)}`;
    switch (kind) {
        case 'dashboard':
            return 'Apply Dashboard';
        case 'script':
            return 'Install Script';
        case 'scene':
            return 'Install Scene';
        default:
            return 'Install Automation';
    }
};

const artifactIcon = (kind: ArtifactKind): string => {
    if (HELPER_KINDS.has(kind)) return 'mdi-tune-variant';
    switch (kind) {
        case 'dashboard':
            return 'mdi-view-dashboard';
        case 'script':
            return 'mdi-script-text-outline';
        case 'scene':
            return 'mdi-palette-outline';
        default:
            return 'mdi-download';
    }
};

const artifactColor = (kind: ArtifactKind): string => {
    if (HELPER_KINDS.has(kind)) return 'info';
    switch (kind) {
        case 'dashboard':
            return 'primary';
        case 'script':
            return 'secondary';
        case 'scene':
            return 'warning';
        default:
            return 'success';
    }
};

const formatTime = (date: Date): string => {
    return new Intl.DateTimeFormat('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
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
    flex-wrap: wrap;
    gap: 0.5rem;
    padding-top: 0.5rem;
    border-top: 1px solid var(--ha-border);
}
</style>
