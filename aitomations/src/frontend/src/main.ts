import { createApp } from 'vue'
import App from './App.vue'

// Vuetify
import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import '@mdi/font/css/materialdesignicons.css'

// Import highlight.js CSS theme
import 'highlight.js/styles/github-dark.css' // Dark theme
// Or use: import 'highlight.js/styles/github.css' // Light theme

const vuetify = createVuetify({
  components,
  directives,
  icons: {
    defaultSet: 'mdi',
  },
})

createApp(App)
  .use(vuetify)
  .mount('#app')