<template>
  <div class="ai-chat-container">
    <!-- AI Response Display -->
    <div 
      v-if="response" 
      class="ai-response-container mb-4 pa-3" 
      :class="responseContainerClass"
    >
      <div class="ai-response-header">
        <v-icon 
          :color="headerIconColor" 
          class="mr-2"
        >
          {{ headerIcon }}
        </v-icon>
        <span class="font-weight-bold">{{ headerText }}</span>
      </div>

      <!-- Success Response -->
      <template v-if="!response.error">
        <!-- Display the explanation -->
        <div v-if="response.explanation" class="explanation-text mt-3">
          <v-card variant="outlined" class="pa-3">
            <v-card-text class="pb-2">
              {{ response.explanation }}
            </v-card-text>
          </v-card>
        </div>

        <!-- Display the formatted YAML -->
        <div v-if="response.automation_yaml" class="yaml-container mt-3">
          <v-card variant="outlined">
            <v-card-title class="text-subtitle-2 py-2">
              Generated Automation YAML
              <v-spacer></v-spacer>
              <v-btn 
                icon="mdi-content-copy" 
                size="small" 
                variant="text"
                @click="copyYaml"
                :disabled="copying"
              >
                <v-icon>{{ copying ? 'mdi-check' : 'mdi-content-copy' }}</v-icon>
              </v-btn>
            </v-card-title>
            <v-divider></v-divider>
            <v-card-text class="pa-0">
              <pre class="yaml-code">{{ response.automation_yaml }}</pre>
            </v-card-text>
          </v-card>
        </div>

        <!-- Install Button -->
        <div v-if="response.automation_yaml" class="mt-4">
          <v-btn 
            color="success" 
            variant="elevated"
            @click="handleInstallAutomation"
          >
            <v-icon left>mdi-download</v-icon>
            Install Automation
          </v-btn>
        </div>
      </template>

      <!-- Error Response -->
      <template v-else>
        <v-alert 
          type="error" 
          class="mt-3"
          :title="errorTitle"
        >
          <div class="error-message">
            {{ response.error }}
          </div>
          
          <!-- Raw response for debugging -->
          <v-expansion-panels v-if="response.rawResponse" class="mt-3">
            <v-expansion-panel>
              <v-expansion-panel-title>
                <v-icon class="mr-2">mdi-bug</v-icon>
                Debug Information
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <pre class="debug-response">{{ response.rawResponse }}</pre>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
        </v-alert>
      </template>
    </div>

    <!-- Prompt Input -->
    <v-textarea 
      v-model="internalPrompt" 
      label="Your Prompt" 
      placeholder="e.g., 'Turn on the porch light at sunset and turn it off at sunrise'" 
      rows="3" 
      auto-grow 
      clearable
      :disabled="generating"
    />

    <!-- Generate Button -->
    <div class="mt-3">
      <v-btn 
        color="primary" 
        :loading="generating" 
        :disabled="!internalPrompt.trim()"
        @click="handleGenerate"
        block
      >
        <v-icon left>mdi-magic-staff</v-icon>
        Generate Automation
      </v-btn>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';

interface AiResponse {
  automation_yaml?: string;
  explanation?: string;
  error?: string;
  rawResponse?: string;
}

interface Props {
  response: AiResponse | null;
  generating?: boolean;
  modelValue?: string; // For v-model support on prompt
}

const props = withDefaults(defineProps<Props>(), {
  generating: false,
  modelValue: '',
});

const emit = defineEmits<{
  'install-automation': [yaml: string];
  'generate-prompt': [prompt: string];
  'update:modelValue': [value: string]; // For v-model support
}>();

const copying = ref(false);
const internalPrompt = ref(props.modelValue);

// Watch for external prompt changes (v-model)
watch(() => props.modelValue, (newValue) => {
  internalPrompt.value = newValue;
});

// Emit prompt changes for v-model
watch(internalPrompt, (newValue) => {
  emit('update:modelValue', newValue);
});

const responseContainerClass = computed(() => ({
  'success-response': !props.response?.error,
  'error-response': !!props.response?.error,
}));

const headerIcon = computed(() => 
  props.response?.error ? 'mdi-alert-circle' : 'mdi-robot'
);

const headerIconColor = computed(() => 
  props.response?.error ? 'error' : 'primary'
);

const headerText = computed(() => 
  props.response?.error ? 'AItomations Assistant - Error' : 'AItomations Assistant'
);

const errorTitle = computed(() => 
  'Failed to Generate Automation'
);

const handleGenerate = () => {
  if (!internalPrompt.value.trim()) return;
  emit('generate-prompt', internalPrompt.value.trim());
};

const handleInstallAutomation = () => {
  if (props.response?.automation_yaml) {
    emit('install-automation', props.response.automation_yaml);
  }
};

const copyYaml = async () => {
  if (!props.response?.automation_yaml) return;
  
  try {
    copying.value = true;
    await navigator.clipboard.writeText(props.response.automation_yaml);
    
    setTimeout(() => {
      copying.value = false;
    }, 2000);
  } catch (error) {
    console.error('Failed to copy YAML:', error);
    copying.value = false;
  }
};
</script>

<style scoped>
.ai-chat-container {
  width: 100%;
}

.ai-response-container {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  background-color: #fafafa;
}

.success-response {
  border-left: 4px solid #4caf50;
}

.error-response {
  border-left: 4px solid #f44336;
}

.ai-response-header {
  display: flex;
  align-items: center;
  font-size: 1.1rem;
}

.yaml-code {
  font-family: 'Roboto Mono', Monaco, 'Cascadia Code', 'Segoe UI Mono', Consolas, 'Courier New', monospace;
  font-size: 0.875rem;
  line-height: 1.4;
  margin: 0;
  padding: 16px;
  background-color: #f8f9fa;
  border-radius: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
  overflow-x: auto;
}

.debug-response {
  font-family: 'Roboto Mono', Monaco, 'Cascadia Code', 'Segoe UI Mono', Consolas, 'Courier New', monospace;
  font-size: 0.75rem;
  margin: 0;
  white-space: pre-wrap;
  color: #666;
  background-color: #f5f5f5;
  padding: 12px;
  border-radius: 4px;
}

.explanation-text {
  font-size: 0.95rem;
  line-height: 1.5;
}

.error-message {
  font-family: 'Roboto Mono', Monaco, monospace;
  font-size: 0.9rem;
}
</style>