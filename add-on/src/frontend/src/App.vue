<template>
    <v-app>
        <v-app-bar app color="primary" dark>
            <v-app-bar-nav-icon></v-app-bar-nav-icon>
            <v-toolbar-title>LLM Automation Creator</v-toolbar-title>
            <v-spacer></v-spacer>
            <v-btn icon @click="refreshPage">
                <v-icon>mdi-refresh</v-icon>
            </v-btn>
            <v-btn icon href="https://github.com/your-username/your-addon-repo" target="_blank">
                <v-icon>mdi-github</v-icon>
            </v-btn>
        </v-app-bar>

        <v-main>
            <v-container fluid class="fill-height pa-4">
                <v-row dense class="fill-height">
                    <!-- Left Panel: Prompt Input -->
                    <v-col cols="12" md="6">
                        <v-card class="pa-4 h-100 d-flex flex-column">
                            <v-card-title class="text-h5 mb-4">Describe your desired automation:</v-card-title>
                            <v-textarea v-model="userPrompt"
                                label="E.g., 'Turn on the living room lights when motion is detected after sunset and turn them off after 5 minutes of no motion.'"
                                variant="outlined" rows="8" auto-grow class="flex-grow-1" :loading="loading"
                                :disabled="loading"></v-textarea>
                            <v-card-actions class="mt-4">
                                <v-spacer></v-spacer>
                                <v-btn color="success" size="large" @click="generateAutomation" :loading="loading"
                                    :disabled="!userPrompt.trim() || loading" prepend-icon="mdi-robot-outline">
                                    Generate Automation
                                </v-btn>
                            </v-card-actions>
                            <v-alert v-if="errorMessage" type="error" dismissible class="mt-4"
                                @input="errorMessage = ''">
                                {{ errorMessage }}
                            </v-alert>
                        </v-card>
                    </v-col>

                    <!-- Right Panel: Automation Summary & Actions -->
                    <v-col cols="12" md="6">
                        <v-card class="pa-4 h-100 d-flex flex-column">
                            <v-card-title class="text-h5 mb-4">Generated Automation Proposal:</v-card-title>
                            <div v-if="loading" class="text-center py-10">
                                <v-progress-circular indeterminate color="primary" size="64"></v-progress-circular>
                                <p class="mt-4">Generating automation...</p>
                            </div>
                            <div v-else-if="generatedAutomation" class="flex-grow-1 overflow-auto">
                                <v-alert type="info" variant="tonal" prominent class="mb-4">
                                    Review the proposed automation. You can install it directly or refine your prompt
                                    for modifications.
                                </v-alert>
                                <AutomationSummary :automation="generatedAutomation" />
                            </div>
                            <div v-else class="text-center py-10 text-grey">
                                <v-icon size="64">mdi-lightbulb-on-outline</v-icon>
                                <p class="mt-4">Your generated automation will appear here.</p>
                            </div>

                            <v-card-actions v-if="generatedAutomation" class="mt-4">
                                <v-btn color="warning" size="large"
                                    @click="userPrompt = ''; generatedAutomation = null; errorMessage = ''"
                                    prepend-icon="mdi-pencil-outline">
                                    Clear & Start Over
                                </v-btn>
                                <v-spacer></v-spacer>
                                <v-btn color="info" size="large" @click="modifyAutomation" :loading="modifying"
                                    :disabled="modifying" prepend-icon="mdi-update">
                                    Modify with New Prompt
                                </v-btn>
                                <v-btn color="primary" size="large" @click="installAutomation" :loading="installing"
                                    :disabled="installing" prepend-icon="mdi-check-circle-outline">
                                    Install Automation
                                    &nbsp;</v-btn>
                            </v-card-actions>
                        </v-card>
                    </v-col>
                </v-row>
            </v-container>
        </v-main>
    </v-app>
</template>

<script setup lang="ts">
import { ref } from 'vue';

interface AutomationResponse {
    summary: string;
    yaml: string;
}

const userPrompt = ref('');
const generatedAutomation = ref<AutomationResponse | null>(null);
const loading = ref(false);
const installing = ref(false);
const modifying = ref(false);
const errorMessage = ref('');

const API_BASE_URL = import.meta.env.DEV ? '/api' : ''; // Use proxy in dev, direct in prod

async function generateAutomation() {
    loading.value = true;
    errorMessage.value = '';
    generatedAutomation.value = null;

    try {
        const response = await fetch(`${API_BASE_URL}/generate_automation`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ prompt: userPrompt.value }),
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Failed to generate automation: ${response.status} ${response.statusText} - ${errorText}`);
        }

        const data: AutomationResponse = await response.json();
        generatedAutomation.value = data;
    } catch (error: any) {
        console.error('Error generating automation:', error);
        errorMessage.value = `Error: ${error.message || 'An unknown error occurred during generation.'}`;
    } finally {
        loading.value = false;
    }
}

async function installAutomation() {
    if (!generatedAutomation.value) return;

    installing.value = true;
    errorMessage.value = '';

    try {
        const response = await fetch(`${API_BASE_URL}/install_automation`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ automation_yaml: generatedAutomation.value.yaml }),
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Failed to install automation: ${response.status} ${response.statusText} - ${errorText}`);
        }

        // Handle successful installation (e.g., show a success message)
        alert('Automation installed successfully!'); // Replace with custom modal later
        userPrompt.value = '';
        generatedAutomation.value = null;
    } catch (error: any) {
        console.error('Error installing automation:', error);
        errorMessage.value = `Error: ${error.message || 'An unknown error occurred during installation.'}`;
    } finally {
        installing.value = false;
    }
}

async function modifyAutomation() {
    // For modification, the user needs to add more context to the prompt.
    // The current design just clears and lets them re-prompt.
    // A more advanced design would pre-fill the prompt with the old prompt + generated summary.
    // For now, it will act like a "new generation" with modified prompt.
    modifying.value = true;
    errorMessage.value = '';
    const currentPrompt = userPrompt.value; // Store current prompt

    // Optionally, you could pre-fill the prompt with the existing summary + new instructions
    // userPrompt.value = `Given the previous attempt:\n---\n${generatedAutomation.value?.summary}\n---\n${userPrompt.value}\n\nNow, refine it by: `

    try {
        await generateAutomation(); // Re-use the generate function with the potentially modified prompt
    } finally {
        modifying.value = false;
    }
}

function refreshPage() {
    window.location.reload();
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
</style>
