<template>
    <div class="ai-chat-container">
        <!-- Chat Messages -->
        <v-card class="chat-messages mb-4" elevation="2">
            <v-card-text ref="messagesContainer" class="messages-container">
                <template v-if="messages.length === 0">
                    <div class="empty-state">
                        <v-icon size="64" color="primary">mdi-chat-outline</v-icon>
                        <h3 class="mt-4">Start a Conversation</h3>
                        <p class="text-secondary">
                            Describe the automation you'd like to create, and I'll help you build it.
                        </p>
                        <div class="example-prompts mt-4">
                            <v-chip v-for="example in examplePrompts" :key="example" class="ma-1"
                                @click="selectExample(example)">
                                {{ example }}
                            </v-chip>
                        </div>
                    </div>
                </template>

                <template v-else>
                    <div class="messages-header mb-3">
                        <v-btn @click="handleClearChat" variant="text" size="small" color="error">
                            <v-icon start>mdi-delete</v-icon>
                            Clear Chat
                        </v-btn>
                    </div>

                    <ChatMessage v-for="message in messages" :key="message.id" :message="message"
                        :show-install-button="message.yaml === latestYaml" @install="handleInstallAutomation" />

                    <!-- Loading indicator -->
                    <div v-if="isGenerating" class="chat-message chat-message--assistant">
                        <div class="chat-message__header">
                            <v-avatar color="success" size="32">
                                <v-icon>mdi-robot</v-icon>
                            </v-avatar>
                            <span class="chat-message__role">AI Assistant</span>
                        </div>
                        <div class="chat-message__content">
                            <v-progress-linear indeterminate color="primary"></v-progress-linear>
                            <p class="text-secondary mt-2">Thinking...</p>
                        </div>
                    </div>
                </template>
            </v-card-text>
        </v-card>

        <!-- Input Area -->
        <v-card class="chat-input" elevation="2">
            <v-card-text>
                <v-textarea v-model="internalPrompt"
                    :placeholder="messages.length === 0 ? 'e.g., Turn on the porch light at sunset and turn it off at sunrise' : 'Ask for changes or provide more details...'"
                    rows="2" auto-grow :disabled="isGenerating" variant="outlined"
                    @keydown.enter.exact.prevent="handleSend" @keydown.enter.shift.exact="handleNewLine" hide-details>
                    <template v-slot:append-inner>
                        <v-btn :disabled="!internalPrompt.trim() || isGenerating" @click="handleSend" icon
                            color="primary" variant="flat">
                            <v-icon>mdi-send</v-icon>
                        </v-btn>
                    </template>
                </v-textarea>
                <div class="input-hint mt-2">
                    <small class="text-secondary">
                        Press Enter to send, Shift+Enter for new line
                    </small>
                </div>
            </v-card-text>
        </v-card>
    </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, onMounted } from 'vue';
import { useChat } from '@/composables/useChat';
import { ChatStorage } from '@/services/chatStorage';
import ChatMessage from './ChatMessage.vue';

console.log('[AIChat] Component script loaded');

const { messages, isGenerating, isLoadingHistory, latestYaml, sendMessage, clearChat } = useChat();

console.log('[AIChat] useChat composable loaded');

interface Props {
    modelValue?: string;
}

const props = withDefaults(defineProps<Props>(), {
    modelValue: '',
});

const emit = defineEmits<{
    'install-automation': [yaml: string];
    'update:modelValue': [value: string];
}>();

const internalPrompt = ref(props.modelValue);
const messagesContainer = ref<HTMLElement>();
const wasRestored = ref(false);

const examplePrompts = [
    'Turn on lights at sunset',
    'Notify me when the door opens',
    'Start the coffee maker on weekday mornings',
];

onMounted(async () => {
    console.log('[AIChat] Component mounted');

    // Wait for chat history to load
    watch(isLoadingHistory, async (loading) => {
        if (!loading && messages.value.length > 0) {
            console.log('[AIChat] Chat history loaded with', messages.value.length, 'messages');
            wasRestored.value = true;
            // Hide the indicator after 3 seconds
            setTimeout(() => {
                wasRestored.value = false;
            }, 3000);
        }
    }, { immediate: true });
});

// Watch for external prompt changes
watch(
    () => props.modelValue,
    (newValue) => {
        console.log('[AIChat] modelValue changed:', newValue);
        internalPrompt.value = newValue;
    }
);

// Emit prompt changes
watch(internalPrompt, (newValue) => {
    console.log('[AIChat] internalPrompt changed:', newValue);
    emit('update:modelValue', newValue);
});

// Scroll to bottom when new messages arrive
watch(messages, async (newMessages) => {
    console.log('[AIChat] Messages changed, count:', newMessages.length);
    await nextTick();
    if (messagesContainer.value) {
        messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
        console.log('[AIChat] Scrolled to bottom');
    }
}, { deep: true });

const handleSend = async () => {
    console.log('[AIChat] handleSend called');
    console.log('[AIChat] internalPrompt:', internalPrompt.value);
    console.log('[AIChat] isGenerating:', isGenerating.value);

    if (!internalPrompt.value.trim() || isGenerating.value) {
        console.log('[AIChat] handleSend aborted');
        return;
    }

    const prompt = internalPrompt.value.trim();
    console.log('[AIChat] Sending prompt:', prompt);
    internalPrompt.value = '';

    console.log('[AIChat] Calling sendMessage...');
    await sendMessage(prompt);
    console.log('[AIChat] sendMessage completed');
};

const handleNewLine = () => {
    console.log('[AIChat] handleNewLine called');
    internalPrompt.value += '\n';
};

const selectExample = (example: string) => {
    console.log('[AIChat] selectExample called:', example);
    internalPrompt.value = example;
    handleSend();
};

const handleClearChat = async () => {
    console.log('[AIChat] handleClearChat called');
    if (confirm('Are you sure you want to clear the chat history? This will delete it from Home Assistant storage.')) {
        await clearChat();
        internalPrompt.value = '';
        console.log('[AIChat] Chat cleared');
    } else {
        console.log('[AIChat] Clear cancelled');
    }
};

const handleInstallAutomation = (yaml: string) => {
    console.log('[AIChat] handleInstallAutomation called');
    console.log('[AIChat] YAML length:', yaml.length);
    emit('install-automation', yaml);
};
</script>

<style scoped>
.ai-chat-container {
    display: flex;
    flex-direction: column;
    height: 100%;
}

.chat-messages {
    flex: 1;
    overflow: hidden;
    display: flex;
    flex-direction: column;
}

.messages-container {
    overflow-y: auto;
    max-height: 600px;
    min-height: 400px;
}

.messages-header {
    display: flex;
    justify-content: flex-end;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--ha-border);
}

.empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 3rem 1rem;
    color: var(--ha-secondary-text);
}

.empty-state h3 {
    color: var(--ha-primary-text);
}

.example-prompts {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 0.5rem;
    max-width: 600px;
}

.example-prompts .v-chip {
    cursor: pointer;
}

.chat-input {
    flex-shrink: 0;
}

.input-hint {
    text-align: right;
}
</style>