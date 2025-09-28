<template>
    <div class="dashboard">
        <AIChat v-model="prompt" :response="aiResponse" :generating="generating" @generate-prompt="handleGeneratePrompt"
            @install-automation="handleInstallAutomation" />

        <v-divider class="my-6"></v-divider>

        <!-- Automation List -->
        <v-card class="automation-list-card" elevation="2">
            <v-card-title class="automation-list-title">
                <v-icon class="mr-2">mdi-cog-outline</v-icon>
                Existing Automations
            </v-card-title>
            <v-card-text>
                <v-data-table :headers="headers" :items="automations" :loading="loading" item-key="id"
                    class="automation-table" :items-per-page="10">
                    <template v-slot:item.state="{ item }">
                        <v-chip :color="item.state === 'on' ? 'success' : 'default'" size="small">
                            {{ item.state }}
                        </v-chip>
                    </template>
                    <template v-slot:item.prompt="{ item }">
                        <span class="text-truncate" style="max-width: 200px;">
                            {{ item.prompt || 'N/A' }}
                        </span>
                    </template>
                    <template v-slot:item.actions="{ item }">
                        <v-btn size="small" :disabled="!item.is_editable" @click="handleEditAutomation(item)"
                            color="primary" variant="outlined">
                            <v-icon start>mdi-pencil</v-icon>
                            Edit with AI
                        </v-btn>
                    </template>
                </v-data-table>
            </v-card-text>
        </v-card>
    </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import AIChat from '@/components/AIChat.vue';

interface Automation {
    id: string;
    entity_id: string;
    alias: string;
    state: string;
    prompt: string | null;
    source: string | null;
    is_editable: boolean;
}

interface AiResponse {
    full_response?: string;
    error?: string;
    rawResponse?: string;
}

// Refs for existing automation list
const loading = ref(true);
const automations = ref<Automation[]>([]);
const headers = [
    { title: 'Alias', value: 'alias', width: '25%' },
    { title: 'Entity ID', value: 'entity_id', width: '20%' },
    { title: 'State', value: 'state', width: '10%' },
    { title: 'Prompt', value: 'prompt', width: '30%' },
    { title: 'Actions', value: 'actions', sortable: false, width: '15%' },
];

// Refs for chat interface
const prompt = ref('');
const aiResponse = ref<AiResponse | null>(null);
const generating = ref(false);

const handleGeneratePrompt = async (promptText: string) => {
    generating.value = true;
    aiResponse.value = null;

    let response;
    try {
        response = await fetch('api/generate_automation', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt: promptText }),
        });

        const data = await response.json();

        if (response.ok) {
            aiResponse.value = data;
        } else {
            throw new Error(data.error || 'An unknown error occurred');
        }
    } catch (error: any) {
        console.error("Frontend Error:", error);

        if (response) {
            response.text().then(text => {
                console.error("Raw Backend Response Text:", text);
                aiResponse.value = {
                    error: error.message,
                    rawResponse: text
                };
            });
        } else {
            aiResponse.value = { error: error.message };
        }
    } finally {
        generating.value = false;
    }
};

const handleInstallAutomation = async (yaml: string) => {
    try {
        const response = await fetch('api/install_automation', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                automation_yaml: yaml,
                prompt: prompt.value
            }),
        });

        if (!response.ok) {
            throw new Error('Failed to install automation');
        }

        // Refresh automations list and clear the current response
        await fetchAutomations();
        aiResponse.value = null;
        prompt.value = '';

        console.log('Automation installed successfully');
    } catch (error) {
        console.error('Failed to install automation:', error);
    }
};

const handleEditAutomation = (automation: Automation) => {
    // Pre-fill the prompt with existing automation info for editing
    if (automation.prompt) {
        prompt.value = `Edit this automation: "${automation.alias}" - ${automation.prompt}`;
    } else {
        prompt.value = `Edit automation: "${automation.alias}" (Entity: ${automation.entity_id})`;
    }
    console.log('Edit automation:', automation);
};

const fetchAutomations = async () => {
    loading.value = true;
    try {
        const response = await fetch('api/automations');
        if (!response.ok) throw new Error('Failed to fetch automations');
        automations.value = await response.json();
    } catch (error) {
        console.error('Failed to fetch automations:', error);
    } finally {
        loading.value = false;
    }
};

onMounted(fetchAutomations);
</script>

<style scoped>
.dashboard {
    max-width: 100%;
}

.automation-list-card {
    background-color: var(--ha-card-background);
    border: 1px solid var(--ha-border);
}

.automation-list-title {
    color: var(--ha-primary-text);
    font-size: 1.2rem;
    font-weight: 500;
}

.automation-table {
    background-color: transparent;
}

.text-truncate {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    display: inline-block;
}
</style>