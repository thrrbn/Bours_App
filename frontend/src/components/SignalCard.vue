<script setup>
// Affiche un signal complet : scores, signal final, explications, confiance,
// disclaimer. Ne fait AUCUNE mise en forme qui suggererait un ordre a
// executer (vocabulaire neutre impose par le backend, voir docs/11 et 17).
import { SIGNAL_LABELS, SIGNAL_COLORS, ML_STATUS_STYLES, ML_STATUS_LABELS } from "../utils/signalStyles";

const props = defineProps({
  signal: { type: Object, required: true },
});
</script>

<template>
  <div class="border rounded-lg p-4 bg-white shadow-sm">
    <div class="flex items-center justify-between mb-3">
      <span
        class="px-3 py-1 rounded-full text-sm font-medium border"
        :class="SIGNAL_COLORS[signal.final_signal] || 'bg-gray-100'"
      >
        {{ SIGNAL_LABELS[signal.final_signal] || signal.final_signal }}
      </span>
      <span class="text-xs text-gray-500">Confiance : {{ signal.scores.confidence.toFixed(0) }}/100</span>
    </div>

    <div class="grid grid-cols-3 gap-3 mb-4 text-center text-sm">
      <div>
        <div class="text-gray-500 text-xs">Technique</div>
        <div class="font-semibold">{{ signal.scores.technical.toFixed(0) }}</div>
      </div>
      <div>
        <div class="text-gray-500 text-xs">News</div>
        <div class="font-semibold">{{ signal.scores.news.toFixed(0) }}</div>
      </div>
      <div>
        <div class="text-gray-500 text-xs">Risque</div>
        <div class="font-semibold">{{ signal.scores.risk.toFixed(0) }}</div>
      </div>
    </div>

    <div class="space-y-2 mb-4">
      <div
        v-for="exp in signal.explanations"
        :key="exp.component"
        class="text-sm text-gray-700 border-l-2 border-gray-200 pl-3"
      >
        <span class="text-xs uppercase text-gray-400 mr-1">{{ exp.component }} ({{ exp.contribution_pct }}%)</span>
        <p>{{ exp.text }}</p>
      </div>
    </div>

    <!-- Apercu du modele statistique V2 : toujours secondaire, jamais le signal officiel -->
    <div v-if="signal.ml_preview" class="border rounded-md p-3 mb-4" :class="ML_STATUS_STYLES[signal.ml_preview.model_status]">
      <div class="flex items-center justify-between mb-1">
        <span class="text-xs font-semibold uppercase">Modele statistique (apercu)</span>
        <span class="text-xs font-medium px-2 py-0.5 rounded-full border" :class="ML_STATUS_STYLES[signal.ml_preview.model_status]">
          {{ ML_STATUS_LABELS[signal.ml_preview.model_status] }}
          ({{ signal.ml_preview.sample_count }}/{{ signal.ml_preview.min_required_samples }})
        </span>
      </div>
      <p class="text-sm">{{ signal.ml_preview.explanation }}</p>
    </div>

    <p class="text-xs text-gray-400 italic">{{ signal.disclaimer }}</p>
  </div>
</template>
