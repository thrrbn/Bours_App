# 1. Vision produit

## Nom de travail
**Bourse Assistant** (nom provisoire — à remplacer si besoin d'une identité commerciale).

## En une phrase
Un assistant d'analyse boursière pour investisseurs particuliers en Belgique, qui transforme des données de prix, de volumes et d'actualités financières en **scores explicables et en niveaux de confiance**, jamais en promesses de gain ni en conseils financiers personnalisés.

## Le problème
Un particulier qui investit seul en Belgique doit aujourd'hui croiser manuellement plusieurs sources disparates : cours de bourse, actualités financières en anglais ou en français, rapports d'analystes payants, indicateurs techniques éparpillés dans des outils différents. Le temps d'agrégation et d'interprétation est élevé, et le biais émotionnel (peur, avidité, effet de mode) pèse plus lourd que l'analyse froide des faits.

Les outils existants se répartissent en deux extrêmes peu satisfaisants :
- des terminaux professionnels chers et complexes (Bloomberg, Refinitiv), hors de portée d'un particulier ;
- des applications grand public qui affichent des indicateurs bruts sans explication ni contexte, ou pire, qui suggèrent des signaux d'achat/vente avec une fausse assurance ("l'IA dit d'acheter").

## Ce que l'application fait
1. Elle **ingère** en continu des données de marché (prix, volumes, indicateurs techniques) et des actualités financières pour une liste d'actifs suivis par l'utilisateur.
2. Elle **analyse** ces données selon trois axes indépendants : la dynamique temporelle des prix (tendance, momentum, volatilité, ruptures), le contenu des actualités (sentiment, mots-clés à impact financier), et l'agrégation de ces signaux dans le temps.
3. Elle **synthétise** ces analyses en un score composite par horizon (court, moyen, long terme), accompagné d'un **niveau de confiance** et d'une **explication textuelle lisible** ("pourquoi ce score ?").
4. Elle **historise** chaque signal généré et permet de vérifier a posteriori sa pertinence via un module de backtesting transparent (précision, taux de faux positifs, drawdown).
5. Elle **affiche** tout cela dans un tableau de bord simple : recherche d'un actif, vue par horizon, historique des signaux, filtres par marché/secteur.

## Ce que l'application n'est pas
- Ce n'est **pas un conseiller en investissement** au sens réglementaire (pas de conseil personnalisé au sens de la directive MiFID II / loi belge sur les services d'investissement).
- Ce n'est **pas un système de trading automatique** : aucun ordre n'est jamais passé par l'application.
- Ce n'est **pas un générateur de certitudes** : chaque sortie est un score probabiliste borné par une incertitude affichée, jamais un verdict binaire "achetez" / "vendez" présenté comme une vérité.
- Ce n'est **pas une IA de prédiction magique** : les modèles utilisés sont volontairement simples et interprétables avant d'être sophistiqués (voir doc 10).

## Principe directeur : l'explicabilité avant la performance
Le risque numéro un d'un outil de ce type est de générer de la confiance mal placée. La règle de conception non négociable est donc : **un signal sans explication n'est jamais affiché**. Chaque score technique, score news, score de risque et score de confiance doit pouvoir être décomposé, en langage clair, dans l'interface ("ce signal de surveillance vient à 60% du momentum baissier sur 20 jours, à 30% d'une actualité de guidance négative publiée il y a 2 jours, et à 10% d'une volatilité en hausse").

## Utilisateur cible
Un particulier belge, investisseur autodidacte, qui a déjà un compte-titres (Bolero, Keytrade, DEGIRO...) et qui veut un outil d'aide à la décision structuré, sans payer un abonnement de terminal professionnel, et sans se faire dicter des ordres par une boîte noire.

## Positionnement réglementaire (résumé — détails doc 17)
L'application se positionne comme un **outil d'information et d'aide à la décision**, pas comme un service de conseil en investissement au sens de la loi belge (contrôle FSMA) ni un service de gestion de portefeuille. Toute sortie de l'application doit porter une mention explicite de cette limite. Ce point conditionne des choix produit concrets : pas de bouton "acheter maintenant", pas de garantie de performance affichée, vocabulaire prudent ("signal statistique", "scénario probable"), jamais "recommandation".

## Pourquoi une architecture monolithe modulaire, pour un développeur solo
Ce point revient dans plusieurs documents (03, 06), mais il structure toute la vision produit : la valeur du produit vient de la **qualité et de la cohérence des explications**, pas de la scalabilité horizontale. Un monolithe modulaire bien découpé par domaine (assets, market_data, news, signals, backtests, users, compliance) permet à un développeur seul de raisonner sur tout le système, de déployer une seule application, et de faire évoluer chaque domaine indépendamment sans la complexité opérationnelle de microservices (déploiements multiples, orchestration, latence réseau inter-services, observabilité distribuée) qui ne se justifie à aucun stade de ce projet.
