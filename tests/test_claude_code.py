"""Issue #160: the Claude Code backend, which sends a model call to headless `claude -p` on the
founder's subscription in place of OpenRouter, and the tree writer's two levels on it.

Every test here is free: the subprocess is a fake runner and the ledger is a temporary file.
"""

import json
import threading
import time
from pathlib import Path

import pytest

from rlm import cli, ingest, notes, tree, write
from rlm.gateway import (
    API_EQUIVALENT,
    CLAUDE_CODE_MODELS,
    CLAUDE_EFFORT,
    PRICES,
    REASONING,
    ClaudeCode,
    ClaudeCodeError,
    Gateway,
    NoReply,
    WrongModel,
    api_price,
    price,
)
from test_phase8_command import copy_room, write_ledger
from test_pick import small_room
from test_tree import LOAN, QUOTES, built_tree, ids_in

SONNET = "claude-code/claude-sonnet-5-5"
HAIKU = "claude-code/claude-haiku-5-5"
REPO = Path(__file__).resolve().parents[1]


def cli_reply(result, model="claude-sonnet-5-5", inputs=(900, 50, 50), output=120, is_error=False, turns=None) -> str:
    fresh, read, created = inputs
    reply = {
        "type": "result",
        "is_error": is_error,
        "result": result,
        "usage": {"input_tokens": fresh, "cache_read_input_tokens": read,
                  "cache_creation_input_tokens": created, "output_tokens": output},
        "modelUsage": {model: {"inputTokens": fresh, "outputTokens": output}},
    }
    if turns is not None:
        reply["num_turns"] = turns
    return json.dumps(reply)


class FakeRunner:
    """Stands in for the subprocess: records every call and answers with answer(args, stdin)."""

    def __init__(self, answer, code=0, hold=0.0):
        self.answer = answer
        self.code = code
        self.hold = hold
        self.calls: list[dict] = []
        self.active = 0
        self.most = 0
        self._lock = threading.Lock()

    def __call__(self, args, cwd, env, stdin):
        with self._lock:
            self.active += 1
            self.most = max(self.most, self.active)
            self.calls.append({"args": list(args), "cwd": Path(cwd), "env": dict(env), "stdin": stdin,
                               "cwd_empty": not any(Path(cwd).iterdir())})
        time.sleep(self.hold)
        with self._lock:
            self.active -= 1
        return self.code, self.answer(args, stdin), ""


def system_of(args) -> str:
    return args[args.index("--system-prompt") + 1]


def gateway_with(runner) -> Gateway:
    return Gateway(api_key="k", transport=None, rate_limit_waits=(), claude_code=ClaudeCode(runner=runner, pause=0.0))


MESSAGES = [{"role": "system", "content": "SYSTEM WORDS"}, {"role": "user", "content": "USER WORDS"}]


# ---------------------------------------------------------------- the backend


def test_a_claude_code_model_is_sent_to_headless_claude_with_no_tools_from_an_empty_folder(monkeypatch):
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("CLAUDE_CODE_ENTRYPOINT", "cli")
    runner = FakeRunner(lambda args, stdin: cli_reply('{"a": 1}'))
    completion = gateway_with(runner).complete(SONNET, MESSAGES, max_tokens=1000)

    call = runner.calls[0]
    args = call["args"]
    assert args[:2] == ["claude", "-p"]
    assert args[args.index("--output-format") + 1] == "json"
    assert args[args.index("--model") + 1] == "claude-sonnet-5-5"
    assert args[args.index("--tools") + 1] == ""
    assert args[args.index("--setting-sources") + 1] == ""
    for flag in ("--strict-mcp-config", "--disable-slash-commands", "--no-session-persistence"):
        assert flag in args
    assert system_of(args) == "SYSTEM WORDS"
    assert call["stdin"] == "USER WORDS"
    assert call["cwd_empty"]
    assert REPO not in call["cwd"].resolve().parents
    assert not call["cwd"].exists()
    assert "CLAUDECODE" not in call["env"]
    assert [name for name in call["env"] if name.startswith("CLAUDE_CODE_")] == ["CLAUDE_CODE_MAX_OUTPUT_TOKENS"]

    assert completion.text == '{"a": 1}'
    assert completion.tokens_in == 1000
    assert completion.tokens_out == 120
    assert completion.model == SONNET


