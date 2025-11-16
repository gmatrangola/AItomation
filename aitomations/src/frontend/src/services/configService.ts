export interface ConfigValidationResult {
    isValid: boolean;
    error: string | null;
    config?: {
        llm_provider: 'gemini' | 'ollama';
        gemini_api_key?: string;
        gemini_model?: string;
        ollama_api_url?: string;
        ollama_model?: string;
        request_timeout?: number;
        system_prompt_template?: string;
    };
}

export class ConfigService {
    /**
     * Check if the LLM configuration is valid
     * Designed to work within Home Assistant iframe context
     * @returns Validation result with error message if invalid
     */
    async checkConfiguration(): Promise<ConfigValidationResult> {
        try {
            const response = await fetch('./api/config', { headers: { 'Cache-Control': 'no-cache' } });
            if (!response.ok) {
                return { isValid: false, error: 'Unable to load configuration.' };
            }
            const config = await response.json();

            if (!config.llm_provider) {
                return { isValid: false, error: 'No AI provider selected.', config };
            }

            if (config.llm_provider === 'gemini') {
                if (!config.gemini_api_key_present) {
                    return { isValid: false, error: 'Gemini API key is missing.', config };
                }
            }

            if (config.llm_provider === 'ollama') {
                if (!config.ollama_api_url || config.ollama_api_url.trim() === '') {
                    return { isValid: false, error: 'Ollama API URL is missing.', config };
                }
            }

            return { isValid: true, error: null, config };
        } catch (e) {
            console.error('[ConfigService] checkConfiguration error', e);
            return { isValid: false, error: 'Failed to verify configuration.' };
        }
    }

    /**
     * Load configuration from the API
     * @returns Configuration object or null on error
     */
    async loadConfiguration() {
        try {
            const response = await fetch('api/config');
            if (response.status === 401) {
                throw new Error('Unauthorized (401) – likely wrong base path (core API).');
            }
            if (!response.ok) {
                throw new Error('Failed to load configuration');
            }
            return await response.json();
        } catch (error) {
            console.error('[ConfigService] Failed to load configuration:', error);
            return null;
        }
    }

    /**
     * Save configuration to the API
     * @param config Configuration object to save
     * @returns Success status
     */
    async saveConfiguration(config: ConfigValidationResult['config']): Promise<{ success: boolean; error?: string }> {
        try {
            // Remove masked secrets so backend can preserve existing
            const payload = { ...config };
            if (payload?.gemini_api_key === '***') {
                delete payload.gemini_api_key;
            }

            const response = await fetch('./api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            if (!response.ok) {
                const err = await response.json().catch(() => ({}));
                return { success: false, error: err.error || 'Failed to save configuration' };
            }
            return { success: true };
        } catch (e) {
            console.error('[ConfigService] saveConfiguration error', e);
            return { success: false, error: e instanceof Error ? e.message : 'Failed to save configuration' };
        }
    }
}

// Export singleton instance for use across the application
export const configService = new ConfigService();
