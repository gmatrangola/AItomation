<template>
    <v-container>
        <v-row>
            <v-col>
                <h1>AItomations Dashboard</h1>
                <p class="text-subtitle-1">Describe your desired automation or ask a question about your setup.</p>
            </v-col>
        </v-row>

        <!-- Step 2: Chat Interface -->
        <v-row>
            <v-col>
                <v-card>
                    <v-card-text>
                        <!-- AI Response Area -->
                        <div v-if="aiResponse" class="mb-4 pa-3"
                            style="border: 1px solid #ccc; border-radius: 4px; background-color: #f9f9f9;">
                            <p class="font-weight-bold">AItomations Assistant:</p>

                            <!-- Display the explanation -->
                            <p v-if="aiResponse.explanation">{{ aiResponse.explanation }}</p>

                            <!-- Display the formatted YAML -->
                            <pre v-if="aiResponse.automation_yaml"
                                style="white-space: pre-wrap; font-family: monospace; background-color: #eef; padding: 10px; border-radius: 4px;">{{ aiResponse.automation_yaml }}</pre>

                            <!-- Display raw error for debugging -->
                            <pre v-if="aiResponse.error"
                                style="white-space: pre-wrap; color: red;">{{ aiResponse.rawResponse }}</pre>
                        </div>

                        <!-- Prompt Input -->
                        <v-textarea v-model="prompt" label="Your Prompt"
                            placeholder="e.g., 'Turn on the porch light at sunset and turn it off at sunrise'" rows="3"
                            auto-grow clearable></v-textarea>
                    </v-card-text>
                    <v-card-actions>
                        <v-spacer></v-spacer>
                        <v-btn color="primary" :loading="generating" @click="submitPrompt">
                            Generate
                        </v-btn>
                    </v-card-actions>
                </v-card>
            </v-col>
        </v-row>
        <!-- End of Chat Interface -->

        <v-divider class="my-6"></v-divider>

        <!-- Existing Automation List -->
        <v-row>
            <v-col>
                <v-card>
                    <v-card-title>Existing Automations</v-card-title>
                    <v-data-table :headers="headers" :items="automations" :loading="loading" item-key="id">
                        <template v-slot:item.actions="{ item }">
                            <v-btn small :disabled="!item.is_editable">Edit with AI</v-btn>
                        </template>
                    </v-data-table>
                </v-card>
            </v-col>
        </v-row>
    </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';

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

// Refs for new chat interface
const prompt = ref('');
const aiResponse = ref<AiResponse | null>(null); // Use the new interface
const generating = ref(false);

const submitPrompt = async () => {
    if (!prompt.value) return;
    generating.value = true;
    aiResponse.value = null; // Clear previous response
    let response;
    try {
        response = await fetch('api/generate_automation', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt: prompt.value }),
        });
        const data = await response.json();
        if (response.ok) {
            // The backend now sends a structured object
            aiResponse.value = data;
        } else {
            throw new Error(data.error || 'An unknown error occurred');
        }
    } catch (error: any) {
        console.error("Frontend Error:", error);
        if (response) {
            response.text().then(text => {
                console.error("Raw Backend Response Text:", text);
                aiResponse.value = { error: error.message, rawResponse: text };
            });
        } else {
            aiResponse.value = { error: error.message };
        }
    } finally {
        generating.value = false;
    }
};

const fetchAutomations = async () => {
    loading.value = true;
    try {
        // REMOVED leading slash '/'
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