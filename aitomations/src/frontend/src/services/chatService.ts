import type { ChatMessage } from '@/types/chat';
import { v4 as uuidv4 } from 'uuid';

export class ChatService {
    async sendMessage(
        prompt: string,
        conversationHistory: ChatMessage[] = []
    ): Promise<{ message: ChatMessage; error?: string }> {
        console.log('[ChatService] sendMessage called');
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
            
            console.log('[ChatService] Request body:', JSON.stringify(requestBody, null, 2));
            
            // Use relative path for Home Assistant ingress compatibility
            const apiUrl = 'api/generate_automation';
            console.log('[ChatService] Fetching', apiUrl);
            
            const response = await fetch(apiUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody),
            });

            console.log('[ChatService] Response status:', response.status);
            console.log('[ChatService] Response ok:', response.ok);
            console.log('[ChatService] Response URL:', response.url);

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

            const data = await response.json();
            console.log('[ChatService] Response data:', data);

            const message: ChatMessage = {
                id: uuidv4(),
                role: 'assistant',
                content: data.full_response || data.error || 'No response received',
                timestamp: new Date(),
                yaml: this.extractYamlFromMarkdown(data.full_response || '')
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