<template>
    <div>
        <!-- Summary -->
        <v-alert type="success" variant="tonal" class="mb-4">
            <v-alert-title>
                <v-icon class="mr-2">mdi-lightbulb-on</v-icon>
                What this automation does:
            </v-alert-title>
            {{ automation.summary }}
        </v-alert>

        <!-- YAML Code -->
        <v-card variant="outlined" class="mb-4">
            <v-card-title class="text-h6">
                <v-icon class="mr-2">mdi-code-braces</v-icon>
                Automation YAML
                <v-spacer />
                <v-btn @click="copyToClipboard" variant="text" size="small" :color="copied ? 'success' : 'primary'">
                    <v-icon>{{ copied ? 'mdi-check' : 'mdi-content-copy' }}</v-icon>
                    {{ copied ? 'Copied!' : 'Copy' }}
                </v-btn>
            </v-card-title>

            <v-card-text>
                <pre class="yaml-code">{{ automation.yaml }}</pre>
            </v-card-text>
        </v-card>

        <!-- Action Buttons -->
        <div class="d-flex gap-3">
            <v-btn @click="$emit('install')" :loading="installing" color="success" size="large" variant="elevated">
                <v-icon left>mdi-download</v-icon>
                Install in Home Assistant
            </v-btn>

            <v-btn @click="$emit('modify')" :loading="modifying" color="primary" size="large" variant="outlined">
                <v-icon left>mdi-pencil</v-icon>
                Modify
            </v-btn>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

interface AutomationResponse {
    summary: string
    yaml: string
}

defineProps<{
    automation: AutomationResponse
    installing: boolean
    modifying: boolean
}>()

defineEmits<{
    install: []
    modify: []
}>()

const copied = ref(false)

async function copyToClipboard() {
    try {
        await navigator.clipboard.writeText(props.automation.yaml)
        copied.value = true
        setTimeout(() => {
            copied.value = false
        }, 2000)
    } catch (error) {
        console.error('Failed to copy to clipboard:', error)
    }
}
</script>

<style scoped>
.yaml-code {
    background-color: #f5f5f5;
    padding: 16px;
    border-radius: 4px;
    overflow-x: auto;
    font-family: 'Courier New', monospace;
    font-size: 14px;
    line-height: 1.4;
    white-space: pre-wrap;
    word-wrap: break-word;
}

.v-theme--dark .yaml-code {
    background-color: #2d2d2d;
    color: #f8f8f2;
}
</style>
