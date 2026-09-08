"""The unnamed knob: sample 1 with the matter named nowhere.

Seven identifiers go. Five are names the matter is known by across functions: the codename of
the forensic workstream, the network-quality reference, the name of the user-facing programme,
the phrase the product organisation calls the symptom by and the phrase finance and legal call
the work by. Two are the file-name identifiers that link its documents, the backup object and
the legacy signing key. Each becomes one plain phrase, the same phrase in every document, so
the room still says what happened and never says what it is called. Dates, record counts,
amounts, people and organisations are untouched, and so are the system names `legacy_uap` and
`VPAuth`, the deal codename `Project Atlas`, and the streaming organisation whose name resembles
the workstream's codename and is a different organisation.

How a phrase is written into a sentence. Five of the seven phrases take an article and the two
mass phrases never do. A quote mark on each side of a name belongs to the name and goes with it.
Two names written one after the other name one thing, so the first goes and the second is
written where the first stood. A bracketed aside carrying one name and nothing but label words
goes with its brackets, and so does a trailing apposition inside a bracket. The head nouns and
the label words standing immediately before the name, or the head noun standing immediately
after it, are the same thing the phrase is, so the name and those words together become the
phrase.

Then the phrase takes `the` where a bare noun would not read. A determiner already standing in
the noun phrase, one word back or two, is kept and the phrase is written bare. A slash makes a
list of what one thing is called, and the phrase joins the list the way the member before the
slash was written. Otherwise the phrase takes the article after a sentence end, a colon, a
semicolon, a comma, a bracket, a quote mark, a pipe, a dash, a preposition or the start of a
line, and where none of those settles it, it takes the article when what follows carries no
noun of its own and is written bare when it modifies the word after it. A phrase is capitalised
where a sentence starts and is written in small letters everywhere else, whatever case the name
it replaces was written in, so a line the source wrapped mid-sentence keeps its small letters.

The four documents whose file name carried a name are renamed by the same rewriter, reading the
underscores as spaces and writing the result back with underscores and each word's own capital.
A file name is not a sentence, so no phrase takes an article there. The document ids do not
change.

The key by construction. The five identifier facts whose value is a removed name are dropped and
listed in the README. The identifier facts for the forensics firm, outside counsel and the object
store stay: they are organisations and a system, not names of the matter. Every fact that stays
carries the rewritten text where its value held a removed name, and a quote fact takes the text
its own document now writes, so the quote stands in the document as phase 1 and the grader read
it. The first rubric row names the incident the way the room now names it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace

from rlm.widen import Drop, Source, Variant, identity, markdown_path, wrap

NAME = "unnamed"


@dataclass(frozen=True)
class Identifier:
    """One name the knob removes: what it is called here, the spellings the room writes it in,
    the phrase that replaces it, whether that phrase takes an article, and the head nouns that
    are the same word the phrase is and are absorbed into it."""

    id: str
    names: tuple[str, ...]
    phrase: str
    article: bool
    synonyms: tuple[str, ...]

    @property
    def words(self) -> frozenset[str]:
        """The words the phrase and its head nouns are made of, in small letters."""
        return frozenset(self.phrase.lower().split()) | {one.lower() for one in self.synonyms}


IDENTIFIERS: tuple[Identifier, ...] = (
    Identifier(
        id="workstream",
        names=("AURORA",),
        phrase="workstream",
        article=True,
        synonyms=("workstream",),
    ),
    Identifier(
        id="ticket",
        names=("NQ-17", "NQ17"),
        phrase="ticket",
        article=True,
        synonyms=("ticket", "incident", "reference"),
    ),
    Identifier(
        id="programme",
        names=("Trust Reset",),
        phrase="programme",
        article=True,
        synonyms=("programme", "program"),
    ),
    Identifier(
        id="sign-in-difficulty",
        names=("login friction",),
        phrase="sign-in difficulty",
        article=False,
        synonyms=(),
    ),
    Identifier(
        id="account-security",
        names=("credential-hygiene", "credential hygiene"),
        phrase="account-security",
        article=False,
        synonyms=(),
    ),
    Identifier(
        id="archive",
        names=("legacy_uap_backup_2021.tar.gz",),
        phrase="archive",
        article=True,
        synonyms=("object", "file", "archive", "backup"),
    ),
    Identifier(
        id="signing-key",
        names=("vpauth-legacy-2019",),
        phrase="signing key",
        article=True,
        synonyms=("key",),
    ),
)

BY_ID = {one.id: one for one in IDENTIFIERS}

# How each identifier's names are found in a section text. The workstream's codename is matched
# on the capitals alone, because the publisher schedule writes a streaming organisation whose
# name is the same word in ordinary case. Every other name is matched whatever its case. A name
# is a whole token: neither a letter, a figure nor an underscore stands on either side of it, so
# a system name that carries one of these words is left alone.
BODY = {
    "workstream": r"AURORA",
    "ticket": r"NQ-?17",
    "programme": r"(?i:Trust Reset)",
    "sign-in-difficulty": r"(?i:login friction)",
    "account-security": r"(?i:credential[- ]hygiene)",
    "archive": r"legacy_uap_backup_2021\.tar\.gz",
    "signing-key": r"vpauth-legacy-2019",
}

# The same names as a file name writes them, where the workstream's codename is matched whatever
# its case: a file name is not a sentence and no organisation is named in one.
IN_A_FILE_NAME = dict(BODY, workstream=r"(?i:AURORA)")

# A determiner already standing before a name stays, and the phrase is written bare.
DETERMINERS = frozenset(
    ("the", "a", "an", "this", "that", "these", "those", "its", "our", "their", "his", "her")
)

# The prepositions after which a bare noun does not read, so the phrase takes an article.
PREPOSITIONS = frozenset(
    (
        "of", "on", "in", "to", "for", "under", "with", "from", "by", "at", "during",
        "across", "about", "re", "as", "into",
    )
)

# The characters after which the phrase takes an article: a bracket, a quote mark and a pipe all
# leave the phrase at the head of what follows them.
OPENERS = "([{|\"'“‘`"

# The marks that end a clause, after which the phrase takes an article.
BREAKS = ":;,|—–"

# The marks that close what was being said, so a phrase standing before one of them is the head
# of it and takes an article. An opening bracket or a quote mark closes nothing.
CLOSERS = ".,;:!?|—–)]}"

# The words that carry no noun of their own, so a phrase standing before one of them is the head
# of what is being said and takes an article, where a phrase standing before an ordinary word
# modifies that word and is written bare.
FUNCTION = frozenset(
    (
        "and", "or", "but", "is", "was", "are", "were", "be", "been", "being", "has", "have",
        "had", "will", "would", "can", "could", "may", "might", "shall", "should", "do", "does",
        "did", "not", "that", "which", "who", "whose", "when", "while", "if", "so", "than",
        "then", "it", "we", "they", "he", "she",
    )
)

# The marks that end a sentence, after which the phrase takes an article and a capital.
STOPS = ".?!"

# The quote marks that belong to a name when one stands on each side of it.
QUOTES = {'"': '"', "'": "'", "“": "”", "‘": "’", "`": "`"}

# The words that label a name and say nothing once it is gone. One standing immediately before a
# name goes with the name, and a bracketed aside carrying a name and nothing but these goes with
# its brackets.
HEADS = frozenset(("code", "codename", "kid", "id", "ref"))
LABELS = frozenset(("the", "a", "an", "and", "or")) | HEADS

ASIDE = re.compile(r"\([^()]*\)")


def pattern_over(bodies: dict[str, str]) -> re.Pattern:
    """One pattern over every name, with a group per identifier so a match knows what it is."""
    return re.compile(
        "|".join(
            rf"(?P<{one.id.replace('-', '_')}>(?<![A-Za-z0-9_]){bodies[one.id]}(?![A-Za-z0-9_]))"
            for one in IDENTIFIERS
        )
    )


IN_TEXT = pattern_over(BODY)
IN_NAME = pattern_over(IN_A_FILE_NAME)


def identifier_of(match: re.Match) -> Identifier:
    """The identifier one match of a name pattern belongs to."""
    return BY_ID[match.lastgroup.replace("_", "-")]


def core(word: str) -> str:
    """One neighbouring word with the punctuation that hangs off it taken away."""
    return word.strip(".,;:!?()[]\"'`“”‘’—–").lower()


def word_before(text: str, at: int) -> tuple[int, str] | None:
    """The word standing before `at`, with only whitespace between, and where it starts."""
    match = re.search(r"(\S+)\s+$", text[:at])
    return (match.start(1), match.group(1)) if match else None


def word_after(text: str, at: int) -> tuple[int, str] | None:
    """The word standing after `at`, with only whitespace between, and where it starts."""
    match = re.match(r"\s+(\S+)", text[at:])
    return (at + match.start(1), match.group(1)) if match else None


def determined(text: str, start: int) -> bool:
    """Says whether a determiner already stands in the noun phrase the span opens.

    The word before is read, and the word before that where the first is a modifier, so that
    `the related Trust Reset programme` keeps the determiner it has and writes the phrase bare.
    The reading stops at a preposition or at any word carrying a mark of its own, because a
    determiner past one of those belongs to another phrase.
    """
    at = start
    for _ in range(2):
        standing = word_before(text, at)
        if standing is None:
            return False
        word = standing[1]
        if core(word) in DETERMINERS:
            return True
        if core(word) in PREPOSITIONS or word[-1] in STOPS or word[-1] in BREAKS:
            return False
        at = standing[0]
    return False


def following(text: str, end: int) -> str:
    """What stands after the span on the same line: a mark, a word, or nothing."""
    line = text[end:].split("\n", 1)[0]
    rest = line.lstrip(" \t")
    if not rest:
        return ""
    return rest.split(" ")[0] if rest[0].isalnum() else rest[0]


def opening(text: str, start: int, end: int) -> tuple[bool, bool]:
    """Whether the phrase written over the span takes an article and a capital.

    The answer is read from what stands before the span: the start of the text, a slash that
    makes the phrase one of a list, a determiner already in the noun phrase, a mark that ends a
    sentence or a clause, a preposition, or the start of a line. Where none of those settles it,
    the phrase takes an article when what follows it carries no noun of its own, and is written
    bare when it modifies the word after it. A phrase takes a capital only where a sentence
    starts, so a line the source wrapped in the middle of a sentence keeps its small letters.
    """
    before = text[:start]
    if not before.strip():
        return True, True
    if before.rstrip().endswith("/"):
        # A slash makes a list of what one thing is called, and the phrase is written the way
        # the member before the slash is. A member that is another name carries its own article;
        # a member that is a word of the source carries whatever determiner the source gave it,
        # and the phrase joins the list bare.
        head = before.rstrip()[:-1].rstrip()
        first = [one for one in IN_TEXT.finditer(text) if one.end() == len(head)]
        if first:
            return opening(text, first[0].start(), first[0].end())[0], False
        return False, False
    last = before[-1]
    if last not in " \t\n":
        return last in OPENERS, False
    word = word_before(text, start)[1]
    if word[-1] in STOPS:
        return True, True
    if determined(text, start):
        return False, False
    if word[-1] in BREAKS or word in ("—", "–", "-"):
        return True, False
    if core(word) in PREPOSITIONS:
        return True, False
    if before.endswith("\n"):
        return True, False
    after = following(text, end)
    if not after:
        return False, False
    return (core(after) in FUNCTION if after[0].isalnum() else after[0] in CLOSERS), False


def phrase_at(
    text: str, start: int, end: int, one: Identifier, articles: bool = True
) -> str:
    """The phrase as the span is written: with or without its article, capital or small."""
    article, capital = opening(text, start, end)
    said = f"the {one.phrase}" if article and articles and one.article else one.phrase
    return said[0].upper() + said[1:] if capital else said


def covered(taken: list, at: int) -> bool:
    """Says whether a position is already inside a span the knob is going to write over."""
    return any(start <= at < end for start, end, _ in taken)


def empty_aside(content: str, one: Identifier, names: re.Pattern) -> bool:
    """Says whether a bracketed aside says nothing once the name inside it is gone.

    What is left is read as words, and the aside is empty when every word is a label, a
    determiner or the same word the phrase is.
    """
    rest = re.sub(r"[^\w\s-]", " ", names.sub(" ", content))
    return all(word.strip("-").lower() in LABELS | one.words for word in rest.split())


def quoted(text: str, start: int, end: int) -> tuple[int, int]:
    """The span of a match with the quote marks that hug it on each side taken in."""
    if start > 0 and end < len(text) and QUOTES.get(text[start - 1]) == text[end]:
        return start - 1, end + 1
    return start, end


def absorbed(text: str, start: int, end: int, one: Identifier, taken: list) -> tuple[int, int]:
    """The span of a match with the duplicated head nouns standing beside it taken in.

    The words before are read first, one after another while each is the same word the phrase is
    or a label of the name: `the AURORA workstream`, `Workstream AURORA` and `incident code
    NQ-17` are all one thing, and the name and those words together become the phrase. A head
    noun that follows keeps the punctuation hanging off it.
    """
    heads = set(one.synonyms) | HEADS
    at = start
    while True:
        before = word_before(text, at)
        if before is not None and before[1] == "/":
            # A slash joins two words for one thing, and the head noun on the far side of it is
            # the same word the phrase is: `programme / Trust Reset costs` is one programme.
            before = word_before(text, before[0])
        if before is None or covered(taken, before[0]) or core(before[1]) not in heads:
            break
        at = before[0]
    if at != start:
        return at, end
    after = word_after(text, end)
    if after is not None and not covered(taken, after[0]) and core(after[1]) in one.synonyms:
        return start, after[0] + len(core(after[1]))
    return start, end


def dropped_asides(text: str, matches: list, names: re.Pattern) -> list[tuple[int, int, str]]:
    """The bracketed asides that go, with the whitespace standing before them.

    An aside carrying one name and nothing but label words says nothing once the name is gone,
    and neither does a trailing apposition inside a bracket, so each goes whole. An aside
    carrying two names is a list of what one thing is called, and it stays.
    """
    gone = []
    for aside in ASIDE.finditer(text):
        inside = [
            one for one in matches if aside.start() < one.start() and one.end() < aside.end()
        ]
        if len(inside) != 1:
            continue
        one = identifier_of(inside[0])
        content = aside.group(0)[1:-1]
        if empty_aside(content, one, names):
            start = re.search(r"\s*$", text[: aside.start()]).start()
            gone.append((start, aside.end(), ""))
            continue
        head, mark, tail = content.rpartition(",")
        at = aside.start() + 1 + len(head)
        if mark and at <= inside[0].start() and empty_aside(tail, one, names):
            gone.append((at, aside.end() - 1, ""))
    return gone


def edits(text: str, names: re.Pattern = IN_TEXT, articles: bool = True) -> list:
    """Every span of one text the knob writes over, and what it writes there."""
    matches = list(names.finditer(text))
    taken = dropped_asides(text, matches, names)
    standing = [one for one in matches if not covered(taken, one.start())]

    for number, match in enumerate(standing):
        one = identifier_of(match)
        start, end = quoted(text, match.start(), match.end())
        after = standing[number + 1] if number + 1 < len(standing) else None
        if after is not None and not text[end : after.start()].strip():
            # Two names one after the other name one thing: the first goes with the space that
            # follows it, and the second is written where the first stood, so the sentence keeps
            # the article and the capital the first would have taken.
            taken.append((start, after.start(), ""))
            continue
        start, end = absorbed(text, start, end, one, taken)
        taken.append((start, end, phrase_at(text, start, end, one, articles)))

    return sorted(taken)


def apply(text: str, pieces: list) -> str:
    """One text with every span the knob writes over written over, and no line left empty."""
    out = []
    at = 0
    for start, end, said in pieces:
        out.append(text[at:start])
        out.append(said)
        at = end
    out.append(text[at:])
    return "\n".join(line for line in "".join(out).split("\n") if line.strip())


def rewrite(text: str) -> str:
    """One section text with the matter named nowhere."""
    return apply(text, edits(text))


def carry(text: str, start: int, end: int) -> str:
    """The text of one span of a source section as the rewritten section writes it.

    The span is widened over any replacement it cuts through, so a quote that opens on a name
    carries the whole phrase, and the answer is read out of the rewritten section itself.
    """
    pieces = edits(text)
    for was_start, was_end, _ in pieces:
        if was_start < start < was_end:
            start = was_start
        if was_start < end < was_end:
            end = was_end

    def moved(at: int) -> int:
        return at + sum(
            len(said) - (was_end - was_start)
            for was_start, was_end, said in pieces
            if was_end <= at
        )

    return apply(text, pieces)[moved(start) : moved(end)]


def rename(doc: str) -> str:
    """The path a source document takes in the variant.

    A file name that carries a name is rewritten by the same rewriter, with the underscores read
    as spaces and the result written back with underscores and each word's own capital. A file
    name the rewriter leaves alone keeps the name and the capitals the source gave it.
    """
    path = markdown_path(doc)
    head, slash, name = path.rpartition("/")
    stem, dot, rest = name.partition(".")
    was = " ".join(stem.split("_"))
    said = apply(was, edits(was, names=IN_NAME, articles=False))
    if said == was:
        return path
    written = "_".join(word[:1].upper() + word[1:] for word in said.split())
    return f"{head}{slash}{written}{dot}{rest}"


def carried(source: Source) -> dict[str, list[str]]:
    """The document ids sample 1 writes each identifier in, by the identifier's id."""
    ids = {path: doc_id for doc_id, path in source.key["documents"].items()}
    found: dict[str, list[str]] = {one.id: [] for one in IDENTIFIERS}
    for doc in sorted(source.sections, key=lambda path: ids[path]):
        text = "\n".join(source.sections[doc])
        for name in sorted({identifier_of(match).id for match in IN_TEXT.finditer(text)}):
            found[name].append(ids[doc])
    return found


