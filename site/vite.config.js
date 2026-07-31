import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";

const entry = (path) => fileURLToPath(new URL(path, import.meta.url));

export default defineConfig({
  build: {
    target: "es2020",
    sourcemap: false,
    rollupOptions: {
      // MPA: o painel e' uma pasta (`admin/index.html`) de proposito. Vite nao
      // faz fallback de SPA, entao `/admin` sem extensao so' resolve se existir
      // um `index.html` la' dentro — vale pro dev e pro estatico do Vercel.
      input: {
        main: entry("./index.html"),
        admin: entry("./admin/index.html"),
      },
    },
  },
  server: {
    host: "127.0.0.1",
    port: 5173,
  },
});
