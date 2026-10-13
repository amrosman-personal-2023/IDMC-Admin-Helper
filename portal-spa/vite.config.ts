import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/__tests__/setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov'],
    },
  },
  server: {
    proxy: {
      '/auth':       'http://localhost:8001',
      '/enroll':     'http://localhost:8001',
      '/admin/auth': 'http://localhost:8001',
      '/admin/vendors':          'http://localhost:8001',
      '/admin/devices':          'http://localhost:8001',
      '/admin/enrollment-links': 'http://localhost:8001',
      '/admin/sessions':         'http://localhost:8001',
      '/admin/audit':            'http://localhost:8001',
      '/admin/dashboard':        'http://localhost:8001',
      '/portal/config':    'http://localhost:8002',
      '/admin/extensions':    'http://localhost:8002',
      '/admin/logs':          'http://localhost:8002',
      '/admin/llm':           'http://localhost:8002',
      '/upload':           'http://localhost:8002',
      '/operations':       'http://localhost:8002',
    },
  },
})
