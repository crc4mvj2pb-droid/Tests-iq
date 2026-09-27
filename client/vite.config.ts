import { defineConfig } from 'vite';
import path from 'path';

export default defineConfig({
  base: process.env.VITE_BASE_PATH || '/',
  resolve: {
    alias: {
      '@shared': path.resolve(__dirname, '../shared'),
    },
  },
  server: {
    host: true,
    port: 5173,
  },
  build: {
    target: 'es2020',
  },
});