@pytest.mark.parametrize("model, effort", [(SONNET, "medium"), (HAIKU, "low")])
def test_every_claude_code_call_asks_for_its_models_effort(model, effort):
    """Sonnet 5.5 thinks at high effort unless told otherwise, and its thinking counts against
    the reply cap, so a call that leaves the effort unset can be cut off before it answers.
    Sonnet is asked for medium and Haiku 5.5, which writes the notes, for low."""
    runner = FakeRunner(lambda args, stdin: cli_reply('{"a": 1}', model=CLAUDE_CODE_MODELS[model]))
    gateway_with(runner).complete(model, MESSAGES, max_tokens=1000)

    args = runner.calls[0]["args"]
    assert args.count("--effort") == 1
    assert args[args.index("--effort") + 1] == effort


def test_every_claude_code_model_has_an_effort_and_sonnet_on_open_router_keeps_medium():
    assert set(CLAUDE_CODE_MODELS) <= set(CLAUDE_EFFORT)
    assert CLAUDE_EFFORT[SONNET] == "medium"
    assert CLAUDE_EFFORT[HAIKU] == "low"
    assert REASONING["anthropic/claude-sonnet-5.5"] == {"effort": "medium"}


def test_haiku_5_5_is_a_claude_code_model_and_its_reply_must_name_it():
    assert CLAUDE_CODE_MODELS[HAIKU] == "claude-haiku-5-5"
    runner = FakeRunner(lambda args, stdin: cli_reply('{"a": 1}', model="claude-haiku-5-5"))
    completion = gateway_with(runner).complete(HAIKU, MESSAGES, max_tokens=1000)
    args = runner.calls[0]["args"]
    assert args[args.index("--model") + 1] == "claude-haiku-5-5"
    assert completion.model == HAIKU and completion.text == '{"a": 1}'
    sonnet = FakeRunner(lambda args, stdin: cli_reply("{}", model="claude-sonnet-5-5"))
    with pytest.raises(WrongModel):
        gateway_with(sonnet).complete(HAIKU, MESSAGES, max_tokens=1000)


def test_a_reply_continued_past_its_cap_is_a_cut_off_no_reply():
    """The note stage halves a piece only on a cut off NoReply, so a reply that ran past its cap
    on Claude Code says it was cut off, as OpenRouter's length finish reason does."""
    runner = FakeRunner(lambda args, stdin: cli_reply('{"a": 1}', model="claude-haiku-5-5", turns=2))
    with pytest.raises(NoReply) as raised:
        gateway_with(runner).complete(HAIKU, MESSAGES, max_tokens=1000)
    assert raised.value.cut_off is True
    assert (raised.value.tokens_in, raised.value.tokens_out) == (1000, 120)


def test_a_reply_from_any_model_but_sonnet_5_5_is_refused():
    runner = FakeRunner(lambda args, stdin: cli_reply("{}", model="claude-haiku-4-5"))
    with pytest.raises(WrongModel):
        gateway_with(runner).complete(SONNET, MESSAGES, max_tokens=1000)


def test_a_failed_call_raises_and_an_empty_reply_is_no_reply():
    failed = FakeRunner(lambda args, stdin: cli_reply("", is_error=True))
    with pytest.raises(ClaudeCodeError):
        gateway_with(failed).complete(SONNET, MESSAGES, max_tokens=1000)
    exited = FakeRunner(lambda args, stdin: "", code=1)
    with pytest.raises(ClaudeCodeError):
        gateway_with(exited).complete(SONNET, MESSAGES, max_tokens=1000)
    empty = FakeRunner(lambda args, stdin: cli_reply(""))
    with pytest.raises(NoReply):
        gateway_with(empty).complete(SONNET, MESSAGES, max_tokens=1000)


