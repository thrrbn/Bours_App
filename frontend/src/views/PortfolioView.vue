<script setup>
// Portefeuille virtuel de simulation (Etape 12) : aucun ordre reel, cash et
// positions purement simules, executes au dernier cours connu. Voir
// backend/app/domains/portfolio/service.py pour la logique de calcul.
import { computed, onMounted, reactive, ref } from "vue";
import { usePortfolioStore } from "../stores/portfolio";
import { useAnalystStore } from "../stores/analyst";
import AssetAutocomplete from "../components/AssetAutocomplete.vue";

const store = usePortfolioStore();
const analystStore = useAnalystStore();

const buyAsset = ref(null);
const buyQuantity = ref(1);
const sellQuantities = reactive({});

onMounted(async () => {
  await store.loadSummary();
  await store.loadTransactions();
  await analystStore.loadPortfolioAlerts();
});

function pnlClass(value) {
  if (value === null || value === undefined) return "text-gray-400";
  return value >= 0 ? "text-emerald-600" : "text-red-600";
}

function fmt(value) {
  return value === null || value === undefined ? "-" : value.toFixed(2);
}

const canBuy = computed(() => buyAsset.value && buyQuantity.value > 0);

function onSelectBuyAsset(asset) {
  buyAsset.value = asset;
}

async function onBuy() {
  if (!canBuy.value) return;
  const ok = await store.buy(buyAsset.value.id, Number(buyQuantity.value));
  if (ok) {
    buyAsset.value = null;
    buyQuantity.value = 1;
  }
}

async function onSell(position) {
  const quantity = Number(sellQuantities[position.asset.id] ?? position.quantity);
  await store.sell(position.asset.id, quantity);
}

async function onReset() {
  if (!window.confirm("Reinitialiser le portefeuille de simulation (cash et positions repartent a zero) ?")) {
    return;
  }
  await store.reset();
}
</script>

