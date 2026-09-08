"""Phase 3 map tests. The map reads a sample's index, sections and notes and writes map.json:
the documents as nodes, the values they share as weighted edges, and the matter its cluster is
built around. These tests run the map twice, the second time into a temporary directory, and
check that the two files are byte identical, that every document the key names is a node, that
every edge names two documents, one of the four kinds, a shared value and an anchor in each
document that parses and belongs to that document, that the first matter's cluster holds every
document of the key's phase 3 matter-documents fact, that the ranked list covers the room in
descending score, that the matter carries the version pairs of the room and the consequences the
map read off the index and the notes, and that the run prints one readout line. A sample whose
map inputs are absent is skipped.

Whether a decoy sits in the cluster or outranks a planted document is not a phase 3 test. On
northwind the decoy is a master service agreement whose change-of-control clause is benign in
its wording, and the map, which links documents by the values they share, cannot tell that
clause from the automatic one: the two agreements share their template. The founder moved that
check to phase 4 on 2026-09-07, where the dossier reads the clauses out of the notes. The
readout still prints the count of decoys in the cluster for every sample."""

from __future__ import annotations

import datetime
import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path

import pytest

from rlm.key import load_key
from rlm.map import (
    DATE_WINDOW,
    EDGE_KINDS,
    KIND_WEIGHTS,
    MATTER_FACT,
    REACH_SHARE,
    VIA_KINDS,
    build_edges,
    figure_number,
    is_count,
    main,
    turn_index,
    value_weight,
)
from rlm.sections import parse_anchor

ROOT = Path(__file__).resolve().parents[1]

# The three gate samples, in the order the readout prints them.
ENABLED = ("atlas", "northwind", "northstar-dental")
SKIP_REASON = "map not run for this sample yet"

# What the map's inputs are called under runs/<sample>/.
INPUTS = ("index.jsonl", "sections.jsonl")


@dataclass(frozen=True)
class Run:
    """One pair of map runs on a sample: the two files, the map read back and what was printed."""

    first: Path
    second: Path
    document: dict
    printed: str


_RUNS: dict[str, Run] = {}


def _inputs_ready(run_dir: Path) -> bool:
    if not all((run_dir / name).exists() for name in INPUTS):
        return False
    notes_dir = run_dir / "notes"
    return notes_dir.is_dir() and any(notes_dir.glob("*.json"))


@pytest.fixture
def mapped(sample, sample_dir, run_dir, capsys, tmp_path_factory):
    """Runs the map twice on the sample and returns both files, the map and the output.

    The pair of runs is done once per sample and reused. The second run reads copies of the
    same inputs from a temporary directory and writes its map there, which is what makes the
    byte-identical check a check on the map and not on the file it overwrote.
    """
    if sample not in ENABLED or not _inputs_ready(run_dir):
        pytest.skip(SKIP_REASON)
    if sample not in _RUNS:
        second_dir = tmp_path_factory.mktemp(f"map-{sample}")
        for name in INPUTS:
            shutil.copy(run_dir / name, second_dir / name)
        shutil.copytree(run_dir / "notes", second_dir / "notes")
        assert main([str(sample_dir), str(run_dir)]) == 0
        assert main([str(sample_dir), str(second_dir)]) == 0
        printed = capsys.readouterr().out
        first = run_dir / "map.json"
        _RUNS[sample] = Run(
            first=first,
            second=second_dir / "map.json",
            document=json.loads(first.read_text(encoding="utf-8")),
            printed=printed,
        )
    return _RUNS[sample]


@pytest.fixture
def key(sample_dir):
    return load_key(sample_dir)


