<template>
    <v-container class="ha-themed-container">
        <AIChat v-model="prompt" :response="aiResponse" :generating="generating" @generate-prompt="handleGeneratePrompt"
            @install-automation="handleInstallAutomation" />

        <v-divider class="my-6"></v-divider>

        <!-- Automation List -->
        <v-card class="ha-themed-card">
            <v-card-title class="ha-themed-title">Existing Automations</v-card-title>
            <v-data-table :headers="headers" :items="automations" :loading="loading" item-key="id"
                class="ha-themed-table">
                <template v-slot:item.actions="{ item }">
                    <v-btn size="small" :disabled="!item.is_editable" @click="handleEditAutomation(item)"
                        class="ha-themed-button">
                        Edit with AI
                    </v-btn>
                </template>
            </v-data-table>
        </v-card>
    </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import AIChat from '../components/AIChat.vue';
import { useHATheme } from '../composables/useHATheme';

const { haTheme } = useHATheme()

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
    automation_yaml?: string;
    explanation?: string;
    error?: string;
    rawResponse?: string;
}

// Refs for existing automation list
const loading = ref(true);
const automations = ref<Automation[]>([]);
const headers = [
    { title: 'Alias', value: 'alias' },
    { title: 'Entity ID', value: 'entity_id' },
    { title: 'State', value: 'state' },
    { title: 'Prompt', value: 'prompt' },
    { title: 'Actions', value: 'actions', sortable: false },
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

        // You might want to show a success message here
        console.log('Automation installed successfully');
    } catch (error) {
        console.error('Failed to install automation:', error);
        // You might want to show an error message here
    }
};

const handleEditAutomation = (automation: Automation) => {
    // Implement edit functionality
    console.log('Edit automation:', automation);
};

const fetchAutomations = async () => {
    loading.value = true;
    try {
        const response = await fetch('api/automations');
        if (!response.ok) throw new Error('Failed to fetch automations');
        automations.value = await response.json();
    } catch (error) {
        console.error(error);
    } finally {
        loading.value = false;
    }
};

onMounted(fetchAutomations);
</script>

<style scoped></style>