# Why each dropped fact is dropped. Its value is a name the knob takes out of the room, so the
# fact has nothing left in the room to resolve to.
WHY = {
    "backup-object": "the value is the backup object's file name, now written as a phrase.",
    "signing-key": "the value is the legacy signing key's name, now written as a phrase.",
    "ticket": "the value is the reference the matter is tracked under, now written as a phrase.",
    "workstream": "the value is the codename of the forensic workstream, now written as a "
    "phrase.",
    "programme": "the value is the name of the user-facing programme, now written as a phrase.",
}


def table(rooms: dict[str, list[str]]) -> str:
    """The README's table: one row per phrase, with the documents that carried what it replaced."""
    lines = ["| phrase | documents |", "|---|---|"]
    for one in IDENTIFIERS:
        lines.append(f"| {one.phrase} | {', '.join(rooms[one.id])} |")
    return "\n".join(lines)


def notes(rooms: dict[str, list[str]], renamed: list[tuple[str, str]]) -> str:
    """The section the knob adds to the variant's README."""
    said = wrap(
        f"The knob takes out the {len(IDENTIFIERS)} identifiers the matter is named by and "
        f"writes one plain phrase for each, the same phrase in every document. Five of the "
        f"phrases take an article and the two mass phrases do not. Dates, record counts, "
        f"amounts, people and organisations are untouched, and so are the system names the room "
        f"writes for the profile store and the authentication platform, the deal codename, and "
        f"the streaming organisation whose name resembles the codename of the workstream and is "
        f"a different organisation."
    )
    paths = wrap(
        f"{len(renamed)} documents are renamed, because a path that carries a name defeats the "
        f"knob. The document ids do not change."
    )
    listed = "\n".join(f"- {doc_id}: `{path.rpartition('/')[2]}`" for doc_id, path in renamed)
    return f"## Phrases\n\n{said}\n\n{table(rooms)}\n\n{paths}\n\n{listed}\n"


