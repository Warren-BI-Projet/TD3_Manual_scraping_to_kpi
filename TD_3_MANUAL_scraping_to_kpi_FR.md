# TD3 — Web scraping et conversion d'un texte non structuré en KPI mesurable


**Comment utiliser ce document :** chaque question de réflexion ci-dessous est
marquée
**Réfléchir :**. Répondez à chacune — 2 à 4 phrases honnêtes, basées sur quelque
chose que vous venez d'exécuter ou de lire, pas sur une définition — dans un
fichier nommé `REFLECTIONS.md` que vous allez commit sur votre propre dépôt. Une
liste consolidée de chaque question se trouve à la fin de ce document afin que
vous puissiez vérifier que vous avez bien répondu à toutes.

## La question centrale

Vous avez une pile de texte brut extrait. Comment la transformer en un nombre que
vous pouvez réellement défendre dans un rapport ? C'est toute la séance — un vrai
petit pipeline, de bout en bout : acquérir le texte → le structurer → vérifier sa
qualité → définir un KPI à partir de lui → décider ce qui est sûr à publier → le
visualiser pour une décision. Chaque étape correspond à quelque chose des cours
CM ; chaque section ci-dessous dit lequel.

## Ce que vous construisez

```
td-scraping-to-kpi/
  data/
    jobs_sample.csv          # fourni/recupéré soi-même comme donnée initiale -- LOCAL ONLY, gitignored
    extracted.json            # généré par extract_skills.py -- LOCAL ONLY, gitignored
  scripts/
    scrape_demo.py             # démo optionnelle de 10 minutes de l'enseignant -- robots.txt + une vraie extraction
    extract_skills.py          # local: Ollama structure le texte libre de chaque offre
    compute_kpi.py             # local: agrège en un KPI défendable
  docs/                       # source GitHub Pages
    index.html
    data/
      kpi.json                 # généré par compute_kpi.py, commit -- agrégat uniquement, sûr à publier
  .gitignore
  README.md
```

Il n'y a pas de GitHub Action dans ce projet. Contrairement à TD1/TD2/TD4, ce
pipeline n'est jamais planifié pour s'exécuter automatiquement — per CM4, c'est
un vrai choix de conception, pas une omission : un runner GitHub Actions n'a pas
de GPU, donc un appel LLM qui prend 10 à 40 secondes sur votre propre portable
serait bien pire là-bas. Tout ceci s'exécute localement, une seule fois, et vous
pousser ensuite le résultat à la main.

---

## Étape 1 — Acquisition (CM3 : modèles d'acquisition, provenance, règles d'accès)

### Installation

Si vous avez déjà installé Ollama pour TP1, passez directement à la suite — même
installation unique pour tout le cours.

