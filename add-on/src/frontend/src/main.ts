import { createApp } from 'vue';
import App from './App.vue';
import 'vuetify/styles';
import { createVuetify } from 'vuetify';
import * as components from 'vuetify/components';
import * as directives from 'vuetify/directives';
import '@mdi/font/css/materialdesignicons.css'; // MDI font for Vuetify icons
import 'roboto-fontface/css/roboto/roboto-fontface.css'; // Roboto font

// Vuetify configuration
const vuetify = createVuetify({
    components,
    directives,
    theme: {
        defaultTheme: 'dark', // Or 'light', or define custom themes
    },
    icons: {
        defaultSet: 'mdi',
    },
});

createApp(App).use(vuetify).mount('#app');
