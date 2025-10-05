import type { ChatMessage } from '@/types/chat';

export class ChatStorage {
    /**
     * Save chat messages to Home Assistant storage via backend API
     */
    static async save(messages: ChatMessage[]): Promise<void> {
        try {
            console.log('[ChatStorage] Saving', messages.length, 'messages to HA storage');
            
            // Convert Date objects to ISO strings for JSON serialization
            const serializedMessages = messages.map(msg => ({
                ...msg,
                timestamp: msg.timestamp instanceof Date ? msg.timestamp.toISOString() : msg.timestamp
            }));
            
            const response = await fetch('api/chat/history', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ messages: serializedMessages })
            });
            
            if (!response.ok) {
                throw new Error(`Failed to save: HTTP ${response.status}`);
            }
            
            console.log('[ChatStorage] Successfully saved to HA storage');
        } catch (error) {
            console.error('[ChatStorage] Failed to save:', error);
            // Fall back to localStorage as backup
            this.saveToLocalStorage(messages);
        }
    }

    /**
     * Load chat messages from Home Assistant storage via backend API
     */
    static async load(): Promise<ChatMessage[] | null> {
        try {
            console.log('[ChatStorage] Loading messages from HA storage');
            
            const response = await fetch('api/chat/history');
            
            if (!response.ok) {
                throw new Error(`Failed to load: HTTP ${response.status}`);
            }
            
            const data = await response.json();
            const messages = data.messages || [];
            
            if (messages.length === 0) {
                console.log('[ChatStorage] No messages found in HA storage');
                // Try to load from localStorage as fallback
                return this.loadFromLocalStorage();
            }
            
            // Convert timestamp strings back to Date objects
            const parsedMessages = messages.map((msg: any) => ({
                ...msg,
                timestamp: new Date(msg.timestamp)
            }));
            
            console.log('[ChatStorage] Loaded', parsedMessages.length, 'messages from HA storage');
            return parsedMessages;
            
        } catch (error) {
            console.error('[ChatStorage] Failed to load from HA storage:', error);
            // Fall back to localStorage
            return this.loadFromLocalStorage();
        }
    }

    /**
     * Clear stored chat messages from Home Assistant storage
     */
    static async clear(): Promise<void> {
        try {
            console.log('[ChatStorage] Clearing HA storage');
            
            const response = await fetch('api/chat/history', {
                method: 'DELETE'
            });
            
            if (!response.ok) {
                throw new Error(`Failed to clear: HTTP ${response.status}`);
            }
            
            console.log('[ChatStorage] Successfully cleared HA storage');
            
            // Also clear localStorage backup
            this.clearLocalStorage();
            
        } catch (error) {
            console.error('[ChatStorage] Failed to clear HA storage:', error);
            // Still try to clear localStorage
            this.clearLocalStorage();
        }
    }

    /**
     * Check if there are stored messages (checks both HA storage and localStorage)
     */
    static async hasStoredMessages(): Promise<boolean> {
        try {
            const response = await fetch('api/chat/history');
            if (response.ok) {
                const data = await response.json();
                return (data.messages || []).length > 0;
            }
        } catch (error) {
            console.warn('[ChatStorage] Could not check HA storage:', error);
        }
        
        // Fall back to checking localStorage
        return this.hasLocalStorageMessages();
    }

    // ===== LocalStorage fallback methods =====
    
    private static STORAGE_KEY = 'aitomations_chat_history';
    
    private static saveToLocalStorage(messages: ChatMessage[]): void {
        try {
            const data = {
                messages: messages.map(msg => ({
                    ...msg,
                    timestamp: msg.timestamp instanceof Date ? msg.timestamp.toISOString() : msg.timestamp
                })),
                timestamp: Date.now()
            };
            localStorage.setItem(this.STORAGE_KEY, JSON.stringify(data));
            console.log('[ChatStorage] Saved to localStorage as fallback');
        } catch (error) {
            console.error('[ChatStorage] Failed to save to localStorage:', error);
        }
    }
    
    private static loadFromLocalStorage(): ChatMessage[] | null {
        try {
            const stored = localStorage.getItem(this.STORAGE_KEY);
            if (!stored) return null;
            
            const data = JSON.parse(stored);
            const messages = data.messages.map((msg: any) => ({
                ...msg,
                timestamp: new Date(msg.timestamp)
            }));
            
            console.log('[ChatStorage] Loaded from localStorage fallback');
            return messages;
        } catch (error) {
            console.error('[ChatStorage] Failed to load from localStorage:', error);
            return null;
        }
    }
    
    private static clearLocalStorage(): void {
        try {
            localStorage.removeItem(this.STORAGE_KEY);
            console.log('[ChatStorage] Cleared localStorage');
        } catch (error) {
            console.error('[ChatStorage] Failed to clear localStorage:', error);
        }
    }
    
    private static hasLocalStorageMessages(): boolean {
        try {
            return localStorage.getItem(this.STORAGE_KEY) !== null;
        } catch {
            return false;
        }
    }
}