@pytest.fixture
def known_anchors(run_dir):
    """Every anchor the phase 1 and phase 2 artefacts wrote, by document path.

    An anchor the map writes has to be one of these: the map cites the artefacts it read and
    invents no place of its own.
    """
    found: dict[str, set[str]] = {}

    def keep(anchor):
        doc = anchor.rsplit("#", 1)[0]
        found.setdefault(doc, set()).add(anchor)

    for line in (run_dir / "sections.jsonl").read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        keep(record["anchor"])
        for cell in record.get("cells") or []:
            keep(f"{record['doc']}#{record['heading']}!{cell['ref']}")
    for line in (run_dir / "index.jsonl").read_text(encoding="utf-8").splitlines():
        for anchor in json.loads(line)["anchors"]:
            keep(anchor)
    for path in sorted((run_dir / "notes").glob("*.json")):
        note = json.loads(path.read_text(encoding="utf-8"))
        for field in ("concealed", "cross_references", "figures", "flags"):
            for item in note[field]:
                keep(item["anchor"])
    return found


@pytest.fixture
def dated_anchors(run_dir):
    """Every anchor of an index date record, which is what a date edge is allowed to cite."""
    anchors: set[str] = set()
    for line in (run_dir / "index.jsonl").read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        if record["kind"] == "date":
            anchors.update(record["anchors"])
    return anchors


# ---------------------------------------------------------------- the pure rules


def test_value_weight_falls_with_the_number_of_documents():
    """A value two documents share weighs more than the same value in sixteen."""
    four = value_weight("identifier", 4)
    sixteen = value_weight("identifier", 16)
    assert four == pytest.approx(KIND_WEIGHTS["identifier"] / 4)
    assert sixteen == pytest.approx(KIND_WEIGHTS["identifier"] / 16)
    assert four > sixteen

    # A value a note wrote weighs more than the same value only the index saw.
    assert value_weight("cross-reference", 4) > value_weight("identifier", 4)
    # Mere date proximity weighs least of the four.
    for kind in ("identifier", "cross-reference", "version"):
        assert value_weight("date", 4) < value_weight(kind, 4)

    with pytest.raises(ValueError):
        value_weight("identifier", 1)


def test_is_count_reads_a_bare_number_as_a_count_and_nothing_else():
    """A value of digits alone is a count the whole room shares, not a value of the matter.

    `5`, `2025` and `1,840` are counts; `912.8m`, `$12m`, `7.2`, `24 months` and `NQ-17` name
    something.
    """
    for value in ("5", "2025", "1,840", "  41500 "):
        assert is_count(value)
    for value in ("912.8m", "$12m", "7.2", "24 months", "NQ-17", "AURORA", "(30) days"):
        assert not is_count(value)


def test_reach_share_is_a_share_of_the_room_under_a_half():
    """A value that reaches a document from the set is rarer than one that merely links two."""
    assert 0 < REACH_SHARE < 0.5
    assert set(VIA_KINDS) == {
        "compare",
        "consequence",
        "covenant",
        "reach",
        "seed",
        "shared",
        "version",
    }


def test_turn_index_finds_where_a_column_stops_wobbling():
    """A column turns where its steps start running one way and are bigger than its usual step."""
    assert turn_index([615, 616, 615, 617, 616, 615, 611, 606, 599, 594]) == 6

    # A column that only wobbles by its usual step never turns.
    assert turn_index([615, 616, 617, 617, 618, 618, 619, 620, 621, 622, 623]) is None
    assert turn_index([5, 5, 5, 5, 5, 5, 5]) is None
    # A column too short to hold a run has no turn.
    assert turn_index([615, 611, 606]) is None


def test_figure_number_reads_a_figure_without_its_unit():
    """A figure is the number it names, so 615 and 615m are the same figure and 4100 is not."""
    assert figure_number("615") == figure_number("615m") == "615"
    assert figure_number("$410m") == figure_number("410") == "410"
    assert figure_number("4100") != figure_number("410")
    assert figure_number("8.0%") == "8"
    assert figure_number("early reset ramp") is None


# The two documents the shared rule is tested on, and the value they both write.
TWO_DOCS = {"a.md": "DR-001", "b.md": "DR-002"}
SHARED_TEXT = "The AURORA workstream was paused on the day of the incident."
INDEX_RECORDS = [
    {
        "kind": "identifier",
        "surface": "AURORA",
        "value": "AURORA",
        "unit": None,
        "docs": sorted(TWO_DOCS),
        "anchors": ["a.md#p1l1", "b.md#p1l1"],
    }
]