def build(source: Source) -> Variant:
    """The variant of sample 1 with the matter named nowhere."""
    documents = source.key["documents"]

    def text(doc: str, one: str) -> str:
        return rewrite(one)

    def quote(value: str, doc: str) -> str:
        """The value of a quote fact as its own document now writes it."""
        wanted = re.compile(r"\s+".join(re.escape(word) for word in value.split()))
        for section in source.sections.get(documents[doc], ()):
            match = wanted.search(section)
            if match:
                return carry(section, match.start(), match.end())
        return rewrite(value)

    def fact(one: dict) -> dict | Drop:
        if one["id"] in WHY:
            return Drop(id=one["id"], why=WHY[one["id"]])
        if not IN_TEXT.search(one["value"]):
            return one
        value = (
            quote(one["value"], one["documents"][0])
            if one["kind"] == "quote"
            else rewrite(one["value"])
        )
        return {**one, "value": value}

    variant = identity(source, NAME, text=text, fact=fact, path=rename)
    rubric = [dict(row) for row in source.key["rubric"]]
    rubric[0] = {**rubric[0], "earns": rewrite(rubric[0]["earns"])}
    renamed = [
        (document.id, document.path)
        for document in variant.documents
        if document.path != markdown_path(documents[document.id])
    ]
    return replace(
        variant, notes=notes(carried(source), renamed), key_fields={"rubric": rubric}
    )
