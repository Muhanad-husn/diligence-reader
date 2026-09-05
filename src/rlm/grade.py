"""Grades a written report against a sample's answer key.

The grade has two halves. Planted-fact recall is code: a fact counts when its normalised
value appears in the normalised report and the report cites one of the fact's documents.
The rubric score is one call to a Claude subagent through the claude command line, on the
subscription. Nothing here reads OPENROUTER_API_KEY, opens a socket or writes LEDGER.md.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from rlm.key import Fact, Key, load_key

# The two sides of a comparison fact are joined by this literal string and by nothing else.
COMPARISON_JOIN = " against "

_CURRENCY = re.compile(r"\bus\$|\busd\b|[$£€]")
_THOUSANDS = re.compile(r"(?<=\d),(?=\d{3}(?!\d))")
_MILLIONS = re.compile(r"(?<=\d)\s*(?:millions?|m)\b")
_WHITESPACE = re.compile(r"\s+")


def normalise(text: str) -> str:
    """Folds a piece of text to the form recall compares on.

    Case is folded, currency marks and codes are dropped, thousands separators are dropped,
    a number followed by million or by m becomes the number followed by m, and runs of
    whitespace collapse to one space.
    """
    folded = text.casefold()
    folded = _CURRENCY.sub(" ", folded)
    folded = _THOUSANDS.sub("", folded)
    folded = _MILLIONS.sub("m", folded)
    return _WHITESPACE.sub(" ", folded).strip()


def cited_documents(report: str, key: Key) -> set[str]:
    """Returns the ids of the key's documents that the report names anywhere in its text."""
    lowered = report.casefold()
    return {doc_id for doc_id in key.documents if doc_id.casefold() in lowered}


def is_recalled(fact: Fact, report_normalised: str, cited: set[str]) -> bool:
    """Says whether the report carries this fact, by the rule for the fact's kind.

    A document fact needs every one of its documents cited. A comparison fact is split on
    the literal string " against " and needs both sides present and one document cited.
    Every other kind needs its value present and one document cited.
    """
    if fact.kind == "document":
        return all(doc in cited for doc in fact.documents)
    if not any(doc in cited for doc in fact.documents):
        return False
    if fact.kind == "comparison":
        sides = fact.value.split(COMPARISON_JOIN)
        return all(normalise(side) in report_normalised for side in sides)
    return normalise(fact.value) in report_normalised


def measure_recall(key: Key, report: str) -> tuple[float, list[str], list[str]]:
    """Returns the recall percentage over all of the key's facts, and the ids either way."""
    report_normalised = normalise(report)
    cited = cited_documents(report, key)
    recalled = []
    missed = []
    for fact in key.facts:
        if is_recalled(fact, report_normalised, cited):
            recalled.append(fact.id)
        else:
            missed.append(fact.id)
    percentage = 100.0 * len(recalled) / len(key.facts) if key.facts else 0.0
    return round(percentage, 2), recalled, missed


def build_prompt(key: Key, report: str) -> str:
    """Writes the grading prompt: the rubric rows, the answer key material and the report."""
    rows = "\n".join(
        f"{row.id}. {row.criterion} (max {row.points} points). Earns the points: {row.earns}"
        for row in key.rubric
    )
    facts = "\n".join(f"- {fact.id} ({fact.kind}): {fact.value} [{', '.join(fact.documents)}]" for fact in key.facts)
    decoys = "\n".join(f"- {decoy.document}: {decoy.why}" for decoy in key.decoys)
    answer = (
        f"{key.answer.action}, {key.answer.number} {key.answer.unit} "
        f"(range {key.answer.low} to {key.answer.high})"
    )
    return f"""You are grading a diligence report against an answer key. Award points row by row.

Award a row its full points when every element named in "Earns the points" is present in the
report. When you withhold points, name the missing element in the reason.

RUBRIC
{rows}

THE EXPECTED ANSWER
{answer}

THE DOCUMENTS THE REPORT MUST CITE
{", ".join(key.required_documents)}

THE DECOYS, WHICH THE REPORT MUST TREAT AS SMALLER
{decoys}

THE PLANTED FACTS
{facts}

THE REPORT
{report}

Reply with JSON only and nothing else: a list of objects, one per rubric row, in row order,
each {{"id": <row id as an integer>, "points": <integer from 0 to that row's maximum>,
"reason": "<one line>"}}. No prose before or after the list.
"""


