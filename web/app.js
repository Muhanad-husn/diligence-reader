// The diligence-reader page: upload a room, connect an OpenRouter key, confirm the estimate,
// follow the run's AG-UI events, read the report with its citations, export it.
// Plain script, no build step. vendor/marked.min.js is marked v15.0.12 (MIT), taken from
// https://cdn.jsdelivr.net/npm/marked@15.0.12/marked.min.js and updated by hand.
//
// The key lives in the variable `key` alone: never in localStorage, sessionStorage, a cookie
// or a URL. It goes in the X-OpenRouter-Key header of each request that starts a run. The page
// talks to this machine's server, to openrouter.ai for the sign-in, and once a day to GitHub's
// latest-release address, which carries no document data.
"use strict";

(function () {
  const REPO = "Muhanad-husn/diligence-reader";
  const LATEST = "https://api.github.com/repos/" + REPO + "/releases/latest";
  const AUTH = "https://openrouter.ai/auth";
  const EXCHANGE = "https://openrouter.ai/api/v1/auth/keys";
  const STAGES = ["ingest", "notes", "map", "dossier", "write", "export"];
  // localStorage holds the day of the last update check and the version it found, nothing else.
  const UPDATE_STORE = "diligence-reader-update-check";
  // sessionStorage holds the PKCE verifier across the one redirect to OpenRouter and back.
  const VERIFIER_STORE = "diligence-reader-pkce-verifier";
  // Codes the run's own fix cannot cover, which get a Report a problem link.
  const REPORTABLE = ["unexpected", "unknown"];

  let key = null;
  let version = "";
  let chosen = null;
  let run = null;

  const $ = (id) => document.getElementById(id);

  class Refusal extends Error {
    constructor(code, message) {
      super(message || code);
      this.code = code;
    }
  }

  // ------------------------------------------------------------ the local API

  async function call(method, path, body, withKey) {
    const headers = {};
    if (withKey && key) headers["X-OpenRouter-Key"] = key;
    let response;
    try {
      response = await fetch(path, { method, headers, body, credentials: "same-origin" });
    } catch (err) {
      throw new Refusal("unexpected", "The local server did not answer. Is it still running?");
    }
    if (!response.ok) {
      let found = {};
      try {
        found = await response.json();
      } catch (err) {
        found = {};
      }
      throw new Refusal(found.code || "unexpected", found.message || "The server answered " + response.status + ".");
    }
    return response;
  }

  async function json(method, path, body, withKey) {
    return (await call(method, path, body, withKey)).json();
  }

  function pathOf(text) {
    return text.split("/").map(encodeURIComponent).join("/");
  }

  // ------------------------------------------------------------ the key

  function useKey(value) {
    const trimmed = (value || "").trim();
    if (!trimmed) {
      $("key-state").textContent = "no key: the key is empty";
      return;
    }
    key = trimmed;
    $("key-input").value = "";
    $("key-state").textContent = "connected";
  }

  function base64url(bytes) {
    let text = "";
    bytes.forEach((byte) => (text += String.fromCharCode(byte)));
    return btoa(text).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  }

  async function challengeOf(verifier) {
    const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier));
    return base64url(new Uint8Array(digest));
  }

  // OpenRouter takes a localhost callback, so a page opened on 127.0.0.1 moves to localhost first.
  async function signIn() {
    if (location.hostname === "127.0.0.1" || location.hostname === "[::1]") {
      const here = new URL(location.href);
      here.hostname = "localhost";
      here.search = "?signin=1";
      here.hash = "";
      location.assign(here.toString());
      return;
    }
    const verifier = base64url(crypto.getRandomValues(new Uint8Array(32)));
    sessionStorage.setItem(VERIFIER_STORE, verifier);
    const auth = new URL(AUTH);
    auth.searchParams.set("callback_url", location.origin + location.pathname);
    auth.searchParams.set("code_challenge", await challengeOf(verifier));
    auth.searchParams.set("code_challenge_method", "S256");
    location.assign(auth.toString());
  }

  async function exchange(code) {
    const verifier = sessionStorage.getItem(VERIFIER_STORE);
    sessionStorage.removeItem(VERIFIER_STORE);
    history.replaceState(null, "", location.pathname);
    if (!verifier) {
      $("key-state").textContent = "no key: the sign-in was started in another tab; sign in again";
      return;
    }
    $("key-state").textContent = "connecting";
    try {
      const response = await fetch(EXCHANGE, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code, code_verifier: verifier, code_challenge_method: "S256" }),
        credentials: "omit",
      });
      if (!response.ok) throw new Error("OpenRouter answered " + response.status);
      const found = await response.json();
      useKey(found.key);
    } catch (err) {
      $("key-state").textContent = "no key: the sign-in did not give a key; sign in again or paste one";
    }
  }

  // ------------------------------------------------------------ upload, estimate, confirm

  function choose(input) {
    chosen = input.files && input.files.length ? input : null;
  }

  // The upload button asks first when a run is going; the question's buttons carry on from there.
  function uploadClicked() {
    if (run && run.going) {
      $("replace-question").hidden = false;
      return;
    }
    upload();
  }

  async function stopAndUpload() {
    $("replace-question").hidden = true;
    try {
      await stop();
    } catch (err) {
      showError(err.code || "unexpected", err.message, false);
      return;
    }
    upload();
  }

  async function stop() {
    $("stop").disabled = true;
    try {
      await call("POST", "/runs/" + run.id + "/stop");
    } catch (err) {
      // A run that ended while the click was on its way needs no stop.
      if (err.code !== "not-running") throw err;
    } finally {
      $("stop").disabled = false;
    }
  }

  async function upload() {
    hideError();
    if (!key) {
      $("key-state").textContent = "no key: connect a key before the upload";
      return;
    }
    if (!chosen) {
      showError("no-room", "Choose a folder or a zip first.", false);
      return;
    }
    if (run && run.source) run.source.close();
    run = null;
    $("stop").hidden = true;
    const form = new FormData();
    for (const file of chosen.files) form.append("files", file, file.webkitRelativePath || file.name);
    $("upload").disabled = true;
    try {
      const made = await json("POST", "/runs", form, true);
      startRun(made.id);
      const estimate = await json("GET", "/runs/" + run.id + "/estimate");
      $("estimate-dollars").textContent = "$" + estimate.dollars.toFixed(4);
      $("estimate-tokens").textContent = estimate.tokens.toLocaleString("en");
      $("estimate-notes-model").textContent = estimate.notes_model;
      $("estimate-write-model").textContent = estimate.write_model;
      $("estimate-card").hidden = false;
      $("confirm").disabled = false;
    } catch (err) {
      showError(err.code || "unexpected", err.message, false);
    } finally {
      $("upload").disabled = false;
    }
  }

  function startRun(id) {
    if (run && run.source) run.source.close();
    run = { id, source: null, going: false, values: { stage: null, documents_noted: 0, dollars: 0 } };
    $("run-id").textContent = id;
    $("estimate-card").hidden = true;
    $("progress-card").hidden = true;
    $("report-card").hidden = true;
  }

  async function confirm() {
    hideError();
    $("confirm").disabled = true;
    try {
      await call("POST", "/runs/" + run.id + "/confirm", null, true);
      follow();
    } catch (err) {
      $("confirm").disabled = false;
      showError(err.code || "unexpected", err.message, true);
    }
  }

  async function retry() {
    hideError();
    try {
      await call("POST", "/runs/" + run.id + "/retry", null, true);
      follow();
    } catch (err) {
      showError(err.code || "unexpected", err.message, true);
    }
  }

  // ------------------------------------------------------------ progress

  function drawStages() {
    const list = $("stages");
    list.textContent = "";
    for (const stage of STAGES) {
      const row = document.createElement("li");
      row.dataset.stage = stage;
      const name = document.createElement("span");
      name.className = "name";
      name.textContent = stage;
      const state = document.createElement("span");
      state.className = "state";
      row.append(name, " ", state);
      list.append(row);
      mark(stage, "waiting");
    }
  }

  function mark(stage, state) {
    const row = document.querySelector('#stages [data-stage="' + stage + '"]');
    if (!row) return;
    row.dataset.state = state;
    row.querySelector(".state").textContent = state;
  }

  function showValues() {
    $("noted").textContent = String(run.values.documents_noted || 0);
    $("dollars").textContent = "$" + Number(run.values.dollars || 0).toFixed(4);
  }

  function follow() {
    if (run.source) run.source.close();
    drawStages();
    $("progress-card").hidden = false;
    $("report-card").hidden = true;
    run.going = true;
    $("stop").hidden = false;
    const source = new EventSource("/runs/" + encodeURIComponent(run.id) + "/events");
    run.source = source;
    source.onmessage = (message) => {
      let event;
      try {
        event = JSON.parse(message.data);
      } catch (err) {
        return;
      }
      handle(event, source);
    };
  }

  function handle(event, source) {
    switch (event.type) {
      case "RUN_STARTED":
        drawStages();
        break;
      case "STATE_SNAPSHOT":
        Object.assign(run.values, event.snapshot || {});
        showValues();
        break;
      case "STATE_DELTA":
        for (const op of event.delta || []) {
          if (op.op === "replace" || op.op === "add") run.values[op.path.replace(/^\//, "")] = op.value;
        }
        showValues();
        break;
      case "STEP_STARTED":
        mark(event.stepName, "running");
        break;
      case "STEP_FINISHED":
        mark(event.stepName, "finished");
        break;
      case "RUN_FINISHED":
        source.close();
        ended();
        if (event.result && event.result.dollars != null) run.values.dollars = event.result.dollars;
        showValues();
        showReport();
        break;
      case "RUN_ERROR":
        source.close();
        ended();
        for (const row of document.querySelectorAll('#stages [data-state="running"]')) mark(row.dataset.stage, "stopped");
        showError(event.code || "unexpected", event.message, true);
        break;
      default:
        break;
    }
  }

  // The run is over: no Stop button, and an upload needs no question.
  function ended() {
    run.going = false;
    $("stop").hidden = true;
    $("replace-question").hidden = true;
  }

  // ------------------------------------------------------------ the error card

  function hideError() {
    $("error").hidden = true;
  }

  async function showError(code, message, retryable) {
    const card = $("error");
    card.querySelector(".code").textContent = code;
    card.querySelector(".fix").textContent = message || "";
    $("retry").hidden = !retryable || code === "unreadable-file" || code === "running";
    $("top-up").hidden = code !== "no-credits";
    const report = $("report-problem");
    report.hidden = true;
    report.removeAttribute("href");
    card.hidden = false;
    if (REPORTABLE.includes(code) && run) {
      report.href = await problemUrl(code);
      report.hidden = false;
    }
  }

  // A new-issue URL carrying the run id, the version, the stage, the code and the dollars:
  // never the key and never a word of the room's documents.
  async function problemUrl(code) {
    let state = null;
    try {
      state = (await json("GET", "/runs/" + run.id)).state;
    } catch (err) {
      state = null;
    }
    const stage = (state && state.stage) || run.values.stage || "unknown";
    const dollars = Number((state && state.dollars) || run.values.dollars || 0).toFixed(4);
    const runVersion = (state && state.version) || version;
    const body = [
      "Run id: " + run.id,
      "Version: " + runVersion,
      "Stage: " + stage,
      "Error code: " + code,
      "Dollars spent: " + dollars,
      "",
      "What happened before it stopped (please leave out document text and your key):",
      "",
    ].join("\n");
    const url = new URL("https://github.com/" + REPO + "/issues/new");
    url.searchParams.set("title", "Run stopped: " + code + " at " + stage);
    url.searchParams.set("body", body);
    url.searchParams.set("labels", "user-report");
    return url.toString();
  }

  // ------------------------------------------------------------ the report

  const CITATION = /\[\s*([^\[\]|]+?)\s*\|\s*([^\[\]|]+?)\s*\]|\[\s*([^\[\]|]*?#[^\[\]|]*?)\s*\]/g;

  function escapeHtml(text) {
    return text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  // Raw HTML in the report is shown as text, never run.
  marked.use({
    renderer: {
      html(token) {
        return escapeHtml(token.text);
      },
    },
  });

  // Each citation becomes a link to its section. Citations are swapped for plain tokens before
  // Markdown is read, so no Markdown rule can change them, and put back as links after.
  function renderReport(text) {
    const citations = [];
    const held = text.replace(CITATION, (whole, doc, anchor, bare) => {
      const target = anchor !== undefined ? anchor : bare;
      const document_ = doc !== undefined ? doc : bare.slice(0, bare.indexOf("#"));
      citations.push({ whole, doc: document_.trim(), anchor: target.trim() });
      return "XCITEX" + (citations.length - 1) + "XENDX";
    });
    const html = marked.parse(held).replace(/XCITEX(\d+)XENDX/g, (whole, index) => {
      const citation = citations[Number(index)];
      return (
        '<a class="cite" href="#" data-doc="' + escapeHtml(citation.doc) + '" data-anchor="' +
        escapeHtml(citation.anchor) + '">' + escapeHtml(citation.whole) + "</a>"
      );
    });
    const report = $("report");
    report.innerHTML = html;
    for (const link of report.querySelectorAll("a:not(.cite)")) {
      const href = link.getAttribute("href") || "";
      if (!/^https?:\/\//i.test(href)) link.removeAttribute("href");
      link.target = "_blank";
      link.rel = "noopener noreferrer";
    }
  }

  async function showReport() {
    const response = await call("GET", "/runs/" + run.id + "/report");
    renderReport(await response.text());
    for (const link of document.querySelectorAll("#exports a")) {
      link.href = "/runs/" + encodeURIComponent(run.id) + "/export/" + link.dataset.format;
    }
    $("source").hidden = true;
    $("report-card").hidden = false;
  }

  async function documentOf(doc, anchor) {
    try {
      return await json("GET", "/runs/" + run.id + "/documents/" + pathOf(doc));
    } catch (err) {
      const section = await json("GET", "/runs/" + run.id + "/sections/" + encodeURIComponent(anchor));
      return json("GET", "/runs/" + run.id + "/documents/" + pathOf(section.doc));
    }
  }

  async function openSource(doc, anchor) {
    let found;
    try {
      found = await documentOf(doc, anchor);
    } catch (err) {
      $("source-doc").textContent = doc;
      $("source-lines").textContent = "The cited section " + anchor + " is not in this run's sections.";
      $("source").hidden = false;
      return;
    }
    $("source-doc").textContent = found.doc;
    const lines = $("source-lines");
    lines.textContent = "";
    let cited = null;
    for (const section of found.sections) {
      const line = document.createElement("p");
      line.dataset.anchor = section.anchor;
      if (section.anchor === anchor) {
        cited = document.createElement("mark");
        cited.textContent = section.text;
        line.append(cited);
        line.className = "cited";
      } else {
        line.textContent = section.text;
      }
      lines.append(line);
    }
    $("source").hidden = false;
    if (cited) cited.scrollIntoView({ block: "center" });
  }

  // ------------------------------------------------------------ the update check

  function newer(found, current) {
    const parts = (text) => text.split(/[.+-]/).slice(0, 3).map((part) => parseInt(part, 10) || 0);
    const a = parts(found);
    const b = parts(current);
    for (let i = 0; i < 3; i += 1) {
      if (a[i] !== b[i]) return a[i] > b[i];
    }
    return false;
  }

  function readStore() {
    try {
      return JSON.parse(localStorage.getItem(UPDATE_STORE) || "null");
    } catch (err) {
      return null;
    }
  }

  function writeStore(value) {
    try {
      localStorage.setItem(UPDATE_STORE, JSON.stringify(value));
    } catch (err) {
      // A browser that keeps nothing asks again on the next load.
    }
  }

  async function checkForUpdate(current) {
    const today = new Date().toISOString().slice(0, 10);
    const saved = readStore();
    let latest = saved && saved.day === today ? saved.latest : null;
    if (!latest) {
      try {
        const response = await fetch(LATEST, { credentials: "omit", referrerPolicy: "no-referrer" });
        if (response.ok) {
          const release = await response.json();
          latest = String(release.tag_name || "").replace(/^v/, "");
          if (latest) writeStore({ day: today, latest });
        }
      } catch (err) {
        latest = null;
      }
    }
    if (latest && newer(latest, current)) {
      $("update-version").textContent = latest;
      $("update-docker").textContent = "docker pull ghcr.io/muhanad-husn/diligence-reader:latest";
      $("update-pipx").textContent = "pipx upgrade diligence-reader";
      $("update-helm").textContent =
        "helm upgrade diligence-reader oci://ghcr.io/muhanad-husn/charts/diligence-reader --version " + latest;
      $("update").hidden = false;
    }
    document.body.dataset.updateCheck = "done";
  }

  async function configure() {
    try {
      const config = await json("GET", "/api/config");
      version = config.version;
      $("version").textContent = version;
      if (config.update_check) {
        await checkForUpdate(version);
      } else {
        document.body.dataset.updateCheck = "off";
      }
    } catch (err) {
      document.body.dataset.updateCheck = "failed";
    }
  }

  // ------------------------------------------------------------ start

  $("key-use").addEventListener("click", () => useKey($("key-input").value));
  $("key-input").addEventListener("keydown", (event) => {
    if (event.key === "Enter") useKey($("key-input").value);
  });
  $("sign-in").addEventListener("click", signIn);
  $("room-folder").addEventListener("change", (event) => choose(event.target));
  $("room-zip").addEventListener("change", (event) => choose(event.target));
  $("upload").addEventListener("click", uploadClicked);
  $("replace-stop").addEventListener("click", stopAndUpload);
  $("replace-keep").addEventListener("click", () => ($("replace-question").hidden = true));
  $("stop").addEventListener("click", () => stop().catch((err) => showError(err.code || "unexpected", err.message, false)));
  $("confirm").addEventListener("click", confirm);
  $("retry").addEventListener("click", retry);
  $("report").addEventListener("click", (event) => {
    const link = event.target.closest("a.cite");
    if (!link) return;
    event.preventDefault();
    openSource(link.dataset.doc, link.dataset.anchor);
  });

  drawStages();
  const params = new URLSearchParams(location.search);
  if (params.has("code")) {
    exchange(params.get("code"));
  } else if (params.get("signin") === "1") {
    history.replaceState(null, "", location.pathname);
    signIn();
  }
  configure();
})();
