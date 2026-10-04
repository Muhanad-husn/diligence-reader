"""Phase 8 slice 04: the web page in web/, driven by Playwright against a real local server.

The tests at $0 serve the app with uvicorn on a free localhost port, a runs folder under
tmp_path and the real LocalRunner. The child the runner starts is the real command on
test_phase8_command's RoomTransport, so no model call leaves the machine: a note call gets a
fake note, a write call gets PAGE_REPORT, a run on BAD_KEY is refused the way OpenRouter
refuses a bad key, and a run on CRASH_KEY raises inside the write call, which the command
records as `unexpected`. PAGE_REPORT quotes sample 3's own lines and cites them, so the run
verifies and its report carries every planted fact of sample 3's key.

The browser reaches only the local server. openrouter.ai and api.github.com are faked with
page.route, and every other host is aborted and recorded, so a test fails when the page asks
anything else.
"""

import base64
import hashlib
import io
import json
import sys
import threading
import time
import zipfile
from pathlib import Path
from urllib.parse import parse_qs, unquote_plus, urlparse

import pytest
import uvicorn
from playwright.sync_api import Page, expect

from app.events import FIXES
from app.main import create_app
from app.runner import LocalRunner
from conftest import ROOT
from rlm import __version__, cli
from rlm.grade import measure_recall
from rlm.key import load_key
from test_phase8_api import BAD_KEY, GOOD_KEY, SLOW_KEY, SRC, TESTS, free_port
from test_phase8_command import ROOM, copy_room

WEB = ROOT / "web"
CRASH_KEY = "sk-or-v1-test-CRASHKEY-0123456789abcdef"
SIGNED_KEY = "sk-or-v1-test-SIGNEDIN-0123456789abcdef"
REPO = "Muhanad-husn/diligence-reader"
LATEST = f"https://api.github.com/repos/{REPO}/releases/latest"
RUN_TIMEOUT = 90_000
EXPORTS = (("md", "report.md"), ("docx", "report.docx"), ("pdf", "report.pdf"), ("csv", "evidence.csv"))

# A report quoting sample 3's own lines with their anchors: it passes the verifier on a fake
# run and carries every planted fact of sample 3's key.
PAGE_REPORT = """## Executive summary

Recommendation: reprice or condition the deal, because the seller's growth claim is contradicted by its own workbook.

The risk register flags that "The CIM states 18.0% year-over-year revenue growth, while the generated revenue workbook shows 2024 revenue of $22.2M and 2025 revenue of $24.8M, or 11.7% growth" [risks/risk_register.md | risks/risk_register.md#l5].

## Findings ranked by materiality

CloudDent Practice Systems is the practice management software vendor at "$0.48M annual spend, renewal: 2025-09-30, risk: high" [company_profile.md | company_profile.md#l33].

The CIM describes 2025 as a breakout year, citing "18.0% revenue growth, improved provider utilization, and higher implant attach rates" [cim.md | cim.md#l16].

The workbook shows "YoY Growth 2024-2025" of 11.7% [revenue_summary.xlsx | revenue_summary.xlsx#Annual Totals!A4].

The board update confirms "Total 2025 revenue: $24.8M" [board_materials/q1-board-update.md | board_materials/q1-board-update.md#l14].

CIM growth 18.0% against workbook growth 11.7%, "Management describes 2025 as a breakout year, citing 18.0% revenue growth, improved provider utilization, and higher implant attach rates." and "YoY Growth 2024-2025 | 11.7%" [cim.md | cim.md#l16] [revenue_summary.xlsx | revenue_summary.xlsx#Annual Totals!A4].

The largest payor relationship is Buckeye Family Health Plan at "$5.8M" annual revenue with renewal on 2026-03-31 [cim.md | cim.md#l24].

The second largest payor is Midwest Dental Benefits Network at "$4.2M" with renewal on 2025-12-31 [cim.md | cim.md#l31].

The risk register states "The two largest insurance payor relationships represent $10.0M of 2025 revenue" [risks/risk_register.md | risks/risk_register.md#l17].

Every payor contract file carries the open item to "Confirm whether renewal terms preserve current reimbursement rates" [customer_contracts/buckeye-family-health-plan.md | customer_contracts/buckeye-family-health-plan.md#l18].

The same open item appears for Midwest Dental Benefits Network [customer_contracts/midwest-dental-benefits-network.md | customer_contracts/midwest-dental-benefits-network.md#l18].

The CloudDent vendor file describes the system as "Single system of record for scheduling, claims, and treatment plans." [vendor_agreements/clouddent-practice-systems.md | vendor_agreements/clouddent-practice-systems.md#l14].

The board directs management to "Review CloudDent renewal terms before 2025-09-30" [board_materials/q1-board-update.md | board_materials/q1-board-update.md#l18].

The risk register states "CloudDent is the system of record for scheduling, claims, and treatment plans" [risks/risk_register.md | risks/risk_register.md#l11].

## The most material issue quantified

The CIM claims "18.0% revenue growth" [cim.md | cim.md#l16].

The workbook shows "YoY Growth 2024-2025" of 11.7% [revenue_summary.xlsx | revenue_summary.xlsx#Annual Totals!A4].

Calculation: 18.0% - 11.7% = 6.3 percentage points.

## Lesser issues

The CIM notes on Midwest "Strong volume but slower-than-average claims payment cycle" [cim.md | cim.md#l31].

## Open items

The CIM's own diligence note says to "compare this narrative with `revenue_summary.xlsx` before relying on the stated growth rate" [cim.md | cim.md#l18].
"""

