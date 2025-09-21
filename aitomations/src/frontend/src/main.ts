import { createApp } from 'vue'
import App from './App.vue'
import router from '@/router' // Import the router

// Vuetify
import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import '@mdi/font/css/materialdesignicons.css'

const vuetify = createVuetify({
  components,
  directives,
  icons: {
    defaultSet: 'mdi',
  },
})

createApp(App)
  .use(router) // Tell the app to use Vue Router
  .use(vuetify)
  .mount('#app')
