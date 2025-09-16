<script setup>
import { ref, onMounted } from 'vue';

const emit = defineEmits(['close']);

const options = ref({
    ollama_url: '',
    gemini_api_key: '',
});

const message = ref('');

// Fetch current settings when the component mounts
onMounted(async () => {
    try {
        const res = await fetch('/api/options');
        if (res.ok) {
            options.value = await res.json();
        }
    } catch (error) {
        message.value = 'Error fetching settings.';
        console.error(error);
    }
});

// Save settings
async function saveSettings() {
    message.value = '';
    try {
        const res = await fetch('/api/options', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(options.value),
        });
        if (res.ok) {
            message.value = 'Settings saved successfully!';
            setTimeout(() => emit('close'), 1500); // Close modal after a short delay
        } else {
            const errorData = await res.json();
            message.value = `Error: ${errorData.error || 'Failed to save settings.'}`;
        }
    } catch (error) {
        message.value = 'Error saving settings.';
        console.error(error);
    }
}
</script>

<template>
    <div class="settings-modal-backdrop">
        <div class="settings-modal">
            <h2>Settings</h2>
            <form @submit.prevent="saveSettings">
                <div class="form-group">
                    <label for="ollama-url">Ollama URL</label>
                    <input id="ollama-url" v-model="options.ollama_url" type="text"
                        placeholder="e.g., http://localhost:11434" />
                </div>
                <div class="form-group">
                    <label for="gemini-key">Google Gemini API Key</label>
                    <input id="gemini-key" v-model="options.gemini_api_key" type="password"
                        placeholder="Enter your Gemini API Key" />
                </div>
                <!-- Add other settings inputs here -->
                <div class="actions">
                    <button type="submit">Save</button>
                    <button type="button" @click="$emit('close')">Cancel</button>
                </div>
            </form>
            <p v-if="message" class="message">{{ message }}</p>
        </div>
    </div>
</template>

<style scoped>
.settings-modal-backdrop {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.6);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 1000;
}

.settings-modal {
    background-color: #2c2c2c;
    padding: 2rem;
    border-radius: 8px;
    width: 90%;
    max-width: 500px;
    color: #f0f0f0;
}

.form-group {
    margin-bottom: 1rem;
}

.form-group label {
    display: block;
    margin-bottom: 0.5rem;
}

.form-group input {
    width: 100%;
    padding: 0.5rem;
    border-radius: 4px;
    border: 1px solid #555;
    background-color: #333;
    color: #f0f0f0;
}

.actions {
    display: flex;
    justify-content: flex-end;
    gap: 1rem;
    margin-top: 1.5rem;
}

button {
    padding: 0.5rem 1rem;
    border-radius: 4px;
    border: none;
    cursor: pointer;
}

button[type='submit'] {
    background-color: #4caf50;
    color: white;
}

button[type='button'] {
    background-color: #f44336;
    color: white;
}

.message {
    margin-top: 1rem;
    text-align: center;
}
</style>