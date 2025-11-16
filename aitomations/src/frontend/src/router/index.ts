import { createMemoryHistory, createRouter } from 'vue-router';
import Dashboard from '@/views/Dashboard.vue';
import ConfigurationView from '@/views/ConfigurationView.vue';

const router = createRouter({
    history: createMemoryHistory(),
    routes: [
        {
            path: '/',
            name: 'Dashboard',
            component: Dashboard,
        },
        {
            path: '/config',
            name: 'Configuration',
            component: ConfigurationView,
        },
        // Catch-all redirect to dashboard for any unknown routes
        {
            path: '/:pathMatch(.*)*',
            redirect: '/',
        },
    ],
});

export default router;
