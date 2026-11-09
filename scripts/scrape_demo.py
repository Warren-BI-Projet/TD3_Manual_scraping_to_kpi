"""Optional demonstration: check robots.txt before extracting one Wikipedia field."""

from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

URL = "https://fr.wikipedia.org/wiki/Le_Mans"
ROBOTS_URL = "https://fr.wikipedia.org/robots.txt"
USER_AGENT = "ENSIM-BI-course-TD (educational; contact: student@univ-lemans.fr)"


def main():
    session = requests.Session()
    session.trust_env = False
    session.headers.update({"User-Agent": USER_AGENT})

    robots_response = session.get(ROBOTS_URL, timeout=15)
    robots_response.raise_for_status()
    parser = RobotFileParser()
    parser.parse(robots_response.text.splitlines())
    allowed = parser.can_fetch(USER_AGENT, URL)
    print(f"robots.txt allows fetching {URL}: {allowed}")
    if not allowed:
        raise SystemExit("robots.txt forbids this URL; stopping.")

    response = session.get(URL, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    heading = soup.find("h1")
    if heading is None:
        raise RuntimeError("Page heading not found; HTML structure may have changed.")
    paragraph = next(
        (
            text
            for p in soup.find_all("p")
            if not p.find_parent(class_="hatnote")
            if len(text := p.get_text(" ", strip=True)) > 40
        ),
        None,
    )
    if paragraph is None:
        raise RuntimeError("Article paragraph not found.")

    population = None
    for row in soup.select("table.infobox_v2 tr, table.infobox tr"):
        header = row.find("th")
        if header and "population" in header.get_text(" ", strip=True).casefold():
            cell = row.find("td")
            if cell:
                population = cell.get_text(" ", strip=True)
                break

    print(f"Page title: {heading.get_text(' ', strip=True)}")
    print(f"First article paragraph: {paragraph[:200]}...")
    print(f"Population field: {population!r}")


if __name__ == "__main__":
    main()
