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

            <!-- Assistant messages - markdown with each artifact's apply button inline,
                 directly after the YAML block it applies to. The @click delegates copy-code
                 buttons that useMarkdown injects into each code block. -->
            <div v-else @click="onCopyCodeClick">
                <!-- Top-level: copy the entire response as Markdown -->
                <div v-if="message.content" class="chat-message__md-toolbar">
                    <v-btn
                        class="chat-message__copy-md"
                        size="x-small"
                        variant="text"
                        :color="copiedAll ? 'success' : copyFailed ? 'error' : undefined"
                        :title="copiedAll ? 'Copied!' : 'Copy the entire response as Markdown'"
                        @click="copyAll"
                    >
                        <v-icon start size="x-small">
                            {{ copiedAll ? 'mdi-check' : copyFailed ? 'mdi-alert-circle-outline' : 'mdi-content-copy' }}
                        </v-icon>
                        {{ copiedAll ? 'Copied' : copyFailed ? 'Copy failed' : 'Copy Markdown' }}
                    </v-btn>
                </div>

                <template v-for="(seg, i) in contentSegments" :key="i">
                    <div v-if="seg.html" class="markdown-content" v-html="seg.html"></div>
                    <div v-if="seg.items.length && showInstallButton" class="chat-message__actions">
                        <v-btn
                            v-for="item in seg.items"
                            :key="item.index"
                            :color="statusFor(item.index) === 'done' ? 'success' : artifactColor(item.artifact.kind)"
                            variant="elevated"
                            size="small"
                            :loading="statusFor(item.index) === 'applying'"
                            :disabled="statusFor(item.index) === 'done' || applyingAll"
                            @click="applyOne(item.index, item.artifact)"
                        >
                            <v-icon start size="small">
                                {{ statusFor(item.index) === 'done' ? 'mdi-check' : artifactIcon(item.artifact.kind) }}
                            </v-icon>
                            {{ buttonLabel(item.index, item.artifact.kind) }}
                        </v-btn>
                    </div>
                </template>

                <!-- Apply all remaining artifacts in dependency order -->
                <div v-if="showApplyAll" class="chat-message__apply-all">
                    <v-btn color="primary" variant="tonal" size="small" :loading="applyingAll" @click="applyAll">
                        <v-icon start size="small">mdi-checkbox-multiple-marked-outline</v-icon>
                        Apply All
                    </v-btn>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue';
import { useMarkdown } from '@/composables/useMarkdown';
import { ARTIFACT_KINDS, HELPER_KINDS, type Artifact, type ArtifactKind, type ChatMessage } from '@/types/chat';

const { renderMarkdown } = useMarkdown();

type ApplyStatus = 'idle' | 'applying' | 'done' | 'error';

interface Props {
    message: ChatMessage;
    showInstallButton?: boolean;
    // Applies an artifact and resolves true on success (provided by the parent view).
    applyFn?: (artifact: Artifact) => Promise<boolean>;
}

const props = withDefaults(defineProps<Props>(), {
    showInstallButton: true,
    applyFn: undefined,
});

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
// `index` is the artifact's position in messageArtifacts, used to key its apply status.
interface ArtifactItem {
    artifact: Artifact;
    index: number;
}
interface Segment {
    html: string;
    items: ArtifactItem[];
}

const contentSegments = computed((): Segment[] => {
    const content = props.message.content ?? '';
    const artifacts = messageArtifacts.value;
    const allItems = artifacts.map((artifact, index) => ({ artifact, index }));
    if (!artifacts.length) return [{ html: renderMarkdown(content), items: [] }];

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
        return [{ html: renderMarkdown(content), items: allItems }];
    }

    const segments: Segment[] = [];
    let start = 0;
    blockEnds.forEach((end, i) => {
        segments.push({ html: renderMarkdown(content.slice(start, end)), items: [allItems[i]] });
        start = end;
    });
    const tail = content.slice(start);
    if (tail.trim()) segments.push({ html: renderMarkdown(tail), items: [] });
    return segments;
});

// --- per-artifact apply status + Apply All ---
const statuses = reactive<Record<number, ApplyStatus>>({});
const applyingAll = ref(false);

const statusFor = (index: number): ApplyStatus => statuses[index] ?? 'idle';

const buttonLabel = (index: number, kind: ArtifactKind): string => {
    const status = statusFor(index);
    if (status === 'done') return 'Done';
    if (status === 'error') return 'Retry';
    return artifactLabel(kind);
};

const applyOne = async (index: number, artifact: Artifact): Promise<boolean> => {
    if (!props.applyFn || statusFor(index) === 'applying' || statusFor(index) === 'done') {
        return statusFor(index) === 'done';
    }
    statuses[index] = 'applying';
    try {
        const ok = await props.applyFn(artifact);
        statuses[index] = ok ? 'done' : 'error';
        return ok;
    } catch {
        statuses[index] = 'error';
        return false;
    }
};

const allApplied = computed(
    () => messageArtifacts.value.length > 0 && messageArtifacts.value.every((_, i) => statusFor(i) === 'done')
);

const showApplyAll = computed(() => props.showInstallButton && messageArtifacts.value.length > 1 && !allApplied.value);

const applyAll = async () => {
    if (applyingAll.value) return;
    applyingAll.value = true;
    try {
        // Apply in dependency order; stop on the first failure so dependents aren't applied broken.
        for (let i = 0; i < messageArtifacts.value.length; i++) {
            if (statusFor(i) === 'done') continue;
            const ok = await applyOne(i, messageArtifacts.value[i]);
            if (!ok) break;
        }
    } finally {
        applyingAll.value = false;
    }
};

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
    // navigator.clipboard only exists in secure contexts; the HA companion apps serve the
    // ingress UI over plain http, so it's usually undefined there — fall back to execCommand.
    try {
        if (window.isSecureContext && navigator.clipboard?.writeText) {
            await navigator.clipboard.writeText(text);
            return true;
        }
    } catch {
        // fall through to the legacy execCommand path
    }
    try {
        const ta = document.createElement('textarea');
        ta.value = text;
        ta.setAttribute('readonly', '');
        // Keep it in the viewport but visually hidden — offscreen/opacity:0 elements can't be
        // selected for copy in some webviews (e.g. the macOS HA app).
        ta.style.position = 'fixed';
        ta.style.top = '0';
        ta.style.left = '0';
        ta.style.width = '1px';
        ta.style.height = '1px';
        ta.style.padding = '0';
        ta.style.border = 'none';
        ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.focus();
        ta.select();
        ta.setSelectionRange(0, text.length);
        const ok = document.execCommand('copy');
        document.body.removeChild(ta);
        return ok;
    } catch {
        return false;
    }
};

const copyFailed = ref(false);

const copyAll = async () => {
    if (await writeClipboard(props.message.content ?? '')) {
        copiedAll.value = true;
        setTimeout(() => (copiedAll.value = false), 1500);
    } else {
        copyFailed.value = true;
        setTimeout(() => (copyFailed.value = false), 2500);
    }
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

/* Top-of-response "Copy Markdown" toolbar */
.chat-message__md-toolbar {
    display: flex;
    justify-content: flex-end;
    margin-bottom: 0.15rem;
}

/* The button is variant="text" with no color in the default (idle) state, so Vuetify's
   light-theme near-black text was invisible on the dark HA card. Force the HA secondary-text
   color when idle; the success/error color props still win in those states. */
.chat-message__copy-md:not(.text-success):not(.text-error) {
    color: var(--ha-secondary-text) !important;
}

/* "Apply All" sits below the last artifact button */
.chat-message__apply-all {
    margin-top: 0.6rem;
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
