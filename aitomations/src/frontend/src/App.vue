<template>
    <v-app>
        <v-app-bar app color="primary" dark>
            <v-toolbar-title>AItomations</v-toolbar-title>
            <v-spacer></v-spacer>
            <v-btn to="/" text>
                <v-icon left>mdi-view-dashboard</v-icon>
                Dashboard
            </v-btn>
            <v-btn to="/settings" text>
                <v-icon left>mdi-cog</v-icon>
                Settings
            </v-btn>
        </v-app-bar>

        <v-main>
            <!-- The current page component will be rendered here -->
            <router-view />
        </v-main>
    </v-app>
</template>

<script setup lang="ts">
// This component is now just for layout, so the script is minimal.
</script>

<style>
/* Basic styling for full height and consistent padding */
html,
body,
#app {
    height: 100%;
    margin: 0;
    overflow: hidden;
    /* Prevent scrolling on main body */
}

.v-application {
    background-color: var(--v-theme-surface);
    /* Use Vuetify theme surface color */
}

.fill-height {
    height: 100%;
}

.h-100 {
    height: 100%;
}

.flex-grow-1 {
    flex-grow: 1;
}

.overflow-auto {
    overflow: auto;
}

#app-container {
    display: flex;
    flex-direction: column;
    height: 100vh;
}

header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
}

.settings-btn {
    background: none;
    border: 1px solid #555;
    color: #f0f0f0;
    padding: 0.5rem 1rem;
    border-radius: 5px;
    cursor: pointer;
}

.settings-btn:hover {
    background-color: #444;
}
</style>
