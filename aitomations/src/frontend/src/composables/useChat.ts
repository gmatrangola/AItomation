import { ref, computed, watch, onMounted } from 'vue';
import { ChatService } from '@/services/chatService';
import { ChatStorage } from '@/services/chatStorage';
import type { ChatMessage } from '@/types/chat';
import { v4 as uuidv4 } from 'uuid';

export function useChat() {
    console.log('[useChat] Composable initialized');
    const chatService = new ChatService();
    
    const messages = ref<ChatMessage[]>([]);
    const isGenerating = ref(false);
    const isLoadingHistory = ref(true);

    const latestYaml = computed(() => {
        // Find the most recent assistant message with YAML
        for (let i = messages.value.length - 1; i >= 0; i--) {
            const msg = messages.value[i];
            if (msg.role === 'assistant' && msg.yaml) {
                console.log('[useChat] Latest YAML found at index:', i);
                return msg.yaml;
            }
        }
        console.log('[useChat] No YAML found in messages');
        return null;
    });

    // Load persisted messages on initialization
    onMounted(async () => {
        console.log('[useChat] Loading chat history...');
        try {
            const storedMessages = await ChatStorage.load();
            if (storedMessages && storedMessages.length > 0) {
                messages.value = storedMessages;
                console.log('[useChat] Restored', storedMessages.length, 'messages from storage');
            } else {
                console.log('[useChat] No stored messages found');
            }
        } catch (error) {
            console.error('[useChat] Failed to load chat history:', error);
        } finally {
            isLoadingHistory.value = false;
        }
    });

    // Watch messages and save to storage whenever they change
    // Use debouncing to avoid saving too frequently
    let saveTimeout: number | null = null;
    watch(messages, (newMessages) => {
        if (saveTimeout) {
            clearTimeout(saveTimeout);
        }
        
        saveTimeout = window.setTimeout(() => {
            ChatStorage.save(newMessages);
        }, 1000); // Wait 1 second after last change before saving
    }, { deep: true });

    const sendMessage = async (prompt: string) => {
        console.log('[useChat] sendMessage called');
        console.log('[useChat] Prompt:', prompt);
        console.log('[useChat] isGenerating:', isGenerating.value);
        console.log('[useChat] Current messages count:', messages.value.length);
        
        if (!prompt.trim() || isGenerating.value) {
            console.log('[useChat] sendMessage aborted - empty prompt or already generating');
            return;
        }

        // Add user message
        const userMessage: ChatMessage = {
            id: uuidv4(),
            role: 'user',
            content: prompt,
            timestamp: new Date(),
        };
        console.log('[useChat] Adding user message:', userMessage);
        messages.value.push(userMessage);
        console.log('[useChat] Messages after user add:', messages.value.length);

        isGenerating.value = true;
        console.log('[useChat] Set isGenerating to true');

        try {
            // Pass all messages except the one we just added (it's already in the prompt)
            const historyToSend = messages.value.slice(0, -1);
            console.log('[useChat] History to send length:', historyToSend.length);
            
            console.log('[useChat] Calling chatService.sendMessage...');
            const { message, error } = await chatService.sendMessage(
                prompt,
                historyToSend
            );
            
            console.log('[useChat] Received response from chatService');
            console.log('[useChat] Response message:', message);
            console.log('[useChat] Response error:', error);
            
            messages.value.push(message);
            console.log('[useChat] Messages after assistant add:', messages.value.length);

            if (error) {
                console.error('[useChat] Chat error:', error);
            }
        } catch (error) {
            console.error('[useChat] Exception in sendMessage:', error);
            // Add error message to chat
            const errorMessage: ChatMessage = {
                id: uuidv4(),
                role: 'assistant',
                content: `I encountered an error: ${error instanceof Error ? error.message : 'Unknown error'}. Please try again.`,
                timestamp: new Date(),
            };
            console.log('[useChat] Adding error message:', errorMessage);
            messages.value.push(errorMessage);
        } finally {
            isGenerating.value = false;
            console.log('[useChat] Set isGenerating to false');
            console.log('[useChat] Final messages count:', messages.value.length);
        }
    };

    const clearChat = async () => {
        console.log('[useChat] Clearing chat - current messages:', messages.value.length);
        messages.value = [];
        await ChatStorage.clear();
        console.log('[useChat] Chat cleared');
    };

    return {
        messages,
        isGenerating,
        isLoadingHistory,
        latestYaml,
        sendMessage,
        clearChat,
    };
}