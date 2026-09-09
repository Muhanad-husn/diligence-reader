"""Fetches sample 4, the Verizon and Yahoo filings, from SEC EDGAR and writes them as markdown.

`python -m rlm.yahoo fetch samples/yahoo` downloads the seven filings named in
`samples/yahoo/README.md` from the EDGAR archives by accession number, converts each document
to markdown with html2text, splits it on its top-level headings and then at paragraph
boundaries past 40,000 characters, and writes one markdown file per section under
`samples/yahoo/documents/<folder>/`.

EDGAR asks every caller to name itself, so every request carries the User-Agent below and the
run waits between requests, well under the ten requests a second EDGAR allows. The raw HTML is
cached under `samples/yahoo/documents/_raw/` and a rerun reads the cache rather than the
network. An archived filing carries no date of its own run, so nothing is stripped for time and
two runs write the same bytes.
"""

from __future__ import annotations

import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import html2text
import httpx

# EDGAR asks for a caller who names a person and an address.
USER_AGENT = "RLM rebuild muhanad.a.husn@gmail.com"

# Yahoo! Inc.
CIK = "1011006"

ARCHIVES = "https://www.sec.gov/Archives/edgar/data"

# Seconds between requests. EDGAR allows ten a second; this takes four.
PACE = 0.25

# The largest a written section may be, in characters.
LIMIT = 40000

# A part shorter than this and holding no text of its own is not a section of its own.
FRONT = "front matter"


@dataclass(frozen=True)
class Source:
    """One document of a filing: the label the filing gives it and its file name on EDGAR."""

    label: str
    file: str


@dataclass(frozen=True)
class Filing:
    """One filing: its folder here, its accession number, its form, its date and its documents."""

    folder: str
    accession: str
    form: str
    date: str
    sources: tuple[Source, ...]


@dataclass(frozen=True)
class Part:
    """One section of a filing: the heading that opens it and the text under that heading."""

    heading: str
    text: str


# The seven filings, in filing order. samples/yahoo/README.md names the same seven.
FILINGS: tuple[Filing, ...] = (
    Filing(
        folder="8-K-2016-07-25-stock-purchase-agreement",
        accession="0001193125-16-656036",
        form="8-K",
        date="2016-07-25",
        sources=(
            Source(label="8-K", file="d178500d8k.htm"),
            Source(label="exhibit 2.1 stock purchase agreement", file="d178500dex21.htm"),
        ),
    ),
    Filing(
        folder="8-K-2016-09-22-2014-security-incident",
        accession="0001193125-16-717056",
        form="8-K",
        date="2016-09-22",
        sources=(
            Source(label="8-K", file="d260014d8k.htm"),
            Source(label="exhibit 99.1 press release", file="d260014dex991.htm"),
        ),
    ),
    Filing(
        folder="8-K-2016-12-14-2013-security-incident",
        accession="0001193125-16-793106",
        form="8-K",
        date="2016-12-14",
        sources=(
            Source(label="8-K", file="d305610d8k.htm"),
            Source(label="exhibit 99.1 press release", file="d305610dex991.htm"),
        ),
    ),
    Filing(
        folder="8-K-2017-02-21-amendment",
        accession="0001193125-17-049548",
        form="8-K",
        date="2017-02-21",
        sources=(
            Source(label="8-K", file="d353690d8k.htm"),
            Source(label="exhibit 2.1 amendment to stock purchase agreement", file="d353690dex21.htm"),
            Source(label="exhibit 2.2 amendment to reorganization agreement", file="d353690dex22.htm"),
            Source(label="exhibit 10.1 settlement and release agreement", file="d353690dex101.htm"),
        ),
    ),
    Filing(
        folder="DEFA14A-2017-02-21-press-release",
        accession="0001193125-17-049549",
        form="DEFA14A",
        date="2017-02-21",
        sources=(Source(label="exhibit 99.1 press release", file="d353690dex991.htm"),),
    ),
    Filing(
        folder="10-K-2016",
        accession="0001193125-17-065791",
        form="10-K",
        date="2017-03-01",
        sources=(Source(label="10-K", file="d293630d10k.htm"),),
    ),
    Filing(
        folder="DEFM14A-2017-04-24",
        accession="0001193125-17-133449",
        form="DEFM14A",
        date="2017-04-24",
        sources=(Source(label="DEFM14A", file="d206374ddefm14a.htm"),),
    ),
)

