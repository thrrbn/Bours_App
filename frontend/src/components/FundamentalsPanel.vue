<script setup>
// Fiche titre (fondamentaux Yahoo Finance) - onglet de la page actif (voir
// DashboardView.vue). Chaque terme technique (PER, capitalisation, beta...)
// s'explique au survol, meme esprit pedagogique que le Labo d'analyse (voir
// AnalysisLabView.vue / constants/analysisLabGlossary.js).
import { computed, onMounted, watch } from "vue";
import { useAssetsStore } from "../stores/assets";
import {
  FUNDAMENTALS_GLOSSARY,
  fmtMarketCap,
  interpretBeta,
  interpretDebtToEquity,
  interpretDividendYield,
  interpretEvToEbitda,
  interpretMarketCap,
  interpretPE,
  interpretPriceToBook,
  interpretProfitMargin,
  interpretReturnOnEquity,
  toneClasses,
} from "../constants/fundamentalsGlossary";

const props = defineProps({ assetId: { type: String, required: true } });

const store = useAssetsStore();

async function loadAll() {
  await store.loadFundamentals(props.assetId);
  await store.loadSectorComparison(props.assetId);
}

onMounted(loadAll);
watch(() => props.assetId, loadAll);

async function onRefresh() {
  await store.refreshFundamentals(props.assetId);
  await store.loadSectorComparison(props.assetId);
}

function fmtPct(value) {
  return value === null || value === undefined ? "n/d" : value.toFixed(2) + "%";
}

// ROE/marge nette sont stockes en FRACTION cote backend (0.15 = 15%, voir
// fundamentals_provider.py) - a la difference de dividend_yield deja en %.
function fmtFracPct(value) {
  return value === null || value === undefined ? "n/d" : (value * 100).toFixed(2) + "%";
}

function fmtRatio(value) {
  return value === null || value === undefined ? "n/d" : value.toFixed(1);
}

function fmtPrice(value, currency) {
  if (value === null || value === undefined) return "n/d";
  return value.toFixed(2) + (currency ? " " + currency : "");
}

const week52Position = computed(() => {
  const f = store.fundamentals;
  if (!f || f.week52_low === null || f.week52_high === null || f.week52_high === f.week52_low) return null;
  return ((f.week52_low + f.week52_high) / 2 - f.week52_low) / (f.week52_high - f.week52_low);
});
</script>

