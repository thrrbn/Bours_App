<script setup>
// Briefing quotidien (portefeuille virtuel + watchlist) - synthese en
// francais des actus/signaux recents, jamais un conseil (voir
// backend/app/domains/notifications/briefing_service.py). L'apercu est
// consultable meme si l'envoi d'email est desactive (MAIL_ENABLED=false,
// reglage par defaut) - "on prepare mais on n'envoie pas encore".
import { onMounted, reactive, ref } from "vue";
import { useBriefingStore } from "../stores/briefing";

const store = useBriefingStore();
const windowDays = ref(3);
const expandedSummaries = reactive({});

const newKeyword = ref("");
const newWeight = ref(0);
const newHorizon = ref("medium");
const isAddingKeyword = ref(false);

onMounted(() => {
  store.loadPreview(windowDays.value);
  store.loadCustomKeywords();
  store.loadKeywordMatches();
});

async function onRefreshPreview() {
  await store.loadPreview(windowDays.value);
}

async function onSendNow() {
  await store.sendNow();
}

async function onAddKeyword() {
  if (!newKeyword.value.trim()) return;
  isAddingKeyword.value = true;
  try {
    const ok = await store.addCustomKeyword(newKeyword.value.trim(), Number(newWeight.value) || 0, newHorizon.value);
    if (ok) {
      newKeyword.value = "";
      newWeight.value = 0;
      newHorizon.value = "medium";
      await store.loadKeywordMatches();
    }
  } finally {
    isAddingKeyword.value = false;
  }
}

async function onToggleArticleSummary(articleId) {
  expandedSummaries[articleId] = !expandedSummaries[articleId];
  if (expandedSummaries[articleId] && !store.articleSummaries[articleId]) {
    await store.loadArticleSummary(articleId);
  }
}

async function onRescan() {
  const result = await store.rescanKeywords();
  if (result) {
    await store.loadPreview(windowDays.value);
    await store.loadKeywordMatches();
  }
}
</script>

