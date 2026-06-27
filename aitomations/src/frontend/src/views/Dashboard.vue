<template>
    <div class="dashboard">
        <!-- Configuration Error Banner - Takes Priority -->
        <v-alert
            v-if="configError"
            type="warning"
            variant="tonal"
            prominent
            class="config-error-banner"
            closable
            @click:close="configError = null"
        >
            <v-alert-title>
                <v-icon start>mdi-cog-alert</v-icon>
                Configuration Required
            </v-alert-title>
            <div class="mt-2">
                {{ configError }}
            </div>
            <v-btn class="mt-3" color="warning" variant="elevated" size="small" :to="{ name: 'Configuration' }">
                <v-icon start size="small">mdi-cog</v-icon>
                Go to Configuration
            </v-btn>
        </v-alert>

        <!-- Error Banner - Top Level, Most Prominent -->
        <ErrorMessage v-if="currentError" :error="currentError" class="error-banner" @close="clearError" />

        <!-- Main Chat Area -->
        <div class="chat-wrapper">
            <AIChat
                ref="chatRef"
                v-model="prompt"
                :disabled="!!configError"
                :apply-fn="handleApplyArtifact"
                @has-messages="hasMessages = $event"
                @error="handleError"
            />
        </div>

        <!-- Action bar: pinned at the bottom, below the prompt input -->
        <div class="action-bar">
            <v-btn variant="tonal" size="small" color="success" @click="handleDone">
                <v-icon start size="small">mdi-check-circle-outline</v-icon>
                Done
            </v-btn>
            <v-spacer />
            <v-btn variant="tonal" size="small" color="primary" class="mr-2" @click="openDashboards">
                <v-badge :content="dashboards.length" :model-value="dashboards.length > 0" color="success" inline>
                    <v-icon start size="small">mdi-view-dashboard-outline</v-icon>
                </v-badge>
                Dashboards
            </v-btn>
            <v-btn variant="tonal" size="small" color="primary" @click="drawer = true">
                <v-badge :content="automations.length" :model-value="automations.length > 0" color="success" inline>
                    <v-icon start size="small">mdi-cog-outline</v-icon>
                </v-badge>
                Automations
            </v-btn>
        </div>

        <!-- Automation List Drawer -->
        <v-navigation-drawer v-model="drawer" location="right" temporary width="400" class="automation-drawer">
            <template #prepend>
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
                    <v-list-item-title class="text-secondary text-caption"> No automations found </v-list-item-title>
                </v-list-item>

                <v-list-item v-for="automation in automations" :key="automation.id" class="automation-item">
                    <template #prepend>
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

                    <template #append>
                        <v-btn
                            v-if="automation.is_editable"
                            size="x-small"
                            color="primary"
                            variant="text"
                            icon
                            @click="handleEditAutomation(automation)"
                        >
                            <v-icon size="small">mdi-pencil</v-icon>
                        </v-btn>
                    </template>
                </v-list-item>
            </v-list>
        </v-navigation-drawer>

        <!-- Dashboard List Drawer -->
        <v-navigation-drawer v-model="dashboardDrawer" location="right" temporary width="400">
            <template #prepend>
                <div class="drawer-header">
                    <div class="drawer-title">
                        <v-icon size="small" class="mr-2">mdi-view-dashboard-outline</v-icon>
                        <span>Dashboards</span>
                    </div>
                    <v-btn icon variant="text" size="x-small" @click="dashboardDrawer = false">
                        <v-icon size="small">mdi-close</v-icon>
                    </v-btn>
                </div>
                <v-divider />
            </template>

            <v-list density="compact">
                <v-list-item v-if="dashboardsLoading">
                    <v-progress-circular indeterminate color="primary" size="20" />
                    <span class="ml-3 text-caption">Loading...</span>
                </v-list-item>

                <v-list-item v-else-if="dashboards.length === 0">
                    <v-list-item-title class="text-secondary text-caption"> No dashboards found </v-list-item-title>
                </v-list-item>

                <v-list-item v-for="dash in dashboards" :key="dash.url_path ?? 'default'" class="automation-item">
                    <template #prepend>
                        <v-avatar color="primary" size="28">
                            <v-icon size="x-small" color="white">mdi-view-dashboard</v-icon>
                        </v-avatar>
                    </template>

                    <v-list-item-title class="text-body-2">{{ dash.title || dash.url_path }}</v-list-item-title>
                    <v-list-item-subtitle class="text-caption">
                        {{ dash.url_path ?? 'default' }} · {{ dash.mode }}
                    </v-list-item-subtitle>

                    <template #append>
                        <v-btn size="x-small" color="primary" variant="text" icon @click="handleEditDashboard(dash)">
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

        <!-- Script / Scene Applied Snackbar -->
        <v-snackbar v-model="showEntitySnackbar" color="success" :timeout="3000" location="top">
            <v-icon start>mdi-check-circle</v-icon>
            {{ entitySnackbarText }}
        </v-snackbar>

        <!-- Dashboard Applied Snackbar (with deep link out of the ingress iframe) -->
        <v-snackbar v-model="showDashboardSnackbar" color="success" :timeout="6000" location="top">
            <v-icon start>mdi-check-circle</v-icon>
            Dashboard applied!
            <template #actions>
                <v-btn v-if="dashboardLink" variant="text" :href="dashboardLink" target="_top"> Open dashboard </v-btn>
            </template>
        </v-snackbar>
    </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import AIChat from '@/components/AIChat.vue';