# The child the server's LocalRunner starts: the real command on a fake transport.
CHILD = """import json
import os
import sys
import time
from pathlib import Path

sys.path[:0] = [{tests!r}, {src!r}]

from rlm import cli
from rlm.gateway import Gateway
from test_phase8_command import WRITE_MODEL, RoomTransport


class Crash(RoomTransport):
    def _handle(self, request):
        if json.loads(request.content)["model"] == WRITE_MODEL:
            raise RuntimeError("the fake transport stops at the write")
        return super()._handle(request)


key = os.environ["OPENROUTER_API_KEY"]
report = Path({report!r}).read_text(encoding="utf-8")
if key == {slow!r}:
    time.sleep(120)
if key == {crash!r}:
    transport = Crash(report=report)
else:
    transport = RoomTransport(status=401 if key == {bad!r} else None, report=report)
gateway = Gateway(api_key=key, transport=transport, rate_limit_waits=())
sys.exit(cli.main(sys.argv[1:], gateway=gateway))
"""


class Served:
    """The running server: its address, its runs folder and its runner."""

    def __init__(self, port: int, runs: Path, runner: LocalRunner):
        self.port = port
        self.url = f"http://127.0.0.1:{port}"
        self.runs = runs
        self.runner = runner

    def run_dirs(self) -> list[Path]:
        return sorted(path for path in self.runs.iterdir() if path.is_dir()) if self.runs.exists() else []


