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
    // usePolling : necessaire dans ce conteneur Docker sur Windows - les
    // evenements inotify d'un bind mount (./frontend:/app, voir
    // docker-compose.yml) ne se propagent pas toujours de l'hote vers le
    // conteneur, donc Vite peut ne jamais detecter qu'un fichier a change
    // (symptome observe le 30/07/2026 : un lien ajoute a App.vue
    // n'apparaissait pas tant que le conteneur n'etait pas redemarre a la
    // main). Le polling force Vite a verifier les fichiers a intervalle
    // regulier au lieu d'attendre un evenement qui peut ne jamais arriver.
    watch: {
      usePolling: true,
      interval: 300,
    },
    proxy: {
      "/api": {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
});