def two_notes(about_a: list[str], about_b: list[str]) -> dict[str, dict]:
    """One note per document, each with one flag quoting the shared sentence.

    The flag's consequence names AURORA in both notes, so a rule that looked inside a flag's own
    words would join the two whatever about carries.
    """
    notes = {}
    for path, about in (("a.md", about_a), ("b.md", about_b)):
        anchor = f"{path}#p1l1"
        notes[TWO_DOCS[path]] = {
            "doc": path,
            "what": "x",
            "concealed": [],
            "cross_references": [],
            "figures": [],
            "flags": [
                {
                    "flag": "The workstream stopped",
                    "quote": SHARED_TEXT,
                    "consequence": "AURORA is the workstream the deal turns on.",
                    "about": list(about),
                    "anchor": anchor,
                }
            ],
        }
    return notes


def edges_of(about_a: list[str], about_b: list[str]) -> list[dict]:
    """The edges build_edges writes for the two documents, given what their flags are about."""
    sections = [
        {"doc": path, "anchor": f"{path}#p1l1", "ordinal": 1, "text": SHARED_TEXT}
        for path in sorted(TWO_DOCS)
    ]
    first_anchors = {doc_id: f"{path}#p1l1" for path, doc_id in TWO_DOCS.items()}
    return build_edges(
        INDEX_RECORDS,
        sections,
        two_notes(about_a, about_b),
        TWO_DOCS,
        first_anchors,
        sorted(TWO_DOCS.values()),
    )


def test_shared_rule_joins_two_documents_whose_flags_are_about_the_value():
    """A value both notes' flags name is what the shared rule looks inside."""
    edges = edges_of(["AURORA"], ["AURORA"])

    assert [(edge["a"], edge["b"], edge["kind"], edge["value"]) for edge in edges] == [
        ("DR-001", "DR-002", "identifier", "AURORA")
    ]


def test_shared_rule_ignores_a_value_only_a_flags_consequence_writes():
    """A flag that mentions a code in its own words is not a flag about that code."""
    assert edges_of([], []) == []
    assert edges_of(["AURORA"], []) == []


# ---------------------------------------------------------------- the artefact


def test_shared_rule_reads_a_value_whole_and_never_inside_another():
    """legacy_uap named by one flag is not legacy_uap_backup_2021.tar.gz named by another."""
    assert edges_of(["AURORA"], ["AURORA"])
    assert not edges_of(["AURORA"], ["AURORA-2"])
    assert not edges_of(["AURORA workstream"], ["AURORA"])


