<template>
    <div class="ai-response">
        <!-- Display the full response with Markdown rendering -->
        <div class="markdown-content mt-3" v-html="renderMarkdown(response)"></div>

        <!-- Install Button -->
        <div v-if="extractedYaml" class="action-section mt-4">
            <v-btn color="success" variant="elevated" size="large" @click="handleInstallAutomation">
                <v-icon left>mdi-download</v-icon>
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
    margin-bottom: 1rem;
}
</style>