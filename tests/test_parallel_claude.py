"""Issue #161: Claude Code calls run up to four at once, and the stages that send many
independent calls send them together.

Every test here is free: the subprocess is a fake runner and the ledger a temporary file.
"""

import json
import threading
import time
from pathlib import Path

import pytest

from rlm import gateway as gateway_module
from rlm import ingest, notes, tree, write
from rlm.gateway import (
    PHASE_CAPS,
    CapExceeded,
    ClaudeCode,
    Completion,
    Gateway,
    Ledger,
)
from test_claude_code import HAIKU, SONNET, cli_reply, note_json, system_of, tree_answer
from test_phase8_command import write_ledger
from test_pick import small_room
from test_tree import built_tree

PRICED = "deepseek/deepseek-v4-flash-0731"


class TimedRunner:
    """Stands in for the subprocess: answers with answer(args, stdin), holds each call for
    hold(stdin) seconds, and records when each call started and ended and how many ran at once."""

    def __init__(self, answer, hold=lambda stdin: 0.0):
        self.answer = answer
        self.hold = hold
        self.calls: list[dict] = []
        self.started: list[float] = []
        self.finished: list[str] = []
        self.active = 0
        self.most = 0
        self._lock = threading.Lock()

    def __call__(self, args, cwd, env, stdin):
        with self._lock:
            self.active += 1
            self.most = max(self.most, self.active)
            self.started.append(time.monotonic())
            self.calls.append({"args": list(args), "stdin": stdin})
        time.sleep(self.hold(stdin))
        reply = self.answer(args, stdin)
        with self._lock:
            self.active -= 1
            self.finished.append(stdin)
        return 0, reply, ""


def gateway_of(runner, concurrency=None, pause=0.0) -> Gateway:
    """A gateway whose Claude Code calls go to runner, at the process's own limit unless
    concurrency names another."""
    limit = {} if concurrency is None else {"concurrency": concurrency}
    return Gateway(api_key="k", transport=None, rate_limit_waits=(),
                   claude_code=ClaudeCode(runner=runner, pause=pause, **limit))


MESSAGES = [{"role": "system", "content": "S"}, {"role": "user", "content": "U"}]


