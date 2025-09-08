import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { resolve } from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],

  build: {
    // This tells Vite to build the final production files
    // into the 'static' folder that your Python server uses.
    outDir: resolve(__dirname, '../backend/static'),
    emptyOutDir: true,
    manifest: true,
  },

  server: {
    // This is the crucial part for development.
    // It tells Vite's dev server to listen on all network interfaces,
    // which is necessary for the container's port forwarding to work.
    host: '0.0.0.0', 
    port: 5173,

    proxy: {
      // This forwards any request from your Vue app starting with '/api'
      // to your Python backend running on port 8099.
      '/api': {
        target: 'http://localhost:8099',
        changeOrigin: true,
        secure: false,
      },
    },
  },
});
