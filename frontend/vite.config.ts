import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

// Ports/hosts come from the repo-root .env (see .env.example).
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, path.resolve(import.meta.dirname, '..'), '')
  const backend = `http://${env.BACKEND_HOST || '127.0.0.1'}:${env.BACKEND_PORT || '8000'}`
  return {
    plugins: [react(), tailwindcss()],
    resolve: { alias: { '@': path.resolve(import.meta.dirname, 'src') } },
    server: {
      port: Number(env.FRONTEND_PORT || 5173),
      strictPort: true,
      proxy: {
        '/api': { target: backend, changeOrigin: true },
        '/files': { target: backend, changeOrigin: true },
      },
    },
  }
})
