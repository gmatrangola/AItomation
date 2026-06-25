<template>
    <div class="configuration-view">
        <v-container fluid class="pa-4">
            <div class="config-header mb-4">
                <h2 class="text-h5 primary-text">
                    <v-icon class="mr-2">mdi-cog</v-icon>
                    Configuration
                </h2>
                <p class="secondary-text mt-2">Configure your AI provider and customize the system prompt</p>
            </div>

            <!-- Show alert if redirected due to missing configuration -->
            <v-alert
                v-if="showSetupRequired"
                type="info"
                variant="tonal"
                closable
                class="mb-4"
                @click:close="showSetupRequired = false"
            >
                <v-alert-title>Configuration Required</v-alert-title>
                Please configure your AI provider before using AItomations Creator.
            </v-alert>

            <v-alert v-if="saveSuccess" type="success" variant="tonal" closable class="mb-4">
                Configuration saved successfully!
            </v-alert>

            <v-alert v-if="saveError" type="error" variant="tonal" closable class="mb-4">
                {{ saveError }}
            </v-alert>

            <v-form ref="form" v-model="valid" @submit.prevent="saveConfiguration">
                <!-- LLM Provider Section -->
                <v-card class="mb-4 config-card">
                    <v-card-title class="d-flex align-center card-title">
                        <v-icon class="mr-2">mdi-robot</v-icon>
                        AI Provider
                    </v-card-title>
                    <v-divider />
                    <v-card-text>
                        <v-radio-group v-model="config.llm_provider" inline class="radio-group">
                            <v-radio label="Google Gemini" value="gemini" />
                            <v-radio label="Ollama (Local)" value="ollama" />
                        </v-radio-group>

                        <!-- Gemini Configuration -->
                        <v-expand-transition>
                            <div v-if="config.llm_provider === 'gemini'" class="mt-4">
                                <v-text-field
                                    v-model="config.gemini_api_key"
                                    label="Gemini API Key"
                                    :rules="geminiRules"
                                    hint="Get your API key from https://makersuite.google.com/app/apikey"
                                    persistent-hint
                                    prepend-inner-icon="mdi-key"
                                    class="mb-4"
                                    variant="outlined"
                                    density="comfortable"
                                />

                                <v-select
                                    v-model="config.gemini_model"
                                    label="Model"
                                    :items="geminiModels"
                                    prepend-inner-icon="mdi-brain"
                                    variant="outlined"
                                    density="comfortable"
                                />
                            </div>
                        </v-expand-transition>

                        <!-- Ollama Configuration -->
                        <v-expand-transition>
                            <div v-if="config.llm_provider === 'ollama'" class="mt-4">
                                <v-text-field
                                    v-model="config.ollama_api_url"
                                    label="Ollama API URL"
                                    :rules="ollamaUrlRules"
                                    hint="e.g., http://192.168.1.100:11434/api/generate"
                                    persistent-hint
                                    prepend-inner-icon="mdi-server"
                                    class="mb-4"
                                    variant="outlined"
                                    density="comfortable"
                                />

                                <v-text-field
                                    v-model="config.ollama_model"
                                    label="Model Name"
                                    hint="e.g., llama3.2:latest, qwen2.5:3b"
                                    persistent-hint
                                    prepend-inner-icon="mdi-brain"
                                    variant="outlined"
                                    density="comfortable"
                                />
                            </div>
                        </v-expand-transition>

                        <v-slider
                            v-model="config.request_timeout"
                            label="Request Timeout (seconds)"
                            :min="30"
                            :max="600"
                            :step="10"
                            thumb-label
                            class="mt-6"
                            color="primary"
                        />
                    </v-card-text>
                </v-card>

                <!-- System Prompt Template Section -->
                <v-card class="config-card">
                    <v-card-title class="d-flex align-center justify-space-between card-title">
                        <div class="d-flex align-center">
                            <v-icon class="mr-2">mdi-file-document-edit</v-icon>
                            System Prompt Template
                        </div>
                        <v-btn
                            size="small"
                            variant="text"
                            color="primary"
                            @click="showTemplateHelp = !showTemplateHelp"
                        >
                            <v-icon start size="small">mdi-help-circle</v-icon>
                            {{ showTemplateHelp ? 'Hide' : 'Show' }} Help
                        </v-btn>
                    </v-card-title>
                    <v-divider />

                    <!-- Template Help -->
                    <v-expand-transition>
                        <v-card-text v-if="showTemplateHelp" class="help-section">
                            <div class="template-help">
                                <h4 class="mb-2 primary-text">Available Variables:</h4>
                                <v-chip
                                    v-for="variable in availableVariables"
                                    :key="variable.name"
                                    size="small"
                                    class="ma-1 variable-chip"
                                    @click="insertVariable(variable.name)"
                                >
                                    <v-icon start size="small">mdi-code-braces</v-icon>
                                    {{ variable.name }}
                                </v-chip>

                                <v-divider class="my-3" />

                                <div
                                    v-for="variable in availableVariables"
                                    :key="variable.name"
                                    class="variable-doc mb-2"
                                >
                                    <code class="variable-code">{{ variable.name }}</code>
                                    <span class="ml-2 secondary-text">{{ variable.description }}</span>
                                </div>

                                <v-divider class="my-3" />

                                <div class="example-section">
                                    <h4 class="mb-2 primary-text">Example Template:</h4>
                                    <pre class="example-template">{{ exampleTemplate }}</pre>
                                </div>
                            </div>
                        </v-card-text>
                    </v-expand-transition>

                    <v-card-text>
                        <v-textarea
                            ref="templateEditor"
                            v-model="config.system_prompt_template"
                            label="Custom Template (leave empty for default)"
                            hint="Use Jinja2 syntax with {{ variable }} for variables"
                            persistent-hint
                            rows="12"
                            auto-grow
                            variant="outlined"
                            density="comfortable"
                            class="template-editor"
                            @keydown="handleTemplateKeydown"
                        >
                            <template #prepend-inner>
                                <v-menu
                                    v-model="autocompleteMenu"
                                    :close-on-content-click="false"
                                    location="bottom start"
                                >
                                    <template #activator="{ props }">
                                        <span v-bind="props"></span>
                                    </template>
                                    <v-card max-width="300" class="autocomplete-menu">
                                        <v-list density="compact">
                                            <v-list-item
                                                v-for="suggestion in filteredSuggestions"
                                                :key="suggestion.name"
                                                @click="completeSuggestion(suggestion)"
                                            >
                                                <template #prepend>
                                                    <v-icon size="small">mdi-code-braces</v-icon>
                                                </template>
                                                <v-list-item-title>{{ suggestion.name }}</v-list-item-title>
                                                <v-list-item-subtitle>{{
                                                    suggestion.description
                                                }}</v-list-item-subtitle>
                                            </v-list-item>
                                        </v-list>
                                    </v-card>
                                </v-menu>
                            </template>
                        </v-textarea>

                        <div class="d-flex justify-space-between mt-3">
                            <v-btn variant="text" color="secondary" @click="loadDefaultTemplate">
                                <v-icon start>mdi-refresh</v-icon>
                                Load Default Template
                            </v-btn>
                            <v-btn
                                variant="text"
                                color="primary"
                                :disabled="!config.system_prompt_template"
                                @click="previewTemplate"
                            >
                                <v-icon start>mdi-eye</v-icon>
                                Preview
                            </v-btn>
                        </div>
                    </v-card-text>
                </v-card>

                <!-- Action Buttons -->
                <div class="d-flex justify-end gap-2 mt-4">
                    <v-btn variant="text" @click="nextTick(loadConfiguration)">
                        <v-icon start>mdi-refresh</v-icon>
                        Reset
                    </v-btn>
                    <v-btn type="submit" color="primary" :loading="saving" :disabled="!valid" variant="elevated">
                        <v-icon start>mdi-content-save</v-icon>
                        Save Configuration
                    </v-btn>
                </div>
            </v-form>

            <!-- Preview Dialog -->
            <v-dialog v-model="showPreview" max-width="800">
                <v-card class="preview-dialog">
                    <v-card-title class="card-title">
                        <v-icon class="mr-2">mdi-eye</v-icon>
                        Template Preview
                    </v-card-title>
                    <v-divider />
                    <v-card-text>
                        <v-alert v-if="previewError" type="error" variant="tonal" class="mb-4">
                            {{ previewError }}
                        </v-alert>
                        <pre v-else class="preview-content">{{ previewContent }}</pre>
                    </v-card-text>
                    <v-card-actions>
                        <v-spacer />
                        <v-btn variant="text" @click="showPreview = false">Close</v-btn>
                    </v-card-actions>
                </v-card>
            </v-dialog>

            <!-- Build stamp -->
            <div class="build-stamp secondary-text mt-6">
                <v-icon size="x-small" class="mr-1">mdi-tag-outline</v-icon>
                <span>v{{ buildInfo.version }}</span>
                <span class="mx-2">·</span>
                <span class="build-commit">{{ buildInfo.commit }}</span>
                <span class="mx-2">·</span>
                <span>built {{ buildTimeLocal }}</span>
            </div>
        </v-container>
    </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue';
