<template>
    <v-alert
        v-if="formattedError"
        type="error"
        variant="tonal"
        closable
        class="error-alert ma-3 mb-0"
        @click:close="$emit('close')"
    >
        <template #prepend>
            <span class="error-icon">{{ formattedError.icon }}</span>
        </template>

        <v-alert-title class="error-title">
            {{ formattedError.title }}
        </v-alert-title>

        <div v-if="formattedError.description" class="error-description mt-2">
            {{ formattedError.description }}
        </div>

        <div v-if="formattedError.steps.length > 0" class="error-steps mt-3">
            <div class="steps-title">{{ formattedError.stepsTitle }}</div>
            <ul class="mt-2">
                <li v-for="(step, index) in formattedError.steps" :key="index">
                    {{ step }}
                </li>
            </ul>
        </div>

        <div v-if="formattedError.details" class="error-details mt-3">
            <details>
                <summary>Technical details</summary>
                <pre class="mt-2">{{ formattedError.details }}</pre>
            </details>
        </div>
    </v-alert>
</template>

<script setup lang="ts">
import { computed } from 'vue';

interface Props {
    error: string;
}

const props = defineProps<Props>();

defineEmits<{
    close: [];
}>();

interface FormattedError {
    icon: string;
    title: string;
    description?: string;
    stepsTitle: string;
    steps: string[];
    details?: string;
}

const formattedError = computed((): FormattedError | null => {
    if (!props.error) return null;

    // Hostname resolution failed
    if (props.error.includes('HOSTNAME_RESOLUTION_FAILED:')) {
        const hostname = props.error.split(':')[1]?.trim() || 'unknown';
        return {
            icon: '🔌',
            title: `Cannot resolve hostname '${hostname}'`,
            stepsTitle: 'Troubleshooting steps:',
            steps: [
                'Verify the hostname is correct in your add-on configuration',
                'If using a .local hostname, ensure mDNS/Bonjour is working',
                'Try using an IP address instead (e.g., http://192.168.1.100:11434)',
                'Ensure the Ollama server is on the same network',
            ],
            details: props.error,
        };
    }

    // Connection refused
    if (props.error.includes('CONNECTION_REFUSED:')) {
        const hostPort = props.error.split(':').slice(1).join(':').trim();
        return {
            icon: '🚫',
            title: `Cannot connect to Ollama at ${hostPort}`,
            stepsTitle: 'Troubleshooting steps:',
            steps: [
                "Verify Ollama is running (run 'ollama serve' on the host)",
                'Check if the port is accessible from Home Assistant',
                'If Ollama is in Docker, ensure ports are properly exposed',
                'Check firewall settings on both machines',
            ],
            details: props.error,
        };
    }

    // Connection lost
    if (props.error.includes('CONNECTION_LOST:')) {
        return {
            icon: '📡',
            title: 'Connection lost to Ollama server',
            stepsTitle: 'Troubleshooting steps:',
            steps: [
                'Verify Ollama is still running',
                'Check network connectivity',
                'Ensure no firewall is blocking the connection',
                'Try restarting the Ollama service',
            ],
            details: props.error,
        };
    }

    // Request timeout
    if (props.error.includes('REQUEST_TIMEOUT:')) {
        const parts = props.error.split(':');
        const model = parts[1]?.split('-')[0]?.trim() || 'unknown';
        return {
            icon: '⏱️',
            title: 'Request timed out after 120 seconds',
            description: 'The request took too long to complete.',
            stepsTitle: 'Try:',
            steps: [
                `Ensure the model is downloaded: ollama pull ${model}`,
                'Use a smaller/faster model',
                'Check Ollama logs for errors',
                'Verify the server has enough resources',
            ],
            details: props.error,
        };
    }

    // Model not found
    if (props.error.includes('MODEL_NOT_FOUND:')) {
        const model = props.error.split(':')[1]?.trim() || 'unknown';
        return {
            icon: '🔍',
            title: `Model '${model}' not found on Ollama server`,
            stepsTitle: 'To fix this:',
            steps: [
                `Install the model: ollama pull ${model}`,
                'List available models: ollama list',
                'Update your add-on configuration with an available model',
            ],
            details: props.error,
        };
    }

    // HTTP error
    if (props.error.includes('HTTP_ERROR:')) {
        const details = props.error.substring(props.error.indexOf(':') + 1).trim();
        return {
            icon: '⚠️',
            title: 'Ollama server returned an error',
            description: 'Check the Ollama server logs for more details.',
            stepsTitle: 'Server response:',
            steps: [details],
            details: props.error,
        };
    }

    // Network/fetch errors
    if (props.error.includes('Failed to fetch') || props.error.includes('NetworkError')) {
        return {
            icon: '🌐',
            title: 'Cannot connect to the backend server',
            stepsTitle: 'Please check:',
            steps: ['The add-on is running', 'Your network connection', 'Home Assistant is accessible'],
            details: props.error,
        };
    }

    // Generic error - check if it's markdown formatted from backend
    if (props.error.includes('❌')) {
        // Backend already formatted it nicely
        return {
            icon: '❌',
            title: 'An error occurred',
            description: props.error,
            stepsTitle: '',
            steps: [],
        };
    }

    // Generic error
    return {
        icon: '⚠️',
        title: 'An error occurred',
        description: props.error,
        stepsTitle: '',
        steps: [],
    };
});
</script>

<style scoped>
.error-alert {
    border-left: 4px solid rgb(var(--v-theme-error)) !important;
}

.error-icon {
    font-size: 1.5rem;
    line-height: 1;
}

.error-title {
    font-weight: 600;
    font-size: 1rem;
}

.error-description {
    font-size: 0.9rem;
    opacity: 0.9;
}

.error-steps {
    font-size: 0.9rem;
}

.steps-title {
    font-weight: 500;
    opacity: 0.95;
}

.error-steps ul {
    margin: 0;
    padding-left: 1.25rem;
    list-style-type: disc;
}

.error-steps li {
    margin: 0.35rem 0;
    opacity: 0.9;
}

.error-details {
    font-size: 0.85rem;
}

.error-details details {
    cursor: pointer;
}

.error-details summary {
    opacity: 0.8;
    user-select: none;
    font-weight: 500;
}

.error-details summary:hover {
    opacity: 1;
}

.error-details pre {
    margin: 0;
    padding: 0.5rem;
    background-color: rgba(0, 0, 0, 0.2);
    border-radius: 4px;
    font-size: 0.75rem;
    overflow-x: auto;
    opacity: 0.8;
    font-family: 'Roboto Mono', monospace;
}
</style>
