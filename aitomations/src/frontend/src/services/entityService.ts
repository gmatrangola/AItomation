import type { Artifact } from '@/types/chat';

export interface ApplyEntityResult {
    success: boolean;
    id?: string;
    error?: string;
    error_code?: string;
}

export class EntityService {
    /** Apply a generated config entity (script/scene/automation) to Home Assistant. */
    async applyEntity(artifact: Artifact, prompt?: string): Promise<ApplyEntityResult> {
        try {
            const response = await fetch('api/apply_entity', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    kind: artifact.kind,
                    yaml: artifact.yaml,
                    id: artifact.id,
                    prompt,
                }),
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                return {
                    success: false,
                    error: data.error || data.context?.details || `Failed to apply ${artifact.kind}`,
                    error_code: data.error_code,
                };
            }
            return { success: true, id: data.id };
        } catch (e) {
            console.error('[EntityService] applyEntity error', e);
            return { success: false, error: e instanceof Error ? e.message : `Failed to apply ${artifact.kind}` };
        }
    }
}

export const entityService = new EntityService();
