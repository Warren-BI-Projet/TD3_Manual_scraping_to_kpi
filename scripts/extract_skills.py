"""Extract named technical skills from local job descriptions with Ollama."""

import argparse
import csv
import json
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "jobs_sample.csv"
OUTPUT = ROOT / "data" / "extracted.json"
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MAX_CHARS = 5000  # The first 1500 characters of several ads contain only company copy.
PROMPT = """Extract only concrete named tools, technologies, and hard skills explicitly
mentioned in this job posting. Do not infer skills from the title or employer and do
not include soft skills. The text may be French or English. Return only a JSON object
with a required_skills array of strings. Use [] when none are explicit.

POSTING TEXT:
{text}
"""


def call_ollama(session, model, description, retries=3):
    error = None
    for attempt in range(1, retries + 1):
        try:
            response = session.post(
                OLLAMA_URL,
                json={
                    "model": model,
                    "prompt": PROMPT.format(text=description[:MAX_CHARS]),
                    "format": "json",
                    "stream": False,
                    "think": False,
                },
                timeout=(10, 120),
            )
            response.raise_for_status()
            parsed = json.loads(response.json()["response"])
            skills = parsed.get("required_skills")
            if not isinstance(skills, list) or not all(isinstance(s, str) for s in skills):
                raise ValueError("Ollama returned an invalid required_skills list")
            return list(dict.fromkeys(s.strip() for s in skills if s.strip()))
        except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
            error = exc
            print(f"  Attempt {attempt}/{retries} failed: {exc}")
            if attempt < retries:
                time.sleep(5)
    raise RuntimeError("Could not extract skills from this posting") from error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("count", nargs="?", type=int, default=12)
    parser.add_argument("--model", default="qwen3:8b")
    parser.add_argument("--retry-empty", action="store_true", help="Recheck empty lists using the end of each description")
    args = parser.parse_args()
    if args.count < 1:
        parser.error("count must be positive")

    with SOURCE.open(newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        needed = {"title", "company", "description"}
        if not needed.issubset(reader.fieldnames or []):
            raise ValueError(f"CSV must contain {', '.join(sorted(needed))}")
        rows = [row for row in reader if row["description"].strip()][: args.count]
    if not rows:
        raise ValueError("No descriptions to extract from")

    session = requests.Session()
    session.trust_env = False
    if args.retry_empty:
        previous = json.loads(OUTPUT.read_text(encoding="utf-8"))
        postings = previous["postings"]
        if previous.get("model") != args.model or len(postings) != len(rows) or any(
            posting["title"] != row["title"] or posting["company"] != row["company"]
            for posting, row in zip(postings, rows)
        ):
            raise ValueError("Existing extraction does not match this model and sample")
    else:
        postings = []
    start = time.monotonic()
    print(f"Extracting {len(rows)} postings with {args.model}...")
    for index, row in enumerate(rows, 1):
        if args.retry_empty and postings[index - 1]["required_skills"]:
            print(f"  {index}/{len(rows)}: kept existing skills")
            continue
        begun = time.monotonic()
        description = row["description"]
        skills = call_ollama(session, args.model, description[-2500:] if args.retry_empty else description)
        if not skills and not args.retry_empty and len(description) > 2500:
            skills = call_ollama(session, args.model, description[-2500:])
        posting = {
            "title": row["title"],
            "company": row["company"],
            "required_skills": skills,
        }
        if args.retry_empty:
            postings[index - 1] = posting
        else:
            postings.append(posting)
        print(f"  {index}/{len(rows)} ({time.monotonic() - begun:.1f}s): {skills}")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps({
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "model": args.model,
            "postings": postings,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT} in {time.monotonic() - start:.1f}s")


if __name__ == "__main__":
    main()
