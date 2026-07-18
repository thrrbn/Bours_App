/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{vue,js}"],
  theme: {
    extend: {
      colors: {
        // Palette neutre volontairement sobre : ce produit affiche des scores
        // et des incertitudes, pas des promesses de gain (voir docs/01, docs/17).
        surveillance: "#f5a623",
        neutre: "#9aa0a6",
        prudence: "#e07856",
        achat: "#3fa66a",
        vente: "#d94f4f",
      },
    },
  },
  plugins: [],
};
