export interface ChatMessage {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp: Date;
    yaml?: string;
    error?: boolean; // Add this line
}

export interface ChatSession {
    id: string;
    messages: ChatMessage[];
    createdAt: Date;
}
