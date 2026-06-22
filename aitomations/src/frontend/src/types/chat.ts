export type ArtifactKind = 'automation' | 'dashboard' | 'script' | 'scene';

export interface Artifact {
    yaml: string;
    kind: ArtifactKind;
    id?: string; // from # aitomation_id: marker
}

export interface ChatMessage {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp: Date;
    artifacts?: Artifact[];
    // Legacy fields — kept for deserializing old chat_history.json entries
    yaml?: string;
    artifactKind?: ArtifactKind;
    error?: boolean;
}

export interface ChatSession {
    id: string;
    messages: ChatMessage[];
    createdAt: Date;
}
