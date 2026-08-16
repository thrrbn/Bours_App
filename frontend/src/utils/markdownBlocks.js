// Mini-parseur Markdown -> blocs structures (16/08/2026), pour l'analyste IA
// (voir LlmAnalystView.vue). Volontairement PAS un rendu markdown->HTML via
// v-html : le texte contient des affirmations generees par un LLM (voir
// backend/app/domains/llm_analyst/analyst.py) - meme si le risque reste
// theorique sur une instance locale mono-utilisateur, on evite d'injecter
// du HTML brut non fiable dans le DOM. Chaque bloc est rendu par le
// template Vue via interpolation ({{ }}), jamais par innerHTML : impossible
// d'executer quoi que ce soit, quel que soit le texte produit par le modele.
//
// Ne couvre que le sous-ensemble de Markdown genere par
// analyst.py::render_markdown() (titres #/##, citation >, tableaux |a|b|,
// listes a puces -, gras **, italique _..._) - pas un parseur Markdown
// generaliste.

export function parseInline(text) {
  const parts = text.split(/(\*\*[^*]+\*\*|_[^_]+_)/g).filter((p) => p !== "");
  if (!parts.length) return [{ type: "text", text: "" }];
  return parts.map((part) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return { type: "bold", text: part.slice(2, -2) };
    }
    if (part.startsWith("_") && part.endsWith("_")) {
      return { type: "italic", text: part.slice(1, -1) };
    }
    return { type: "text", text: part };
  });
}

function isSeparatorRow(cells) {
  return cells.every((c) => /^:?-+:?$/.test(c.trim()));
}

export function parseMarkdownBlocks(markdown) {
  const lines = (markdown || "").split("\n");
  const blocks = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    if (!line.trim()) {
      i++;
      continue;
    }

    if (line.startsWith("# ")) {
      blocks.push({ type: "h1", text: line.slice(2).trimEnd() });
      i++;
      continue;
    }

    if (line.startsWith("## ")) {
      blocks.push({ type: "h2", text: line.slice(3).trimEnd() });
      i++;
      continue;
    }

    if (line.startsWith("> ")) {
      const quoteLines = [];
      while (i < lines.length && lines[i].startsWith("> ")) {
        quoteLines.push(lines[i].slice(2));
        i++;
      }
      blocks.push({ type: "blockquote", text: quoteLines.join(" ").trimEnd() });
      continue;
    }

    if (line.startsWith("|")) {
      const tableLines = [];
      while (i < lines.length && lines[i].startsWith("|")) {
        tableLines.push(lines[i]);
        i++;
      }
      const rows = tableLines
        .map((l) => l.split("|").slice(1, -1).map((c) => c.trim()))
        .filter((cells) => !isSeparatorRow(cells));
      if (rows.length) {
        blocks.push({ type: "table", header: rows[0], rows: rows.slice(1) });
      }
      continue;
    }

    if (line.startsWith("- ")) {
      const items = [];
      while (i < lines.length && lines[i].startsWith("- ")) {
        items.push(lines[i].slice(2).trimEnd());
        i++;
      }
      blocks.push({ type: "list", items });
      continue;
    }

    blocks.push({ type: "p", text: line.trimEnd() });
    i++;
  }

  return blocks;
}
