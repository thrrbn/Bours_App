import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

// Cible du proxy API : en local (npm run dev hors Docker) l'API tourne sur
// localhost:8000. Dans le conteneur Docker (docker-compose.yml), le backend
// n'est joignable que via le nom du service "backend" sur le reseau Docker
// interne - d'ou la variable VITE_API_TARGET injectee par docker-compose.yml.
const apiTarget = process.env.VITE_API_TARGET || "http://localhost:8000";

export default defineConfig({
  plugins: [vue()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      "/api": {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
});
