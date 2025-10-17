<template>
    <div class="ai-response">
        <!-- Display the full response with Markdown rendering -->
        <div class="markdown-content" v-html="renderMarkdown(response)"></div>

        <!-- Install Button -->
        <div v-if="extractedYaml" class="action-section mt-4">
            <v-btn color="success" variant="elevated" size="large" @click="handleInstallAutomation">
                <v-icon start>mdi-download</v-icon>
                Install Automation
            </v-btn>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useMarkdown } from '@/composables/useMarkdown';

const { renderMarkdown } = useMarkdown();

interface Props {
    response: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    'install-automation': [yaml: string];
}>();

const extractYamlFromMarkdown = (markdown: string): string | null => {
    if (!markdown) return null;
    const match = markdown.match(/```yaml\n([\s\S]*?)\n```/);
    return match ? match[1].trim() : null;
};

const extractedYaml = computed(() => extractYamlFromMarkdown(props.response));

const handleInstallAutomation = () => {
    if (extractedYaml.value) {
        emit('install-automation', extractedYaml.value);
    }
};
</script>

<style scoped>
.action-section {
    text-align: center;
    margin-top: 1.5rem;
}

/* Markdown content inherits colors from parent CSS variables */
.markdown-content {
    line-height: 1.6;
}
</style>
