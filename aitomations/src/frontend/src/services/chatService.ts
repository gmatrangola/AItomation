import type { ChatMessage } from '@/types/chat';
import { v4 as uuidv4 } from 'uuid';

export class ChatService {
    /**
     * Send message with streaming response
     * @param prompt User's message
     * @param conversationHistory Previous messages
     * @param onChunk Callback for each chunk of text
     * @returns Complete message with extracted YAML
     */
    async sendMessageStream(
        prompt: string,
        conversationHistory: ChatMessage[] = [],
        onChunk: (text: string) => void
    ): Promise<{ message: ChatMessage; error?: string }> {
        console.log('[ChatService] sendMessageStream called');
        console.log('[ChatService] Prompt:', prompt);
        console.log('[ChatService] History length:', conversationHistory.length);
        
        try {
            const requestBody = {
                prompt,
                conversation_history: conversationHistory.map(msg => ({
                    role: msg.role,
                    content: msg.content
                }))
            };
            
            console.log('[ChatService] Fetching stream from api/generate_automation/stream');
            
            const response = await fetch('api/generate_automation/stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody),
            });

            console.log('[ChatService] Stream response status:', response.status);

            if (!response.ok) {
                let errorData;
                try {
                    errorData = await response.json();
                } catch {
                    errorData = { error: `HTTP ${response.status}: ${response.statusText}` };
                }
                console.error('[ChatService] Error response:', errorData);
                throw new Error(errorData.error || errorData.detail || `HTTP ${response.status}`);
            }

            // Read the stream
            const reader = response.body?.getReader();
            const decoder = new TextDecoder();
            let fullResponse = '';
            
            if (!reader) {
                throw new Error('No response body reader available');
            }

            while (true) {
                const { done, value } = await reader.read();
                
                if (done) {
                    console.log('[ChatService] Stream complete');
                    break;
                }

                // Decode the chunk
                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            
                            if (data.type === 'content') {
                                fullResponse += data.text;
                                onChunk(data.text);
                            } else if (data.type === 'done') {
                                fullResponse = data.full_response;
                                console.log('[ChatService] Received done signal');
                            } else if (data.type === 'error') {
                                throw new Error(data.error);
                            }
                        } catch (e) {
                            if (e instanceof Error && e.message !== 'Unexpected end of JSON input') {
                                console.error('[ChatService] Error parsing SSE data:', e);
                            }
                        }
                    }
                }
            }

            const message: ChatMessage = {
                id: uuidv4(),
                role: 'assistant',
                content: fullResponse || 'No response received',
                timestamp: new Date(),
                yaml: this.extractYamlFromMarkdown(fullResponse || '')
            };

            console.log('[ChatService] Created message:', message);
            console.log('[ChatService] Extracted YAML:', message.yaml ? 'Yes' : 'No');

            return { message };
        } catch (error: any) {
            console.error('[ChatService] Exception caught:', error);
            console.error('[ChatService] Error stack:', error.stack);
            return {
                message: {
                    id: uuidv4(),
                    role: 'assistant',
                    content: `Error: ${error.message}`,
                    timestamp: new Date(),
                },
                error: error.message
            };
        }
    }

    private extractYamlFromMarkdown(markdown: string): string | undefined {
        if (!markdown) return undefined;
        const match = markdown.match(/```yaml\n([\s\S]*?)\n```/);
        const yaml = match ? match[1].trim() : undefined;
        console.log('[ChatService] YAML extraction:', yaml ? 'Found' : 'Not found');
        return yaml;
    }
}