1. Installez Ollama depuis [ollama.com](https://ollama.com) (gratuit).
2. `ollama pull qwen3:8b` (~5 Go de téléchargement ; un modèle plus petit comme
   `llama3.2` convient aussi sur une machine plus lente, au prix d'une qualité
   d'extraction un peu inférieure).
3. Vérifiez qu'il est accessible :
   ```
   curl --noproxy '*' http://127.0.0.1:11434/api/version
   ```
   doit renvoyer une chaîne de version, pas une erreur de connexion ni une page HTML
   de proxy — `--noproxy '*'` n'est pas optionnel sur un réseau avec un proxy
   institutionnel.

**Point de contrôle :** la commande curl renvoie bien une vraie chaîne de version.

Créez un dépôt public (nécessaire pour GitHub Pages plus tard), par exemple
`td-scraping-to-kpi`.

### Le mécanisme réel de scraping que ce cours n'a pas encore couvert

TD1/TD2 sont tous deux des pipelines purement API ; l'étape facultative jobspy de
TP1 utilise une bibliothèque qui fait le scraping pour vous. C'est la première et
seule fois où vous touchez directement du HTML brut et un vrai fichier
`robots.txt`.

`scripts/scrape_demo.py` (optionnel à exécuter vous-même — une bonne démo de
l'enseignant de toute façon) :

```python
import requests
from bs4 import BeautifulSoup

URL = "https://fr.wikipedia.org/wiki/Le_Mans"
USER_AGENT = "ENSIM-BI-course-TD (educational, contact your-email@univ-lemans.fr)"


def robots_allows(url, user_agent="*"):
    # Vérification minimale et réelle -- confirmée à la main contre fr.wikipedia.org/robots.txt
    # avant d'écrire ceci : /wiki/<Article> est autorisé pour User-agent: *, seulement
    # /wiki/Special:... et quelques autres préfixes sont interdits.
    #
    # rp.read() utilise urllib en interne, ce qui respecte HTTP_PROXY/HTTPS_PROXY --
    # sur un réseau avec un proxy institutionnel (celui-ci inclus), il intercepte
    # silencieusement la requête et robotparser finit par défaut par "interdire tout"
    # sans erreur visible. Test réel confirmé : rp.read() a renvoyé False pour une URL
    # vérifiée manuellement comme autorisée. Récupérer le texte avec requests (déjà exempt
    # de proxy partout ailleurs dans ce cours) puis le passer à rp.parse() évite le même
    # piège silencieux.
    import urllib.robotparser
    resp = requests.get("https://fr.wikipedia.org/robots.txt",
                         proxies={"http": None, "https": None},
                         headers={"User-Agent": USER_AGENT}, timeout=15)
    resp.raise_for_status()
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(resp.text.splitlines())
    return rp.can_fetch(user_agent, url)


def main():
    allowed = robots_allows(URL)
    print(f"robots.txt allows fetching {URL}: {allowed}")
    if not allowed:
        raise SystemExit("robots.txt disallows this -- stopping, not scraping anyway.")

    resp = requests.get(URL, proxies={"http": None, "https": None},
                         headers={"User-Agent": USER_AGENT}, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    title = soup.find("h1").get_text(strip=True)

    first_para = None
    for p in soup.find_all("p"):
        # Une première version naïve de cette boucle (simplement "length > 40") a
        # capturé une notice de désambiguïsation ("Pour les articles homonymes...")
        # au lieu d'un vrai paragraphe d'article -- confirmé sur un vrai fetch.
        # Wikipedia marque ces notices avec une classe "hatnote" sur un ancêtre,
        # une convention réelle bien connue ; ignorer tout <p> imbriqué dans une
        # telle balise est le vrai correctif, pas un seuil de longueur plus élevé
        # (une vraie phrase courte existe aussi, et un hatnote très long peut aussi exister).
        if p.find_parent(class_="hatnote"):
            continue
        text = p.get_text(strip=True)
        if len(text) > 40:
            first_para = text
            break

    print(f"\nPage title: {title}")
    print(f"First real paragraph ({len(first_para)} chars): {first_para[:200]}...")

    # Une variable mesurable extraite depuis un HTML non structuré : la population
    # depuis l'infobox, trouvée par le texte du libellé plutôt qu'une position CSS
    # fragile et fixe.
    population = None
    for row in soup.select("table.infobox_v2 tr, table.infobox tr"):
        header = row.find("th")
        if header and "population" in header.get_text(strip=True).lower():
            cell = row.find("td")
            if cell:
                population = cell.get_text(" ", strip=True)
                break
    print(f"Extracted population field (unstructured -> one variable): {population!r}")


if __name__ == "__main__":
    main()
```

Installez d'abord `beautifulsoup4` : `pip install beautifulsoup4`. Exécutez-le, et
vous devriez voir : `robots.txt allows fetching .../wiki/Le_Mans: True`, le vrai
titre de la page, un vrai premier paragraphe et une vraie population extraite de
l'infobox — une page HTML en entrée, une variable mesurable en sortie, avec une
vérification `robots.txt` qui fonctionne réellement.

**Réfléchir :** `rp.read()` (la version "évidente" en une ligne de cette vérification)
renvoie silencieusement "interdire tout" sur un réseau avec un proxy devant lui —
sans erreur, sans avertissement, sans rien qui ressemble à un problème. `rp.parse()`
(utilisé ci-dessus) n'a pas ce problème. Avec vos propres mots : pourquoi une étape
de pipeline qui échoue de manière *silencieuse* est-elle pire qu'une étape qui
crashe bruyamment, pour quelque chose dont le travail consiste à « respecter les
règles avant d'agir » ? Reliez votre réponse à l'argument de provenance de CM3.

### Pourquoi les vraies données initiales ne sont pas dans ce document

Ce TD a besoin de vrais messages d'offres à scraper pour pratiquer. Ce document ne
contient délibérément aucune vraie description d'offre brute. En effet, les CGU de
LinkedIn et d'Indeed interdisent la redistribution de ce qui est extrait depuis ces
sites — la même raison pour laquelle `TP_1_DELIVERY_MANUAL_smart_internship_match.md`
traite le contenu issu de jobspy comme jamais publiable. Votre enseignant vous
fournira un petit CSV (`title`, `company`, `description` columns, 12-15 offres)
directement — LMS, disque partagé, clé USB, **pas** un dépôt Git public — ou vous
exécuterez vous-même le `fetch_offers_jobspy.py` de TP1 pour obtenir votre propre
échantillon. Dans les deux cas, enregistrez-le sous `data/jobs_sample.csv`.

**Réfléchir :** l'API France Travail (utilisée dans le pipeline principal de TP1) est
des données ouvertes officielles du gouvernement, explicitement licenciées pour
réutilisation. L'échantillon issu de jobspy ne l'est pas. En vos propres mots,
quelle est la différence réelle de risque entre les deux ? Votre réponse changerait-
elle si ce dépôt était privé au lieu d'être public — et si oui, pourquoi le fait
que le dépôt soit public ou privé importe-t-il ici ?

### Décidez ce qui est publiable avant de générer quoi que ce soit

Ajoutez maintenant un `.gitignore`, avant que l'Étape 2 ne crée des fichiers —
choisir ce qu'il est sûr de garder local se fait *avant* de générer des données,
pas comme nettoyage après coup :

```
data/jobs_sample.csv
data/extracted.json
```

Les deux sont locales uniquement. Vous verrez exactement ce qui est sûr à publier
une fois que vous atteindrez l'Étape 4.

---

## Étape 2 — Structuration (CM5 : l'IA agentique a sa place, ou pas)

`scripts/extract_skills.py` appelle un LLM local (Ollama) pour transformer le texte
libre de chaque offre en une liste de compétences concrètes — la seule étape dans
ce pipeline où un LLM est réellement le bon outil.

**Réfléchir, avant de lancer quoi que ce soit :** CM5 affirme que l'IA agentique
appartient à des étapes spécifiques du pipeline, pas partout. Ce TD extrait des
compétences avec un LLM, mais rien dans ce cours n'utilise jamais un LLM pour
décider, par exemple, quelle candidature vous avez réellement envoyée ou quelle est
votre vraie compétence. En utilisant la distinction de CM5 (et pas seulement
« parce que c'est pratique »), expliquez en vos propres mots *pourquoi* le passage
du texte libre à une liste structurée est un bon cas d'usage pour un LLM et un
simple historique de vos propres actions ne l'est pas.

```python
import csv, json, sys, time
import requests

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL = "qwen3:8b"
N_POSTINGS = int(sys.argv[1]) if len(sys.argv) > 1 else 15
MAX_CHARS = 1500  # garde chaque appel rapide assez pour une séance live -- voir ci-dessous

PROMPT_TEMPLATE = """Extract ONLY the concrete named tools/technologies/hard skills mentioned
in this job posting text (it may be in French or English). Do not include generic soft
skills, the job title, or company name.
Return ONLY valid JSON with one key:
- required_skills: array of strings (e.g. ["Python", "Docker", "AWS"]) -- empty array if none found.

TEXT:
{text}
"""


def call_ollama(prompt, retries=3, backoff=5):
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.post(
                OLLAMA_URL,
                proxies={"http": None, "https": None},
                # think: False est le flag important ici -- confirmé par des tests réels
                # que qwen3 exécute par défaut un passage interne de "thinking" avant
                # de répondre, ce qui transforme seul un appel d'environ 2 s en 16 s,
                # et sur un vrai prompt d'extraction plus long, a provoqué des délais
                # de 120 s à plusieurs reprises (échec réel observé lors de la création
                # de ce script, pas une hypothèse).
                json={"model": MODEL, "prompt": prompt, "format": "json", "stream": False, "think": False},
                timeout=(10, 120),
            )
            resp.raise_for_status()
            return json.loads(resp.json()["response"])
        except Exception as e:
            last_error = e
            print(f"    Ollama call attempt {attempt}/{retries} failed: {e}")
            if attempt < retries:
                time.sleep(backoff)
    raise RuntimeError(f"Ollama unreachable after {retries} attempts") from last_error


def main():
    with open("data/jobs_sample.csv", newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r.get("description", "").strip()]
    rows = rows[:N_POSTINGS]
    print(f"Extracting skills from {len(rows)} postings (this takes real time -- "
          f"expect roughly 10-40 seconds per posting on a CPU-only laptop)...")

    postings = []
    start = time.time()
    for i, row in enumerate(rows, 1):
        text = row["description"][:MAX_CHARS]
        t0 = time.time()
        extracted = call_ollama(PROMPT_TEMPLATE.format(text=text))
        elapsed = time.time() - t0
        skills = extracted.get("required_skills", [])
        print(f"  [{i}/{len(rows)}] {row['title'][:50]!r} ({elapsed:.1f}s): {skills}")
        postings.append({
            "title": row["title"], "company": row.get("company"),
            "required_skills": skills,
        })

    with open("data/extracted.json", "w") as f:
        json.dump({
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "postings": postings,
        }, f, indent=2, ensure_ascii=False)
    total = time.time() - start
    print(f"\nWrote data/extracted.json ({len(postings)} postings, {total:.0f}s total, "
          f"{total/len(postings):.1f}s/posting average)")


if __name__ == "__main__":
    main()
```

**Pourquoi `"think": false` est là :** par défaut, ce modèle exécute un passage
interne de « pensée » avant de répondre à chaque appel. Sur ce prompt précis, cela
a transformé un appel d'environ 2 secondes en 16 secondes — et sur un vrai prompt
d'extraction plus long, cela a provoqué des délais de timeout complets. Sans ce
flag, toute cette séance serait beaucoup plus lente, voire impossible à terminer.
C'est une petite ligne avec un effet réel et mesuré sur la praticité d'un pipeline
local basé sur un LLM.

Exécutez-le :

```
python scripts/extract_skills.py 12
```

Vous devriez voir une ligne imprimée par offre — une vraie liste d'outils et
de technologies spécifiques, prenant environ 10 à 40 secondes chacun. (Par
exemple, une offre pour un poste d'ingénierie bench/tools peut extraire quelque
chose comme `['HIL', 'Python', 'MATLAB', 'CAPL', 'CAN', 'CI/CD']` — une liste
réelle et spécifique, pas un buzzword générique. Les offres de votre propre
échantillon seront différentes ; ceci est illustratif, pas un objectif à atteindre.)

**Point de contrôle :** `data/extracted.json` existe avec une entrée par offre, chaque
entrée ayant un tableau `required_skills` non trivial.

*Si un appel timeoute à plusieurs reprises :* vérifiez que `"think": false` est bien
présent dans votre fichier — un copier-coller depuis un script plus ancien, ou depuis
`extract_offers.py` de TP1, ne l'aura pas.

---

## Étape 3 — Qualité des données (vérifier ce que le modèle a réellement produit)

**Réfléchir, avant de lire la suite :** vous venez d'exécuter exactement le même
prompt, avec exactement le même modèle, sur plusieurs offres différentes. Même quand
le modèle identifie correctement les bonnes compétences, quelle inconsistance
spécifique de *formatage* vous attendriez-il entre appels indépendants — la même
compétence écrite de deux manières différentes ? Écrivez votre prédiction d'abord.

Maintenant, ouvrez votre propre `data/extracted.json` et regardez. L'extraction LLM a
un vrai mode de défaillance courant ici : la même compétence peut revenir
capitalisée différemment entre deux appels séparés (`"Computer vision"` dans une
offre, `"computer vision"` dans une autre) — ce qui, sans correction, divise
silencieusement une vraie compétence en deux entrées distinctes dès que vous
commencez à compter. Recherchez au moins une instance de cela, ou confirmez qu'il
n'y en a pas.

**Réfléchir :** avez-vous trouvé une instance ? Si oui, donnez les deux variantes.
Si non, cela signifie-t-il que votre extraction est plus fiable, ou simplement que
vous n'aviez pas deux offres demandant la même compétence ? Soyez honnête sur ce
point.

### La passe de critique — une seconde vérification humaine

Échangez votre `data/extracted.json` (pas `kpi.json` — il faut le détail par offre)
avec un camarade. Vérifiez leurs compétences extraites par rapport aux offres
originales et signalez au moins une vraie erreur — une compétence manquante, une
hallucination, ou exactement le type de doublon de casse décrit ci-dessus.

**Réfléchir :** CM5 appelle ce schéma « human-in-the-loop ». En une ou deux
phrases, expliquez pourquoi cette vérification particulière — une seconde personne
qui relit la sortie brute du modèle par rapport au texte source — compte comme
ça, et pourquoi elle doit se faire sur `extracted.json` plutôt que sur le
`kpi.json` final.

---

## Étape 4 — Définition du KPI (CM2 : un KPI est une construction, pas un fait neutre)

`scripts/compute_kpi.py` transforme vos compétences extraites en un seul nombre.

**Réfléchir, avant de lire le code ci-dessous :** le script va définir
`TARGET_SKILL = "python"` — un choix qu'une personne (ce manuel) a déjà fait à
votre place. Si vous construisiez ce tableau de bord pour le comité pédagogique de
l'ENSIM, quelle compétence unique choisiriez-vous de suivre en premier, et pourquoi ?
Écrivez votre réponse maintenant, avant de voir quel nombre donne le choix par
defaut.

```python
import json, time
from collections import Counter

# Un KPI délibérément simple, délibérément modifiable -- changez
# TARGET_SKILL, ou écrivez une autre fonction KPI entièrement. Selon le
# principe de ce cours : un KPI est un construit que vous choisissez, pas un fait neutre.
TARGET_SKILL = "python"


def load_extracted(path="data/extracted.json"):
    with open(path) as f:
        return json.load(f)["postings"]


def compute_kpi(postings, target_skill=TARGET_SKILL):
    n = len(postings)
    matching = [
        p for p in postings
        if any(target_skill.lower() in s.lower() for s in p.get("required_skills", []))
    ]
    all_skills = Counter()
    for p in postings:
        for s in p.get("required_skills", []):
            all_skills[s] += 1

    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "kpi_label": f"% of postings mentioning '{target_skill}'",
        "kpi_value": round(len(matching) / n, 3) if n else 0.0,
        "n_postings_analyzed": n,
        "n_matching": len(matching),
        "top_skills": [{"skill": s, "count": c} for s, c in all_skills.most_common(10)],
        "avg_skills_per_posting": round(sum(len(p.get("required_skills", [])) for p in postings) / n, 2) if n else 0.0,
    }


def main():
    postings = load_extracted()
    kpi = compute_kpi(postings)
    print(json.dumps(kpi, indent=2))
    with open("docs/data/kpi.json", "w") as f:
        json.dump(kpi, f, indent=2)
    print("\nWrote docs/data/kpi.json")


if __name__ == "__main__":
    main()
```

Exécutez-le :

```
python scripts/compute_kpi.py
```

Vous obtiendrez un vrai `kpi_value` entre 0 et 1, une vraie liste `top_skills`
classée selon la fréquence de répétition de chaque compétence, et un
`avg_skills_per_posting`.

**Point de contrôle :** `docs/data/kpi.json` existe, et `n_postings_analyzed` est
cohérent avec le nombre de l'Étape 2.

**Réfléchir :** changez maintenant `TARGET_SKILL` pour la compétence que vous avez
nommée ci-dessus et relancez. Comparez les deux valeurs `kpi_value`. Quelle version
vous ferait réellement confiance pour dire à un comité pédagogique « les étudiants
devraient apprendre X ensuite » — celle par défaut, la vôtre, ou aucune des deux ?
Expliquerez pourquoi en deux ou trois phrases.

---

## Étape 5 — Stockage et ce qui est réellement sûr à publier (CM3 + CM6)

Revenez au `.gitignore` que vous avez ajouté à l'Étape 1 : `data/jobs_sample.csv` et
`data/extracted.json` ne quittent jamais votre machine. `docs/data/kpi.json` — un
pourcentage, quelques comptes, une liste de noms de compétences et leur fréquence —
est le seul fichier qui est jamais commit.

**Réfléchir :** si un camarade ne regardait que votre `kpi.json` publié (sans accès
à vos fichiers locaux), pourrait-il reconstituer quelles offres spécifiques vous avez
scrapées, ou quelle société chacune venait ? S'il ne le pouvait réellement pas —
qu'est-ce qu'il a exactement fallu laisser de côté dans les champs du KPI pour
garantir cela, et était-ce un choix de conception délibéré dans `compute_kpi()` ou
simplement de la chance ?

---

## Étape 6 — Visualisation pour l'aide à la décision (CM1)

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Scraping to KPI lab</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
  body { font-family: system-ui, sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; }
  #kpi-card { padding: 1rem; border: 2px solid #0d7c9e; border-radius: 8px; }
  #kpi-card .value { font-size: 2rem; font-weight: bold; color: #0d7c9e; }
  #kpi-card .label { font-size: 0.9rem; color: #666; }
  canvas { margin-top: 1.5rem; }
  #updated { color: #666; font-size: 0.85rem; }
</style>
</head>
<body>
  <h1>Scraping to KPI lab</h1>
  <p>One real KPI, computed from LLM-extracted skills across real scraped postings — see <code>data/extracted.json</code> and <code>compute_kpi.py</code>.</p>
  <div id="kpi-card">Loading...</div>
  <canvas id="skillsChart" height="320"></canvas>
  <p id="updated"></p>

<script>
fetch('data/kpi.json')
  .then(r => r.json())
  .then(data => {
    if (!data.n_postings_analyzed) {
      document.getElementById('kpi-card').innerHTML = '<p>No KPI computed yet -- run extract_skills.py then compute_kpi.py.</p>';
      return;
    }

    document.getElementById('kpi-card').innerHTML = `
      <div class="value">${(data.kpi_value * 100).toFixed(0)}%</div>
      <div class="label">${data.kpi_label} (${data.n_matching} of ${data.n_postings_analyzed} postings)</div>
      <div class="label">Average ${data.avg_skills_per_posting} distinct skills extracted per posting</div>
    `;

    const top = data.top_skills || [];
    new Chart(document.getElementById('skillsChart'), {
      type: 'bar',
      data: {
        labels: top.map(s => s.skill),
        datasets: [{ label: 'Postings mentioning this skill', data: top.map(s => s.count), backgroundColor: '#0d7c9e' }],
      },
      options: {
        indexAxis: 'y',
        plugins: {
          legend: { display: false },
          title: { display: true, text: 'Most-mentioned skills across analyzed postings' },
        },
      },
    });

    document.getElementById('updated').textContent = `Data last computed ${data.generated_at || '(see script output)'}`;
  })
  .catch(err => {
    document.getElementById('kpi-card').innerHTML = '<p>Could not load KPI (' + err + ').</p>';
  });
</script>
</body>
</html>
```

Commit et poussez :

```
git add docs/index.html docs/data/kpi.json scripts/ .gitignore README.md
git commit -m "Scraping-to-KPI lab"
git push
```

Vérifiez que `git status` ne montre pas `data/jobs_sample.csv` ni `data/extracted.json`
comme modifiables — s'ils y apparaissent, utilisez `git rm --cached`.

**Settings → Pages → Source : « Deploy from a branch » → Branche `main`, dossier `/docs`
→ Save.** Visitez votre URL Pages — vous devriez voir votre carte KPI et votre
graphique des compétences.

**Réfléchir :** qui est le vrai public de ce tableau de bord tel qu'il est
maintenant — vous personnellement, en train de vérifier votre propre travail, ou
quelqu'un d'autre complètement (par exemple, un comité pédagogique, comme le
suggère le cadrage de l'Étape 4) ? Le titre actuel de la page et sa description en
une ligne correspondent-ils à ce public ? Sinon, quelle phrase changeriez-vous ?

---

## À faire vous-même : un deuxième KPI, argumenté

Écrivez une fonction KPI complètement différente — pas seulement une autre
`TARGET_SKILL`, mais une définition réellement différente (par exemple, la moyenne
des compétences par offre pour un mot-clé de titre spécifique, ou la fraction
d'offres mentionnant au moins un fournisseur cloud). Exécutez-la.

**Réfléchir :** écrivez deux phrases comparant vos deux KPI — celui de l'Étape 4 et
celui-ci. Lequel vous ferait réellement confiance pour prendre une vraie décision,
et pourquoi ?

---

## Liste de vérification des réflexions — ce que votre `REFLECTIONS.md` doit contenir

1. Pourquoi un échec silencieux de `robots.txt` est pire qu'un échec bruyant (CM3).
2. Données France Travail vs. cet échantillon issu de jobspy — quelle est la vraie
différence de risque, et le statut public/privé du dépôt change-t-il votre réponse ?
3. Pourquoi le passage du texte libre aux compétences est un bon cas d'usage LLM et
   le suivi des candidatures ne l'est pas (CM5).
4. Votre incohérence prédite de formatage du LLM, et si vous avez trouvé une vraie
   occurrence dans votre propre `extracted.json`.
5. Pourquoi la passe de critique compte comme human-in-the-loop, et pourquoi elle
   se fait sur `extracted.json` et non sur `kpi.json` (CM5).
6. Votre propre `TARGET_SKILL` choisi, argumenté avant d'avoir vu son nombre, et
   laquelle des deux valeurs KPI (par défaut vs. la vôtre) vous ferait réellement
   confiance pour une vraie décision (CM2).
7. Ce qu'un observateur pourrait et ne pourrait pas reconstruire à partir de
   `kpi.json` seul, et ce qui a précisément empêché cela (CM3/CM6).
8. À qui ce tableau de bord s'adresse vraiment, et si son cadrage actuel correspond
   à ce public (CM1).
9. Votre deuxième KPI conçu vous-même et lequel des deux vous ferait plus confiance.

## Liste de vérification finale

- [ ] Dépôt public, `.gitignore` en place avant que `data/jobs_sample.csv` ou
      `data/extracted.json` n'existe.
- [ ] `data/extracted.json` contient de vraies compétences extraites pour chaque
      offre de votre échantillon.
- [ ] Passe de critique effectuée avec un camarade, une vraie erreur documentée.
- [ ] `docs/data/kpi.json` ne contient que des champs agrégés — vérifiez-le vous-même
      en l'ouvrant.
- [ ] Tableau de bord visible sur GitHub Pages, avec votre vrai KPI et graphique de
      compétences.
- [ ] `REFLECTIONS.md` commit, couvrant les 9 points ci-dessus.

À remettre : l'URL du dépôt, l'URL live de Pages, et `REFLECTIONS.md`.