def test_a_json_reply_in_a_code_fence_comes_back_as_the_object_alone():
    runner = FakeRunner(lambda args, stdin: cli_reply('Here it is:\n```json\n{"findings": []}\n```'))
    assert gateway_with(runner).complete(SONNET, MESSAGES, max_tokens=1000).text == '{"findings": []}'
    prose = FakeRunner(lambda args, stdin: cli_reply("## Executive summary\n\nText {x}."))
    assert gateway_with(prose).complete(SONNET, MESSAGES, max_tokens=1000, json=False).text == "## Executive summary\n\nText {x}."


def test_a_second_turn_carries_the_first_reply_and_the_new_ask_on_stdin():
    runner = FakeRunner(lambda args, stdin: cli_reply("{}"))
    messages = [*MESSAGES, {"role": "assistant", "content": "FIRST REPLY"}, {"role": "user", "content": "ASK AGAIN"}]
    gateway_with(runner).complete(SONNET, messages, max_tokens=1000)
    stdin = runner.calls[0]["stdin"]
    assert stdin.index("USER WORDS") < stdin.index("FIRST REPLY") < stdin.index("ASK AGAIN")
    assert system_of(runner.calls[0]["args"]) == "SYSTEM WORDS"


def test_calls_are_sent_one_at_a_time():
    runner = FakeRunner(lambda args, stdin: cli_reply("{}"), hold=0.05)
    gateway = gateway_with(runner)
    threads = [threading.Thread(target=gateway.complete, args=(SONNET, MESSAGES, 1000)) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(runner.calls) == 4
    assert runner.most == 1


def test_the_subscription_model_costs_nothing_in_cash_and_its_api_price_is_kept_apart():
    # the OpenRouter table and its live check are left alone; the subscription has its own
    assert SONNET not in PRICES
    assert price(SONNET, 1_000_000, 1_000_000) == 0.0
    assert API_EQUIVALENT[SONNET] == (2.0, 10.0)
    assert api_price(SONNET, 1_000_000, 100_000) == pytest.approx(3.0)
    assert api_price("z-ai/glm-5.3-flash", 1_000_000, 0) == pytest.approx(PRICES["z-ai/glm-5.3-flash"][0])
    assert tree.CONTEXT_WINDOWS[SONNET] == 1_000_000


def test_haiku_5_5_costs_nothing_in_cash_and_its_api_price_is_the_lower_tier():
    """The API price is read on a run's totals, so the tier for a prompt over 100,000 tokens is
    never applied; a note call carries at most PIECE_LIMIT characters of document."""
    assert HAIKU not in PRICES
    assert price(HAIKU, 1_000_000, 1_000_000) == 0.0
    assert API_EQUIVALENT[HAIKU] == (0.10, 0.50)
    assert api_price(HAIKU, 1_000_000, 1_000_000) == pytest.approx(0.60)


# ---------------------------------------------------------------- the tree on it


def tree_answer(args, stdin):
    if "buy-side diligence lead" in system_of(args) and "findings" in system_of(args):
        docs = [line[4:].strip() for line in stdin.splitlines() if line.startswith("id: ")]
        return cli_reply(json.dumps({"findings": [{"doc": d, "finding": f"finding of {d}", "quote": QUOTES[d]} for d in docs]}))
    return cli_reply("")


def test_the_middle_level_on_sonnet_books_zero_dollars_and_keeps_the_api_price_in_tree_json(tmp_path, capsys):
    room, run_dir = small_room(tmp_path)
    ledger = write_ledger(tmp_path / "LEDGER.md")
    runner = FakeRunner(tree_answer)
    built = tree.tree(room, run_dir, gateway=gateway_with(runner), ledger=ledger, model=SONNET)

    assert len(runner.calls) == 1
    assert [item["doc"] for item in built["groups"][0]["findings"]] == ["a.txt", "b.txt", "c.txt"]
    row = ledger.rows()[-1]
    assert row["model"] == SONNET
    assert (row["tokens_in"], row["tokens_out"]) == (1000, 120)
    assert float(row["dollars"]) == 0.0
    written = json.loads((run_dir / tree.TREE_FILE).read_text(encoding="utf-8"))
    assert written["model"] == SONNET
    assert (written["tokens_in"], written["tokens_out"]) == (1000, 120)
    assert written["api_dollars"] == pytest.approx(api_price(SONNET, 1000, 120))
    assert "$0.0000" in capsys.readouterr().out


def test_the_writer_on_sonnet_in_tree_mode_records_its_api_price_in_tree_json(tmp_path):
    room, run_dir = small_room(tmp_path)
    (run_dir / tree.TREE_FILE).write_text(json.dumps(built_tree()), encoding="utf-8")
    report = (
        "## Executive summary\n\nRecommendation: proceed.\n\n"
        f'The loan says "{LOAN[:-1]}" [a.txt | a.txt#l1].\n\n'
        "## Findings ranked by materiality\n\n"
        f'The loan is repaid on a change of control, "{LOAN[:-1]}" [a.txt | a.txt#l1].\n\n'
        "## The most material issue quantified\n\nNone [a.txt | a.txt#l1].\n\n"
        "## Lesser issues\n\nNone [c.txt | c.txt#l1].\n\n## Open items\n\nNone [c.txt | c.txt#l1].\n"
    )
    head, tail = report.split("## Lesser issues")
    runner = FakeRunner(lambda args, stdin: cli_reply(
        "## Lesser issues" + tail if system_of(args).startswith(write.FULL_TAIL_PROMPT) else head))
    ledger = write_ledger(tmp_path / "L.md")
    code = write.main([str(room), str(run_dir), "--tree", "--phase", "8", "--model", SONNET],
                      gateway=gateway_with(runner), ledger=ledger)
    assert code == 0
    assert system_of(runner.calls[0]["args"]).startswith(write.FULL_PROMPT)
    assert runner.calls[0]["stdin"] == (run_dir / "digest.md").read_text(encoding="utf-8")
    assert float(ledger.rows()[-1]["dollars"]) == 0.0
    written = json.loads((run_dir / tree.TREE_FILE).read_text(encoding="utf-8"))
    assert written["writer"]["model"] == SONNET
    assert (written["writer"]["tokens_in"], written["writer"]["tokens_out"]) == (2000, 240)
    assert written["writer"]["api_dollars"] == pytest.approx(api_price(SONNET, 2000, 240))


# ---------------------------------------------------------------- the command


def test_the_command_names_the_model_of_each_level_and_defaults_to_today():
    args = cli.parse_args(["run", "room", "--write", "tree"])
    assert args.middle_model is None and args.writer_model is None
    found = cli.resolve_settings(args)
    assert found.group == tree.DEFAULT_MODEL == "z-ai/glm-5.3-flash"
    assert found.writer == write.DEFAULT_MODEL == "z-ai/glm-5.3"
    args = cli.parse_args(["run", "room", "--write", "tree", "--middle-model", SONNET, "--writer-model", SONNET])
    assert (args.middle_model, args.writer_model) == (SONNET, SONNET)
    found = cli.resolve_settings(args)
    assert (found.group, found.writer) == (SONNET, SONNET)


def test_the_command_runs_both_levels_on_sonnet(tmp_path):
    room = copy_room(tmp_path)
    run_dir = tmp_path / "run"

    def answer(args, stdin):
        system = system_of(args)
        if system.startswith(tree.TREE_PROMPT[:60]):
            rows, doc = [], None
            for line in stdin.splitlines():
                if line.startswith("id: "):
                    doc = line[4:].strip()
                elif line.startswith("quote: ") and doc:
                    rows.append({"doc": doc, "finding": f"finding of {doc}", "quote": line[7:]})
                    doc = None
            return cli_reply(json.dumps({"findings": rows}))
        from test_phase8_command import FAKE_REPORT
        return cli_reply(FAKE_REPORT)

    runner = FakeRunner(answer)
    # the notes are made on OpenRouter as before, by the fake room transport
    from test_phase8_command import RoomTransport
    gateway = Gateway(api_key="k", transport=RoomTransport(), rate_limit_waits=(),
                      claude_code=ClaudeCode(runner=runner, pause=0.0))
    ledger = write_ledger(tmp_path / "L.md")
    argv = ["run", str(room), "--out", str(run_dir), "--yes", "--phase", "8", "--write", "tree",
            "--middle-model", SONNET, "--writer-model", SONNET]
    code = cli.main(argv, gateway=gateway, ledger=ledger)

    assert code == 0, (run_dir / "run.json").read_text(encoding="utf-8")
    assert len(runner.calls) == 3  # the group call, then the writer's two
    sonnet_rows = [row for row in ledger.rows() if row["model"] == SONNET]
    assert len(sonnet_rows) == 2
    assert all(float(row["dollars"]) == 0.0 for row in sonnet_rows)
    written = json.loads((run_dir / tree.TREE_FILE).read_text(encoding="utf-8"))
    assert written["model"] == SONNET
    assert written["writer"]["model"] == SONNET


# ---------------------------------------------------------------- the notes on Haiku 5.5

LOAN_LINE = "The borrower shall repay the loan on a change of control."
CALL_LINE = "The lender may call the loan on any default."
RENT_LINE = "Rent is payable monthly in advance."


def note_json(what: str, quote: str) -> str:
    return json.dumps({"what": what, "flags": [{"flag": "risk", "quote": quote, "consequence": "c", "about": []}],
                       "figures": [], "cross_references": [], "concealed": []})


def notes_answer(args, stdin):
    """a.txt whole runs past its cap, and each of its halves is answered; b.txt first quotes
    words it does not carry, and is answered right on the re-ask."""
    if "THE NEXT MESSAGE" in stdin:
        return cli_reply(note_json("a lease", RENT_LINE), model="claude-haiku-5-5")
    if LOAN_LINE in stdin and CALL_LINE in stdin:
        return cli_reply("", model="claude-haiku-5-5", output=6000, turns=2)
    if LOAN_LINE in stdin:
        return cli_reply(note_json("a loan", LOAN_LINE), model="claude-haiku-5-5")
    if CALL_LINE in stdin:
        return cli_reply(note_json("a loan", CALL_LINE), model="claude-haiku-5-5")
    return cli_reply(note_json("a lease", "Rent is free for ever."), model="claude-haiku-5-5")


def test_the_notes_run_on_haiku_through_claude_code_end_to_end(tmp_path):
    """A JSON reply, a re-ask, a piece cut off and halved, every call asked of Haiku 5.5 at low
    effort, and the pass booked at $0.00."""
    room = tmp_path / "room"
    room.mkdir()
    (room / "a.txt").write_text(f"Loan agreement.\n{LOAN_LINE}\n\nDefault.\n{CALL_LINE}\n", encoding="utf-8")
    (room / "b.txt").write_text(f"Lease of office.\n{RENT_LINE}\n", encoding="utf-8")
    run_dir = tmp_path / "run"
    ingest.ingest(room, run_dir)
    runner = FakeRunner(notes_answer)
    ledger = write_ledger(tmp_path / "L.md")

    code = notes.main([str(room), str(run_dir), "--model", HAIKU, "--phase", "8"],
                      gateway=gateway_with(runner), ledger=ledger)

    assert code == 0
    assert len(runner.calls) == 5  # a.txt whole, then its two halves; b.txt, then its re-ask
    for call in runner.calls:
        args = call["args"]
        assert args[args.index("--model") + 1] == "claude-haiku-5-5"
        assert args[args.index("--effort") + 1] == "low"
    loan = json.loads((run_dir / "notes" / "a.txt.json").read_text(encoding="utf-8"))
    assert [flag["quote"] for flag in loan["flags"]] == [LOAN_LINE, CALL_LINE]
    assert [flag["anchor"] for flag in loan["flags"]] == ["a.txt#l1", "a.txt#l4"]
    assert loan["usage"]["calls"] == 3 and loan["usage"]["dollars"] == 0.0
    lease = json.loads((run_dir / "notes" / "b.txt.json").read_text(encoding="utf-8"))
    assert [flag["quote"] for flag in lease["flags"]] == [RENT_LINE]
    assert lease["usage"]["calls"] == 2
    summary = json.loads((run_dir / "notes-summary.json").read_text(encoding="utf-8"))
    assert (summary["noted"], summary["dropped"], summary["dollars"]) == (2, 0, 0.0)
    row = ledger.rows()[-1]
    assert row["model"] == HAIKU
    assert float(row["dollars"]) == 0.0
    assert int(row["tokens_out"]) == 6000 + 4 * 120
