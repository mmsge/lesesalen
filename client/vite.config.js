import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

// The build must stay compatible with `script-src 'self'; style-src 'self'`:
// no inlined scripts, no inlined styles, no eval. `assetsInlineLimit: 0` keeps
// Vite from inlining small assets as data: URIs inside CSS, and every chunk
// lands in /assets, which the server serves immutable.
export default defineConfig({
  plugins: [svelte()],
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    emptyOutDir: true,
    assetsInlineLimit: 0,
    cssCodeSplit: false,
    sourcemap: false,
    target: 'es2022',
  },
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8080',
      '/omslag': 'http://127.0.0.1:8080',
    },
  },
});