def in_threads(target, count):
    threads = [threading.Thread(target=target, args=(i,)) for i in range(count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()


# ---------------------------------------------------------------- the gateway


def test_four_claude_code_calls_run_at_once_and_never_a_fifth():
    assert getattr(gateway_module, "CLAUDE_CODE_CONCURRENCY", None) == 4
    runner = TimedRunner(lambda args, stdin: cli_reply("{}"), hold=lambda stdin: 0.2)
    gateway = gateway_of(runner)
    in_threads(lambda i: gateway.complete(SONNET, MESSAGES, 1000), 10)
    assert len(runner.calls) == 10
    assert runner.most == 4


def test_the_limit_holds_across_every_gateway_of_the_process():
    runner = TimedRunner(lambda args, stdin: cli_reply("{}"), hold=lambda stdin: 0.2)
    gateways = [gateway_of(runner) for _ in range(3)]
    in_threads(lambda i: gateways[i % 3].complete(SONNET, MESSAGES, 1000), 9)
    assert len(runner.calls) == 9
    assert runner.most == 4


def test_a_limit_of_one_sends_one_call_at_a_time():
    runner = TimedRunner(lambda args, stdin: cli_reply("{}"), hold=lambda stdin: 0.05)
    gateway = gateway_of(runner, concurrency=1)
    in_threads(lambda i: gateway.complete(SONNET, MESSAGES, 1000), 4)
    assert len(runner.calls) == 4
    assert runner.most == 1


def test_call_starts_are_staggered_by_the_pause_while_calls_overlap():
    runner = TimedRunner(lambda args, stdin: cli_reply("{}"), hold=lambda stdin: 0.6)
    gateway = gateway_of(runner, pause=0.1)
    in_threads(lambda i: gateway.complete(SONNET, MESSAGES, 1000), 4)
    starts = sorted(runner.started)
    assert all(later - earlier >= 0.09 for earlier, later in zip(starts, starts[1:]))
    assert runner.most == 4


def test_a_calls_seconds_are_its_own_and_not_its_wait_for_a_slot():
    runner = TimedRunner(lambda args, stdin: cli_reply("{}"), hold=lambda stdin: 0.2)
    gateway = gateway_of(runner, concurrency=1)
    took: list[float] = []
    in_threads(lambda i: took.append(gateway.complete(SONNET, MESSAGES, 1000).seconds), 3)
    assert max(took) < 0.35


# ---------------------------------------------------------------- the ledger and the cap


def test_batches_booking_at_once_lose_no_row_and_keep_the_balance(tmp_path, monkeypatch):
    ledger = write_ledger(tmp_path / "L.md")
    real_rows = Ledger.rows

    def slow_rows(self):
        found = real_rows(self)
        time.sleep(0.05)
        return found

    monkeypatch.setattr(Ledger, "rows", slow_rows)
    barrier = threading.Barrier(4)

    def book(i):
        with ledger.batch(f"s{i}", 8, PRICED, 10, 10) as batch:
            batch.record(Completion("x", 1000, 100, 0.0, PRICED, cost=0.01))
            barrier.wait()

    in_threads(book, 4)
    rows = real_rows(ledger)[1:]
    assert sorted(row["sample"] for row in rows) == ["s0", "s1", "s2", "s3"]
    balance = 50.0
    for row in rows:
        balance = round(balance - row["dollars"], 4)
        assert row["balance"] == balance
    assert balance == pytest.approx(49.96)


def test_batches_open_at_once_cannot_pass_the_cap_together(tmp_path, monkeypatch):
    monkeypatch.setitem(PHASE_CAPS, 8, 0.05)
    ledger = write_ledger(tmp_path / "L.md")
    # each batch estimates $0.03 on its own, under the cap; two open at once would pass it
    tokens_out = round(0.03 / (gateway_module.PRICES[PRICED][1] / 1_000_000))
    first = ledger.batch("s", 8, PRICED, 0, tokens_out)
    first.__enter__()
    with pytest.raises(CapExceeded):
        with ledger.batch("s", 8, PRICED, 0, tokens_out):
            pass
    first.__exit__(None, None, None)
    assert len(ledger.rows()) == 2


def test_the_cap_refuses_before_any_call_while_claude_code_calls_are_in_flight(tmp_path, monkeypatch):
    monkeypatch.setitem(PHASE_CAPS, 8, 0.01)
    ledger = write_ledger(tmp_path / "L.md")
    runner = TimedRunner(lambda args, stdin: cli_reply("{}"), hold=lambda stdin: 0.3)
    gateway = gateway_of(runner)
    booked = []

    def free(i):
        with ledger.batch("free", 8, SONNET, 100_000, 100_000) as batch:
            batch.record(gateway.complete(SONNET, MESSAGES, 1000))
        booked.append(i)

    threads = [threading.Thread(target=free, args=(i,)) for i in range(4)]
    for thread in threads:
        thread.start()
    time.sleep(0.05)
    with pytest.raises(CapExceeded):
        with ledger.batch("paid", 8, PRICED, 1_000_000, 1_000_000):
            raise AssertionError("no call is made past the cap")
    for thread in threads:
        thread.join()
    rows = ledger.rows()[1:]
    assert [row["sample"] for row in rows] == ["free"] * 4
    assert all(row["dollars"] == 0.0 for row in rows)


# ---------------------------------------------------------------- the notes

LINES = [f"Clause {n}: the borrower shall pay {n} percent on a change of control." for n in range(8)]
SPLIT_A = "The borrower shall repay the loan on a change of control."
SPLIT_B = "The lender may call the loan on any default."


def notes_room(tmp_path: Path) -> tuple[Path, Path]:
    """Eight documents of one line each, one that is cut off whole and noted in halves, and one
    whose first reply quotes words it does not carry and is right on the re-ask."""
    room = tmp_path / "room"
    room.mkdir()
    for n, line in enumerate(LINES):
        (room / f"d{n}.txt").write_text(f"Agreement {n}.\n{line}\n", encoding="utf-8")
    (room / "e.txt").write_text(f"Loan agreement.\n{SPLIT_A}\n\nDefault.\n{SPLIT_B}\n", encoding="utf-8")
    return room, tmp_path / "run"


def notes_answer(args, stdin):
    if "THE NEXT MESSAGE" in stdin:
        return cli_reply(note_json("a deed", LINES[3]), model="claude-haiku-5-5")
    if SPLIT_A in stdin and SPLIT_B in stdin:
        return cli_reply("", model="claude-haiku-5-5", output=6000, turns=2)
    if SPLIT_A in stdin:
        return cli_reply(note_json("a loan", SPLIT_A), model="claude-haiku-5-5")
    if SPLIT_B in stdin:
        return cli_reply(note_json("a loan", SPLIT_B), model="claude-haiku-5-5")
    for n, line in enumerate(LINES):
        if line in stdin:
            quote = "Words this deed does not carry." if n == 3 else line
            return cli_reply(note_json(f"deed {n}", quote), model="claude-haiku-5-5", output=100 + n)
    raise AssertionError(stdin)


def notes_hold(stdin):
    """The first documents take longest, so the calls finish in another order than they start."""
    for n, line in enumerate(LINES):
        if line in stdin:
            return 0.04 * (len(LINES) - n)
    return 0.01


def without_seconds(value):
    if isinstance(value, dict):
        return {key: without_seconds(item) for key, item in value.items() if key != "seconds"}
    if isinstance(value, list):
        return [without_seconds(item) for item in value]
    return value


def outputs(run_dir: Path) -> dict:
    found = {}
    for path in sorted((run_dir / "notes").glob("*.json")):
        found[f"notes/{path.name}"] = without_seconds(json.loads(path.read_text(encoding="utf-8")))
    for path in sorted((run_dir / "notes-raw").glob("*")):
        found[f"notes-raw/{path.name}"] = path.read_text(encoding="utf-8")
    found["notes-verify.jsonl"] = (run_dir / "notes-verify.jsonl").read_text(encoding="utf-8")
    found["notes-summary.json"] = without_seconds(
        json.loads((run_dir / "notes-summary.json").read_text(encoding="utf-8")))
    return found


def printed(text: str) -> list[str]:
    return [line for line in text.splitlines() if "items kept" in line or "note dropped" in line]


def run_notes(tmp_path, name, concurrency, capsys):
    room = tmp_path / "room"
    if not room.exists():
        notes_room(tmp_path)
    run_dir = tmp_path / name
    ingest.ingest(room, run_dir)
    capsys.readouterr()
    runner = TimedRunner(notes_answer, hold=notes_hold)
    ledger = write_ledger(tmp_path / f"{name}.md")
    code = notes.main([str(room), str(run_dir), "--model", HAIKU, "--phase", "8"],
                      gateway=gateway_of(runner, concurrency=concurrency), ledger=ledger)
    assert code == 0
    return run_dir, runner, ledger, printed(capsys.readouterr().out)


def test_notes_four_at_once_write_what_one_at_a_time_writes_in_the_same_order(tmp_path, capsys):
    serial_dir, serial, serial_ledger, serial_lines = run_notes(tmp_path, "serial", 1, capsys)
    par_dir, par, par_ledger, par_lines = run_notes(tmp_path, "par", 4, capsys)

    assert serial.most == 1
    assert par.most == 4
    started = [call["stdin"] for call in par.calls]
    assert par.finished != started  # the calls came back out of order
    assert len(par.calls) == len(serial.calls) == 8 + 1 + 3  # eight, a re-ask, e.txt whole then halves

    assert outputs(par_dir) == outputs(serial_dir)
    assert par_lines == serial_lines
    assert [line.split(":")[0] for line in par_lines] == [f"d{n}.txt" for n in range(8)] + ["e.txt"]
    deed = json.loads((par_dir / "notes" / "d3.txt.json").read_text(encoding="utf-8"))
    assert [flag["quote"] for flag in deed["flags"]] == [LINES[3]]
    loan = json.loads((par_dir / "notes" / "e.txt.json").read_text(encoding="utf-8"))
    assert [flag["quote"] for flag in loan["flags"]] == [SPLIT_A, SPLIT_B]


def test_notes_four_at_once_book_one_row_with_every_calls_tokens(tmp_path, capsys):
    _, serial, serial_ledger, _ = run_notes(tmp_path, "serial", 1, capsys)
    _, par, par_ledger, _ = run_notes(tmp_path, "par", 4, capsys)
    assert par.most == 4
    serial_rows = serial_ledger.rows()[1:]
    par_rows = par_ledger.rows()[1:]
    assert len(par_rows) == len(serial_rows) == 1
    row = par_rows[0]
    assert (row["model"], row["dollars"], row["balance"]) == (HAIKU, 0.0, 50.0)
    out = sum(json.loads(cli_reply_of(par, call))["usage"]["output_tokens"] for call in par.calls)
    assert row["tokens_out"] == out
    assert row["tokens_in"] == 1000 * len(par.calls)
    assert (row["tokens_in"], row["tokens_out"]) == (serial_rows[0]["tokens_in"], serial_rows[0]["tokens_out"])


def cli_reply_of(runner, call) -> str:
    return runner.answer(call["args"], call["stdin"])


# ---------------------------------------------------------------- the group step


def test_the_group_calls_run_at_once_and_tree_json_is_what_one_at_a_time_writes(tmp_path):
    room, run_dir = small_room(tmp_path)
    built = {}
    most = {}
    for concurrency in (1, 4):
        runner = TimedRunner(tree_answer, hold=lambda stdin: 0.4 if "id: a.txt" in stdin else 0.1)
        built[concurrency] = tree.tree(room, run_dir, gateway=gateway_of(runner, concurrency=concurrency),
                                       ledger=write_ledger(tmp_path / f"L{concurrency}.md"), model=SONNET, budget=1)
        most[concurrency] = runner.most
    assert len(built[4]["groups"]) == 3
    assert (most[1], most[4]) == (1, 3)
    assert built[4] == built[1]


# ---------------------------------------------------------------- the writer

FIRST = (
    "## Executive summary\n\nRecommendation: proceed.\n\n"
    "## Findings ranked by materiality\n\n"
    "1. The loan is repaid on a change of control [a.txt | a.txt#l1].\n\n"
    "## The most material issue quantified\n\nNone [a.txt | a.txt#l1].\n"
)
OPEN = "## Open items\n\n1. None [c.txt | c.txt#l1].\n"
TAILS = {
    "a.txt": "## Lesser issues\n\n1. None [a.txt | a.txt#l1].\n",
    "b.txt": "## Lesser issues\n\n1. The lease [b.txt | b.txt#l1].\n",
    "c.txt": "## Lesser issues\n\n1. The bonus [c.txt | c.txt#l1].\n",
}


def writer_answer(args, stdin):
    if system_of(args).startswith(write.FULL_TAIL_PROMPT):
        mine = stdin.split(write.YOUR_DOCUMENTS, 1)[1]
        doc = next(doc for doc in TAILS if f"- {doc}" in mine)
        return cli_reply(TAILS[doc])
    return cli_reply(FIRST + "\n" + OPEN)


def writer_hold(stdin):
    if write.YOUR_DOCUMENTS not in stdin:
        return 0.0
    mine = stdin.split(write.YOUR_DOCUMENTS, 1)[1]
    return {"a.txt": 0.4, "b.txt": 0.2, "c.txt": 0.05}[next(doc for doc in TAILS if f"- {doc}" in mine)]


def test_the_lesser_issue_parts_are_written_at_once_and_the_report_is_what_one_at_a_time_writes(tmp_path, monkeypatch):
    monkeypatch.setattr(write, "TAIL_ROWS", 1)
    reports = {}
    most = {}
    for concurrency in (1, 4):
        base = tmp_path / str(concurrency)
        base.mkdir()
        room, run_dir = small_room(base)
        (run_dir / tree.TREE_FILE).write_text(json.dumps(built_tree()), encoding="utf-8")
        runner = TimedRunner(writer_answer, hold=writer_hold)
        code = write.main([str(room), str(run_dir), "--tree", "--phase", "8", "--model", SONNET],
                          gateway=gateway_of(runner, concurrency=concurrency),
                          ledger=write_ledger(base / "L.md"))
        assert code == 0
        assert len(runner.calls) == 4
        most[concurrency] = runner.most
        reports[concurrency] = (
            (run_dir / "report.md").read_text(encoding="utf-8"),
            (run_dir / "verify.json").read_text(encoding="utf-8"),
        )
    assert (most[1], most[4]) == (1, 3)
    assert reports[4] == reports[1]
    assert (
        "## Lesser issues\n\n1. None [a.txt | a.txt#l1].\n2. The lease [b.txt | b.txt#l1].\n"
        "3. The bonus [c.txt | c.txt#l1].\n"
    ) in reports[4][0]
