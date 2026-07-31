import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";

import i18nPages from "./build/i18n.js";
import { CONFIG } from "./src/config.js";

const entry = (path) => fileURLToPath(new URL(path, import.meta.url));

// A URL absoluta e' obrigatoria pro `hreflang` — link relativo o Google
// ignora. Vem do config da marca, mas o ambiente ganha: na Vercel da' pra
// deixar o SITE_URL vazio e a propria plataforma informa o dominio.
const siteUrl = (
  process.env.SITE_URL ||
  CONFIG.SITE_URL ||
  (process.env.VERCEL_PROJECT_PRODUCTION_URL
    ? `https://${process.env.VERCEL_PROJECT_PRODUCTION_URL}`
    : "")
).replace(/\/$/, "");

export default defineConfig({
  plugins: [i18nPages({ siteUrl })],
  build: {
    target: "es2020",
    sourcemap: false,
    rollupOptions: {
      // MPA: o painel e' uma pasta (`admin/index.html`) de proposito. Vite nao
      // faz fallback de SPA, entao `/admin` sem extensao so' resolve se existir
      // um `index.html` la' dentro — vale pro dev e pro estatico do Vercel.
      // As paginas por idioma (`/en/`, `/es/`, `/it/`) nao entram aqui: sao
      // geradas a partir do `index.html` ja' construido, em `build/i18n.js`.
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
