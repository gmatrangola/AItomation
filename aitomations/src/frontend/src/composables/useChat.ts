import { ref } from 'vue';
import type { ChatMessage } from '@/types/chat';
import type { APIError } from '@/types/errors';
import type { ProgressEvent } from '@/services/chatService';
import { ChatService } from '@/services/chatService';
import { v4 as uuidv4 } from 'uuid';

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
                const data = await response.json();
                // Handle both formats: direct array or object with messages property
                const history = data.messages;
                // Ensure we always set an array, even if response is null/undefined
                if (Array.isArray(history)) {
                    // Convert timestamp strings/numbers to Date objects
                    messages.value = history.map((msg: ChatMessage) => ({
                        ...msg,
                        timestamp: msg.timestamp ? new Date(msg.timestamp) : new Date(),
                    }));
                } else {
                    messages.value = [];
                }
            } else {
                messages.value = []; // Ensure empty array on error
            }
        } catch (error) {
            console.error('[useChat] Failed to load history:', error);
            messages.value = []; // Ensure empty array on error
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
            id: uuidv4(),
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
            const assistantMessageId = uuidv4();

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
                    // Convert messages to a format safe for JSON serialization
                    const messagesToSave = messages.value.map((msg) => ({
                        ...msg,
                        timestamp: msg.timestamp instanceof Date ? msg.timestamp.toISOString() : msg.timestamp,
                    }));

                    await fetch('api/chat/history', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ messages: messagesToSave }),
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
