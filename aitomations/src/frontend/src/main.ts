import { createApp } from 'vue'
import App from './App.vue'
import router from '@/router' // Import the router

// Vuetify
import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import '@mdi/font/css/materialdesignicons.css'
import '@/styles/ha-theme.css'

// In main.ts
const vuetify = createVuetify({
  components,
  directives,
  icons: {
    defaultSet: 'mdi',
  },
  theme: {
    defaultTheme: 'light',
    themes: {
      light: {
        colors: {
          background: '#fafafa',
          surface: '#ffffff',
          'on-surface': '#212121',
          primary: '#1976d2',
        }
      }
    }
  },
})

createApp(App)
  .use(router) // Tell the app to use Vue Router
  .use(vuetify)
  .mount('#app')
