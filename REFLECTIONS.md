# Réflexions — TD3

## 1. Contrôle silencieux de `robots.txt` (CM3)

Le 9 novembre 2026, `scrape_demo.py` a affiché `True` pour l'article « Le Mans » avant de lire la page, puis a extrait le titre et la population affichée (`146 249 hab. (2023)`). Si la vérification avait renvoyé `False` à cause d'un proxy sans signaler l'échec du chargement de `robots.txt`, je n'aurais pas su distinguer une vraie interdiction d'un problème réseau. Une erreur explicite préserve la provenance de la décision d'accès et empêche d'attribuer à Wikipédia une règle que le programme n'a pas réellement obtenue.

## 2. France Travail et annonces issues de jobspy (CM3)

L'API France Travail constitue une source officielle avec une licence de réutilisation ; le CSV de ce projet contient des textes d'annonces issus d'une collecte jobspy, dont la redistribution n'est pas accordée ici. Un dépôt privé réduit l'exposition publique, mais ne crée pas une autorisation de republier ou de partager ces textes. Je garde donc le CSV et l'extraction par annonce hors du dépôt et ne publie que des statistiques agrégées.

## 3. Pourquoi employer un LLM ici (CM5)

Les descriptions sont longues et rédigées librement en français ou en anglais : transformer leurs mentions explicites de technologies en listes structurées demande une interprétation du langage. Les actions personnelles, comme une candidature envoyée, sont des événements connus qui doivent être enregistrés directement avec leur date et leur statut. Les inférer par LLM introduirait une incertitude inutile dans un registre qui devrait rester vérifiable.

## 4. Incohérences de format (CM5)

Avant l'extraction, je prévoyais des variantes de casse ou de nom pour une même technologie, par exemple `Azure` et `Microsoft Azure`, qui sépareraient artificiellement les comptes. J'ai trouvé `Deep Learning` et `Deep learning` dans deux sorties, ainsi que `Generative Models` et `Generative models` ; le calcul les regroupe par casse. Le fichier contenait aussi `Microsoft Azure` : une règle d'alias le ramène à `azure` pour le KPI cloud.

## 5. Relecture humaine (CM5)

J'ai comparé les listes aux descriptions locales : l'annonce 8 mentionne explicitement Python sous « TECHNOLOGIES », mais le modèle avait renvoyé `[]`, y compris après un second passage. L'annonce 11 citait TCP/IP, Linux et plusieurs normes sans que le modèle les relève ; la sortie de l'annonce 10 contenait des diplômes à la place des compétences Data Science et Machine Learning. J'ai corrigé ces trois sorties avec `review_extraction.py`, qui vérifie la présence littérale des compétences ajoutées dans le texte source ; le JSON agrégé ne permettrait plus ce contrôle par annonce. L'échange avec un camarade demandé par l'énoncé reste à faire : cette relecture personnelle ne prétend pas le remplacer.

## 6. Choix du KPI (CM2)

Avant de connaître les résultats, j'ai choisi `Azure` comme compétence à suivre pour un comité de programme : elle permet de discuter des enseignements liés aux infrastructures cloud et de confronter ce choix à la fréquence de Python. Après correction des sorties, Python apparaît dans 8 annonces sur 12 (66,7 %) et Azure dans 1 sur 12 (8,3 %). Je ne conseillerais pas un changement de programme sur l'un ou l'autre seul : l'échantillon est petit, non aléatoire, et deux premières lignes décrivent presque la même offre.

## 7. Données publiables (CM3 et CM6)

Le tableau publié ne contient que des effectifs, des proportions, des noms de compétences et une date de calcul. Il ne contient aucun titre, nom d'entreprise, texte, lien ou identifiant d'annonce : on ne peut donc pas retrouver directement les 12 lignes du CSV à partir de ce fichier seul. Cette exclusion est volontaire dans `compute_kpi.py`, même si un petit échantillon et des compétences rares limitent encore la portée statistique de la publication.

## 8. Public du tableau de bord (CM1)

En l'état, la page sert d'abord à vérifier mon propre pipeline sur un échantillon réduit ; elle n'établit pas une recommandation générale pour le comité pédagogique. J'ai remplacé le titre générique de l'exemple par « TD3 — Des annonces aux indicateurs » et précisé dès l'introduction qu'il s'agit d'une vue de contrôle d'un échantillon d'offres.

## 9. Second KPI

Le second indicateur est la part des annonces qui mentionnent au moins un fournisseur cloud parmi AWS, Azure et GCP, comptée une seule fois par annonce même si plusieurs fournisseurs y figurent. Il vaut 2 sur 12 (16,7 %), contre 8 sur 12 (66,7 %) pour Python. Pour une décision sur les enseignements cloud, le second est plus utile que le seul taux Python, car il couvre plusieurs plateformes ; il resterait cependant trop fragile pour une décision réelle sans échantillon plus large et revue systématique des extractions.