def parse_rubric(reply: str, key: Key) -> list[dict]:
    """Reads the model's reply into one row per rubric row, with points inside the band."""
    text = reply.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n", "", text)
        text = re.sub(r"\n```\s*$", "", text)
    start = text.find("[")
    end = text.rfind("]")
    if start < 0 or end < start:
        raise ValueError(f"no JSON list in the grader reply: {reply[:200]!r}")
    scored = {int(row["id"]): row for row in json.loads(text[start : end + 1])}
    rows = []
    for row in key.rubric:
        got = scored.get(row.id, {})
        points = int(got.get("points", 0))
        rows.append(
            {
                "id": row.id,
                "points": max(0, min(points, row.points)),
                "reason": str(got.get("reason") or "no reason given"),
            }
        )
    return rows


def run_grader(prompt: str) -> tuple[str, str]:
    """Runs one claude -p call on the prompt and returns its reply and the model id.

    The prompt goes in on stdin because it is far longer than a Windows command line allows.
    The working directory is a temporary one outside the repository so that no CLAUDE.md of
    this project reaches the grader, and CLAUDECODE is dropped so the child starts clean.
    """
    executable = shutil.which("claude")
    if executable is None:
        raise RuntimeError("the claude command line is not on PATH")
    env = {name: value for name, value in os.environ.items() if name != "CLAUDECODE"}
    # The claude process can still hold the working directory open when it exits, so a failed
    # cleanup is ignored rather than raised.
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as workdir:
        finished = subprocess.run(
            [executable, "-p", "--output-format", "json", "--max-turns", "1"],
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=workdir,
            env=env,
            shell=False,
            timeout=600,
        )
    if finished.returncode != 0:
        raise RuntimeError(f"claude -p failed with {finished.returncode}: {finished.stderr[:500]}")
    payload = json.loads(finished.stdout)
    usage = payload.get("modelUsage") or {}
    model = next(iter(usage), payload.get("model", "unknown"))
    return payload.get("result", ""), model


def grade(sample_dir: Path, report_path: Path, run_dir: Path, name: str) -> dict:
    """Grades one report against one sample's key and writes runs/<sample>/grade-<name>.json.

    Recall is measured in code over every fact in the key. The rubric is scored by one model
    call where the key has a rubric. The score is the rubric total where there is a rubric,
    and the recall percentage where there is none.
    """
    started = time.monotonic()
    key = load_key(sample_dir)
    report = report_path.read_text(encoding="utf-8")

    recall, recalled, missed = measure_recall(key, report)

    rubric: list[dict] = []
    model = "none"
    if key.rubric:
        reply, model = run_grader(build_prompt(key, report))
        rubric = parse_rubric(reply, key)
        score = float(sum(row["points"] for row in rubric))
    else:
        score = recall

    result = {
        "sample": key.sample,
        "report": report_path.name,
        "recall": recall,
        "recalled": recalled,
        "missed": missed,
        "rubric": rubric,
        "score": score,
        "model": model,
        "seconds": round(time.monotonic() - started, 2),
    }
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / f"grade-{name}.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    return result


def main(argv: list[str]) -> int:
    """Grades one report from the command line and prints recall, score and the model."""
    if len(argv) != 4:
        print("usage: python -m rlm.grade <sample_dir> <report> <run_dir> <name>")
        return 2
    sample_dir, report, run_dir, name = argv
    result = grade(Path(sample_dir), Path(report), Path(run_dir), name)
    print(f"recall {result['recall']}%  score {result['score']}  model {result['model']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