import { useRouter } from 'vue-router';
import { configService } from '@/services/configService';

interface Configuration {
    llm_provider: 'gemini' | 'ollama';
    gemini_api_key: string;
    gemini_model: string;
    ollama_api_url: string;
    ollama_model: string;
    request_timeout: number;
    system_prompt_template: string;
}

interface TemplateVariable {
    name: string;
    description: string;
}

const form = ref();
const templateEditor = ref();
const valid = ref(false);
const saving = ref(false);
const saveSuccess = ref(false);
const saveError = ref<string | null>(null);
const showTemplateHelp = ref(false);
const showPreview = ref(false);
const previewContent = ref('');
const previewError = ref<string | null>(null);
const autocompleteMenu = ref(false);
const autocompletePrefix = ref('');

const config = ref<Configuration>({
    llm_provider: 'gemini',
    gemini_api_key: '',
    gemini_model: 'gemini-2.5-pro',
    ollama_api_url: 'http://host.local:11434/api/generate',
    ollama_model: 'llama3.2:latest',
    request_timeout: 120,
    system_prompt_template: '',
});

const geminiModels = [
    { title: 'Gemini 2.5 Flash (Fast)', value: 'gemini-2.5-flash' },
    { title: 'Gemini 2.5 Pro (Best)', value: 'gemini-2.5-pro' },
];

