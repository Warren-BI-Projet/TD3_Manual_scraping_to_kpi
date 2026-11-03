import requests
from bs4 import BeautifulSoup

URL = "https://fr.wikipedia.org/wiki/Le_Mans"
USER_AGENT = "ENSIM-BI-course-TD (educational, contact your-email@univ-lemans.fr)"


def robots_allows(url, user_agent="*"):
    # Vérification minimale et réelle -- confirmée à la main contre fr.wikipedia.org/robots.txt
    # avant d'écrire ceci : /wiki/<Article> est autorisé pour User-agent: *, seulement
    # /wiki/Special:... et quelques autres préfixes sont interdits.
    #
    # requests utilise la configuration proxy du réseau si elle existe. On récupère
    # le texte ici puis on le passe à rp.parse() pour éviter les erreurs silencieuses
    # de rp.read() avec certains proxies institutionnels.
    import urllib.robotparser
    resp = requests.get("https://fr.wikipedia.org/robots.txt",
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

    resp = requests.get(URL, headers={"User-Agent": USER_AGENT}, timeout=15)
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