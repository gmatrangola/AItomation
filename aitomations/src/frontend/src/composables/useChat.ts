import { ref } from 'vue';
import type { ChatMessage } from '@/types/chat';
import type { APIError } from '@/types/errors';
import type { ProgressEvent } from '@/services/chatService';
import { ChatService } from '@/services/chatService';

const chatService = new ChatService();

const messages = ref<ChatMessage[]>([]);
const isGenerating = ref(false);
const isConnecting = ref(false);
const latestYaml = ref<string | undefined>();
const streamingMessage = ref<ChatMessage | null>(null);
const currentError = ref<APIError | null>(null);
const progressInfo = ref<ProgressEvent | null>(null);

export function useChat() {
    // Load chat history on mount
    const loadHistory = async () => {
        try {
            const response = await fetch('api/chat/history');
            if (response.ok) {
                const history = await response.json();
                messages.value = history;
                console.log('[useChat] Loaded chat history:', history.length, 'messages');
            }
        } catch (error) {
            console.error('[useChat] Failed to load history:', error);
        }
    };

    loadHistory();

    const sendMessage = async (prompt: string) => {
        if (isGenerating.value) {
            console.warn('[useChat] Already generating, ignoring new message');
            return;
        }

        // Clear previous error
        currentError.value = null;
        progressInfo.value = null;
        streamingMessage.value = null;

        // Add user message
        const userMessage: ChatMessage = {
            id: crypto.randomUUID(),
            role: 'user',
            content: prompt,
            timestamp: new Date(),
        };
        messages.value.push(userMessage);

        // Start generating
        isGenerating.value = true;
        isConnecting.value = true;

        try {
            const conversationHistory = messages.value;

            let accumulatedContent = '';
            const assistantMessageId = crypto.randomUUID();

            // Use generator pattern for streaming
            const streamGenerator = chatService.sendMessageStream(
                prompt,
                conversationHistory,
                (text: string) => {
                    // onChunk callback
                    accumulatedContent += text;
                    if (streamingMessage.value) {
                        streamingMessage.value.content = accumulatedContent;
                    }
                },
                (progress: ProgressEvent) => {
                    // onProgress callback
                    // Clear connecting state once we receive first progress event
                    if (isConnecting.value) {
                        isConnecting.value = false;
                    }
                    progressInfo.value = progress;
                }
            );

            // Initialize streaming message when we start
            streamingMessage.value = {
                id: assistantMessageId,
                role: 'assistant',
                content: '',
                timestamp: new Date(),
            };

            // Wait for completion
            const result = await streamGenerator;

            if (result.error) {
                currentError.value = result.error;
                streamingMessage.value = null;
            } else {
                // Finalize message
                const assistantMessage: ChatMessage = {
                    id: assistantMessageId,
                    role: 'assistant',
                    content: result.message.content,
                    timestamp: new Date(),
                    yaml: result.message.yaml,
                };

                messages.value.push(assistantMessage);
                latestYaml.value = assistantMessage.yaml;
                streamingMessage.value = null;

                // Save to backend storage
                try {
                    await fetch('api/chat/history', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(messages.value),
                    });
                } catch (error) {
                    console.error('[useChat] Failed to save history:', error);
                }
            }
        } catch (error) {
            console.error('[useChat] Error during streaming:', error);
            currentError.value = {
                error_code: 'NETWORK_ERROR',
                context: {},
            };
            streamingMessage.value = null;
        } finally {
            isGenerating.value = false;
            isConnecting.value = false;
        }
    };

    const clearChat = async () => {
        messages.value = [];
        latestYaml.value = undefined;
        streamingMessage.value = null;
        currentError.value = null;
        progressInfo.value = null;
        isConnecting.value = false;

        try {
            await fetch('api/chat/history', { method: 'DELETE' });
        } catch (error) {
            console.error('[useChat] Failed to clear history:', error);
        }
    };

    const clearError = () => {
        currentError.value = null;
    };

    return {
        messages,
        isGenerating,
        isConnecting,
        latestYaml,
        streamingMessage,
        currentError,
        progressInfo,
        sendMessage,
        clearChat,
        clearError,
    };
}
