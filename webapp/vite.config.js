import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// LAN 公開（iPad から）＋ /solve はバックエンド(FastAPI 8077)へプロキシ
export default defineConfig({
  plugins: [react()],
  define: {
    // Excalidraw が参照する process.env を定義（Vite で未定義クラッシュ防止）
    'process.env.IS_PREACT': JSON.stringify('false'),
  },
  server: {
    host: true,
    proxy: {
      '/solve': 'http://localhost:8077',
      '/recognize': 'http://localhost:8077',
    },
  },
})