const availableVariables: TemplateVariable[] = [
    {
        name: '{{ ha_context }}',
        description:
            'Full Home Assistant context object (config, areas, entities, helpers, scenes, automations, services)',
    },
    { name: '{{ ha_context.entities }}', description: 'List of entities (id, name, domain, area_id)' },
    { name: '{{ ha_context.services }}', description: 'List of available services (e.g., light.turn_on)' },
    { name: '{{ ha_context.automations }}', description: 'List of existing automations (id, name, summary)' },
    { name: '{{ user_request }}', description: 'Current user instruction text' },
    { name: '{{ chat_history }}', description: 'Recent conversation messages (role, content)' },
];

const exampleTemplate = `You are a Home Assistant automation expert.

**Available Entities:**
{% for entity in ha_context.entities[:10] %}
- {{ entity.id }} ({{ entity.name }})
{% endfor %}
... and {{ ha_context.entities|length - 10 }} more

**Available Services:**
{{ ha_context.services|join(', ') }}

**Existing Automations:**
{% for auto in ha_context.automations %}
- {{ auto.name }}
{% endfor %}

**User Request:**
{{ user_request }}

Generate YAML automation with explanation.`;

const geminiRules = [
    (v: string) => {
        if (config.value.llm_provider !== 'gemini') return true;
        return !!v || 'API key is required for Gemini';
    },
];

const ollamaUrlRules = [
    (v: string) => {
        if (config.value.llm_provider !== 'ollama') return true;
        return !!v || 'API URL is required for Ollama';
    },
    (v: string) => {
        if (config.value.llm_provider !== 'ollama' || !v) return true;
        try {
            new URL(v);
            return true;
        } catch {
            return 'Please enter a valid URL';
        }
    },
];

const filteredSuggestions = computed(() => {
    if (!autocompletePrefix.value) return availableVariables;
    return availableVariables.filter((v) => v.name.toLowerCase().includes(autocompletePrefix.value.toLowerCase()));
});

const router = useRouter();
const showSetupRequired = ref(false);

// Build stamp (injected at build time by Vite — see vite.config.ts)
const buildInfo = __BUILD_INFO__;
const buildTimeLocal = new Date(buildInfo.buildTime).toLocaleString();

const loadConfiguration = async () => {
    try {
        const data = await configService.loadConfiguration();

        if (!data) {
            saveError.value = 'Failed to load configuration';
            showSetupRequired.value = true;
            return;
        }

        config.value = {
            llm_provider: data.llm_provider || 'gemini',
            gemini_api_key: data.gemini_api_key || '',
            gemini_model: data.gemini_model || 'gemini-2.5-pro',
            ollama_api_url: data.ollama_api_url || 'http://host.local:11434/api/generate',
            ollama_model: data.ollama_model || 'llama3.2:latest',
            request_timeout: data.request_timeout || 120,
            system_prompt_template: data.system_prompt_template || '',
        };

        // Check if configuration is valid
        const validation = await configService.checkConfiguration();
        if (!validation.isValid) {
            showSetupRequired.value = true;
            console.log('Configuration required - showing setup alert');
        }
    } catch (error) {
        console.error('Failed to load configuration:', error);
        saveError.value = 'Failed to load configuration';
        showSetupRequired.value = true;
    }
};

