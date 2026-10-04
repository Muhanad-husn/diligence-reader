"""Exports a run's report.md to Word, PDF and a spreadsheet of its evidence.

`python -m rlm.export <run_dir>` reads <run_dir>/report.md and writes report.docx, report.pdf
and evidence.csv beside it. No model is called and nothing outside the run directory is read.
"""

import csv
import re
import sys
from pathlib import Path

import pypandoc
import typst

# The Markdown dialect the report is written in. Dollar signs are money in these reports, never
# TeX math, and angle brackets inside a quotation are text, never HTML.
MARKDOWN = "gfm-tex_math_dollars-raw_html"

# Typst hyphenates a long word at a line end, which splits a quoted word in the PDF's text.
NO_HYPHENS = "#set text(hyphenate: false)\n"

CSV_HEADER = ["document", "date", "quote", "citation"]

# A schedule line of the usual shape: date, quoted words, bracketed citation. The first field
# holds no bar, quote or bracket; the quote and the citation may hold bars.
_STANDARD = re.compile(r'^- ([^|"\[\]]*?) \| "(.*)" \| \[(.*)\]$')


def evidence_section(report: str) -> str:
    """The text under the report's `## Evidence` heading, up to the next second level heading."""
    match = re.search(r"^## Evidence[ \t]*$", report, re.M)
    if not match:
        return ""
    rest = report[match.end():]
    following = re.search(r"^## ", rest, re.M)
    return rest[: following.start()] if following else rest


def parse_bullet(line: str) -> tuple[str, str, str]:
    """Splits one schedule bullet into date, quote and citation.

    A line of any other shape, such as a comparison of two documents, comes back whole as the
    quote, minus its bullet marker, with the date and the citation empty.
    """
    match = _STANDARD.match(line)
    if match:
        return match.group(1), match.group(2), match.group(3)
    return "", line[2:], ""


def evidence_rows(report: str) -> list[list[str]]:
    """One row of document, date, quote and citation for every bullet of the Evidence section."""
    rows = []
    document = ""
    for line in evidence_section(report).splitlines():
        if line.startswith("### "):
            document = line[4:].strip()
        elif line.startswith("- "):
            rows.append([document, *parse_bullet(line)])
    return rows


def write_csv(report: str, path: Path) -> None:
    """Writes the Evidence section as a CSV that Excel opens: a byte order mark and CRLF ends."""
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\r\n")
        writer.writerow(CSV_HEADER)
        writer.writerows(evidence_rows(report))


def write_docx(report: str, path: Path) -> None:
    """Converts the report to a Word file with the pandoc that ships inside pypandoc-binary."""
    pypandoc.convert_text(report, "docx", format=MARKDOWN, outputfile=str(path))


def write_pdf(report: str, path: Path) -> None:
    """Converts the report to Typst with pandoc and compiles that to a PDF, with no system library."""
    source = pypandoc.convert_text(report, "typst", format=MARKDOWN, extra_args=["--standalone"])
    path.write_bytes(typst.compile((NO_HYPHENS + source).encode("utf-8")))


def export(run_dir: Path) -> dict[str, Path]:
    """Writes report.docx, report.pdf and evidence.csv into run_dir from its report.md."""
    run_dir = Path(run_dir)
    report = (run_dir / "report.md").read_text(encoding="utf-8")
    paths = {name: run_dir / name for name in ("report.docx", "report.pdf", "evidence.csv")}
    write_docx(report, paths["report.docx"])
    write_pdf(report, paths["report.pdf"])
    write_csv(report, paths["evidence.csv"])
    return paths


def main(argv: list[str]) -> int:
    """Exports the run directory named on the command line and prints the files written."""
    if len(argv) != 1:
        print("usage: python -m rlm.export <run_dir>", file=sys.stderr)
        return 2
    for path in export(Path(argv[0])).values():
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
