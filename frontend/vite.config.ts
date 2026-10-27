import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  base: '/jointcheck-solder-inspection/',
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    allowedHosts: ['.e2b.app'],
    proxy: {
      '/health': 'http://127.0.0.1:8000',
      '/v1': 'http://127.0.0.1:8000',
    },
  },
});
