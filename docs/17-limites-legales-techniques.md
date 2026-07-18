# 17. Limites légales et techniques

> Note importante : je ne suis pas juriste et ceci n'est pas un avis juridique. Les points ci-dessous sont des repères de conception à faire valider par un avocat spécialisé en droit financier/FSMA avant tout lancement public, surtout si l'application dépasse un usage strictement personnel.

## Limites réglementaires (Belgique / UE)

- **Conseil en investissement vs information générale** : en droit belge et européen (MiFID II transposée), fournir un "conseil en investissement" personnalisé est une activité réglementée (nécessitant un agrément FSMA ou équivalent). Une application qui affiche des scores génériques basés sur des règles/modèles publics, sans tenir compte de la situation financière personnelle de l'utilisateur (patrimoine, objectifs, tolérance au risque), se rapproche davantage d'un outil d'information générale — mais la frontière est sensible et dépend largement de la formulation et du contexte de commercialisation. **Ne jamais** présenter les signaux comme adaptés à la situation personnelle de l'utilisateur, ne jamais collecter de données de profil financier dans l'app si l'intention est de rester hors du champ du conseil réglementé.
- **Vocabulaire** : éviter tout terme qui suggère une recommandation d'action ("achetez", "vendez", "meilleur choix") au profit de formulations statistiques ("signal de surveillance basé sur...", "scénario probable selon..."). C'est pour cela que le vocabulaire des signaux (doc 11) a été choisi volontairement neutre.
- **Disclaimer systématique et visible** : chaque écran affichant un signal doit rappeler qu'il ne s'agit pas d'un conseil en investissement, que les performances passées ne préjugent pas des performances futures, et que l'utilisateur reste seul responsable de ses décisions.
- **Si l'application devient commerciale** (au-delà d'un usage personnel) : il faudra vérifier au cas par cas avec un juriste si un enregistrement ou une exemption FSMA est nécessaire, selon la formulation exacte du produit, la façon dont il est commercialisé, et s'il y a une contrepartie financière.
- **RGPD** : si des comptes utilisateurs et des watchlists personnelles sont stockés (V2), les obligations RGPD s'appliquent (base légale, minimisation des données, droit à l'effacement, hébergement UE de préférence — un hébergeur belge/UE est cohérent avec le marché cible).

## Limites techniques assumées

- **Yahoo Finance non officiel** : l'accès (via `yfinance` ou requêtes directes) repose sur des endpoints non contractuels, susceptibles de changer sans préavis ou d'être limités en débit. Le provider est abstrait (doc 06/08) précisément pour absorber ce risque, mais il faut prévoir une supervision régulière (alerte si le job d'ingestion échoue plusieurs jours de suite).
- **Contenu des news limité** : les flux RSS gratuits ne fournissent souvent que le titre et un court résumé, pas le corps complet de l'article — le scoring de sentiment/mots-clés opère donc sur une information partielle. Ceci est reflété dans le score de confiance (moins de contenu = moins de certitude affichée).
- **Ambiguïté de matching actif/article** : associer un article à un actif par simple présence du nom/ticker dans le titre génère des faux positifs (homonymes, mentions incidentes). Accepté en V1, amélioré en V2 par reconnaissance d'entités nommées.
- **Modèles simples = biais de simplicité** : les règles pondérées (V1) ne capturent pas d'interactions complexes entre facteurs. C'est un choix assumé (interprétabilité prioritaire), pas un oubli — voir doc 10/11 pour la trajectoire d'évolution.
- **Backtesting ≠ garantie de performance future** : un signal qui a bien performé historiquement peut échouer dans un régime de marché différent (changement de contexte macroéconomique, de taux, de régulation). Le module de backtesting doit lui-même porter cette mise en garde dans son affichage.
- **Dépendance à la qualité des données sources** : toute erreur, retard ou lacune dans les données Yahoo Finance/flux RSS se propage directement dans le score. Il n'existe pas de vérification croisée multi-source en V1 (coût prohibitif pour un particulier), ce qui limite la robustesse face à une source défaillante.
- **Pas de haute disponibilité en V1** : une panne du serveur unique interrompt le service. Acceptable pour un outil d'aide à la décision consulté de façon asynchrone (pas un système critique en temps réel), mais à communiquer clairement si l'app est partagée au-delà d'un usage strictement personnel.

## Ce qui doit systématiquement apparaître dans l'interface (rappel transverse)
1. Mention "signal statistique, pas un conseil en investissement" sur chaque vue de signal.
2. Score de confiance toujours visible à côté du signal, jamais masqué ou secondaire.
3. Distinction visuelle claire entre "ce que dit le score" (fait vérifiable, ex. "RSI à 28") et "ce que cela pourrait signifier" (interprétation, formulée au conditionnel).
4. Accès facile à la méthodologie (lien vers une page "comment ce score est calculé", qui peut réutiliser directement les docs 09/10/11).
