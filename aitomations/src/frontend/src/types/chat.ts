export interface ChatMessage {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp: Date;
    yaml?: string; // Only for assistant messages with automation code
}

export interface ChatSession {
    id: string;
    messages: ChatMessage[];
    createdAt: Date;
}