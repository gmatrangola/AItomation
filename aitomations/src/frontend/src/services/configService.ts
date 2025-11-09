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
            const response = await fetch('api/config', { headers: { 'Cache-Control': 'no-cache' } });

            if (response.status === 401) {
                return {
                    isValid: false,
                    error: 'Unauthorized (401). This may be calling Home Assistant core /api/config instead of the add-on. Refresh the page or verify ingress path.',
                };
            }

            if (!response.ok) {
                return {
                    isValid: false,
                    error: 'Unable to load configuration. Please configure your AI provider.',
                };
            }

            const config = await response.json();

            // Check if LLM provider is configured
            if (!config.llm_provider) {
                return {
                    isValid: false,
                    error: 'No AI provider selected. Please configure your AI provider to continue.',
                    config,
                };
            }

            // Check Gemini configuration
            if (config.llm_provider === 'gemini') {
                if (!config.gemini_api_key || config.gemini_api_key.trim() === '' || config.gemini_api_key === '***') {
                    return {
                        isValid: false,
                        error: 'Gemini API key is missing. Please add your API key in the configuration.',
                        config,
                    };
                }
            }

            // Check Ollama configuration
            if (config.llm_provider === 'ollama') {
                if (!config.ollama_api_url || config.ollama_api_url.trim() === '') {
                    return {
                        isValid: false,
                        error: 'Ollama API URL is missing. Please configure your Ollama endpoint.',
                        config,
                    };
                }
            }

            // Configuration is valid
            return {
                isValid: true,
                error: null,
                config,
            };
        } catch (error) {
            console.error('[ConfigService] Failed to check configuration:', error);
            return {
                isValid: false,
                error: 'Failed to verify configuration. Please check your settings.',
            };
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
            const response = await fetch('api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config),
            });
            if (response.status === 401) {
                return { success: false, error: 'Unauthorized (401). Ingress path resolution issue.' };
            }
            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                return {
                    success: false,
                    error: error.error || 'Failed to save configuration',
                };
            }
            return { success: true };
        } catch (error) {
            console.error('[ConfigService] Failed to save configuration:', error);
            return {
                success: false,
                error: error instanceof Error ? error.message : 'Failed to save configuration',
            };
        }
    }
}

// Export singleton instance for use across the application
export const configService = new ConfigService();
