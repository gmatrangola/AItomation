// Single source of truth for the kinds the app can apply. The value matches the HA domain
// (which the backend slots into POST /api/config/<kind>/config/<id>), except `dashboard`,
// which is applied over the WebSocket Lovelace API.
export const ARTIFACT_KINDS = [
    'automation',
    'dashboard',
    'script',
    'scene',
    'input_boolean',
    'input_number',
    'input_select',
    'input_text',
    'input_datetime',
    'input_button',
    'timer',
    'counter',
] as const;

export type ArtifactKind = (typeof ARTIFACT_KINDS)[number];

// Helper-domain kinds that share generic rendering and the /apply_entity path.
export const HELPER_KINDS: ReadonlySet<ArtifactKind> = new Set([
    'input_boolean',
    'input_number',
    'input_select',
    'input_text',
    'input_datetime',
    'input_button',
    'timer',
    'counter',
]);

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