@pytest.fixture
def server(tmp_path):
    """uvicorn serving the app and web/ on a free port, its runner starting the fake child."""
    report = tmp_path / "page-report.md"
    report.write_text(PAGE_REPORT, encoding="utf-8")
    script = tmp_path / "child.py"
    script.write_text(
        CHILD.format(
            tests=str(TESTS), src=str(SRC), report=str(report), bad=BAD_KEY, crash=CRASH_KEY, slow=SLOW_KEY
        ),
        encoding="utf-8",
    )
    runner = LocalRunner([sys.executable, str(script)])
    runs = tmp_path / "runs"
    app = create_app(runner=runner, runs_root=runs, web_dir=WEB)
    port = free_port()
    config = uvicorn.Config(
        app, host="127.0.0.1", port=port, log_level="warning", timeout_graceful_shutdown=2
    )
    served = uvicorn.Server(config)
    thread = threading.Thread(target=served.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 30
    while not served.started:
        assert thread.is_alive(), "the server stopped"
        assert time.monotonic() < deadline, "the server did not start"
        time.sleep(0.05)
    yield Served(port, runs, runner)
    served.should_exit = True
    thread.join(timeout=15)
    for run_id in list(runner.processes):
        runner.cancel(run_id)


class Watched:
    """A page with every request it makes recorded and every outside host aborted."""

    def __init__(self, page: Page, served: Served):
        self.page = page
        self.served = served
        self.requests = []
        self.outside = []
        self.github = []
        self.latest = __version__
        page.on("request", lambda request: self.requests.append(request))
        page.route(lambda url: not self.allowed(url), self.abort)
        page.route(LATEST, self.fake_latest)
        page.set_default_timeout(15_000)

    def allowed(self, url: str) -> bool:
        parsed = urlparse(url)
        if parsed.scheme in ("data", "blob", "about"):
            return True
        local = parsed.hostname in ("127.0.0.1", "localhost") and parsed.port == self.served.port
        return local or parsed.hostname in ("openrouter.ai", "api.github.com")

    def abort(self, route):
        self.outside.append(route.request.url)
        route.abort()

    def fake_latest(self, route):
        self.github.append(route.request)
        route.fulfill(
            status=200,
            headers={"Access-Control-Allow-Origin": "*"},
            json={"tag_name": f"v{self.latest}", "html_url": f"https://github.com/{REPO}/releases"},
        )

    def local_requests(self):
        return [
            request
            for request in self.requests
            if urlparse(request.url).hostname in ("127.0.0.1", "localhost")
        ]

    def stored(self) -> str:
        """Everything the page keeps in localStorage, sessionStorage and cookies, as one string."""
        return self.page.evaluate(
            "() => JSON.stringify(Object.assign({}, localStorage))"
            " + JSON.stringify(Object.assign({}, sessionStorage)) + document.cookie"
        )

    def assert_kept_in(self, *keys: str) -> None:
        """No request left for an outside host, and no key sits in a URL or the browser's storage."""
        assert self.outside == []
        for request in self.requests:
            assert all(key not in request.url for key in keys), request.url
        stored = self.stored()
        assert all(key not in stored for key in keys)


@pytest.fixture(scope="session")
def browser(launch_browser):
    """The session's browser, left to the driver to end.

    Browser.close waits on the removal of the browser's temporary profile, which on some
    Windows machines never finishes and fails the session; stopping the driver ends the browser
    instead. Downloads are cancelled on the same machines, so the export links are fetched
    through the page's own request context rather than clicked.
    """
    yield launch_browser()


@pytest.fixture
def web(page: Page, server: Served) -> Watched:
    return Watched(page, server)


def room_folder(tmp_path: Path) -> Path:
    return copy_room(tmp_path)


def room_zip(tmp_path: Path) -> Path:
    """Sample 3's room as one zip, every member under a top folder named for the sample."""
    room = copy_room(tmp_path / "forzip")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for path in sorted(room.rglob("*")):
            if path.is_file():
                archive.writestr(f"{ROOM}/{path.relative_to(room).as_posix()}", path.read_bytes())
    target = tmp_path / f"{ROOM}.zip"
    target.write_bytes(buffer.getvalue())
    return target


def paste_key(page: Page, key: str) -> None:
    page.fill("#key-input", key)
    page.click("#key-use")
    expect(page.locator("#key-state")).to_have_text("connected")


def upload_and_confirm(page: Page, chooser: str, path: Path) -> None:
    """Chooses the room, uploads it, waits for the estimate and confirms it."""
    page.set_input_files(chooser, str(path))
    page.click("#upload")
    expect(page.locator("#estimate-dollars")).to_contain_text("$")
    expect(page.locator("#estimate-tokens")).not_to_be_empty()
    page.click("#confirm")


def expect_every_stage(page: Page, state: str) -> None:
    for stage in cli.STAGES:
        row = page.locator(f'#stages [data-stage="{stage}"]')
        expect(row).to_have_attribute("data-state", state, timeout=RUN_TIMEOUT)
        expect(row).to_contain_text(state)


def run_json(run_dir: Path) -> dict:
    return json.loads((run_dir / "run.json").read_text(encoding="utf-8"))


def sections(run_dir: Path) -> list[dict]:
    with (run_dir / "sections.jsonl").open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def keyed_posts(watched: Watched) -> list:
    return [request for request in watched.local_requests() if request.method == "POST"]


# ---------------------------------------------------------------- a run, end to end


def test_a_run_from_the_page_finishes_and_reads_back(web, tmp_path):
    page = web.page
    page.goto(web.served.url)
    paste_key(page, GOOD_KEY)

    upload_and_confirm(page, "#room-folder", room_folder(tmp_path))

    expect_every_stage(page, "finished")
    [run_dir] = web.served.run_dirs()
    state = run_json(run_dir)
    assert state["status"] == "done"
    expect(page.locator("#noted")).to_have_text(str(state["documents_noted"]))
    expect(page.locator("#dollars")).to_contain_text(f"{state['dollars']:.4f}")

    expect(page.locator("#report")).to_contain_text("Executive summary", timeout=RUN_TIMEOUT)
    shown = page.inner_text("#report")
    recall, _, missed = measure_recall(load_key(ROOT / "samples" / ROOM), shown)
    assert recall == 100.0, missed

    page.locator('#report a.cite[data-anchor="cim.md#l16"]').first.click()
    source = page.locator("#source")
    expect(source).to_be_visible()
    expect(page.locator("#source-doc")).to_have_text("cim.md")
    by_anchor = {row["anchor"]: row["text"] for row in sections(run_dir)}
    marked = source.locator("mark")
    expect(marked).to_have_count(1)
    expect(marked).to_have_text(by_anchor["cim.md#l16"].strip())
    expect(source).to_contain_text(by_anchor["cim.md#l18"].strip())
    expect(marked).to_be_in_viewport()

    page.locator('#report a.cite[data-anchor="revenue_summary.xlsx#Annual Totals!A4"]').first.click()
    expect(page.locator("#source-doc")).to_have_text("revenue_summary.xlsx")
    expect(marked).to_have_text(by_anchor["revenue_summary.xlsx#Annual Totals!A4"].strip())

    for fmt, name in EXPORTS:
        link = page.locator(f'#exports a[data-format="{fmt}"]')
        expect(link).to_be_visible()
        assert link.get_attribute("download") is not None, fmt
        fetched = page.request.get(link.evaluate("node => node.href"))
        assert fetched.status == 200, fmt
        assert f"{run_dir.name}-{name}" in fetched.headers["content-disposition"], fmt
        assert len(fetched.body()) > 0, fmt

    posts = keyed_posts(web)
    assert {urlparse(post.url).path for post in posts} == {"/runs", f"/runs/{run_dir.name}/confirm"}
    assert all(post.headers.get("x-openrouter-key") == GOOD_KEY for post in posts)
    web.assert_kept_in(GOOD_KEY)


def test_a_refused_key_shows_its_card_and_a_retry_resumes(web, tmp_path):
    page = web.page
    page.goto(web.served.url)
    paste_key(page, BAD_KEY)

    upload_and_confirm(page, "#room-zip", room_zip(tmp_path))

    card = page.locator("#error")
    expect(card).to_be_visible(timeout=RUN_TIMEOUT)
    expect(card.locator(".code")).to_have_text("key-refused")
    expect(card).to_contain_text(FIXES["key-refused"])
    expect(card.locator("#retry")).to_be_visible()
    expect(card.locator("#report-problem")).to_be_hidden()
    expect(page.locator('#stages [data-stage="ingest"]')).to_have_attribute("data-state", "finished")
    expect(page.locator('#stages [data-stage="notes"]')).to_have_attribute("data-state", "stopped")
    [run_dir] = web.served.run_dirs()
    sections_written = (run_dir / "sections.jsonl").stat().st_mtime_ns

    paste_key(page, GOOD_KEY)
    card.locator("#retry").click()

    expect_every_stage(page, "finished")
    expect(card).to_be_hidden()
    expect(page.locator("#report")).to_contain_text("Executive summary", timeout=RUN_TIMEOUT)
    assert run_json(run_dir)["status"] == "done"
    assert (run_dir / "sections.jsonl").stat().st_mtime_ns == sections_written
    retry = [post for post in keyed_posts(web) if post.url.endswith("/retry")]
    assert len(retry) == 1 and retry[0].headers.get("x-openrouter-key") == GOOD_KEY
    web.assert_kept_in(GOOD_KEY, BAD_KEY)


def test_an_unexpected_stop_offers_a_report_that_names_the_run_and_nothing_else(web, tmp_path):
    page = web.page
    page.goto(web.served.url)
    paste_key(page, CRASH_KEY)

    upload_and_confirm(page, "#room-zip", room_zip(tmp_path))

    card = page.locator("#error")
    expect(card.locator(".code")).to_have_text("unexpected", timeout=RUN_TIMEOUT)
    expect(card).to_contain_text(FIXES["unexpected"])
    expect(card.locator("#retry")).to_be_visible()
    link = card.locator("#report-problem")
    expect(link).to_be_visible()
    href = link.get_attribute("href")
    [run_dir] = web.served.run_dirs()
    state = run_json(run_dir)
    assert (state["status"], state["stage"], state["code"]) == ("failed", "write", "unexpected")

    parsed = urlparse(href)
    assert (parsed.scheme, parsed.hostname, parsed.path) == ("https", "github.com", f"/{REPO}/issues/new")
    query = parse_qs(parsed.query)
    assert query["labels"] == ["user-report"]
    said = query["title"][0] + "\n" + query["body"][0]
    assert run_dir.name in said
    assert __version__ in said
    assert "write" in said
    assert "unexpected" in said
    assert f"{state['dollars']:.4f}" in said

    readable = unquote_plus(href)
    assert CRASH_KEY not in href and CRASH_KEY not in readable
    for row in sections(run_dir):
        text = row["text"].strip()
        if len(text) >= 12:
            assert text not in readable, row["anchor"]
    assert "northstar" not in readable.casefold()
    web.assert_kept_in(CRASH_KEY)


# ---------------------------------------------------------------- a stop


def test_stop_ends_the_run_with_the_stopped_card_and_a_retry(web, tmp_path):
    page = web.page
    page.goto(web.served.url)
    paste_key(page, SLOW_KEY)
    upload_and_confirm(page, "#room-folder", room_folder(tmp_path))
    [run_dir] = web.served.run_dirs()
    expect(page.locator("#stop")).to_be_visible()

    page.click("#stop")

    card = page.locator("#error")
    expect(card).to_be_visible(timeout=RUN_TIMEOUT)
    expect(card.locator(".code")).to_have_text("stopped")
    expect(card).to_contain_text(FIXES["stopped"])
    expect(card.locator("#retry")).to_be_visible()
    expect(page.locator("#stop")).to_be_hidden()
    assert web.served.runner.status(run_dir.name) == "exited"
    web.assert_kept_in(SLOW_KEY)


def test_an_upload_during_a_run_asks_and_keep_it_running_changes_nothing(web, tmp_path):
    page = web.page
    dialogs = []
    page.on("dialog", lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))
    page.goto(web.served.url)
    paste_key(page, SLOW_KEY)
    upload_and_confirm(page, "#room-folder", room_folder(tmp_path))
    [run_dir] = web.served.run_dirs()
    question = page.locator("#replace-question")
    expect(question).to_be_hidden()

    page.set_input_files("#room-zip", str(room_zip(tmp_path)))
    page.click("#upload")

    expect(question).to_be_visible()
    expect(question).to_contain_text("A run is going. Stop it and upload the new room?")
    page.click("#replace-keep")

    expect(question).to_be_hidden()
    expect(page.locator("#stop")).to_be_visible()
    expect(page.locator("#run-id")).to_have_text(run_dir.name)
    assert web.served.runner.status(run_dir.name) == "running"
    assert web.served.run_dirs() == [run_dir]
    assert dialogs == []


