<template>
    <v-app>
        <v-app-bar color="primary" dark>
            <v-app-bar-title>
                <v-icon class="mr-2">mdi-robot</v-icon>
                AItomations
            </v-app-bar-title>
        </v-app-bar>

        <v-main>
            <v-container fluid>
                <v-row justify="center">
                    <v-col cols="12" md="8" lg="6">
                        <v-card class="mt-4">
                            <v-card-title>
                                <v-icon class="mr-2">mdi-magic-staff</v-icon>
                                Create Home Assistant Automation
                            </v-card-title>

                            <v-card-text>
                                <v-textarea v-model="userPrompt" label="Describe your automation"
                                    placeholder="e.g., Turn on the living room lights when motion is detected after sunset"
                                    rows="3" variant="outlined" :disabled="loading" />

                                <v-btn @click="generateAutomation" :loading="loading" :disabled="!userPrompt.trim()"
                                    color="primary" size="large" block class="mt-3">
                                    <v-icon left>mdi-creation</v-icon>
                                    Generate Automation
                                </v-btn>
                            </v-card-text>
                        </v-card>

                        <!-- Error Message -->
                        <v-alert v-if="errorMessage" type="error" dismissible @click:close="errorMessage = ''"
                            class="mt-4">
                            {{ errorMessage }}
                        </v-alert>

                        <!-- Generated Automation -->
                        <v-card v-if="generatedAutomation" class="mt-4">
                            <v-card-title>
                                <v-icon class="mr-2">mdi-check-circle</v-icon>
                                Generated Automation
                            </v-card-title>

                            <v-card-text>
                                <AutomationSummary :automation="generatedAutomation" @install="installAutomation"
                                    @modify="modifyAutomation" :installing="installing" :modifying="modifying" />
                            </v-card-text>
                        </v-card>
                    </v-col>
                </v-row>
            </v-container>
        </v-main>

        <!-- Debug Info (remove in production) -->
        <v-footer app>
            <v-spacer />
            <small class="text-grey">
                API: {{ API_BASE_URL }} | Status: Connected
            </small>
        </v-footer>
    </v-app>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import AutomationSummary from './components/AutomationSummary.vue'

interface AutomationResponse {
    summary: string
    yaml: string
}

const userPrompt = ref('')
const generatedAutomation = ref<AutomationResponse | null>(null)
const loading = ref(false)
const installing = ref(false)
const modifying = ref(false)
const errorMessage = ref('')

// Always use /api for both dev and production
const API_BASE_URL = '/api'

async function generateAutomation() {
    loading.value = true
    errorMessage.value = ''
    generatedAutomation.value = null

    try {
        console.log('Generating automation with prompt:', userPrompt.value)

        const response = await fetch(`${API_BASE_URL}/generate_automation`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ prompt: userPrompt.value }),
        })

        if (!response.ok) {
            const errorText = await response.text()
            throw new Error(`Failed to generate: ${response.status} - ${errorText}`)
        }

        const data: AutomationResponse = await response.json()
        generatedAutomation.value = data
    } catch (error: any) {
        console.error('Error generating automation:', error)
        errorMessage.value = error.message || 'An unknown error occurred'
    } finally {
        loading.value = false
    }
}

async function installAutomation() {
    if (!generatedAutomation.value) return

    installing.value = true
    errorMessage.value = ''

    try {
        const response = await fetch(`${API_BASE_URL}/install_automation`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                automation_yaml: generatedAutomation.value.yaml
            }),
        })

        if (!response.ok) {
            const errorText = await response.text()
            throw new Error(`Failed to install: ${response.status} - ${errorText}`)
        }

        // Success - reset form
        userPrompt.value = ''
        generatedAutomation.value = null

        // You could show a success snackbar here instead
        alert('Automation installed successfully!')
    } catch (error: any) {
        console.error('Error installing automation:', error)
        errorMessage.value = error.message || 'Installation failed'
    } finally {
        installing.value = false
    }
}

async function modifyAutomation() {
    modifying.value = true
    try {
        await generateAutomation()
    } finally {
        modifying.value = false
    }
}
</script>

<style>
/* Basic styling for full height and consistent padding */
html,
body,
#app {
    height: 100%;
    margin: 0;
    overflow: hidden;
    /* Prevent scrolling on main body */
}

.v-application {
    background-color: var(--v-theme-surface);
    /* Use Vuetify theme surface color */
}

.fill-height {
    height: 100%;
}

.h-100 {
    height: 100%;
}

.flex-grow-1 {
    flex-grow: 1;
}

.overflow-auto {
    overflow: auto;
}

#app-container {
    display: flex;
    flex-direction: column;
    height: 100vh;
}

header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
}

.settings-btn {
    background: none;
    border: 1px solid #555;
    color: #f0f0f0;
    padding: 0.5rem 1rem;
    border-radius: 5px;
    cursor: pointer;
}

.settings-btn:hover {
    background-color: #444;
}
</style>