<template>
  <div class="max-w-3xl mx-auto">
    <h2 class="text-xl font-semibold mb-1">Briefing quotidien</h2>
    <p class="text-xs text-gray-400 mb-4">
      Synthese automatique, en francais, des actus/signaux recents sur les titres detenus (portefeuille virtuel) et
      suivis (watchlist). Les titres d'articles restent dans leur langue d'origine (avec lien vers la source) - la
      synthese elle-meme est generee a partir des donnees extraites (sentiment, mots-cles), pas une traduction mot a
      mot. Jamais un conseil en investissement.
    </p>

    <div class="border rounded-lg p-4 bg-white mb-4">
      <div class="flex items-center justify-between flex-wrap gap-2 mb-2">
        <div class="flex items-center gap-2 text-sm">
          <label class="text-gray-500 text-xs">Fenetre :</label>
          <select v-model.number="windowDays" class="border rounded px-2 py-1 text-xs" @change="onRefreshPreview">
            <option :value="1">1 jour</option>
            <option :value="3">3 jours</option>
            <option :value="7">7 jours</option>
          </select>
        </div>
        <div class="flex gap-2">
          <button
            class="text-xs border rounded px-3 py-1.5 text-gray-600 hover:bg-gray-50 disabled:opacity-40"
            :disabled="store.isLoading"
            @click="onRefreshPreview"
          >
            {{ store.isLoading ? "Chargement..." : "Actualiser l'apercu" }}
          </button>
          <button
            class="text-xs bg-gray-900 text-white rounded px-3 py-1.5 disabled:opacity-40"
            :disabled="store.isLoading"
            @click="onSendNow"
            title="Construit et tente d'envoyer le briefing maintenant - n'envoie reellement un email que si MAIL_ENABLED=true est configure dans le .env"
          >
            Envoyer maintenant (test)
          </button>
        </div>
      </div>
      <p class="text-xs text-gray-400">
        "Envoyer maintenant" ne part reellement par email que si l'envoi est active cote serveur (MAIL_ENABLED dans
        le .env) - sinon la synthese est simplement construite, comme pour l'apercu.
      </p>
    </div>

    <p v-if="store.error" class="text-sm text-red-600 mb-4">{{ store.error }}</p>

    <template v-if="store.briefing">
      <p class="text-xs text-gray-400 mb-3">
        Genere le {{ new Date(store.briefing.generated_at).toLocaleString() }} - fenetre de
        {{ store.briefing.window_days }} jour(s)
        <span v-if="store.lastAction === 'send'">- tentative d'envoi effectuee.</span>
      </p>

      <p v-if="!store.briefing.items.length" class="text-sm text-gray-400 mb-4">
        Rien de nouveau a rapporter depuis le dernier briefing sur tes titres detenus/suivis.
      </p>

      <div v-for="item in store.briefing.items" :key="item.asset.id" class="border rounded-lg p-4 bg-white mb-3">
        <div class="flex items-center justify-between mb-2">
          <div>
            <span class="font-medium text-sm">{{ item.asset.name }}</span>
            <span class="text-gray-400 text-xs ml-1">({{ item.asset.ticker }})</span>
          </div>
          <div class="flex gap-1">
            <span v-if="item.held" class="px-2 py-0.5 rounded-full text-xs border bg-gray-50 text-gray-600 border-gray-300">
              detenu{{ item.quantity_held ? ` (${item.quantity_held})` : "" }}
            </span>
            <span v-if="item.watched" class="px-2 py-0.5 rounded-full text-xs border bg-gray-50 text-gray-500 border-gray-200">
              suivi
            </span>
          </div>
        </div>

        <p class="text-sm text-gray-700 mb-2">{{ item.highlight_note }}</p>

        <div class="flex flex-wrap gap-2 mb-2">
          <span
            v-for="s in item.signals"
            :key="s.horizon"
            class="px-2 py-0.5 rounded-full text-xs border"
            :class="s.changed_since_last_briefing ? 'bg-amber-50 text-amber-700 border-amber-300' : 'bg-gray-100 text-gray-500 border-gray-300'"
            :title="s.changed_since_last_briefing ? 'A change depuis le dernier briefing envoye' : 'Inchange depuis le dernier briefing envoye'"
          >
            {{ s.horizon_label }} : {{ s.signal_label }}
          </span>
          <span v-if="item.consensus_label" class="px-2 py-0.5 rounded-full text-xs border bg-gray-50 text-gray-500 border-gray-200">
            Consensus externe : {{ item.consensus_label }}
          </span>
        </div>

        <div v-if="item.keywords.length" class="flex flex-wrap gap-1 mb-2">
          <span
            v-for="kw in item.keywords"
            :key="kw.keyword"
            class="px-1.5 py-0.5 rounded text-[11px] border bg-gray-50 text-gray-500 border-gray-200 cursor-help"
            :title="`Poids ${kw.weight} - horizon ${kw.horizon_impact} - ${kw.occurrences} article(s)`"
          >
            {{ kw.keyword }} ({{ kw.occurrences }})
          </span>
        </div>

        <a
          v-if="item.latest_article"
          :href="item.latest_article.url"
          target="_blank"
          rel="noopener"
          class="text-xs text-blue-600 hover:underline"
        >
          Source : {{ item.latest_article.title }} - {{ item.latest_article.source }}
          ({{ new Date(item.latest_article.published_at).toLocaleDateString() }})
        </a>
      </div>

      <p class="text-xs text-gray-400 italic mt-2">{{ store.briefing.disclaimer }}</p>
    </template>

    <div class="border rounded-lg p-4 bg-white mt-6">
      <h3 class="text-sm font-semibold mb-1">Mots-cles personnalises</h3>
      <p class="text-xs text-gray-400 mb-3">
        Liste globale, en plus du lexique fixe interne - suivis dans l'actu de tous les titres, pris en compte au
        prochain rafraichissement des news et dans ce briefing. Le poids (-1 a 1) est optionnel : laisse a 0 pour
        juste "flaguer" le terme sans influencer le score de ton detecte.
      </p>

      <p v-if="store.keywordsError" class="text-sm text-red-600 mb-2">{{ store.keywordsError }}</p>

      <ul v-if="store.customKeywords.length" class="divide-y border rounded mb-3">
        <li v-for="kw in store.customKeywords" :key="kw.id" class="px-3 py-2 flex items-center justify-between text-sm">
          <span>
            {{ kw.keyword }}
            <span class="text-xs text-gray-400 ml-1">(poids {{ kw.weight }}, horizon {{ kw.horizon_impact }})</span>
          </span>
          <button class="text-xs text-red-500 hover:underline" @click="store.deleteCustomKeyword(kw.id)">
            Retirer
          </button>
        </li>
      </ul>
      <p v-else class="text-xs text-gray-400 mb-3">Aucun mot-cle personnalise pour l'instant.</p>

      <div class="flex flex-wrap gap-2 items-end">
        <div>
          <label class="block text-xs text-gray-500 mb-1">Mot-cle</label>
          <input v-model="newKeyword" type="text" placeholder="ex: rappel produit" class="border rounded px-2 py-1.5 text-sm" @keyup.enter="onAddKeyword" />
        </div>
        <div>
          <label class="block text-xs text-gray-500 mb-1">Poids (-1 a 1)</label>
          <input v-model.number="newWeight" type="number" step="0.1" min="-1" max="1" class="border rounded px-2 py-1.5 text-sm w-24" />
        </div>
        <div>
          <label class="block text-xs text-gray-500 mb-1">Horizon</label>
          <select v-model="newHorizon" class="border rounded px-2 py-1.5 text-sm">
            <option value="short">Court terme</option>
            <option value="medium">Moyen terme</option>
            <option value="long">Long terme</option>
          </select>
        </div>
        <button
          class="px-3 py-1.5 bg-gray-900 text-white rounded text-sm disabled:opacity-40"
          :disabled="isAddingKeyword || !newKeyword.trim()"
          @click="onAddKeyword"
        >
          {{ isAddingKeyword ? "Ajout..." : "Ajouter" }}
        </button>
      </div>

      <div class="border-t mt-4 pt-3">
        <p class="text-xs text-gray-400 mb-2">
          Un mot-cle ajoute ne s'applique qu'aux articles ingeres APRES coup - pour le retrouver dans des articles
          deja connus, il faut repasser l'existant au lexique actuel (aucun nouvel appel Yahoo Finance/Google News,
          juste une relecture de ce qui est deja en base).
        </p>
        <button
          class="text-xs border rounded px-3 py-1.5 text-gray-600 hover:bg-gray-50 disabled:opacity-40"
          :disabled="store.isRescanning"
          @click="onRescan"
        >
          {{ store.isRescanning ? "Rescan en cours..." : "Rescanner les articles existants" }}
        </button>
        <p v-if="store.rescanResult" class="text-xs text-gray-500 mt-2">
          {{ store.rescanResult.articles_rescanned }} article(s) rescanne(s), {{ store.rescanResult.total_keyword_matches }} correspondance(s) de mot-cle au total.
        </p>
      </div>
    </div>

    <div class="border rounded-lg p-4 bg-white mt-4">
      <div class="flex items-center justify-between mb-2 gap-2 flex-wrap">
        <h3 class="text-sm font-semibold">Articles recents correspondant a tes mots-cles</h3>
        <div class="flex gap-2">
          <button
            class="text-xs border rounded px-2 py-1 text-gray-600 hover:bg-gray-50 disabled:opacity-40"
            :disabled="store.isLoadingSummary"
            @click="store.loadKeywordSummary(10)"
          >
            {{ store.isLoadingSummary ? "Resume en cours..." : "Resumer (10 lignes max)" }}
          </button>
          <button
            class="text-xs text-gray-500 hover:underline disabled:opacity-40"
            :disabled="store.isLoadingMatches"
            @click="store.loadKeywordMatches()"
          >
            {{ store.isLoadingMatches ? "Chargement..." : "Actualiser" }}
          </button>
        </div>
      </div>
      <p class="text-xs text-gray-400 mb-3">
        Tous actifs et toutes dates confondus (pas limite a la fenetre du briefing ci-dessus) - les plus recents en
        premier.
      </p>

      <p v-if="store.summaryError" class="text-sm text-red-600 mb-2">{{ store.summaryError }}</p>
      <div v-if="store.keywordSummaryLines.length" class="border rounded bg-gray-50 p-3 mb-4">
        <p class="text-xs uppercase text-gray-400 mb-2">Resume - un mot-cle par ligne, le plus recent en premier</p>
        <ul class="text-sm text-gray-700 space-y-1 list-disc list-inside">
          <li v-for="(line, idx) in store.keywordSummaryLines" :key="idx">{{ line }}</li>
        </ul>
      </div>

      <p v-if="store.matchesError" class="text-sm text-red-600 mb-2">{{ store.matchesError }}</p>
      <p v-else-if="!store.isLoadingMatches && !store.keywordMatches.length" class="text-sm text-gray-400">
        Aucun mot-cle personnalise ne correspond a un article connu pour l'instant - ajoute un mot-cle puis
        "Rescanner les articles existants" ci-dessus, ou attends la prochaine ingestion de news.
      </p>

      <ul v-else class="divide-y">
        <li v-for="(m, idx) in store.keywordMatches" :key="m.article.id + m.keyword + idx" class="py-2">
          <div class="flex items-center gap-2 mb-1 flex-wrap">
            <span class="px-1.5 py-0.5 rounded text-[11px] border bg-gray-50 text-gray-500 border-gray-200">
              {{ m.keyword }}
            </span>
            <span v-if="m.asset_ticker" class="text-xs text-gray-400">{{ m.asset_ticker }}</span>
            <span class="text-xs text-gray-400">{{ new Date(m.article.published_at).toLocaleDateString() }}</span>
          </div>
          <a :href="m.article.url" target="_blank" rel="noopener" class="text-sm text-blue-600 hover:underline">
            {{ m.article.title }}
          </a>
          <span class="text-xs text-gray-400 ml-1">({{ m.article.source }})</span>
          <button
            class="text-xs text-gray-400 hover:text-gray-700 ml-2 disabled:opacity-40"
            :disabled="store.loadingArticleSummaryId === m.article.id"
            @click="onToggleArticleSummary(m.article.id)"
          >
            {{ store.loadingArticleSummaryId === m.article.id ? "Resume..." : expandedSummaries[m.article.id] ? "Masquer le resume" : "Resumer" }}
          </button>

          <div v-if="expandedSummaries[m.article.id] && store.articleSummaries[m.article.id]" class="border rounded bg-gray-50 p-2 mt-2">
            <p class="text-xs text-gray-400 mb-1">
              Resume base sur l'extrait fourni par le flux RSS (pas le texte integral de l'article).
            </p>
            <ul class="text-sm text-gray-700 space-y-0.5 list-disc list-inside">
              <li v-for="(line, i) in store.articleSummaries[m.article.id]" :key="i">{{ line }}</li>
            </ul>
          </div>
        </li>
      </ul>
      <p v-if="store.articleSummaryError" class="text-sm text-red-600 mt-2">{{ store.articleSummaryError }}</p>
    </div>
  </div>
</template>