def test_stop_and_upload_stops_the_old_run_and_shows_the_new_estimate(web, tmp_path):
    page = web.page
    dialogs = []
    page.on("dialog", lambda dialog: (dialogs.append(dialog.message), dialog.dismiss()))
    page.goto(web.served.url)
    paste_key(page, SLOW_KEY)
    upload_and_confirm(page, "#room-folder", room_folder(tmp_path))
    [old] = web.served.run_dirs()

    page.set_input_files("#room-zip", str(room_zip(tmp_path)))
    page.click("#upload")
    expect(page.locator("#replace-question")).to_be_visible()
    page.click("#replace-stop")

    expect(page.locator("#estimate-dollars")).to_contain_text("$")
    expect(page.locator("#replace-question")).to_be_hidden()
    expect(page.locator("#estimate-card")).to_be_visible()
    expect(page.locator("#run-id")).not_to_have_text(old.name)
    assert web.served.runner.status(old.name) == "exited"
    assert len(web.served.run_dirs()) == 2
    stops = [post for post in keyed_posts(web) if post.url.endswith("/stop")]
    assert len(stops) == 1 and urlparse(stops[0].url).path == f"/runs/{old.name}/stop"
    assert dialogs == []


# ---------------------------------------------------------------- past runs and a new room


def run_to_the_end(page: Page, chooser: str, path: Path) -> None:
    upload_and_confirm(page, chooser, path)
    expect_every_stage(page, "finished")
    expect(page.locator("#report")).to_contain_text("Executive summary", timeout=RUN_TIMEOUT)