_RULE = re.compile(r"^[\s\-|:]+$")
_ITEM = re.compile(r"^Item\s+\d+[A-Z]?\b", re.IGNORECASE)
_ARTICLE = re.compile(r"^Article\s+(?:[IVXLCDM]+|\d+)\b", re.IGNORECASE)
_PART = re.compile(r"^Part\s+(?:[IVXLCDM]+|\d+)\b", re.IGNORECASE)
_INTEGER = re.compile(r"^\d+$")
_MARKS = re.compile(r"[*_`#]")
_SPACES = re.compile(r"\s+")
_LOWER = re.compile(r"[a-z]")
_LETTERS = re.compile(r"[A-Za-z]")
_UNSAFE = re.compile(r"[^a-z0-9]+")

# The longest a line may be and still open a section.
HEADING_LIMIT = 150


def archive_url(accession: str, file: str) -> str:
    """Builds the EDGAR archive URL of one document of one filing."""
    return f"{ARCHIVES}/{CIK}/{accession.replace('-', '')}/{file}"


def clean(text: str) -> str:
    """Takes the markdown marks and the runs of space out of one line of text."""
    return _SPACES.sub(" ", _MARKS.sub("", text.replace("\xa0", " ").replace("\\", ""))).strip()


def heading_of(line: str) -> str | None:
    """Returns the heading a line opens, or None when the line opens no section.

    A section is opened by a line that names an item, an article or a part of the filing, or by
    a line of capitals standing on its own. A row of a table opens a section only by the first
    kind, and only when no cell of it is a bare page number, so that a table of contents opens
    nothing.
    """
    raw = line.replace("\xa0", " ")
    if not raw.strip() or _RULE.fullmatch(raw.strip()):
        return None
    table = "|" in raw
    cells = [clean(cell) for cell in raw.split("|")] if table else [clean(raw)]
    if table and any(_INTEGER.fullmatch(cell) for cell in cells if cell):
        return None
    text = " ".join(cell for cell in cells if cell)
    if not text or len(text) > HEADING_LIMIT:
        return None
    if _ITEM.match(text) or _ARTICLE.match(text) or _PART.match(text):
        return text
    if table:
        return None
    if len(_LETTERS.findall(text)) >= 4 and not _LOWER.search(text):
        return text
    return None


def markdown_of(html: str) -> str:
    """Converts one filing document from HTML to markdown.

    A filing writes many of its spaces as non-breaking spaces, so a figure reads as a price
    joined to its unit by a character no later stage can quote. They become ordinary spaces
    here, and every line ends with a single newline. The words, the quotation marks and the
    dashes of the filing are left as they are.
    """
    reader = html2text.HTML2Text()
    reader.body_width = 0
    reader.ignore_images = True
    reader.ignore_links = True
    reader.unicode_snob = True
    text = reader.handle(html)
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\N{NO-BREAK SPACE}", " ")


def has_text(text: str, heading: str) -> bool:
    """Says whether a part carries a line of its own under its heading line."""
    for line in text.splitlines()[1:]:
        stripped = line.strip()
        if stripped and not _RULE.fullmatch(stripped) and clean(stripped) != heading:
            return True
    return False


def split_headings(markdown: str) -> list[Part]:
    """Splits a filing's markdown into one part per top-level heading.

    Everything before the first heading is one part called front matter.
    """
    parts: list[Part] = []
    heading = FRONT
    lines: list[str] = []
    for line in markdown.splitlines():
        found = heading_of(line)
        if found is not None:
            parts.append(Part(heading=heading, text="\n".join(lines).strip("\n") + "\n"))
            heading = found
            lines = [line]
        else:
            lines.append(line)
    parts.append(Part(heading=heading, text="\n".join(lines).strip("\n") + "\n"))
    return [part for part in parts if part.text.strip()]


def fold_empty(parts: list[Part]) -> list[Part]:
    """Folds a heading that carries no text of its own into the part that follows it.

    A filing's cover page is a run of headings with nothing under any of them. Folding them
    forward leaves the cover as the head of one part rather than as a file per line.
    """
    folded: list[Part] = []
    carried: list[str] = []
    for part in parts:
        if part.heading != FRONT and not has_text(part.text, part.heading):
            carried.append(part.text)
            continue
        text = "".join(carried) + part.text
        carried = []
        folded.append(Part(heading=part.heading, text=text))
    if carried:
        if folded:
            last = folded[-1]
            folded[-1] = Part(heading=last.heading, text=last.text + "".join(carried))
        else:
            folded.append(Part(heading=FRONT, text="".join(carried)))
    return folded