<template>
  <div>
    <p v-if="store.fundamentalsError" class="text-sm text-red-600 mb-4">{{ store.fundamentalsError }}</p>

    <div class="border rounded-lg p-4 bg-white">
      <div class="flex items-center justify-between mb-3">
        <h3 class="text-sm font-semibold">Fiche titre (fondamentaux)</h3>
        <button
          class="text-xs text-gray-500 hover:underline disabled:opacity-40"
          :disabled="store.isLoadingFundamentals"
          @click="onRefresh"
        >
          {{ store.isLoadingFundamentals ? "Rafraichissement..." : "Rafraichir depuis Yahoo Finance" }}
        </button>
      </div>

      <p v-if="!store.fundamentals && !store.isLoadingFundamentals" class="text-sm text-gray-400">
        Aucune fiche pour ce titre pour l'instant - clique sur "Rafraichir depuis Yahoo Finance" pour la charger.
      </p>

      <template v-if="store.fundamentals">
        <p class="text-xs text-gray-400 mb-1">
          Derniere mise a jour le {{ new Date(store.fundamentals.fetched_at).toLocaleString() }} - source Yahoo
          Finance.
        </p>
        <p class="text-xs text-gray-400 mb-3">
          Les petites etiquettes sous chaque chiffre situent la valeur par rapport a des reperes GENERIQUES tres
          approximatifs (litterature financiere courante) - contrairement au Labo d'analyse, il n'existe pas de
          convention universelle pour "un bon PER" : ca varie enormement par secteur. Jamais un signal d'achat/vente.
        </p>

        <div class="flex flex-wrap gap-2 mb-4">
          <span
            v-if="store.fundamentals.sector"
            class="px-2 py-0.5 rounded-full text-xs font-medium border bg-gray-50 text-gray-600 border-gray-300 underline decoration-dotted decoration-gray-400 cursor-help"
            :title="FUNDAMENTALS_GLOSSARY.sector"
          >
            {{ store.fundamentals.sector }}
          </span>
          <span
            v-if="store.fundamentals.industry"
            class="px-2 py-0.5 rounded-full text-xs font-medium border bg-gray-50 text-gray-500 border-gray-200 underline decoration-dotted decoration-gray-300 cursor-help"
            :title="FUNDAMENTALS_GLOSSARY.industry"
          >
            {{ store.fundamentals.industry }}
          </span>
        </div>

        <div class="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-4 text-sm">
          <div>
            <div class="text-gray-500 text-xs mb-1 underline decoration-dotted decoration-gray-300 cursor-help" :title="FUNDAMENTALS_GLOSSARY.market_cap">
              Capitalisation
            </div>
            <div class="font-semibold">{{ fmtMarketCap(store.fundamentals.market_cap) }}</div>
            <span
              v-if="interpretMarketCap(store.fundamentals.market_cap)"
              class="inline-block mt-1 px-1.5 py-0.5 rounded text-[11px] border cursor-help"
              :class="toneClasses(interpretMarketCap(store.fundamentals.market_cap).tone)"
              :title="interpretMarketCap(store.fundamentals.market_cap).rangeNote"
            >
              {{ interpretMarketCap(store.fundamentals.market_cap).label }}
            </span>
          </div>
          <div>
            <div class="text-gray-500 text-xs mb-1 underline decoration-dotted decoration-gray-300 cursor-help" :title="FUNDAMENTALS_GLOSSARY.trailing_pe">
              PER (12 derniers mois)
            </div>
            <div class="font-semibold">{{ fmtRatio(store.fundamentals.trailing_pe) }}</div>
            <span
              v-if="interpretPE(store.fundamentals.trailing_pe)"
              class="inline-block mt-1 px-1.5 py-0.5 rounded text-[11px] border cursor-help"
              :class="toneClasses(interpretPE(store.fundamentals.trailing_pe).tone)"
              :title="interpretPE(store.fundamentals.trailing_pe).rangeNote"
            >
              {{ interpretPE(store.fundamentals.trailing_pe).label }}
            </span>
          </div>
          <div>
            <div class="text-gray-500 text-xs mb-1 underline decoration-dotted decoration-gray-300 cursor-help" :title="FUNDAMENTALS_GLOSSARY.forward_pe">
              PER previsionnel
            </div>
            <div class="font-semibold">{{ fmtRatio(store.fundamentals.forward_pe) }}</div>
            <span
              v-if="interpretPE(store.fundamentals.forward_pe)"
              class="inline-block mt-1 px-1.5 py-0.5 rounded text-[11px] border cursor-help"
              :class="toneClasses(interpretPE(store.fundamentals.forward_pe).tone)"
              :title="interpretPE(store.fundamentals.forward_pe).rangeNote"
            >
              {{ interpretPE(store.fundamentals.forward_pe).label }}
            </span>
          </div>
          <div>
            <div class="text-gray-500 text-xs mb-1 underline decoration-dotted decoration-gray-300 cursor-help" :title="FUNDAMENTALS_GLOSSARY.dividend_yield">
              Rendement du dividende
            </div>
            <div class="font-semibold">{{ fmtPct(store.fundamentals.dividend_yield) }}</div>
            <span
              v-if="interpretDividendYield(store.fundamentals.dividend_yield)"
              class="inline-block mt-1 px-1.5 py-0.5 rounded text-[11px] border cursor-help"
              :class="toneClasses(interpretDividendYield(store.fundamentals.dividend_yield).tone)"
              :title="interpretDividendYield(store.fundamentals.dividend_yield).rangeNote"
            >
              {{ interpretDividendYield(store.fundamentals.dividend_yield).label }}
            </span>
          </div>
          <div>
            <div class="text-gray-500 text-xs mb-1 underline decoration-dotted decoration-gray-300 cursor-help" :title="FUNDAMENTALS_GLOSSARY.beta">
              Beta
            </div>
            <div class="font-semibold">{{ fmtRatio(store.fundamentals.beta) }}</div>
            <span
              v-if="interpretBeta(store.fundamentals.beta)"
              class="inline-block mt-1 px-1.5 py-0.5 rounded text-[11px] border cursor-help"
              :class="toneClasses(interpretBeta(store.fundamentals.beta).tone)"
              :title="interpretBeta(store.fundamentals.beta).rangeNote"
            >
              {{ interpretBeta(store.fundamentals.beta).label }}
            </span>
          </div>
          <div>
            <div class="text-gray-500 text-xs mb-1 underline decoration-dotted decoration-gray-300 cursor-help" :title="FUNDAMENTALS_GLOSSARY.return_on_equity">
              ROE
            </div>
            <div class="font-semibold">{{ fmtFracPct(store.fundamentals.return_on_equity) }}</div>
            <span
              v-if="interpretReturnOnEquity(store.fundamentals.return_on_equity)"
              class="inline-block mt-1 px-1.5 py-0.5 rounded text-[11px] border cursor-help"
              :class="toneClasses(interpretReturnOnEquity(store.fundamentals.return_on_equity).tone)"
              :title="interpretReturnOnEquity(store.fundamentals.return_on_equity).rangeNote"
            >
              {{ interpretReturnOnEquity(store.fundamentals.return_on_equity).label }}
            </span>
          </div>
          <div>
            <div class="text-gray-500 text-xs mb-1 underline decoration-dotted decoration-gray-300 cursor-help" :title="FUNDAMENTALS_GLOSSARY.debt_to_equity">
              Dette / capitaux propres
            </div>
            <div class="font-semibold">{{ fmtRatio(store.fundamentals.debt_to_equity) }}</div>
            <span
              v-if="interpretDebtToEquity(store.fundamentals.debt_to_equity)"
              class="inline-block mt-1 px-1.5 py-0.5 rounded text-[11px] border cursor-help"
              :class="toneClasses(interpretDebtToEquity(store.fundamentals.debt_to_equity).tone)"
              :title="interpretDebtToEquity(store.fundamentals.debt_to_equity).rangeNote"
            >
              {{ interpretDebtToEquity(store.fundamentals.debt_to_equity).label }}
            </span>
          </div>
          <div>
            <div class="text-gray-500 text-xs mb-1 underline decoration-dotted decoration-gray-300 cursor-help" :title="FUNDAMENTALS_GLOSSARY.profit_margin">
              Marge nette
            </div>
            <div class="font-semibold">{{ fmtFracPct(store.fundamentals.profit_margin) }}</div>
            <span
              v-if="interpretProfitMargin(store.fundamentals.profit_margin)"
              class="inline-block mt-1 px-1.5 py-0.5 rounded text-[11px] border cursor-help"
              :class="toneClasses(interpretProfitMargin(store.fundamentals.profit_margin).tone)"
              :title="interpretProfitMargin(store.fundamentals.profit_margin).rangeNote"
            >
              {{ interpretProfitMargin(store.fundamentals.profit_margin).label }}
            </span>
          </div>
          <div>
            <div class="text-gray-500 text-xs mb-1 underline decoration-dotted decoration-gray-300 cursor-help" :title="FUNDAMENTALS_GLOSSARY.price_to_book">
              P/B
            </div>
            <div class="font-semibold">{{ fmtRatio(store.fundamentals.price_to_book) }}</div>
            <span
              v-if="interpretPriceToBook(store.fundamentals.price_to_book)"
              class="inline-block mt-1 px-1.5 py-0.5 rounded text-[11px] border cursor-help"
              :class="toneClasses(interpretPriceToBook(store.fundamentals.price_to_book).tone)"
              :title="interpretPriceToBook(store.fundamentals.price_to_book).rangeNote"
            >
              {{ interpretPriceToBook(store.fundamentals.price_to_book).label }}
            </span>
          </div>
          <div>
            <div class="text-gray-500 text-xs mb-1 underline decoration-dotted decoration-gray-300 cursor-help" :title="FUNDAMENTALS_GLOSSARY.ev_to_ebitda">
              VE/EBITDA
            </div>
            <div class="font-semibold">{{ fmtRatio(store.fundamentals.ev_to_ebitda) }}</div>
            <span
              v-if="interpretEvToEbitda(store.fundamentals.ev_to_ebitda)"
              class="inline-block mt-1 px-1.5 py-0.5 rounded text-[11px] border cursor-help"
              :class="toneClasses(interpretEvToEbitda(store.fundamentals.ev_to_ebitda).tone)"
              :title="interpretEvToEbitda(store.fundamentals.ev_to_ebitda).rangeNote"
            >
              {{ interpretEvToEbitda(store.fundamentals.ev_to_ebitda).label }}
            </span>
          </div>
          <div>
            <div class="text-gray-500 text-xs mb-1 underline decoration-dotted decoration-gray-300 cursor-help" :title="FUNDAMENTALS_GLOSSARY.week52_range">
              Fourchette 52 semaines
            </div>
            <div class="font-semibold text-xs">
              {{ fmtRatio(store.fundamentals.week52_low) }} - {{ fmtRatio(store.fundamentals.week52_high) }}
            </div>
            <div v-if="week52Position !== null" class="h-1 bg-gray-100 rounded-full mt-1 relative overflow-hidden">
              <div class="h-1 bg-gray-400 rounded-full" :style="{ width: (week52Position * 100).toFixed(0) + '%' }"></div>
            </div>
          </div>
        </div>

        <div v-if="store.fundamentals.business_summary" class="mb-4">
          <p class="text-xs uppercase text-gray-400 mb-1">Activite de l'entreprise</p>
          <p class="text-sm text-gray-600">{{ store.fundamentals.business_summary }}</p>
        </div>

        <p class="text-xs text-gray-400 italic">{{ store.fundamentals.disclaimer }}</p>
      </template>
    </div>

    <div v-if="store.sectorComparison" class="border rounded-lg p-4 bg-white mt-4">
      <h3
        class="text-sm font-semibold mb-2 underline decoration-dotted decoration-gray-400 cursor-help"
        :title="FUNDAMENTALS_GLOSSARY.sector_comparison"
      >
        Comparatif secteur
      </h3>

      <div v-if="store.sectorComparison.peers" class="grid grid-cols-2 sm:grid-cols-3 gap-2 text-center text-sm mb-2">
        <div>
          <div class="text-gray-500 text-xs mb-1">PER</div>
          <div class="font-semibold">{{ fmtRatio(store.sectorComparison.this_trailing_pe) }}</div>
          <div class="text-xs text-gray-400">secteur : {{ fmtRatio(store.sectorComparison.peers.avg_trailing_pe) }}</div>
        </div>
        <div>
          <div class="text-gray-500 text-xs mb-1">Rendement dividende</div>
          <div class="font-semibold">{{ fmtPct(store.sectorComparison.this_dividend_yield) }}</div>
          <div class="text-xs text-gray-400">secteur : {{ fmtPct(store.sectorComparison.peers.avg_dividend_yield) }}</div>
        </div>
        <div>
          <div class="text-gray-500 text-xs mb-1">Capitalisation</div>
          <div class="font-semibold">{{ fmtMarketCap(store.sectorComparison.this_market_cap) }}</div>
          <div class="text-xs text-gray-400">secteur : {{ fmtMarketCap(store.sectorComparison.peers.avg_market_cap) }}</div>
        </div>
        <div>
          <div class="text-gray-500 text-xs mb-1">ROE</div>
          <div class="font-semibold">{{ fmtFracPct(store.fundamentals?.return_on_equity) }}</div>
          <div class="text-xs text-gray-400">secteur : {{ fmtFracPct(store.sectorComparison.peers.avg_return_on_equity) }}</div>
        </div>
        <div>
          <div class="text-gray-500 text-xs mb-1">Dette/capitaux propres</div>
          <div class="font-semibold">{{ fmtRatio(store.fundamentals?.debt_to_equity) }}</div>
          <div class="text-xs text-gray-400">secteur : {{ fmtRatio(store.sectorComparison.peers.avg_debt_to_equity) }}</div>
        </div>
        <div>
          <div class="text-gray-500 text-xs mb-1">Marge nette</div>
          <div class="font-semibold">{{ fmtFracPct(store.fundamentals?.profit_margin) }}</div>
          <div class="text-xs text-gray-400">secteur : {{ fmtFracPct(store.sectorComparison.peers.avg_profit_margin) }}</div>
        </div>
        <div>
          <div class="text-gray-500 text-xs mb-1">P/B</div>
          <div class="font-semibold">{{ fmtRatio(store.fundamentals?.price_to_book) }}</div>
          <div class="text-xs text-gray-400">secteur : {{ fmtRatio(store.sectorComparison.peers.avg_price_to_book) }}</div>
        </div>
        <div>
          <div class="text-gray-500 text-xs mb-1">VE/EBITDA</div>
          <div class="font-semibold">{{ fmtRatio(store.fundamentals?.ev_to_ebitda) }}</div>
          <div class="text-xs text-gray-400">secteur : {{ fmtRatio(store.sectorComparison.peers.avg_ev_to_ebitda) }}</div>
        </div>
      </div>

      <div v-if="store.sectorComparison.peer_list && store.sectorComparison.peer_list.length" class="mt-3">
        <p class="text-xs uppercase text-gray-400 mb-2">
          Pairs utilises pour la moyenne ({{ store.sectorComparison.peer_list.length }})
        </p>
        <div class="overflow-x-auto">
          <table class="w-full text-xs text-left border-collapse">
            <thead>
              <tr class="text-gray-400 border-b">
                <th class="py-1 pr-2 font-medium">Titre</th>
                <th class="py-1 px-2 font-medium text-right">PER</th>
                <th class="py-1 px-2 font-medium text-right">Rdt div.</th>
                <th class="py-1 px-2 font-medium text-right">Capi.</th>
                <th class="py-1 px-2 font-medium text-right">ROE</th>
                <th class="py-1 px-2 font-medium text-right">Dette/CP</th>
                <th class="py-1 px-2 font-medium text-right">Marge</th>
                <th class="py-1 px-2 font-medium text-right">P/B</th>
                <th class="py-1 pl-2 font-medium text-right">VE/EBITDA</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="peer in store.sectorComparison.peer_list" :key="peer.asset_id" class="border-b last:border-0">
                <td class="py-1 pr-2 whitespace-nowrap">{{ peer.ticker }} <span class="text-gray-400">- {{ peer.name }}</span></td>
                <td class="py-1 px-2 text-right">{{ fmtRatio(peer.trailing_pe) }}</td>
                <td class="py-1 px-2 text-right">{{ fmtPct(peer.dividend_yield) }}</td>
                <td class="py-1 px-2 text-right">{{ fmtMarketCap(peer.market_cap) }}</td>
                <td class="py-1 px-2 text-right">{{ fmtFracPct(peer.return_on_equity) }}</td>
                <td class="py-1 px-2 text-right">{{ fmtRatio(peer.debt_to_equity) }}</td>
                <td class="py-1 px-2 text-right">{{ fmtFracPct(peer.profit_margin) }}</td>
                <td class="py-1 px-2 text-right">{{ fmtRatio(peer.price_to_book) }}</td>
                <td class="py-1 pl-2 text-right">{{ fmtRatio(peer.ev_to_ebitda) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <p class="text-xs text-gray-400 italic mt-2">{{ store.sectorComparison.note }}</p>
    </div>
  </div>
</template>