def test_past_runs_lists_both_rooms_and_opening_the_first_shows_its_report(web, tmp_path):
    page = web.page
    page.goto(web.served.url)
    expect(page.locator("#past-card")).to_contain_text("No runs yet.")
    paste_key(page, GOOD_KEY)

    run_to_the_end(page, "#room-folder", room_folder(tmp_path))
    [first] = web.served.run_dirs()
    run_to_the_end(page, "#room-zip", room_zip(tmp_path))
    first_id = first.name
    [second_id] = [path.name for path in web.served.run_dirs() if path.name != first_id]

    expect(page.locator("#past-list li")).to_have_count(2)
    expect(page.locator(f'#past-list li[data-id="{first_id}"]')).to_contain_text("done")
    expect(page.locator(f'#past-list li[data-id="{second_id}"]')).to_contain_text("done")
    expect(page.locator("#past-card")).not_to_contain_text("No runs yet.")

    page.locator(f'#past-list li[data-id="{first_id}"] button.open').click()

    expect(page.locator("#report-card")).to_be_visible()
    expect(page.locator("#report")).to_contain_text("Executive summary")
    expect(page.locator("#run-id")).to_have_text(first_id)
    for fmt, _ in EXPORTS:
        href = page.locator(f'#exports a[data-format="{fmt}"]').get_attribute("href")
        assert href == f"/runs/{first_id}/export/{fmt}"
    web.assert_kept_in(GOOD_KEY)


