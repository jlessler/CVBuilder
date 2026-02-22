import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // Cache to Linux tmp to avoid Windows NTFS rename-permission issues in WSL
  cacheDir: '/tmp/vite-cvbuilder-cache',
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
