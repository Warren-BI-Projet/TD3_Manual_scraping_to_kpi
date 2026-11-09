"""Publish only aggregate, normalized skill counts from the local extraction."""

import argparse
import json
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "extracted.json"
OUTPUT = ROOT / "docs" / "data" / "kpi.json"
DEFAULT_TARGET = "python"
CLOUD_SKILLS = {"aws", "azure", "google cloud", "gcp"}
SKILL_ALIASES = {
    "amazon web services": "aws",
    "microsoft azure": "azure",
    "google cloud platform": "google cloud",
    "gcp": "google cloud",
    "python3": "python",
    "python 3": "python",
}


def normalized_skills(posting):
    skills = posting.get("required_skills", [])
    if not isinstance(skills, list) or not all(isinstance(s, str) for s in skills):
        raise ValueError("Each posting must have a list of skill strings")
    normalized = {" ".join(skill.split()).casefold() for skill in skills if skill.strip()}
    return {SKILL_ALIASES.get(skill, skill) for skill in normalized}


def compute_kpi(postings, target_skill=DEFAULT_TARGET):
    if not postings:
        raise ValueError("No postings; refusing to publish a misleading zero KPI")
    per_posting = [normalized_skills(posting) for posting in postings]
    target = target_skill.casefold()
    matching = sum(target in skills for skills in per_posting)
    counts = Counter(skill for skills in per_posting for skill in skills)
    cloud_matching = sum(bool(skills & CLOUD_SKILLS) for skills in per_posting)
    n = len(postings)
    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "kpi_label": f"Part des offres mentionnant {target_skill}",
        "target_skill": target_skill,
        "kpi_value": round(matching / n, 3),
        "n_postings_analyzed": n,
        "n_matching": matching,
        "top_skills": [
            {"skill": skill, "count": count}
            for skill, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:10]
        ],
        "avg_skills_per_posting": round(sum(map(len, per_posting)) / n, 2),
        "second_kpi": {
            "label": "Part des offres mentionnant un fournisseur cloud (AWS, Azure ou GCP)",
            "value": round(cloud_matching / n, 3),
            "n_matching": cloud_matching,
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", default=DEFAULT_TARGET)
    args = parser.parse_args()
    if not args.target.strip():
        parser.error("target cannot be empty")
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    postings = source["postings"]
    if not isinstance(postings, list):
        raise ValueError("postings must be a list")
    result = compute_kpi(postings, args.target.strip())
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
