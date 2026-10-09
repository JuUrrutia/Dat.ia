import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    strictPort: true,
  },
  // Tests: solo logica pura, asi que entorno `node` y sin cobertura. Si alguna
  // vez hay que renderizar un componente, el entorno pasa a ser `jsdom` aqui.
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts'],
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    rollupOptions: {
      output: {
        // ECharts pesa ~1 MB y no cambia entre despliegues: separarlo del
        // codigo de la app lo deja en cache entre versiones en vez de invalidar
        // 1 MB de cache en cada build. El resto de vendors (react, router,
        // lucide) van juntos y tampoco cambian por deploy.
        // ponytail: dos entradas, no una tabla de splitting; abrirla solo si
        // el chunk de echarts aparece en la salida como problema real.
        manualChunks: {
          echarts: ['echarts', 'echarts-for-react'],
          vendor: ['react', 'react-dom', 'react-router-dom'],
        },
      },
    },
  },
});
