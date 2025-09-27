import { createApp } from 'vue'
import App from './App.vue'
import router from '@/router'

// Vuetify
import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import '@mdi/font/css/materialdesignicons.css'

// Import global HA theme styles
import '@/styles/ha-theme.css'

// Import highlight.js CSS theme
import 'highlight.js/styles/github-dark.css' // Dark theme
// Or use: import 'highlight.js/styles/github.css' // Light theme

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
    },
  },
})

createApp(App)
  .use(router)
  .use(vuetify)
  .mount('#app')