def test_new_room_clears_the_page_and_keeps_the_key(web, tmp_path):
    page = web.page
    page.goto(web.served.url)
    paste_key(page, GOOD_KEY)
    run_to_the_end(page, "#room-folder", room_folder(tmp_path))

    page.click("#new-room")

    for card in ("#report-card", "#progress-card", "#estimate-card", "#error"):
        expect(page.locator(card)).to_be_hidden()
    expect(page.locator("#key-state")).to_have_text("connected")
    expect(page.locator("#room-card")).to_be_in_viewport()
    assert page.evaluate("() => document.getElementById('room-folder').files.length") == 0

    page.click("#upload")
    expect(page.locator("#error")).to_contain_text("Choose a folder or a zip first.")


def test_opening_a_stopped_run_shows_the_stopped_card_with_retry(web, tmp_path):
    page = web.page
    page.goto(web.served.url)
    paste_key(page, SLOW_KEY)
    upload_and_confirm(page, "#room-folder", room_folder(tmp_path))
    [run_dir] = web.served.run_dirs()
    page.click("#stop")
    expect(page.locator("#error .code")).to_have_text("stopped", timeout=RUN_TIMEOUT)

    page.reload()
    row = page.locator(f'#past-list li[data-id="{run_dir.name}"]')
    expect(row).to_contain_text("stopped")
    expect(page.locator("#error")).to_be_hidden()
    row.locator("button.open").click()

    card = page.locator("#error")
    expect(card).to_be_visible(timeout=RUN_TIMEOUT)
    expect(card.locator(".code")).to_have_text("stopped")
    expect(card.locator("#retry")).to_be_visible()


