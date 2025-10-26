import type { ChatMessage } from '@/types/chat';
import type { APIError } from '@/types/errors';
import { v4 as uuidv4 } from 'uuid';

export interface ProgressEvent {
    stage: 'initializing_context' | 'gathering_context' | 'context_ready' | 'generating' | 'complete';
    stats?: {
        entities: number;
        services: number;
        automations: number;
        prompt_length: number;
    };
    provider?: string;
    chunks_received?: number;
    total_chunks?: number;
    response_length?: number;
}

export class ChatService {
    /**
     * Send message with streaming response
     * @param prompt User's message
     * @param conversationHistory Previous messages
     * @param onChunk Callback for each chunk of text
     * @param onProgress Callback for progress updates
     * @returns Complete message with extracted YAML
     */
    async sendMessageStream(
        prompt: string,
        conversationHistory: ChatMessage[] = [],
        onChunk: (text: string) => void,
        onProgress?: (progress: ProgressEvent) => void
    ): Promise<{ message: ChatMessage; error?: APIError }> {
        console.log('[ChatService] sendMessageStream called with prompt:', prompt);

        try {
            const requestBody = {
                prompt,
                conversation_history: conversationHistory.map((msg) => ({
                    role: msg.role,
                    content: msg.content,
                })),
            };

            console.log('[ChatService] Sending request to:', 'api/generate_automation/stream');

            const response = await fetch('api/generate_automation/stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody),
            });

            console.log('[ChatService] Response status:', response.status, response.ok);

            if (!response.ok) {
                // Try to get structured error
                try {
                    const errorData = await response.json();
                    console.error('[ChatService] Non-OK response with error data:', errorData);
                    throw errorData;
                } catch (e) {
                    // Fallback to generic error
                    console.error('[ChatService] Non-OK response, fallback error', e);
                    throw {
                        error_code: 'NETWORK_ERROR',
                        context: { status_code: response.status },
                    };
                }
            }

            const reader = response.body?.getReader();
            const decoder = new TextDecoder();
            let fullResponse = '';

            if (!reader) {
                throw {
                    error_code: 'NETWORK_ERROR',
                    context: { details: 'No response body reader' },
                };
            }

            console.log('[ChatService] Starting SSE stream reading...');

            while (true) {
                const { done, value } = await reader.read();
                if (done) {
                    console.log('[ChatService] Stream complete');
                    break;
                }

                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const jsonStr = line.slice(6);
                            console.log('[ChatService] Parsing SSE line:', jsonStr);
                            const data = JSON.parse(jsonStr);
                            console.log('[ChatService] SSE data parsed:', data);

                            if (data.type === 'content') {
                                fullResponse += data.text;
                                onChunk(data.text);
                            } else if (data.type === 'done') {
                                fullResponse = data.full_response;
                                console.log('[ChatService] Received done event');
                            } else if (data.type === 'error') {
                                // Structured error from backend
                                console.error('[ChatService] ❌ ERROR EVENT from backend:', data);
                                throw {
                                    error_code: data.error_code,
                                    context: data.context,
                                };
                            } else if (data.type === 'progress') {
                                // Progress update
                                console.log('[ChatService] Progress update:', data);
                                if (onProgress) {
                                    onProgress({
                                        stage: data.stage,
                                        stats: data.stats,
                                        provider: data.provider,
                                        chunks_received: data.chunks_received,
                                        total_chunks: data.total_chunks,
                                        response_length: data.response_length,
                                    });
                                }
                            } else if (data.type === 'start') {
                                console.log('[ChatService] Received start event');
                            }
                        } catch (e) {
                            // Only log non-JSON parsing errors
                            if (e instanceof SyntaxError) {
                                console.warn('[ChatService] JSON parse error (likely incomplete chunk):', e.message);
                                continue;
                            }
                            // Re-throw structured errors
                            console.error('[ChatService] Re-throwing error:', e);
                            throw e;
                        }
                    }
                }
            }

            return {
                message: {
                    id: uuidv4(),
                    role: 'assistant',
                    content: fullResponse || 'No response received',
                    timestamp: new Date(),
                    yaml: this.extractYamlFromMarkdown(fullResponse || ''),
                },
            };
        } catch (error) {
            console.error('[ChatService] ❌ CAUGHT ERROR:', error);

            // Check if it's a structured error
            const apiError = error as APIError;
            if (apiError.error_code) {
                console.log('[ChatService] Returning structured error:', apiError);
                return {
                    message: {
                        id: uuidv4(),
                        role: 'assistant',
                        content: '',
                        timestamp: new Date(),
                    },
                    error: apiError,
                };
            }

            // Fallback for unexpected errors
            console.log('[ChatService] Returning fallback error');
            return {
                message: {
                    id: uuidv4(),
                    role: 'assistant',
                    content: '',
                    timestamp: new Date(),
                },
                error: {
                    error_code: 'UNKNOWN_ERROR',
                    context: {
                        details: error instanceof Error ? error.message : 'Unknown error',
                    },
                },
            };
        }
    }

    private extractYamlFromMarkdown(markdown: string): string | undefined {
        if (!markdown) return undefined;
        const match = markdown.match(/```yaml\n([\s\S]*?)\n```/);
        return match ? match[1].trim() : undefined;
    }
}
