import { ref } from 'vue';
import { ChatService } from '@/services/chatService';
import { ChatStorage } from '@/services/chatStorage';
import type { ChatMessage } from '@/types/chat';
import type { APIError } from '@/types/errors';
import { v4 as uuidv4 } from 'uuid';

const chatService = new ChatService();

export function useChat() {
    const messages = ref<ChatMessage[]>([]);
    const isGenerating = ref(false);
    const latestYaml = ref<string | undefined>();
    const streamingMessage = ref<ChatMessage | null>(null);
    const currentError = ref<APIError | null>(null);

    // Load chat history on mount
    const loadHistory = async () => {
        const stored = await ChatStorage.load();
        if (stored && stored.length > 0) {
            messages.value = stored;
            const lastAssistantMsg = [...stored].reverse().find((m) => m.role === 'assistant');
            if (lastAssistantMsg?.yaml) {
                latestYaml.value = lastAssistantMsg.yaml;
            }
        }
    };

    loadHistory();

    const sendMessage = async (prompt: string) => {
        currentError.value = null;

        // Add user message
        const userMessage: ChatMessage = {
            id: uuidv4(),
            role: 'user',
            content: prompt,
            timestamp: new Date(),
        };
        messages.value.push(userMessage);

        // Initialize streaming message
        streamingMessage.value = {
            id: uuidv4(),
            role: 'assistant',
            content: '',
            timestamp: new Date(),
        };

        isGenerating.value = true;

        try {
            const { message, error } = await chatService.sendMessageStream(prompt, messages.value, (chunk: string) => {
                if (streamingMessage.value) {
                    streamingMessage.value.content += chunk;
                }
            });

            if (error) {
                currentError.value = error;
                streamingMessage.value = null;
            } else {
                // Replace streaming message with final message
                messages.value.push(message);
                streamingMessage.value = null;

                if (message.yaml) {
                    latestYaml.value = message.yaml;
                }

                // Save to storage
                await ChatStorage.save(messages.value);
            }
        } catch (error) {
            currentError.value = {
                error_code: 'UNKNOWN_ERROR',
                context: { details: error instanceof Error ? error.message : 'Unknown error' },
            };
            streamingMessage.value = null;
        } finally {
            isGenerating.value = false;
        }
    };

    const clearChat = async () => {
        messages.value = [];
        latestYaml.value = undefined;
        currentError.value = null;
        streamingMessage.value = null;
        await ChatStorage.clear();
    };

    const clearError = () => {
        currentError.value = null;
    };

    return {
        messages,
        isGenerating,
        latestYaml,
        streamingMessage,
        currentError,
        sendMessage,
        clearChat,
        clearError,
    };
}