# ---------------------------------------------------------------- the update notice


def test_a_newer_release_shows_the_update_notice_and_is_asked_once_a_day(web):
    page = web.page
    web.latest = "9.9.9"
    page.goto(web.served.url)

    notice = page.locator("#update")
    expect(notice).to_be_visible()
    expect(notice).to_contain_text("9.9.9")
    for command in ("docker pull", "pipx upgrade", "helm upgrade"):
        expect(notice).to_contain_text(command)
    assert len(web.github) == 1
    asked = web.github[0]
    assert asked.method == "GET"
    assert asked.url == LATEST
    assert asked.post_data is None

    page.reload()
    expect(notice).to_be_visible()
    assert len(web.github) == 1
    web.assert_kept_in()


def test_the_same_release_shows_no_notice(web):
    page = web.page
    page.goto(web.served.url)

    expect(page.locator("body")).to_have_attribute("data-update-check", "done")
    expect(page.locator("#update")).to_be_hidden()
    assert len(web.github) == 1


def test_the_update_check_is_off_when_the_server_says_so(web, monkeypatch):
    monkeypatch.setenv("RLM_UPDATE_CHECK", "off")
    web.latest = "9.9.9"
    page = web.page
    page.goto(web.served.url)

    expect(page.locator("body")).to_have_attribute("data-update-check", "off")
    expect(page.locator("#version")).to_have_text(__version__)
    expect(page.locator("#update")).to_be_hidden()
    assert web.github == []


# ---------------------------------------------------------------- the sign-in


def challenge_of(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}


def test_sign_in_builds_a_pkce_request_and_exchanges_the_code(web, tmp_path):
    page = web.page
    asked: dict = {}
    exchanged: dict = {}

    def fake_auth(route):
        asked.update(parse_qs(urlparse(route.request.url).query))
        callback = asked["callback_url"][0]
        joiner = "&" if "?" in callback else "?"
        route.fulfill(status=302, headers={"Location": f"{callback}{joiner}code=THECODE"})

    def fake_keys(route):
        if route.request.method == "OPTIONS":
            route.fulfill(status=204, headers=CORS)
            return
        exchanged.update(route.request.post_data_json)
        route.fulfill(status=200, headers=CORS, json={"key": SIGNED_KEY, "user_id": "user-1"})

    page.route(lambda url: url.startswith("https://openrouter.ai/auth?"), fake_auth)
    page.route("https://openrouter.ai/api/v1/auth/keys", fake_keys)
    page.goto(web.served.url)

    page.click("#sign-in")

    expect(page.locator("#key-state")).to_have_text("connected")
    assert asked["code_challenge_method"] == ["S256"]
    callback = urlparse(asked["callback_url"][0])
    assert (callback.scheme, callback.hostname, callback.port) == ("http", "localhost", web.served.port)
    assert exchanged["code"] == "THECODE"
    assert exchanged["code_challenge_method"] == "S256"
    verifier = exchanged["code_verifier"]
    assert 43 <= len(verifier) <= 128
    assert challenge_of(verifier) == asked["code_challenge"][0]
    assert "code=" not in page.url
    assert verifier not in web.stored()

    page.set_input_files("#room-zip", str(room_zip(tmp_path)))
    page.click("#upload")
    expect(page.locator("#estimate-dollars")).to_contain_text("$")
    [upload] = [post for post in keyed_posts(web) if urlparse(post.url).path == "/runs"]
    assert upload.headers.get("x-openrouter-key") == SIGNED_KEY
    web.assert_kept_in(SIGNED_KEY)


def test_the_page_loads_its_markdown_library_from_the_machine(web):
    page = web.page
    page.goto(web.served.url)

    assert page.evaluate("() => typeof marked.parse") == "function"
    assert any(urlparse(request.url).path == "/vendor/marked.min.js" for request in web.local_requests())
    web.assert_kept_in()