const saveConfiguration = async () => {
    if (!valid.value) return;

    saving.value = true;
    saveSuccess.value = false;
    saveError.value = null;

    const result = await configService.saveConfiguration(config.value);

    if (result.success) {
        saveSuccess.value = true;
        showSetupRequired.value = false;

        // Navigate to Dashboard after successful save
        setTimeout(() => {
            saveSuccess.value = false;
            router.push({ name: 'Dashboard' });
        }, 1500);
    } else {
        saveError.value = result.error || 'Failed to save configuration';
    }

    saving.value = false;
};

const previewTemplate = async () => {
    previewError.value = null;
    showPreview.value = true;

    try {
        const response = await fetch('api/preview_prompt_template', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                template: config.value.system_prompt_template,
            }),
        });

        if (!response.ok) {
            const contentType = response.headers.get('content-type');
            let errorMessage = 'Failed to preview template';
            try {
                if (contentType?.includes('application/json')) {
                    const error = await response.json();
                    errorMessage = error.error || error.detail || errorMessage;
                } else {
                    const text = await response.text();
                    errorMessage = text || errorMessage;
                }
            } catch (e) {
                console.error('Error parsing error response:', e);
            }
            throw new Error(errorMessage);
        }

        const contentType = response.headers.get('content-type');
        if (contentType?.includes('application/json')) {
            const data = await response.json();
            previewContent.value = data.rendered || data.preview || JSON.stringify(data, null, 2);
        } else {
            // Response is plain text or HTML
            const text = await response.text();
            previewContent.value = text;
        }
    } catch (error) {
        console.error('Failed to preview template:', error);
        previewError.value = error instanceof Error ? error.message : 'Failed to preview template';
    }
};

const loadDefaultTemplate = async () => {
    try {
        const response = await fetch('api/default_prompt_template');
        if (!response.ok) {
            throw new Error('Failed to load default template');
        }
        const contentType = response.headers.get('content-type');
        if (contentType?.includes('application/json')) {
            const data = await response.json();
            config.value.system_prompt_template = data.template || data.prompt || '';
        } else {
            // Response is plain text (the template itself)
            const text = await response.text();
            config.value.system_prompt_template = text;
        }
    } catch (error) {
        console.error('Failed to load default template:', error);
        saveError.value = 'Failed to load default template';
    }
};

const insertVariable = (variable: string) => {
    const textarea = templateEditor.value?.$el.querySelector('textarea');
    if (!textarea) return;

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const text = config.value.system_prompt_template;

    config.value.system_prompt_template = text.substring(0, start) + variable + text.substring(end);

    nextTick(() => {
        textarea.focus();
        const newPos = start + variable.length;
        textarea.setSelectionRange(newPos, newPos);
    });
};

const handleTemplateKeydown = (event: KeyboardEvent) => {
    const textarea = event.target as HTMLTextAreaElement;
    const cursorPos = textarea.selectionStart;
    const text = config.value.system_prompt_template;

    // Detect {{ for autocomplete
    if (event.key === '{' && text[cursorPos - 1] === '{') {
        autocompleteMenu.value = true;
        autocompletePrefix.value = '';
    }

    // Close autocomplete on Escape
    if (event.key === 'Escape' && autocompleteMenu.value) {
        autocompleteMenu.value = false;
        event.preventDefault();
    }

    // Update autocomplete filter
    if (autocompleteMenu.value) {
        const lastOpenBrace = text.lastIndexOf('{{', cursorPos);
        if (lastOpenBrace !== -1) {
            autocompletePrefix.value = text.substring(lastOpenBrace + 2, cursorPos);
        }
    }
};

