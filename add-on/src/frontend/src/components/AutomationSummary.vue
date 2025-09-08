<template>
    <v-card variant="outlined" class="mb-4">
        <v-card-text>
            <div class="text-subtitle-1 font-weight-bold mb-2">Summary:</div>
            <p class="text-body-1 mb-4">{{ automation.summary }}</p>

            <v-divider class="my-4"></v-divider>

            <div class="text-subtitle-1 font-weight-bold mb-2">Automation YAML:</div>
            <v-textarea :model-value="automation.yaml" label="Generated YAML" variant="solo-filled" rows="15" readonly
                auto-grow density="compact" class="generated-yaml"></v-textarea>
            <v-btn small color="primary" @click="copyYamlToClipboard" prepend-icon="mdi-content-copy" class="mt-2">
                Copy YAML
            </v-btn>
            <v-snackbar v-model="snackbar" :timeout="2000">
                YAML copied to clipboard!
                <template v-slot:actions>
                    <v-btn color="blue" variant="text" @click="snackbar = false">
                        Close
                    </v-btn>
                </template>
            </v-snackbar>
        </v-card-text>
    </v-card>
</template>

<script setup lang="ts">
import { ref } from 'vue';

const props = defineProps<{
    automation: {
        summary: string;
        yaml: string;
    };
}>();

const snackbar = ref(false);

const copyYamlToClipboard = () => {
    // document.execCommand('copy') is used due to potential iframe restrictions
    // on navigator.clipboard.writeText() in some environments.
    const textarea = document.createElement('textarea');
    textarea.value = props.automation.yaml;
    document.body.appendChild(textarea);
    textarea.select();
    try {
        document.execCommand('copy');
        snackbar.value = true;
    } catch (err) {
        console.error('Failed to copy YAML to clipboard:', err);
        // Fallback or user notification
    }
    document.body.removeChild(textarea);
};
</script>

<style scoped>
.generated-yaml :deep(textarea) {
    font-family: 'Roboto Mono', monospace !important;
    /* Monospace font for code */
    font-size: 0.875rem !important;
}
</style>
