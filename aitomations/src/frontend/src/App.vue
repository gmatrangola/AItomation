<template>
    <v-app>
        <v-app-bar color="primary" dark>
            <v-app-bar-title>
                <v-icon class="mr-2">mdi-robot-happy</v-icon>
                AItomations Dashboard
            </v-app-bar-title>
            <v-spacer></v-spacer>
            <v-btn @click="openCreateDialog" prepend-icon="mdi-plus-circle">
                Create New Automation
            </v-btn>
        </v-app-bar>

        <v-main>
            <v-container fluid>
                <v-card>
                    <v-card-title>Your Automations</v-card-title>
                    <v-data-table :headers="headers" :items="automations" :loading="loading" item-key="id"
                        class="elevation-1">
                        <template v-slot:item.alias="{ item }">
                            <strong>{{ item.alias }}</strong>
                        </template>

                        <template v-slot:item.prompt="{ item }">
                            <v-chip v-if="item.prompt" color="blue" variant="tonal" size="small">
                                <v-icon start>mdi-comment-quote-outline</v-icon>
                                {{ item.prompt }}
                            </v-chip>
                            <span v-else class="text-grey">N/A</span>
                        </template>

                        <template v-slot:item.actions="{ item }">
                            <v-btn @click="openEditDialog(item)" color="primary" variant="tonal" size="small"
                                class="mr-2">
                                Edit with AI
                            </v-btn>
                            <v-btn :href="getHAEditLink(item.id)" target="_blank" variant="outlined" size="small">
                                Edit in HA
                            </v-btn>
                        </template>
                    </v-data-table>
                </v-card>
            </v-container>
        </v-main>

        <!-- Create/Edit Dialog -->
        <v-dialog v-model="dialog" max-width="800px">
            <v-card>
                <v-card-title>{{ isEditing ? 'Edit Automation with AI' : 'Create New Automation' }}</v-card-title>
                <v-card-text>
                    <v-textarea v-model="prompt"
                        :label="isEditing ? 'Describe your changes' : 'Describe the automation you want to create'"
                        rows="3" auto-grow></v-textarea>
                    <v-alert v-if="generationError" type="error" class="mt-4">{{ generationError }}</v-alert>
                </v-card-text>
                <v-card-actions>
                    <v-spacer></v-spacer>
                    <v-btn text @click="dialog = false">Cancel</v-btn>
                    <v-btn color="primary" @click="submitGeneration" :loading="generating">
                        {{ isEditing ? 'Generate Changes' : 'Generate Automation' }}
                    </v-btn>
                </v-card-actions>
            </v-card>
        </v-dialog>

        <!-- Result/Install Dialog -->
        <v-dialog v-model="resultDialog" max-width="900px">
            <v-card v-if="generatedResult">
                <v-card-title>Generated Automation</v-card-title>
                <v-alert v-if="generatedResult.context_summary" type="info" variant="tonal" class="mx-4 mb-0"
                    density="compact">
                    {{ generatedResult.context_summary }}
                </v-alert>
                <v-card-text>
                    <AutomationSummary :automation="generatedResult" @install="installAutomation"
                        :installing="installing" />
                </v-card-text>
                <v-card-actions>
                    <v-spacer></v-spacer>
                    <v-btn text @click="resultDialog = false">Close</v-btn>
                </v-card-actions>
            </v-card>
        </v-dialog>

    </v-app>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import AutomationSummary from './components/AutomationSummary.vue';

interface Automation {
    id: string;
    entity_id: string;
    alias: string;
    state: string;
    prompt?: string;
    source?: string;
}

interface GeneratedResult {
    summary: string;
    yaml: string;
    prompt: string;
    context_summary?: string;
}

const API_BASE_URL = './api';

const automations = ref<Automation[]>([]);
const loading = ref(true);
const dialog = ref(false);
const resultDialog = ref(false);
const isEditing = ref(false);
const generating = ref(false);
const installing = ref(false);
const prompt = ref('');
const generationError = ref('');
const currentAutomationId = ref<string | null>(null);
const generatedResult = ref<GeneratedResult | null>(null);

const headers = [
    { title: 'Name', key: 'alias', sortable: true },
    { title: 'AI Prompt', key: 'prompt', sortable: false },
    { title: 'Actions', key: 'actions', sortable: false, align: 'end' as const },
];

async function fetchAutomations() {
    loading.value = true;
    try {
        const response = await fetch(`${API_BASE_URL}/automations`);
        if (!response.ok) throw new Error('Failed to fetch automations');
        automations.value = await response.json();
    } catch (error) {
        console.error(error);
    } finally {
        loading.value = false;
    }
}

onMounted(fetchAutomations);

function getHAEditLink(id: string) {
    return `/config/automation/edit/${id}`;
}

function openCreateDialog() {
    isEditing.value = false;
    prompt.value = '';
    currentAutomationId.value = null;
    generationError.value = '';
    dialog.value = true;
}

function openEditDialog(item: Automation) {
    isEditing.value = true;
    prompt.value = ''; // Start with a blank prompt for changes
    currentAutomationId.value = item.id;
    generationError.value = '';
    dialog.value = true;
}

async function submitGeneration() {
    generating.value = true;
    generationError.value = '';

    const url = isEditing.value ? `${API_BASE_URL}/edit_automation` : `${API_BASE_URL}/generate_automation`;
    const body = isEditing.value
        ? { automation_id: currentAutomationId.value, prompt: prompt.value }
        : { prompt: prompt.value };

    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Failed to generate.');

        generatedResult.value = data;
        dialog.value = false;
        resultDialog.value = true;
    } catch (error: any) {
        generationError.value = error.message;
    } finally {
        generating.value = false;
    }
}

async function installAutomation() {
    if (!generatedResult.value) return;
    installing.value = true;
    try {
        const response = await fetch(`${API_BASE_URL}/install_automation`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                automation_yaml: generatedResult.value.yaml,
                prompt: generatedResult.value.prompt // Pass the prompt for metadata
            }),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Failed to install.');

        resultDialog.value = false;
        await fetchAutomations(); // Refresh the list
    } catch (error: any) {
        alert(`Installation failed: ${error.message}`);
    } finally {
        installing.value = false;
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
