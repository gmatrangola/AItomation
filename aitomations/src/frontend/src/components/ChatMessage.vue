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
            <v-btn
                v-if="message.role === 'assistant' && message.content"
                class="chat-message__copy-all"
                :icon="copiedAll ? 'mdi-check' : 'mdi-content-copy'"
                :color="copiedAll ? 'success' : undefined"
                size="x-small"
                variant="text"
                :title="copiedAll ? 'Copied!' : 'Copy entire response'"
                @click="copyAll"
            />
        </div>

        <div class="chat-message__content">
            <!-- User messages - plain text -->
            <div v-if="message.role === 'user'" class="chat-message__text">
                {{ message.content }}
            </div>

            <!-- Assistant messages - markdown with each artifact's apply button inline,
                 directly after the YAML block it applies to. The @click delegates copy-code
                 buttons that useMarkdown injects into each code block. -->
            <div v-else @click="onCopyCodeClick">
                <template v-for="(seg, i) in contentSegments" :key="i">
                    <div v-if="seg.html" class="markdown-content" v-html="seg.html"></div>
                    <div v-if="seg.artifacts.length && showInstallButton" class="chat-message__actions">
                        <v-btn
                            v-for="(artifact, j) in seg.artifacts"
                            :key="j"
                            :color="artifactColor(artifact.kind)"
                            variant="elevated"
                            size="small"
                            @click="$emit('apply-artifact', artifact)"
                        >
                            <v-icon start size="small">{{ artifactIcon(artifact.kind) }}</v-icon>
                            {{ artifactLabel(artifact.kind) }}
                        </v-btn>
                    </div>
                </template>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { useMarkdown } from '@/composables/useMarkdown';
import { ARTIFACT_KINDS, HELPER_KINDS, type Artifact, type ArtifactKind, type ChatMessage } from '@/types/chat';

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

// Split the assistant content so each artifact's apply button renders inline — right after the
// YAML block it applies to — instead of every button being grouped at the end of the message.
interface Segment {
    html: string;
    artifacts: Artifact[];
}

const contentSegments = computed((): Segment[] => {
    const content = props.message.content ?? '';
    const artifacts = messageArtifacts.value;
    if (!artifacts.length) return [{ html: renderMarkdown(content), artifacts: [] }];

    // End offset of each applyable YAML block, in document order (same scan as the extractor).
    const regex = /```yaml\n([\s\S]*?)\n```/g;
    const blockEnds: number[] = [];
    let match: RegExpExecArray | null;
    while ((match = regex.exec(content)) !== null) {
        const kindMatch = match[1].match(/#\s*aitomation_kind:\s*([a-z_]+)/i);
        if (!kindMatch) continue;
        if (!ARTIFACT_KINDS.includes(kindMatch[1].toLowerCase() as ArtifactKind)) continue;
        blockEnds.push(regex.lastIndex);
    }

    // If blocks don't line up with the artifacts (legacy/partial/streaming), fall back to the old
    // behavior: render everything, then all buttons grouped at the end.
    if (blockEnds.length !== artifacts.length) {
        return [{ html: renderMarkdown(content), artifacts }];
    }

    const segments: Segment[] = [];
    let start = 0;
    blockEnds.forEach((end, i) => {
        segments.push({ html: renderMarkdown(content.slice(start, end)), artifacts: [artifacts[i]] });
        start = end;
    });
    const tail = content.slice(start);
    if (tail.trim()) segments.push({ html: renderMarkdown(tail), artifacts: [] });
    return segments;
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

// --- copy to clipboard ---
const copiedAll = ref(false);

const writeClipboard = async (text: string): Promise<boolean> => {
    try {
        if (navigator.clipboard?.writeText) {
            await navigator.clipboard.writeText(text);
            return true;
        }
    } catch {
        // fall through to the legacy execCommand path (e.g. non-secure contexts)
    }
    try {
        const ta = document.createElement('textarea');
        ta.value = text;
        ta.style.position = 'fixed';
        ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.select();
        const ok = document.execCommand('copy');
        document.body.removeChild(ta);
        return ok;
    } catch {
        return false;
    }
};

const copyAll = async () => {
    if (!(await writeClipboard(props.message.content ?? ''))) return;
    copiedAll.value = true;
    setTimeout(() => (copiedAll.value = false), 1500);
};

// Delegated handler for the per-code-block copy buttons useMarkdown injects.
const onCopyCodeClick = async (event: MouseEvent) => {
    const btn = (event.target as HTMLElement | null)?.closest('.copy-code-btn') as HTMLElement | null;
    if (!btn) return;
    const code = btn.closest('.code-block')?.querySelector('pre')?.textContent ?? '';
    if (!(await writeClipboard(code))) return;
    const icon = btn.querySelector('i');
    if (icon) {
        const previous = icon.className;
        icon.className = 'mdi mdi-check';
        btn.classList.add('copied');
        setTimeout(() => {
            icon.className = previous;
            btn.classList.remove('copied');
        }, 1500);
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

.chat-message__copy-all {
    margin-left: 0.25rem;
}

/* Copy button injected into each rendered code block (see useMarkdown). Lives in v-html
   output, so it must be styled without scoping via :deep(). */
:deep(.code-block) {
    position: relative;
}

:deep(.code-block .copy-code-btn) {
    position: absolute;
    top: 0.4rem;
    right: 0.4rem;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.7rem;
    height: 1.7rem;
    padding: 0;
    border: 1px solid var(--ha-border);
    border-radius: 6px;
    background: var(--ha-card-background);
    color: var(--ha-secondary-text);
    cursor: pointer;
    opacity: 0;
    transition:
        opacity 0.15s ease,
        color 0.15s ease;
    font-size: 0.95rem;
    line-height: 1;
}

:deep(.code-block:hover .copy-code-btn) {
    opacity: 0.85;
}

:deep(.code-block .copy-code-btn:hover) {
    opacity: 1;
    color: var(--ha-primary-text);
}

:deep(.code-block .copy-code-btn.copied) {
    opacity: 1;
    color: rgb(var(--v-theme-success));
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
    margin: 0.4rem 0 0.85rem;
}
</style>
