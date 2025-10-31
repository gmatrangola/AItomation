import type { ChatMessage } from '@/types/chat';

interface SerializedMessage {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp: string;
    yaml?: string;
}

interface StorageData {
    messages: SerializedMessage[];
    timestamp?: number;
}

export class ChatStorage {
    /**
     * Save chat messages to Home Assistant storage via backend API
     */
    static async save(messages: ChatMessage[]): Promise<void> {
        try {
            // Convert Date objects to ISO strings for JSON serialization
            const serializedMessages: SerializedMessage[] = messages.map((msg) => ({
                ...msg,
                timestamp: msg.timestamp instanceof Date ? msg.timestamp.toISOString() : msg.timestamp,
            }));

            const response = await fetch('api/chat/history', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ messages: serializedMessages }),
            });

            if (!response.ok) {
                throw new Error(`Failed to save: HTTP ${response.status}`);
            }
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
            const response = await fetch('api/chat/history');

            if (!response.ok) {
                throw new Error(`Failed to load: HTTP ${response.status}`);
            }

            const data = await response.json();
            const messages: SerializedMessage[] = data.messages || [];

            if (messages.length === 0) {
                // Try to load from localStorage as fallback
                return this.loadFromLocalStorage();
            }

            // Convert timestamp strings back to Date objects
            const parsedMessages: ChatMessage[] = messages.map((msg) => ({
                ...msg,
                timestamp: new Date(msg.timestamp),
            }));

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
            const response = await fetch('api/chat/history', {
                method: 'DELETE',
            });

            if (!response.ok) {
                throw new Error(`Failed to clear: HTTP ${response.status}`);
            }
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
            const data: StorageData = {
                messages: messages.map((msg) => ({
                    ...msg,
                    timestamp: msg.timestamp instanceof Date ? msg.timestamp.toISOString() : msg.timestamp,
                })),
                timestamp: Date.now(),
            };
            localStorage.setItem(this.STORAGE_KEY, JSON.stringify(data));
        } catch (error) {
            console.error('[ChatStorage] Failed to save to localStorage:', error);
        }
    }

    private static loadFromLocalStorage(): ChatMessage[] | null {
        try {
            const stored = localStorage.getItem(this.STORAGE_KEY);
            if (!stored) return null;

            const data: StorageData = JSON.parse(stored);
            const messages: ChatMessage[] = data.messages.map((msg) => ({
                ...msg,
                timestamp: new Date(msg.timestamp),
            }));

            return messages;
        } catch (error) {
            console.error('[ChatStorage] Failed to load from localStorage:', error);
            return null;
        }
    }

    private static clearLocalStorage(): void {
        try {
            localStorage.removeItem(this.STORAGE_KEY);
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
