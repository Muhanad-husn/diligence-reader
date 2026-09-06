"""Phase 3 map tests. The map reads a sample's index, sections and notes and writes map.json:
the documents as nodes, the values they share as weighted edges, and the matter its cluster is
built around. These tests run the map twice, the second time into a temporary directory, and
check that the two files are byte identical, that every document the key names is a node, that
every edge names two documents, one of the four kinds, a shared value and an anchor in each
document that parses and belongs to that document, that the first matter's cluster holds every
document of the key's phase 3 matter-documents fact and none of the key's decoys, that the
ranked list covers the room in descending score, that the matter carries the version pairs of
the room and the consequences the map read off the index and the notes, that every document the
key plants ranks above every decoy, and that the run prints one readout line. A sample whose map
inputs are absent is skipped."""

from __future__ import annotations

import datetime
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
    cluster_size,
    figure_number,
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


def test_cluster_size_takes_the_prefix_above_the_cut():
    """The cut keeps every document scoring at least a hundredth of the highest score."""
    assert cluster_size([1.0, 0.5, 0.02, 0.011, 0.009, 0.0]) == 4
    assert cluster_size([1.0]) == 1
    assert cluster_size([]) == 0
    assert cluster_size([0.0, 0.0]) == 0
    # The cut is a share of the top score, so scaling every score changes nothing.
    assert cluster_size([2.0, 1.0, 0.04, 0.022, 0.018]) == 4


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


# ---------------------------------------------------------------- the artefact


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
        assert node["folder"] and node["folder"] in node["path"]
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


def test_map_first_matter_cluster_holds_the_planted_documents_and_no_decoy(mapped, key):
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
    decoys = {decoy.document for decoy in key.decoys}
    assert not (decoys & cluster), sorted(decoys & cluster)


def test_map_ranked_covers_every_document_in_descending_score(mapped, key):
    matter = mapped.document["matters"][0]
    ranked = matter["ranked"]
    assert [row["doc"] for row in ranked] and len(ranked) == len(key.documents)
    assert {row["doc"] for row in ranked} == set(key.documents)
    scores = [row["score"] for row in ranked]
    assert scores == sorted(scores, reverse=True)
    for row in ranked:
        assert set(row) == {"doc", "score", "why"}
        assert isinstance(row["why"], list)
        assert all(isinstance(reason, str) and reason for reason in row["why"])
    assert matter["cluster"] == sorted(row["doc"] for row in ranked[: len(matter["cluster"])])


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
    """The break names the document whose series turned, the period and a row of that period."""
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
    assert len(breaks) == 1
    found = breaks[0]
    assert found["doc"] == stepped[0]
    began = datetime.date.fromisoformat(started)
    period = datetime.date.fromisoformat(found["period"])
    assert period >= began
    assert (period - began).days <= DATE_WINDOW
    path = key.documents[found["doc"]]
    assert parse_anchor(found["anchor"]).doc == path
    assert found["anchor"] in known_anchors[path]


def test_map_first_matter_model_after_is_dated_after_the_matter(mapped, key, known_anchors):
    """The model names a document written after the matter that still carries its old figure."""
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
    assert len(models) == 1
    found = models[0]
    assert found["doc"] == modelled[0]
    assert found["date"] > started
    path = key.documents[found["doc"]]
    assert parse_anchor(found["anchor"]).doc == path
    assert found["anchor"] in known_anchors[path]


def test_map_every_required_document_ranks_above_every_decoy(mapped, key):
    """No decoy outranks a planted document: the ranked list is the order the dossier reads."""
    matter = mapped.document["matters"][0]
    places = {row["doc"]: place for place, row in enumerate(matter["ranked"], 1)}
    planted = planted_documents(key)
    decoys = {decoy.document for decoy in key.decoys}
    assert planted and decoys
    worst = max(places[doc] for doc in planted)
    best = min(places[doc] for doc in decoys)
    assert worst < best, (
        sorted((places[doc], doc) for doc in planted)[-3:],
        sorted((places[doc], doc) for doc in decoys)[:3],
    )


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
    """The documents the key's phase 3 matter-documents fact names."""
    for fact in key.facts:
        if fact.id == MATTER_FACT:
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