def test_map_parses_with_sorted_keys_and_one_trailing_newline(mapped):
    raw = mapped.first.read_text(encoding="utf-8")
    assert raw == json.dumps(mapped.document, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    assert raw.endswith("}\n") and not raw.endswith("\n\n")
    assert set(mapped.document) == {"documents", "edges", "matters", "sample"}


def test_map_two_runs_are_byte_identical(mapped):
    """Two runs of the same sample write the same bytes, which is what makes the map pinnable."""
    assert mapped.first.read_bytes() == mapped.second.read_bytes()


def test_map_has_a_node_for_every_key_document(mapped, key, sample):
    nodes = {node["doc"]: node for node in mapped.document["documents"]}
    assert mapped.document["sample"] == sample
    assert set(nodes) == set(key.documents)
    assert [node["doc"] for node in mapped.document["documents"]] == list(key.documents)
    for doc_id, node in nodes.items():
        assert set(node) == {"date", "doc", "folder", "path", "status"}
        assert node["path"] == key.documents[doc_id]
        # The folder is the name of the directory the document sits in, and a document at
        # the room's root has an empty one.
        assert node["folder"] == node["path"].rpartition("/")[0].rpartition("/")[2]
        assert node["date"] is None or len(node["date"]) == 10
        assert isinstance(node["status"], list)
        assert node["status"] == sorted(node["status"])


def test_map_edges_name_two_documents_a_kind_a_value_and_two_anchors(mapped, key, known_anchors):
    """Every edge joins two of the room's documents by a shared value, with a resolving anchor
    in each of them."""
    nodes = set(key.documents)
    edges = mapped.document["edges"]
    assert edges
    seen = set()
    for edge in edges:
        assert set(edge) == {"a", "anchors", "b", "kind", "value", "weight"}
        assert edge["a"] in nodes and edge["b"] in nodes
        assert edge["a"] < edge["b"]
        assert edge["kind"] in EDGE_KINDS
        assert isinstance(edge["value"], str) and edge["value"].strip()
        assert edge["weight"] > 0
        marker = (edge["a"], edge["b"], edge["kind"], edge["value"])
        assert marker not in seen
        seen.add(marker)
        assert set(edge["anchors"]) == {"a", "b"}
        for side in ("a", "b"):
            path = key.documents[edge[side]]
            anchor = edge["anchors"][side]
            assert parse_anchor(anchor).doc == path, anchor
            assert anchor in known_anchors[path], anchor
    assert [(e["a"], e["b"], e["kind"], e["value"]) for e in edges] == sorted(
        (e["a"], e["b"], e["kind"], e["value"]) for e in edges
    )


def test_map_date_edges_anchor_two_dated_sections(mapped, dated_anchors):
    date_edges = [edge for edge in mapped.document["edges"] if edge["kind"] == "date"]
    assert date_edges
    for edge in date_edges:
        assert edge["anchors"]["a"] in dated_anchors
        assert edge["anchors"]["b"] in dated_anchors


def test_map_first_matter_cluster_holds_the_planted_documents(mapped, key):
    matters = mapped.document["matters"]
    assert matters
    matter = matters[0]
    assert set(matter) == {"cluster", "consequences", "date", "id", "ranked", "seed", "versions"}
    assert matter["id"] == 1
    assert matter["seed"] and all(doc in key.documents for doc in matter["seed"])
    assert matter["cluster"] == sorted(matter["cluster"])

    planted = planted_documents(key)
    cluster = set(matter["cluster"])
    assert planted <= cluster, sorted(planted - cluster)


def test_map_ranked_covers_every_document_in_descending_score(mapped, key):
    matter = mapped.document["matters"][0]
    ranked = matter["ranked"]
    assert [row["doc"] for row in ranked] and len(ranked) == len(key.documents)
    assert {row["doc"] for row in ranked} == set(key.documents)
    scores = [row["score"] for row in ranked]
    assert scores == sorted(scores, reverse=True)
    for row in ranked:
        assert set(row) == {"doc", "score", "via", "why"}
        assert isinstance(row["why"], list)
        assert all(isinstance(reason, str) and reason for reason in row["why"])
    assert matter["cluster"] == sorted(row["doc"] for row in ranked[: len(matter["cluster"])])


def test_map_every_cluster_document_is_reached_from_the_seed(mapped, key):
    """The cluster is explained, not cut: each document names the link that put it there.

    A ranked row's `via` is None outside the cluster. Inside, it names the kind of link, the
    cluster documents it came from and the values it came by, and following `from` back from
    any document reaches the seed. A `shared` or `reach` link is a non-date edge of the map
    between the document and one of its `from` documents carrying that value, and a `reach`
    takes two different documents and two different values, or one document and one money
    figure, which names a matter on its own; a `consequence` is a row of the
    matter's consequences, a `version` a document of one of its version pairs; the seed's own
    via is the seed kind with nothing behind it.
    """
    matter = mapped.document["matters"][0]
    cluster = set(matter["cluster"])
    seed = set(matter["seed"])
    rows = {row["doc"]: row for row in matter["ranked"]}
    edges: dict[tuple[str, str], set[str]] = {}
    for edge in mapped.document["edges"]:
        if edge["kind"] == "date":
            continue
        for pair in ((edge["a"], edge["b"]), (edge["b"], edge["a"])):
            edges.setdefault(pair, set()).add(edge["value"])
    consequences = {row["doc"] for row in matter["consequences"]}
    versioned = {doc for pair in matter["versions"] for doc in pair["docs"]}

    for doc, row in rows.items():
        if doc not in cluster:
            assert row["via"] is None, doc
            continue
        via = row["via"]
        assert isinstance(via, dict) and set(via) == {"from", "kind", "values"}, doc
        assert via["kind"] in VIA_KINDS, doc
        assert via["from"] == sorted(via["from"]) and set(via["from"]) <= cluster - {doc}, doc
        assert all(isinstance(value, str) and value for value in via["values"]), doc
        if doc in seed:
            assert via["kind"] == "seed" and via["from"] == [] and via["values"] == []
            continue
        assert via["from"], doc
        if via["kind"] in ("shared", "reach"):
            assert via["values"], doc
            for value in via["values"]:
                assert not is_count(value), (doc, value)
                assert any(value in edges.get((doc, other), set()) for other in via["from"]), (
                    doc,
                    value,
                )
        if via["kind"] == "reach":
            witnessed = len(via["from"]) >= 2 and len(set(via["values"])) >= 2
            money = (
                len(via["from"]) == 1
                and len(via["values"]) == 1
                and via["values"][0].startswith("$")
            )
            assert witnessed or money, doc
        if via["kind"] == "consequence":
            assert doc in consequences, doc
        if via["kind"] == "version":
            assert doc in versioned, doc

    reached = set(seed)
    frontier = list(seed)
    behind: dict[str, set[str]] = {}
    for doc in cluster:
        for other in rows[doc]["via"]["from"]:
            behind.setdefault(other, set()).add(doc)
    while frontier:
        doc = frontier.pop()
        for other in behind.get(doc, ()):
            if other not in reached:
                reached.add(other)
                frontier.append(other)
    assert reached == cluster, sorted(cluster - reached)


def test_map_first_matter_versions_pair_the_draft_and_the_final(mapped, key):
    """Every version pair names two documents, their two dates and their two status lists."""
    matter = mapped.document["matters"][0]
    nodes = {node["doc"]: node for node in mapped.document["documents"]}
    for pair in matter["versions"]:
        assert set(pair) == {"dates", "docs", "status"}
        assert len(pair["docs"]) == 2 and len(pair["dates"]) == 2 and len(pair["status"]) == 2
        assert all(doc in key.documents for doc in pair["docs"])
        assert all(isinstance(day, str) and len(day) == 10 for day in pair["dates"])
        assert pair["dates"] == sorted(pair["dates"])
        assert [nodes[doc]["status"] for doc in pair["docs"]] == pair["status"]

    draft = fact_documents(key, "forensic-draft")
    final = fact_documents(key, "forensic-final")
    if not (draft and final):
        return
    assert len(matter["versions"]) == 1
    assert matter["versions"][0]["docs"] == [draft[0], final[0]]


def test_map_first_matter_series_break_is_within_a_week_of_the_matter_date(
    mapped, key, known_anchors
):
    """Every break names a document whose series turned, the period and a row of that period."""
    matter = mapped.document["matters"][0]
    breaks = [row for row in matter["consequences"] if row["kind"] == "series-break"]
    for row in breaks:
        assert set(row) == {"anchor", "doc", "kind", "period", "series"}
        assert row["doc"] in key.documents
        assert isinstance(row["series"], str) and row["series"].strip()
        assert len(row["period"]) == 10

    stepped = fact_documents(key, "step-down")
    started = fact_value(key, "incident-start")
    if not (stepped and started):
        return
    # Every series that turns inside the window is kept, not one of them, so sample 1 carries
    # both the metrics dashboard whose step-down is planted and the weekly KPI file beside it.
    waved = fact_documents(key, "reset-wave")
    assert len(breaks) == 2
    assert [row["doc"] for row in breaks] == sorted({stepped[0], waved[0]})
    began = datetime.date.fromisoformat(started)
    for found in breaks:
        period = datetime.date.fromisoformat(found["period"])
        assert period >= began
        assert (period - began).days <= DATE_WINDOW
        path = key.documents[found["doc"]]
        assert parse_anchor(found["anchor"]).doc == path
        assert found["anchor"] in known_anchors[path]


def test_map_first_matter_model_after_is_dated_after_the_matter(mapped, key, known_anchors):
    """Every model names a document written after the matter that still carries an old figure."""
    matter = mapped.document["matters"][0]
    models = [row for row in matter["consequences"] if row["kind"] == "model-after"]
    for row in models:
        assert set(row) == {"anchor", "date", "doc", "kind"}
        assert row["doc"] in key.documents
        assert len(row["date"]) == 10

    modelled = fact_documents(key, "synergy-npv")
    started = fact_value(key, "incident-start")
    if not (modelled and started):
        return
    # Every model dated after the matter that still carries one of the broken series' old
    # numbers is kept, not the earliest, so sample 1 carries two.
    assert len(models) == 2
    assert modelled[0] in {row["doc"] for row in models}
    for found in models:
        assert found["date"] > started
        path = key.documents[found["doc"]]
        assert parse_anchor(found["anchor"]).doc == path
        assert found["anchor"] in known_anchors[path]


def test_map_readout_counts_versions_and_consequences(mapped, sample):
    lines = [line for line in mapped.printed.splitlines() if line.startswith(f"map {sample}:")]
    assert lines
    for line in lines:
        assert "versions" in line and "consequences" in line


def test_map_prints_one_readout_line(mapped, sample):
    lines = [line for line in mapped.printed.splitlines() if line.startswith(f"map {sample}:")]
    assert len(lines) == 2, mapped.printed
    for line in lines:
        for word in ("nodes", "edges", "matters", "cluster", "seconds"):
            assert word in line


def test_map_digest_is_pinned(mapped, sample):
    """The sha256 of the sample's map.json is the one tests/phase3-digests.json holds."""
    digests = json.loads((ROOT / "tests" / "phase3-digests.json").read_text(encoding="utf-8"))
    assert sample in digests, f"{sample} has no pinned map digest"
    assert set(digests[sample]) == {"map.json"}
    got = hashlib.sha256(mapped.first.read_bytes()).hexdigest()
    assert got == digests[sample]["map.json"]


# ---------------------------------------------------------------- the gate


def test_gate_pin_maps_digests_what_is_on_disk(tmp_path, capsys):
    """pin.main --maps digests each sample's map.json as it sits on disk, copies nothing and
    writes one digest per sample keyed map.json."""
    from rlm import pin

    runs_root = tmp_path / "runs"
    wanted = {}
    for sample in ("atlas", "northwind"):
        sample_dir = runs_root / sample
        sample_dir.mkdir(parents=True)
        map_bytes = json.dumps({"sample": sample}, indent=1, sort_keys=True).encode() + b"\n"
        (sample_dir / "map.json").write_bytes(map_bytes)
        wanted[sample] = {"map.json": hashlib.sha256(map_bytes).hexdigest()}

    digests_path = tmp_path / "phase3-digests.json"
    code = pin.main(
        [str(runs_root), "--maps", "--samples", "atlas", "northwind", "--digests", str(digests_path)]
    )
    out = capsys.readouterr().out

    assert code == 0
    assert json.loads(digests_path.read_text(encoding="utf-8")) == wanted
    raw = digests_path.read_text(encoding="utf-8")
    assert raw == json.dumps(wanted, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    assert "atlas" in out and "northwind" in out
    for sample in wanted:
        assert (runs_root / sample / "map.json").exists()


def test_gate_pin_maps_refuses_a_sample_with_no_map(tmp_path, capsys):
    """pin.main --maps refuses, names the sample and writes no digest when a map is missing."""
    from rlm import pin

    runs_root = tmp_path / "runs"
    (runs_root / "atlas").mkdir(parents=True)
    (runs_root / "atlas" / "map.json").write_bytes(b"{}\n")
    (runs_root / "northwind").mkdir(parents=True)

    digests_path = tmp_path / "phase3-digests.json"
    code = pin.main(
        [str(runs_root), "--maps", "--samples", "atlas", "northwind", "--digests", str(digests_path)]
    )
    out = capsys.readouterr().out

    assert code == 1
    assert not digests_path.exists()
    assert "northwind" in out


def test_gate_default_digests_path_follows_the_mode():
    """The default digest file is tests/phase2-digests.json for notes and
    tests/phase3-digests.json for maps."""
    from rlm import pin

    assert pin.default_digests_path().name == "phase2-digests.json"
    assert pin.default_digests_path(maps=True).name == "phase3-digests.json"
    assert pin.default_digests_path(maps=True).parent == ROOT / "tests"


# ---------------------------------------------------------------- the readout


def fact_value(key, fact_id: str):
    """The value of the key fact with that id, or None where the sample has no such fact."""
    for fact in key.facts:
        if fact.id == fact_id:
            return fact.value
    return None


def fact_documents(key, fact_id: str) -> tuple[str, ...]:
    """The documents the key fact with that id resolves to, empty where there is no such fact."""
    for fact in key.facts:
        if fact.id == fact_id:
            return fact.documents
    return ()


def planted_documents(key) -> set[str]:
    """The documents the key's phase 3 document fact names: the matter's cluster.

    Sample 1 and sample 3 call that fact matter-documents; sample 2 calls it hero-documents.
    The fact is found by its phase and kind, with the id as the first choice, and a key with
    no such fact falls back to its required documents.
    """
    for fact in key.facts:
        if fact.id == MATTER_FACT:
            return set(fact.documents)
    for fact in key.facts:
        if fact.phase == 3 and fact.kind == "document":
            return set(fact.documents)
    return set(key.required_documents)


def readout(terminalreporter):
    """Writes, per sample with a map, one line of counts and one line of cluster recall."""
    if not _RUNS:
        return
    terminalreporter.section("phase 3 readout")
    for sample in ENABLED:
        if sample not in _RUNS:
            continue
        run = _RUNS[sample]
        document = run.document
        by_kind: dict[str, int] = {}
        for edge in document["edges"]:
            by_kind[edge["kind"]] = by_kind.get(edge["kind"], 0) + 1
        by_kind_text = ", ".join(f"{kind} {by_kind[kind]}" for kind in sorted(by_kind))
        matter = document["matters"][0]
        cluster = set(matter["cluster"])
        key = load_key(ROOT / "samples" / sample)
        planted = planted_documents(key)
        decoys = {decoy.document for decoy in key.decoys}
        found = planted & cluster
        recall = (len(found) / len(planted) * 100) if planted else 0.0
        seconds = 0.0
        for line in run.printed.splitlines():
            if line.startswith(f"map {sample}:") and "seconds" in line:
                seconds = float(line.rsplit("seconds ", 1)[1])
                break
        terminalreporter.write_line(
            f"phase 3 {sample}: nodes {len(document['documents'])}, "
            f"edges {len(document['edges'])} ({by_kind_text}), "
            f"matters {len(document['matters'])}, "
            f"cluster {len(cluster)}, seconds {seconds:.1f}"
        )
        terminalreporter.write_line(
            f"phase 3 {sample}: planted cluster recall {recall:.1f}% "
            f"({len(found)} of {len(planted)}), decoys in cluster {len(decoys & cluster)}"
        )
        for doc in sorted(planted - cluster):
            terminalreporter.write_line(f"phase 3 {sample}: not clustered {doc}")
        for doc in sorted(decoys & cluster):
            terminalreporter.write_line(f"phase 3 {sample}: decoy clustered {doc}")
