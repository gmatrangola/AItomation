import { ARTIFACT_KINDS, type Artifact, type ArtifactKind, type ChatMessage } from '@/types/chat';
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
        try {
            const requestBody = {
                prompt,
                conversation_history: conversationHistory.map((msg) => ({
                    role: msg.role,
                    content: msg.content,
                })),
            };

            const response = await fetch('api/generate_automation/stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody),
            });

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

            while (true) {
                const { done, value } = await reader.read();
                if (done) {
                    // ChatService Stream complet
                    break;
                }

                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const jsonStr = line.slice(6);
                            const data = JSON.parse(jsonStr);
                            if (data.type === 'content') {
                                fullResponse += data.text;
                                onChunk(data.text);
                            } else if (data.type === 'done') {
                                fullResponse = data.full_response;
                            } else if (data.type === 'error') {
                                // Structured error from backend
                                console.error('[ChatService] ❌ ERROR EVENT from backend:', data);
                                throw {
                                    error_code: data.error_code,
                                    context: data.context,
                                };
                            } else if (data.type === 'progress') {
                                // Progress update
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

            const artifacts = this.extractArtifactsFromMarkdown(fullResponse || '');
            return {
                message: {
                    id: uuidv4(),
                    role: 'assistant',
                    content: fullResponse || 'No response received',
                    timestamp: new Date(),
                    artifacts,
                    // Legacy fields for backward compat with existing chat history
                    yaml: artifacts[0]?.yaml,
                    artifactKind: artifacts[0]?.kind,
                },
            };
        } catch (error) {
            console.error('[ChatService] ❌ CAUGHT ERROR:', error);

            // Check if it's a structured error
            const apiError = error as APIError;
            if (apiError.error_code) {
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

    private extractArtifactsFromMarkdown(markdown: string): Artifact[] {
        if (!markdown) return [];
        const artifacts: Artifact[] = [];
        const regex = /```yaml\n([\s\S]*?)\n```/g;
        let match;
        while ((match = regex.exec(markdown)) !== null) {
            const yaml = match[1].trim();
            // Only process blocks that carry our kind marker with a recognized kind
            const kindMatch = yaml.match(/#\s*aitomation_kind:\s*([a-z_]+)/i);
            if (!kindMatch) continue;
            const kind = kindMatch[1].toLowerCase() as ArtifactKind;
            if (!ARTIFACT_KINDS.includes(kind)) continue;
            const idMatch = yaml.match(/#\s*aitomation_id:\s*(\S+)/i);
            const artifact: Artifact = { yaml, kind };
            if (idMatch) artifact.id = idMatch[1];
            artifacts.push(artifact);
        }
        return artifacts;
    }
}
