<script setup>
// Graphique simple d'evolution du score dans le temps (Chart.js). Reste
// volontairement minimal en V1 - un graphique de prix/volume complet est un
// enrichissement V2 une fois le module market_data expose cote frontend.
import { Line } from "vue-chartjs";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
} from "chart.js";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend);

const props = defineProps({
  history: { type: Array, required: true }, // [{computed_at, technical_score, news_score, confidence_score}]
});

function toChartData(history) {
  const labels = history.map((h) => new Date(h.computed_at).toLocaleDateString("fr-BE"));
  return {
    labels,
    datasets: [
      {
        label: "Score technique",
        data: history.map((h) => h.technical_score),
        borderColor: "#3fa66a",
        tension: 0.2,
      },
      {
        label: "Score news",
        data: history.map((h) => h.news_score),
        borderColor: "#f5a623",
        tension: 0.2,
      },
      {
        label: "Confiance",
        data: history.map((h) => h.confidence_score),
        borderColor: "#9aa0a6",
        borderDash: [4, 4],
        tension: 0.2,
      },
    ],
  };
}

const chartOptions = { responsive: true, scales: { y: { min: 0, max: 100 } } };
</script>

<template>
  <Line v-if="history.length" :data="toChartData(history)" :options="chartOptions" />
  <p v-else class="text-sm text-gray-500">Pas encore d'historique de signaux pour cet actif.</p>
</template>