<template>
  <div class="max-w-4xl mx-auto">
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-xl font-semibold">Portefeuille virtuel</h2>
      <button class="text-xs text-red-500 hover:underline" @click="onReset">Reinitialiser</button>
    </div>

    <div v-if="analystStore.portfolioAlerts.length" class="border border-amber-300 bg-amber-50 rounded-lg p-3 mb-6">
      <p class="text-xs font-semibold uppercase text-amber-700 mb-2">
        Avis externes penchant vers la vente (avis d'analystes, pas un ordre)
      </p>
      <ul class="space-y-1">
        <li v-for="alert in analystStore.portfolioAlerts" :key="alert.asset.id" class="text-sm text-amber-900">
          {{ alert.asset.ticker }} - {{ alert.quantity_held }} en portefeuille, consensus {{ alert.consensus_label }}
          ({{ alert.consensus_score.toFixed(2) }})
        </li>
      </ul>
    </div>

    <p v-if="store.error" class="text-sm text-red-600 mb-4">{{ store.error }}</p>
    <p v-if="store.isLoading" class="text-sm text-gray-500">Chargement...</p>

    <div v-if="store.summary" class="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-6">
      <div class="border rounded-lg p-3 bg-white">
        <div class="text-xs text-gray-500">Cash disponible</div>
        <div class="font-semibold">{{ fmt(store.summary.cash_balance) }} EUR</div>
      </div>
      <div class="border rounded-lg p-3 bg-white">
        <div class="text-xs text-gray-500">Valeur totale</div>
        <div class="font-semibold">{{ fmt(store.summary.total_value) }} EUR</div>
      </div>
      <div class="border rounded-lg p-3 bg-white">
        <div class="text-xs text-gray-500">Gain/perte</div>
        <div class="font-semibold" :class="pnlClass(store.summary.total_pnl)">
          {{ store.summary.total_pnl >= 0 ? "+" : "" }}{{ fmt(store.summary.total_pnl) }} EUR
        </div>
      </div>
      <div class="border rounded-lg p-3 bg-white">
        <div class="text-xs text-gray-500">Performance</div>
        <div class="font-semibold" :class="pnlClass(store.summary.total_pnl_pct)">
          {{ store.summary.total_pnl_pct >= 0 ? "+" : "" }}{{ fmt(store.summary.total_pnl_pct) }} %
        </div>
      </div>
      <div class="border rounded-lg p-3 bg-white">
        <div class="text-xs text-gray-500">Frais payes (cumules)</div>
        <div class="font-semibold text-gray-700">{{ fmt(store.summary.total_fees_paid) }} EUR</div>
      </div>
    </div>

    <div class="border rounded-lg p-4 bg-white mb-6">
      <h3 class="text-sm font-semibold mb-3">Acheter (simulation)</h3>
      <div class="flex flex-col sm:flex-row gap-2">
        <div class="flex-1">
          <AssetAutocomplete @select="onSelectBuyAsset" />
          <p v-if="buyAsset" class="text-xs text-gray-500 mt-1">
            Selectionne : {{ buyAsset.ticker }} - {{ buyAsset.name }}
          </p>
        </div>
        <input
          v-model="buyQuantity"
          type="number"
          min="0.000001"
          step="any"
          class="border rounded px-3 py-2 text-sm w-full sm:w-32"
          placeholder="Quantite"
        />
        <button
          class="px-4 py-2 bg-gray-900 text-white rounded text-sm disabled:opacity-40"
          :disabled="!canBuy"
          @click="onBuy"
        >
          Acheter
        </button>
      </div>
      <p v-if="store.actionError" class="text-sm text-red-600 mt-2">{{ store.actionError }}</p>
    </div>

    <h3 class="text-sm font-semibold mb-2">Positions</h3>
    <p v-if="store.summary && !store.summary.positions.length" class="text-sm text-gray-400 mb-6">
      Aucune position - achete un actif ci-dessus pour commencer la simulation.
    </p>
    <table v-else-if="store.summary" class="w-full text-sm border rounded bg-white mb-6 overflow-hidden">
      <thead class="bg-gray-50 text-xs text-gray-500 uppercase">
        <tr>
          <th class="text-left px-3 py-2">Actif</th>
          <th class="text-right px-3 py-2">Quantite</th>
          <th class="text-right px-3 py-2">Prix moyen</th>
          <th class="text-right px-3 py-2">Cours actuel</th>
          <th class="text-right px-3 py-2">Valeur</th>
          <th class="text-right px-3 py-2">Gain/perte</th>
          <th class="text-right px-3 py-2">Vendre</th>
        </tr>
      </thead>
      <tbody class="divide-y">
        <tr v-for="position in store.summary.positions" :key="position.asset.id">
          <td class="px-3 py-2">
            <span class="font-medium">{{ position.asset.ticker }}</span>
            <span class="text-gray-500 text-xs block">{{ position.asset.name }}</span>
          </td>
          <td class="px-3 py-2 text-right">{{ position.quantity }}</td>
          <td class="px-3 py-2 text-right">{{ fmt(position.avg_cost) }}</td>
          <td class="px-3 py-2 text-right">{{ fmt(position.current_price) }}</td>
          <td class="px-3 py-2 text-right">{{ fmt(position.market_value) }}</td>
          <td class="px-3 py-2 text-right" :class="pnlClass(position.unrealized_pnl)">
            {{ position.unrealized_pnl >= 0 ? "+" : "" }}{{ fmt(position.unrealized_pnl) }}
            <span class="text-xs block">
              ({{ position.unrealized_pnl_pct >= 0 ? "+" : "" }}{{ fmt(position.unrealized_pnl_pct) }}%)
            </span>
          </td>
          <td class="px-3 py-2 text-right">
            <div class="flex gap-1 justify-end">
              <input
                v-model="sellQuantities[position.asset.id]"
                type="number"
                min="0.000001"
                :max="position.quantity"
                step="any"
                class="border rounded px-2 py-1 text-xs w-20"
                :placeholder="String(position.quantity)"
              />
              <button class="text-xs text-red-500 hover:underline" @click="onSell(position)">Vendre</button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>

    <h3 class="text-sm font-semibold mb-2">Transactions recentes</h3>
    <ul class="divide-y border rounded bg-white text-sm">
      <li v-for="tx in store.transactions" :key="tx.id" class="px-3 py-2">
        <div class="flex justify-between">
          <span>
            <span class="font-medium">{{ tx.side === "buy" ? "Achat" : "Vente" }}</span>
            {{ tx.quantity }} x {{ tx.asset.ticker }} @ {{ fmt(tx.price) }}
          </span>
          <span class="text-gray-400 text-xs">{{ new Date(tx.executed_at).toLocaleString() }}</span>
        </div>
        <div v-if="tx.quoted_price !== null && tx.quoted_price !== undefined" class="text-xs text-gray-400 mt-0.5">
          Cours cote {{ fmt(tx.quoted_price) }} - slippage {{ fmt(tx.slippage_amount) }} EUR - commission
          {{ fmt(tx.commission) }} EUR
        </div>
      </li>
    </ul>

    <p class="text-xs text-gray-400 italic mt-4">{{ store.summary?.disclaimer }}</p>
  </div>
</template>
