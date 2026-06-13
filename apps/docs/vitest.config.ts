import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'node:path';

export default defineConfig({
  plugins: [
    react(),
    {
      name: 'css-ignore',
      transform(code, id) {
        if (id.endsWith('.css')) return { code: '' };
      },
    },
  ],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/__tests__/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
    onConsoleLog(log) {
      if (log.includes('act(')) return false;
      return true;
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      'collections': path.resolve(__dirname, './.source'),
    },
  },
});
