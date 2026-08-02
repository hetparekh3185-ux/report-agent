import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  base: '/static/react/',
  build: {
    outDir: '../static/react',
    emptyOutDir: true,
  },
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:5000',
      '/generate': 'http://127.0.0.1:5000',
      '/download': 'http://127.0.0.1:5000',
      '/logout': 'http://127.0.0.1:5000',
    }
  }
})
