# TD3 — Du scraping au KPI

Ce projet transforme un échantillon local d'annonces d'emploi en indicateurs agrégés. Le script de démonstration vérifie d'abord `robots.txt` avant de lire une page Wikipédia. Les annonces du CSV proviennent d'une collecte antérieure : ce TP ne les republie pas et ne scrape pas les sites d'emploi.

## Exécution locale

Prérequis : Python 3.13, `requests`, `beautifulsoup4`, Ollama et un modèle local (`llama3.2` dans les commandes ci-dessous). Depuis la racine du dépôt :

```powershell
python -m pip install requests beautifulsoup4
ollama pull llama3.2
python -X utf8 scripts/scrape_demo.py
python -X utf8 scripts/extract_skills.py 12 --model llama3.2
python -X utf8 scripts/review_extraction.py
python -X utf8 scripts/compute_kpi.py
```

L'extraction analyse les 5 000 premiers caractères de chaque description et réessaie sur la fin du texte lorsqu'elle obtient une liste vide. Le contrôle manuel corrige trois erreurs observées dans les lignes 8, 10 et 11 du CSV local, après vérification littérale dans leurs descriptions ; il est spécifique à cet échantillon. Le calcul compte chaque compétence au plus une fois par annonce et normalise les espaces, la casse et quelques alias. L'indicateur principal est la part des annonces mentionnant explicitement Python. Le second mesure la part mentionnant au moins un fournisseur cloud parmi AWS, Azure et GCP.

## Données et publication

- `data/jobs_sample.csv` : annonces brutes, locales uniquement.
- `data/extracted.json` : résultats par annonce, locaux uniquement.
- `docs/data/kpi.json` : nombres agrégés destinés à la publication.
- `docs/index.html` : tableau de bord statique lisant le JSON agrégé.

Les deux premiers fichiers sont exclus par `.gitignore`. Le JSON public ne contient ni titre, ni entreprise, ni description, ni URL d'annonce. Il décrit cet échantillon et ne permet pas d'estimer à lui seul la demande du marché. Les réponses et limites de méthode figurent dans `REFLECTIONS.md`.

Pour publier via GitHub Pages : choisir la branche `main` et le dossier `/docs` dans **Settings → Pages** après avoir poussé les fichiers publics. Vérifier le graphique et les deux pourcentages à l'URL Pages du dépôt.
