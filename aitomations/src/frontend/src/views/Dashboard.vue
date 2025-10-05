<template>
    <div class="dashboard">
        <!-- Compact Action Bar -->
        <div class="action-bar">
            <v-btn variant="text" size="small" color="error" @click="handleClearChat" v-if="hasMessages">
                <v-icon start size="small">mdi-delete</v-icon>
                Clear
            </v-btn>
            <v-spacer />
            <v-btn variant="tonal" size="small" color="primary" @click="drawer = true">
                <v-badge :content="automations.length" :model-value="automations.length > 0" color="success" inline>
                    <v-icon start size="small">mdi-cog-outline</v-icon>
                </v-badge>
                Automations
            </v-btn>
        </div>

        <!-- Main Chat Area -->
        <div class="chat-wrapper">
            <AIChat ref="chatRef" v-model="prompt" @install-automation="handleInstallAutomation"
                @has-messages="hasMessages = $event" />
        </div>

        <!-- Automation List Drawer -->
        <v-navigation-drawer v-model="drawer" location="right" temporary width="400" class="automation-drawer">
            <template v-slot:prepend>
                <div class="drawer-header">
                    <div class="drawer-title">
                        <v-icon size="small" class="mr-2">mdi-cog-outline</v-icon>
                        <span>Automations</span>
                    </div>
                    <v-btn icon variant="text" size="x-small" @click="drawer = false">
                        <v-icon size="small">mdi-close</v-icon>
                    </v-btn>
                </div>
                <v-divider />
            </template>

            <v-list density="compact">
                <v-list-item v-if="loading">
                    <v-progress-circular indeterminate color="primary" size="20" />
                    <span class="ml-3 text-caption">Loading...</span>
                </v-list-item>

                <v-list-item v-else-if="automations.length === 0">
                    <v-list-item-title class="text-secondary text-caption">
                        No automations found
                    </v-list-item-title>
                </v-list-item>

                <v-list-item v-for="automation in automations" :key="automation.id" class="automation-item">
                    <template v-slot:prepend>
                        <v-avatar :color="automation.state === 'on' ? 'success' : 'grey'" size="28">
                            <v-icon size="x-small" color="white">
                                {{ automation.state === 'on' ? 'mdi-check' : 'mdi-power' }}
                            </v-icon>
                        </v-avatar>
                    </template>

                    <v-list-item-title class="text-body-2">{{ automation.alias }}</v-list-item-title>
                    <v-list-item-subtitle class="text-caption">
                        {{ automation.entity_id }}
                    </v-list-item-subtitle>
                    <v-list-item-subtitle v-if="automation.prompt" class="text-caption mt-1">
                        <v-icon size="x-small">mdi-chat</v-icon>
                        {{ truncate(automation.prompt, 40) }}
                    </v-list-item-subtitle>

                    <template v-slot:append>
                        <v-btn v-if="automation.is_editable" size="x-small" @click="handleEditAutomation(automation)"
                            color="primary" variant="text" icon>
                            <v-icon size="small">mdi-pencil</v-icon>
                        </v-btn>
                    </template>
                </v-list-item>
            </v-list>
        </v-navigation-drawer>

        <!-- Success Snackbar -->
        <v-snackbar v-model="showSuccessSnackbar" color="success" :timeout="3000" location="top">
            <v-icon start>mdi-check-circle</v-icon>
            Automation installed successfully!
        </v-snackbar>
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

const loading = ref(true);
const automations = ref<Automation[]>([]);
const drawer = ref(false);
const prompt = ref('');
const showSuccessSnackbar = ref(false);
const hasMessages = ref(false);
const chatRef = ref<InstanceType<typeof AIChat> | null>(null);

const handleClearChat = async () => {
    if (confirm('Clear chat history?')) {
        if (chatRef.value) {
            await chatRef.value.clearChat();
            prompt.value = '';
        }
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
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || errorData.detail || 'Failed to install automation');
        }

        await fetchAutomations();
        showSuccessSnackbar.value = true;
        console.log('Automation installed successfully');
    } catch (error) {
        console.error('Failed to install automation:', error);
        alert(`Failed to install automation: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
};

const handleEditAutomation = (automation: Automation) => {
    drawer.value = false;
    if (automation.prompt) {
        prompt.value = `Edit: "${automation.alias}" - ${automation.prompt}`;
    } else {
        prompt.value = `Edit: "${automation.alias}" (${automation.entity_id})`;
    }
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

const truncate = (text: string, length: number): string => {
    if (text.length <= length) return text;
    return text.substring(0, length) + '...';
};

onMounted(fetchAutomations);
</script>

<style scoped>
.dashboard {
    display: flex;
    flex-direction: column;
    height: 100vh;
    max-height: 100vh;
    overflow: hidden;
}

.action-bar {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 1rem;
    background: var(--ha-card-background);
    border-bottom: 1px solid var(--ha-border);
    flex-shrink: 0;
    z-index: 10;
    height: 48px;
}

.chat-wrapper {
    flex: 1;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    min-height: 0;
}

.automation-drawer {
    border-left: 1px solid var(--ha-border);
}

.drawer-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.75rem 1rem;
}

.drawer-title {
    display: flex;
    align-items: center;
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--ha-primary-text);
}

.automation-item {
    border-bottom: 1px solid var(--ha-border);
    padding: 0.75rem 1rem;
}
</style>