import ErrorMessage from '@/components/ErrorMessage.vue';
import { configService } from '@/services/configService';
import { dashboardService, type DashboardSummary } from '@/services/dashboardService';
import { entityService } from '@/services/entityService';
import type { Artifact } from '@/types/chat';
import type { APIError } from '@/types/errors';

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
const showEntitySnackbar = ref(false);
const entitySnackbarText = ref('');
const hasMessages = ref(false);
const chatRef = ref<InstanceType<typeof AIChat> | null>(null);
const currentError = ref<APIError | null>(null);
const configError = ref<string | null>(null);

// Dashboards
const dashboards = ref<DashboardSummary[]>([]);
const dashboardDrawer = ref(false);
const dashboardsLoading = ref(false);
const showDashboardSnackbar = ref(false);
const dashboardLink = ref<string | null>(null);

const checkConfiguration = async () => {
    const result = await configService.checkConfiguration();

    if (!result.isValid) {
        configError.value = result.error;
    } else {
        configError.value = null;
    }
};

const handleError = (error: APIError) => {
    currentError.value = error;

    // Check if error is configuration-related
    if (error.error_code === 'LLM_API_ERROR' || error.error_code === 'CONFIG_ERROR') {
        configError.value = error.context?.details || 'Configuration error detected. Please check your settings.';
    }
};

const clearError = () => {
    currentError.value = null;
};

// Finish the current conversation: clear the prompt, the responses, and server history
// so the user can start fresh.
const handleDone = async () => {
    if (!confirm('Done with this conversation? This clears the chat and starts a new one.')) return;
    if (chatRef.value) {
        await chatRef.value.clearChat();
    }
    prompt.value = '';
    currentError.value = null;
};

// Returns true on success so the chat UI can mark the artifact applied.
const handleApplyArtifact = async (artifact: Artifact): Promise<boolean> => {
    switch (artifact.kind) {
        case 'automation':
            return handleInstallAutomation(artifact.yaml);
        case 'dashboard':
            return handleApplyDashboard(artifact.yaml);
        default:
            // script, scene, and helper kinds (input_*, timer, counter) apply through
            // /apply_entity (helpers go to the WebSocket path on the backend).
            return handleApplyEntity(artifact);
    }
};

