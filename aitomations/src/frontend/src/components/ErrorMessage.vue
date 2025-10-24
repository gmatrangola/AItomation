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
            <div class="steps-title">Troubleshooting steps:</div>
            <ul class="mt-2">
                <li v-for="(step, index) in formattedError.steps" :key="index">
                    {{ step }}
                </li>
            </ul>
        </div>

        <div v-if="formattedError.details" class="error-details mt-3">
            <details>
                <summary>{{ formattedError.detailsLabel || 'Technical details' }}</summary>
                <pre class="mt-2">{{ formattedError.details }}</pre>
            </details>
        </div>
    </v-alert>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { ErrorService } from '@/services/errorService';
import type { APIError } from '@/types/errors';

interface Props {
    error: APIError;
}

const props = defineProps<Props>();

defineEmits<{
    close: [];
}>();

const formattedError = computed(() => {
    return ErrorService.formatError(props.error);
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
}

.error-steps li {
    margin: 0.35rem 0;
}

.error-details details {
    cursor: pointer;
}

.error-details summary {
    opacity: 0.8;
    user-select: none;
    font-weight: 500;
}

.error-details pre {
    margin: 0;
    padding: 0.5rem;
    background-color: rgba(0, 0, 0, 0.2);
    border-radius: 4px;
    font-size: 0.75rem;
    overflow-x: auto;
    font-family: 'Roboto Mono', monospace;
}
</style>
