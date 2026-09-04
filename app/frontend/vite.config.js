import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Development keeps the browser on one origin. Requests to /api are
// forwarded by Vite to the local FastAPI process running on Brownie.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
