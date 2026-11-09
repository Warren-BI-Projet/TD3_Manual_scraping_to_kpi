"""Apply documented manual corrections to three verified extraction errors.

This review is specific to the first 12 rows of the local seed CSV. It checks that
every added skill is explicitly present in the corresponding private description.
"""

import csv
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "jobs_sample.csv"
OUTPUT = ROOT / "data" / "extracted.json"

# One-based row number -> replacement list after reading the source description.
CORRECTIONS = {
    8: ["Python"],
    10: ["Data Science", "Machine Learning"],
    11: ["TCP/IP", "Linux", "WiFi", "5G", "LTE", "WCDMA", "GSM"],
}


def main():
    with SOURCE.open(newline="", encoding="utf-8-sig") as source:
        rows = [row for row in csv.DictReader(source) if row["description"].strip()]
    extracted = json.loads(OUTPUT.read_text(encoding="utf-8"))
    postings = extracted["postings"]
    if len(postings) != 12:
        raise ValueError("This review only applies to the first 12 postings")

    for number, skills in CORRECTIONS.items():
        row = rows[number - 1]
        posting = postings[number - 1]
        if (posting["title"], posting["company"]) != (row["title"], row["company"]):
            raise ValueError(f"Posting {number} no longer matches the source")
        description = row["description"].casefold()
        missing = [skill for skill in skills if skill.casefold() not in description]
        if missing:
            raise ValueError(f"Posting {number}: skills absent from source: {missing}")
        posting["required_skills"] = skills
        print(f"Reviewed posting {number}: {skills}")

    extracted["reviewed_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    extracted["review_method"] = "Manual source comparison for postings 8, 10, and 11"
    OUTPUT.write_text(json.dumps(extracted, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
