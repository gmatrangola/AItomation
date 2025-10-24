import type { APIError, ErrorContext } from '@/types/errors';

interface ErrorMessage {
    icon: string;
    title: string;
    description?: string;
    steps: string[];
    detailsLabel?: string;
}

export class ErrorService {
    // In the future, this can be loaded from locale files
    private static messages: Record<string, (ctx: ErrorContext) => ErrorMessage> = {
        HOSTNAME_RESOLUTION_FAILED: (ctx) => ({
            icon: '🔌',
            title: `Cannot resolve hostname '${ctx.hostname}'`,
            description: 'The system cannot find this server on the network.',
            steps: [
                'Verify the hostname is spelled correctly in your configuration',
                'If using a .local hostname, ensure mDNS/Bonjour is enabled',
                `Try using an IP address instead (e.g., http://192.168.1.100:11434)`,
                'Ensure the server is on the same network as Home Assistant',
            ],
        }),

        CONNECTION_REFUSED: (ctx) => ({
            icon: '🚫',
            title: `Cannot connect to ${ctx.provider} server`,
            description: `The server at ${ctx.hostname}:${ctx.port} is not responding.`,
            steps: [
                ctx.provider === 'ollama'
                    ? "Verify Ollama is running (run 'ollama serve' on the host)"
                    : 'Verify the server is running',
                'Check if the port is accessible from Home Assistant',
                'Verify firewall settings allow the connection',
                ctx.provider === 'ollama'
                    ? 'If Ollama is in Docker, ensure ports are exposed with -p 11434:11434'
                    : 'Check Docker port mappings if using containers',
                "Ensure 'host_network: true' is set in the add-on configuration",
            ],
        }),

        CONNECTION_LOST: (ctx) => ({
            icon: '📡',
            title: 'Connection lost during request',
            description: `Lost connection to ${ctx.provider} server at ${ctx.url}`,
            steps: [
                `Verify ${ctx.provider} is still running`,
                'Check network stability between Home Assistant and the server',
                'Look for errors in the server logs',
                `Try restarting the ${ctx.provider} service`,
            ],
        }),

        REQUEST_TIMEOUT: (ctx) => ({
            icon: '⏱️',
            title: `Request timed out after ${ctx.timeout} seconds`,
            description: `The ${ctx.provider} server took too long to respond.`,
            steps: [
                ctx.model
                    ? `Verify model '${ctx.model}' is installed and downloaded`
                    : 'Check if the model is available',
                ctx.provider === 'ollama' ? `Run: ollama pull ${ctx.model}` : 'Download the required model',
                'Try using a smaller or faster model',
                `Increase the timeout in add-on configuration (current: ${ctx.timeout}s)`,
                'Check server resources (CPU, memory, GPU)',
                ctx.provider === 'ollama' ? `Test with: ollama run ${ctx.model} "hello"` : 'Test the model directly',
            ],
        }),

        MODEL_NOT_FOUND: (ctx) => ({
            icon: '🔍',
            title: `Model '${ctx.model}' not found`,
            description: `The ${ctx.provider} server doesn't have this model installed.`,
            steps: [
                ctx.provider === 'ollama' ? `Install the model: ollama pull ${ctx.model}` : 'Download the model',
                ctx.provider === 'ollama' ? 'List available models: ollama list' : 'Check available models',
                'Update your add-on configuration to use an available model',
                ...(ctx.provider === 'ollama' ? ['Popular models: llama3.2, qwen2.5:3b, phi3, mistral'] : []),
            ],
        }),

        INVALID_API_KEY: (ctx) => ({
            icon: '🔑',
            title: 'API key not configured',
            description: `${ctx.provider} requires an API key to work.`,
            steps: [
                `Get an API key from ${ctx.provider === 'gemini' ? 'Google AI Studio (https://makersuite.google.com/app/apikey)' : 'the provider'}`,
                'Add the API key to your add-on configuration',
                'Restart the add-on after updating configuration',
            ],
        }),

        INVALID_CONFIG: (ctx) => ({
            icon: '⚙️',
            title: 'Invalid configuration',
            description: `There's a problem with your ${ctx.provider} configuration.`,
            steps: [
                'Check the add-on configuration for errors',
                'Verify the URL format is correct (e.g., http://192.168.1.100:11434)',
                'Ensure the port number is valid (1-65535)',
                'Remove any extra characters from the configuration',
                'Save and restart the add-on after fixing',
            ],
            detailsLabel: 'Configuration error',
        }),

        HTTP_ERROR: (ctx) => ({
            icon: '⚠️',
            title: `Server returned error ${ctx.status_code}`,
            description: `The ${ctx.provider} server encountered an error.`,
            steps: [
                'Check the server logs for detailed error messages',
                ctx.provider === 'ollama' ? 'Run: docker logs <ollama-container>' : 'Check application logs',
                'Verify server configuration is correct',
                `Try restarting the ${ctx.provider} service`,
            ],
            detailsLabel: 'Server response',
        }),

        LLM_ERROR: (ctx) => ({
            icon: '🤖',
            title: `${ctx.provider} error`,
            description: `An error occurred while generating the response.`,
            steps: [
                'Check your API configuration',
                'Verify you have sufficient credits/quota',
                'Try again in a few moments',
                'Check the add-on logs for more details',
            ],
        }),

        NETWORK_ERROR: (_ctx) => ({
            icon: '🌐',
            title: 'Network error',
            description: 'Failed to communicate with the server.',
            steps: [
                'Check your network connection',
                'Verify Home Assistant can reach the internet',
                'Try restarting the add-on',
                'Check firewall and proxy settings',
            ],
        }),

        INVALID_INPUT: (_ctx) => ({
            icon: '📝',
            title: 'Invalid input',
            description: 'Required input is missing or invalid.',
            steps: ['Please provide a valid prompt and try again'],
        }),

        UNKNOWN_ERROR: (_ctx) => ({
            icon: '❌',
            title: 'An unexpected error occurred',
            description: "Something went wrong that we didn't anticipate.",
            steps: [
                'Try again in a few moments',
                'Check the add-on logs for more information',
                'Restart the add-on if the problem persists',
                'Report this issue if it continues',
            ],
            detailsLabel: 'Error details',
        }),
    };

    static formatError(error: APIError): ErrorMessage & { details?: string } {
        const formatter = this.messages[error.error_code];

        if (!formatter) {
            // Fallback for unknown error codes
            return {
                ...this.messages.UNKNOWN_ERROR(error.context),
                details: `Error code: ${error.error_code}\n${JSON.stringify(error.context, null, 2)}`,
            };
        }

        const formatted = formatter(error.context);

        // Add technical details if available
        const details = error.context.details;
        if (details) {
            return {
                ...formatted,
                details: typeof details === 'string' ? details : JSON.stringify(details, null, 2),
            };
        }

        return formatted;
    }

    // For future i18n support
    static setLocale(_locale: string) {
        // Load messages for the specified locale
        // this.messages = await import(`./locales/${locale}.ts`);
    }
}