const completeSuggestion = (suggestion: TemplateVariable) => {
    const textarea = templateEditor.value?.$el.querySelector('textarea');
    if (!textarea) return;

    const cursorPos = textarea.selectionStart;
    const text = config.value.system_prompt_template;
    const lastOpenBrace = text.lastIndexOf('{{', cursorPos);

    if (lastOpenBrace !== -1) {
        config.value.system_prompt_template =
            text.substring(0, lastOpenBrace) + suggestion.name + text.substring(cursorPos);

        nextTick(() => {
            textarea.focus();
            const newPos = lastOpenBrace + suggestion.name.length;
            textarea.setSelectionRange(newPos, newPos);
        });
    }

    autocompleteMenu.value = false;
};

onMounted(() => {
    loadConfiguration();
});
</script>

<style scoped>
.configuration-view {
    height: 100%;
    overflow-y: auto;
    background-color: var(--ha-background);
}

.config-header h2 {
    color: var(--ha-primary-text);
}

.build-stamp {
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.75rem;
    opacity: 0.7;
}

.build-stamp .build-commit {
    font-family: 'Roboto Mono', monospace;
}

.primary-text {
    color: var(--ha-primary-text) !important;
}

.secondary-text {
    color: var(--ha-secondary-text) !important;
}

.config-card {
    background-color: var(--ha-card-background) !important;
    border: 1px solid var(--ha-border);
}

.card-title {
    color: var(--ha-primary-text) !important;
    font-weight: 600;
}

/* Radio buttons */
.radio-group :deep(.v-label) {
    color: var(--ha-primary-text) !important;
}

.radio-group :deep(.v-selection-control__input) {
    color: var(--ha-primary-color) !important;
}

/* Text fields */
:deep(.v-field) {
    background-color: var(--ha-card-background);
    border-color: var(--ha-border);
}

:deep(.v-field__input) {
    color: var(--ha-primary-text) !important;
}

:deep(.v-field__outline) {
    color: var(--ha-border) !important;
}

:deep(.v-label) {
    color: var(--ha-secondary-text) !important;
}

:deep(.v-field--focused .v-label) {
    color: var(--ha-primary-color) !important;
}

:deep(.v-messages__message) {
    color: var(--ha-secondary-text) !important;
}

/* Slider */
:deep(.v-slider__tick-label) {
    color: var(--ha-secondary-text) !important;
}

/* Help section */
.help-section {
    background-color: rgba(255, 255, 255, 0.05) !important;
    border-top: 1px solid var(--ha-border);
    border-bottom: 1px solid var(--ha-border);
}

.template-help {
    font-size: 0.9rem;
}

.variable-chip {
    cursor: pointer;
    background-color: rgba(var(--v-theme-primary), 0.2) !important;
    border: 1px solid var(--ha-primary-color);
}

.variable-chip:hover {
    background-color: rgba(var(--v-theme-primary), 0.3) !important;
}

.variable-doc code.variable-code {
    background: rgba(var(--v-theme-primary), 0.15);
    color: var(--ha-primary-color);
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.85rem;
    font-weight: 500;
}

.example-template {
    background: var(--ha-card-background);
    border: 1px solid var(--ha-border);
    color: var(--ha-primary-text);
    padding: 12px;
    border-radius: 4px;
    overflow-x: auto;
    font-size: 0.85rem;
}

.template-editor :deep(textarea) {
    font-family: 'Roboto Mono', monospace;
    font-size: 0.9rem;
    color: var(--ha-primary-text) !important;
}

.autocomplete-menu {
    background-color: var(--ha-card-background) !important;
    border: 1px solid var(--ha-border);
}

.autocomplete-menu :deep(.v-list-item-title) {
    color: var(--ha-primary-text) !important;
}

.autocomplete-menu :deep(.v-list-item-subtitle) {
    color: var(--ha-secondary-text) !important;
}

.preview-dialog {
    background-color: var(--ha-card-background) !important;
}

.preview-content {
    background: rgba(0, 0, 0, 0.3);
    border: 1px solid var(--ha-border);
    color: var(--ha-primary-text);
    padding: 16px;
    border-radius: 4px;
    overflow-x: auto;
    max-height: 60vh;
    font-size: 0.85rem;
    white-space: pre-wrap;
    font-family: 'Roboto Mono', monospace;
}

/* Ensure all text inputs have proper contrast */
:deep(.v-text-field input),
:deep(.v-textarea textarea) {
    color: var(--ha-primary-text) !important;
}

/* Select dropdown */
:deep(.v-select .v-field__input) {
    color: var(--ha-primary-text) !important;
}

:deep(.v-list-item-title) {
    color: var(--ha-primary-text) !important;
}

:deep(.v-list-item-subtitle) {
    color: var(--ha-secondary-text) !important;
}
</style>