const handleApplyEntity = async (artifact: Artifact): Promise<boolean> => {
    const result = await entityService.applyEntity(artifact, prompt.value);

    if (!result.success) {
        currentError.value = {
            error_code: result.error_code || 'UNKNOWN_ERROR',
            context: { details: result.error || `Failed to apply ${artifact.kind}` },
        };
        return false;
    }

    currentError.value = null;
    const label = artifact.kind
        .split('_')
        .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
        .join(' ');
    entitySnackbarText.value = `${label} installed successfully!`;
    showEntitySnackbar.value = true;
    return true;
};

const handleInstallAutomation = async (yaml: string): Promise<boolean> => {
    try {
        const response = await fetch('api/install_automation', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                automation_yaml: yaml,
                prompt: prompt.value,
            }),
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || errorData.detail || 'Failed to install automation');
        }

        await fetchAutomations();
        showSuccessSnackbar.value = true;
        currentError.value = null;
        return true;
    } catch (error) {
        console.error('Failed to install automation:', error);
        currentError.value = {
            error_code: 'UNKNOWN_ERROR',
            context: {
                details: error instanceof Error ? error.message : 'Failed to install automation',
            },
        };
        return false;
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

// Build a deep link to a dashboard that escapes the ingress iframe (target="_top").
const dashboardUrl = (urlPath: string | null | undefined): string => {
    return urlPath ? `/${urlPath}` : '/lovelace';
};

const handleApplyDashboard = async (yaml: string): Promise<boolean> => {
    // The model marks the target dashboard with `# aitomation_url_path: <slug>` when
    // modifying or naming a dashboard. Without it we always create a new dashboard so we
    // never clobber the user's default dashboard.
    const urlPathMatch = yaml.match(/^#\s*aitomation_url_path:\s*(\S+)/im);
    const targetUrlPath = urlPathMatch ? urlPathMatch[1] : null;
    const exists = targetUrlPath ? dashboards.value.some((d) => d.url_path === targetUrlPath) : false;

    const result = await dashboardService.applyDashboard({
        config_yaml: yaml,
        url_path: targetUrlPath,
        create: !exists, // existing dashboard => save in place; otherwise create
    });

    if (!result.success) {
        currentError.value = {
            error_code: result.error_code || 'UNKNOWN_ERROR',
            context: { details: result.error || 'Failed to apply dashboard' },
        };
        return false;
    }

    currentError.value = null;
    dashboardLink.value = dashboardUrl(result.url_path);
    showDashboardSnackbar.value = true;
    await fetchDashboards();
    return true;
};

const fetchDashboards = async () => {
    dashboardsLoading.value = true;
    try {
        dashboards.value = await dashboardService.listDashboards();
    } finally {
        dashboardsLoading.value = false;
    }
};

const handleEditDashboard = (dashboard: DashboardSummary) => {
    dashboardDrawer.value = false;
    const name = dashboard.title || dashboard.url_path || 'dashboard';
    prompt.value = `Modify the "${name}" dashboard (url_path: ${dashboard.url_path ?? 'default'}): `;
};

const openDashboards = async () => {
    dashboardDrawer.value = true;
    await fetchDashboards();
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

onMounted(async () => {
    await checkConfiguration();
    await fetchAutomations();
    await fetchDashboards();
});
</script>

<style scoped>
.dashboard {
    display: flex;
    flex-direction: column;
    /* Fill the v-main content box (which is offset below the fixed app bar), not the full
       viewport — otherwise the bottom action bar would be clipped. */
    height: 100%;
    max-height: 100%;
    overflow: hidden;
}

.config-error-banner {
    flex-shrink: 0;
    z-index: 101;
    margin: 0.5rem;
}

.error-banner {
    flex-shrink: 0;
    z-index: 100;
}

.action-bar {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 1rem;
    background: var(--ha-card-background);
    border-top: 1px solid var(--ha-border);
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
