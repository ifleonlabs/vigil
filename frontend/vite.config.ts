import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In dev, proxy the API to the FastAPI backend so the browser talks to one
// origin (no CORS). In prod, `npm run build` emits dist/ and FastAPI serves it.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
  build: { outDir: 'dist' },
})