def blocks_of(text: str) -> list[str]:
    """Splits a part's text into paragraphs, each keeping the blank line that closed it."""
    blocks: list[str] = []
    current: list[str] = []
    blank = False
    for line in text.splitlines(keepends=True):
        if line.strip():
            if blank and current:
                blocks.append("".join(current))
                current = []
            blank = False
        else:
            blank = True
        current.append(line)
    if current:
        blocks.append("".join(current))
    return blocks


def cut(block: str, limit: int) -> list[str]:
    """Cuts one paragraph that is longer than the limit, at a line break where there is one."""
    pieces: list[str] = []
    rest = block
    while len(rest) > limit:
        window = rest[:limit]
        at = window.rfind("\n")
        if at <= 0:
            at = limit
        else:
            at += 1
        pieces.append(rest[:at])
        rest = rest[at:]
    if rest:
        pieces.append(rest)
    return pieces


def split_long(part: Part, limit: int) -> list[Part]:
    """Splits a part longer than the limit at paragraph boundaries, keeping every character.

    The second and later pieces keep the heading with the count of the piece appended, so the
    order of a split section is readable from its file names.
    """
    if len(part.text) <= limit:
        return [part]
    pieces: list[str] = []
    current = ""
    for block in blocks_of(part.text):
        for piece in cut(block, limit) if len(block) > limit else [block]:
            if current and len(current) + len(piece) > limit:
                pieces.append(current)
                current = ""
            current += piece
    if current:
        pieces.append(current)
    return [
        Part(heading=part.heading if number == 1 else f"{part.heading} (continued {number})", text=text)
        for number, text in enumerate(pieces, start=1)
    ]


def split_filing(markdown: str, limit: int = LIMIT) -> list[Part]:
    """Splits one filing document into the parts that are written as files."""
    parts = fold_empty(split_headings(markdown))
    return [piece for part in parts for piece in split_long(part, limit)]


def slug(text: str) -> str:
    """Turns a heading into the middle of a file name."""
    made = _UNSAFE.sub("-", text.lower()).strip("-")[:60].strip("-")
    return made or "section"


def write_parts(folder: Path, parts: list[Part], start: int = 1) -> list[Path]:
    """Writes one markdown file per part under folder, numbered from start, and returns them."""
    folder.mkdir(parents=True, exist_ok=True)
    written = []
    for number, part in enumerate(parts, start=start):
        path = folder / f"{number:02d}-{slug(part.heading)}.md"
        path.write_bytes(part.text.encode("utf-8"))
        written.append(path)
    return written


def read_source(client: httpx.Client | None, cache: Path, filing: Filing, source: Source) -> str:
    """Reads one document of one filing from the cache, downloading it once when it is absent."""
    path = cache / filing.accession / source.file
    if not path.exists():
        if client is None:
            raise FileNotFoundError(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        url = archive_url(filing.accession, source.file)
        print(f"fetching {url}")
        response = client.get(url)
        response.raise_for_status()
        path.write_bytes(response.content)
        time.sleep(PACE)
    return path.read_text(encoding="utf-8", errors="replace")


def clear(folder: Path) -> None:
    """Takes the markdown files a previous run wrote out of a filing's folder."""
    if folder.is_dir():
        for path in sorted(folder.glob("*.md")):
            path.unlink()


def fetch(sample_dir: Path) -> tuple[int, int, int]:
    """Fetches the seven filings and writes their sections. Returns filings, files, characters."""
    documents = sample_dir / "documents"
    cache = documents / "_raw"
    cache.mkdir(parents=True, exist_ok=True)
    files = 0
    characters = 0
    with httpx.Client(headers={"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"}, timeout=180) as client:
        for filing in FILINGS:
            folder = documents / filing.folder
            clear(folder)
            number = 1
            for source in filing.sources:
                parts = split_filing(markdown_of(read_source(client, cache, filing, source)), LIMIT)
                written = write_parts(folder, parts, start=number)
                number += len(written)
                files += len(written)
                characters += sum(len(part.text) for part in parts)
            print(f"{filing.folder}: {number - 1} sections")
    return len(FILINGS), files, characters


def main(argv: list[str]) -> int:
    """Runs the command line: fetch <sample directory>."""
    if len(argv) != 2 or argv[0] != "fetch":
        print("usage: python -m rlm.yahoo fetch samples/yahoo", file=sys.stderr)
        return 2
    filings, files, characters = fetch(Path(argv[1]))
    print(f"filings: {filings}, sections written: {files}, characters: {characters}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
