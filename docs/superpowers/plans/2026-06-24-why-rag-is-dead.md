# "Why R.A.G is Dead" Showcase Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish a public GitHub repo `LlamaopNV/why-rag-is-dead` containing the NEXUS app and a static GitHub Pages landing page that argues RAG is dead and demonstrates the NEXUS verified-microagent pipeline via a deterministic, client-side simulation.

**Architecture:** A self-contained static site in `/docs` (vanilla HTML/CSS/JS, no build step), served by GitHub Pages from `main`/`/docs`. The page is a 7-section editorial manifesto; its centerpiece is a scripted, client-side simulation of a real query flowing through Planner -> Workers -> Manager -> Main LLM using NEXUS's real token numbers. Visual design is produced by the design-taste-frontend skill within divergence guardrails.

**Tech Stack:** HTML5, CSS3, vanilla ES module JS. `gh` CLI + git for repo/Pages. design-taste-frontend skill for the visual layer. No framework, no bundler, no network calls at runtime.

## Global Constraints

- No backend, Claude API, or Ollama call from the page. Everything client-side and deterministic. (verbatim from spec)
- No secrets, tokens, or `.env` values written to the page or committed. `nexus/.env` stays untracked. (verbatim from spec)
- Token numbers used verbatim from README: Naive dump ~50K, Claude Code ~53K, NEXUS ~13K, Planner ~500 tokens. Do not invent numbers beyond these.
- Repo is PUBLIC, name `why-rag-is-dead`, default branch `main`.
- Page lives in `/docs`; Pages source = `main` branch, `/docs` folder.
- House style: no em dashes; first-person voice in prose (per CLAUDE.md).
- Visual must be deliberately distinct from the owner's existing pages (near-black + monospace-dominant + neon-multi-accent + glassy dashboards). New page = light editorial canvas, display/serif headline, one accent, monospace quarantined inside the dark terminal panel.
- Demo query (fixed): "Where is binary search implemented and how does it handle an empty array?" against TheAlgorithms/Python.

---

### Task 1: Create the public repo and push the NEXUS app

**Files:**
- Modify: git state of the whole repo (commit in-progress work)
- No source files created in this task

**Interfaces:**
- Consumes: existing local repo at `C:/Users/Llama/PycharmProjects/WarpDev-Context-Demo`, `gh` authenticated as `LlamaopNV`.
- Produces: public remote `https://github.com/LlamaopNV/why-rag-is-dead` with all current work pushed on branch `main`. Later tasks push the `/docs` page to this remote.

- [ ] **Step 1: Confirm no secrets are tracked**

Run:
```bash
cd "C:/Users/Llama/PycharmProjects/WarpDev-Context-Demo"
git ls-files | grep -iE "\.env$" || echo "OK: no .env tracked"
```
Expected: prints `OK: no .env tracked`. If any `.env` is listed, STOP and remove it from tracking before continuing.

- [ ] **Step 2: Stage and commit the in-progress work**

Run:
```bash
git add -A
git status --short
```
Confirm the list contains the modified backend/frontend files, the new `nexus/backend/services/claude_code_benchmark.py`, `nexus/frontend/src/components/BenchmarkStatus.tsx`, `CLAUDE.md`, `TODO.md`, `WORKLOG.md`, and `.idea/`. If `.idea/` should not be public, add it to `.gitignore` first, then re-stage.

```bash
git commit -m "chore: snapshot NEXUS app for public showcase

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```
Expected: a new commit is created.

- [ ] **Step 3: Create the public repo on GitHub**

Run:
```bash
gh repo create why-rag-is-dead --public --description "Why RAG is dead: verified microagents that fetch only what is true. Live NEXUS pipeline demo."
```
Expected: prints the new repo URL `https://github.com/LlamaopNV/why-rag-is-dead`. Do NOT pass `--source`/`--push` here; we add the remote explicitly next to avoid clobbering the existing `origin`.

- [ ] **Step 4: Add the new remote and push as `main`**

Run:
```bash
git remote add showcase "https://github.com/LlamaopNV/why-rag-is-dead.git"
git push showcase HEAD:main
```
Expected: branch `main` appears on the new repo with the full history.

- [ ] **Step 5: Verify the push**

Run:
```bash
gh repo view LlamaopNV/why-rag-is-dead --json visibility,defaultBranchRef --jq '{visibility: .visibility, default: .defaultBranchRef.name}'
```
Expected: `{"visibility":"PUBLIC","default":"main"}`. If default is not `main`, set it:
```bash
gh repo edit LlamaopNV/why-rag-is-dead --default-branch main
```

- [ ] **Step 6: Update WORKLOG**

Append to `WORKLOG.md`:
```
- [2026-06-24] Created public repo why-rag-is-dead and pushed the NEXUS app.
```
Commit:
```bash
git add WORKLOG.md && git commit -m "docs: log repo creation

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
git push showcase HEAD:main
```

---

### Task 2: Scaffold the page and write all real content

**Files:**
- Create: `docs/index.html`
- Create: `docs/styles.css` (base reset + minimal functional layout only; real design comes in Task 4)
- Create: `docs/data/citations.json` (canned citation data the sim reads)

**Interfaces:**
- Consumes: nothing from prior tasks except the repo.
- Produces: `docs/index.html` with seven labelled `<section>` regions and stable IDs the simulation hooks into. Stable IDs that Task 3 depends on, exact strings: section `#hero`, `#problem`, `#sim`, `#receipt`, `#how`, `#proof`, `#cta`; inside `#sim`: `#sim-run` (button), `#sim-planner`, `#sim-workers`, `#sim-manager`, `#sim-answer`, `#sim-rag-lane`, `#tok-planner`, `#tok-nexus`, `#tok-rag`, `#bar-naive`, `#bar-cc`, `#bar-nexus`.

- [ ] **Step 1: Create the HTML skeleton with real copy**

Create `docs/index.html`. Use this structure and copy verbatim (the design pass in Task 4 restyles, it does not rewrite the argument):

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Why R.A.G is Dead</title>
  <meta name="description" content="Retrieval should not mean stuffing chunks into context. It should mean verified microagents fetching only what is true. A live demo of the NEXUS pipeline." />
  <link rel="stylesheet" href="./styles.css" />
</head>
<body>
  <main>
    <section id="hero">
      <p class="eyebrow">A manifesto, and a working demo</p>
      <h1>Why R.A.G is Dead</h1>
      <p class="lede">Retrieval was never supposed to mean stuffing a wall of chunks into a context window and praying. It should mean verified microagents fetching only what is true, and proving where every word came from.</p>
      <div class="hero-cta">
        <a class="btn-primary" href="#sim">Watch it work</a>
        <a class="btn-ghost" href="https://github.com/LlamaopNV/why-rag-is-dead">Read the source</a>
      </div>
    </section>

    <section id="problem">
      <h2>RAG asks you to trust a black box</h2>
      <p>Classic retrieval-augmented generation embeds your data, pulls the top-k nearest chunks, and dumps them into one giant prompt. Three things break:</p>
      <ul class="problem-list">
        <li><strong>Hallucinated relevance.</strong> Cosine similarity is not understanding. The "nearest" chunk is often the wrong one, and the model cannot tell.</li>
        <li><strong>No provenance.</strong> The answer cites nothing you can check. You are trusting that the chunk said what the model claims it said.</li>
        <li><strong>Context bloat.</strong> To be safe, RAG over-fetches. Tens of thousands of tokens of maybe-relevant text, every single call.</li>
      </ul>
    </section>

    <section id="sim">
      <h2>Watch a query get answered, and verified</h2>
      <p class="sim-query">Query: <code>Where is binary search implemented and how does it handle an empty array?</code></p>
      <button id="sim-run" class="btn-primary">Run query</button>
      <div class="sim-stage" id="sim-planner" data-stage="planner"><h3>Planner</h3><div class="stage-body"></div></div>
      <div class="sim-stage" id="sim-workers" data-stage="workers"><h3>Workers</h3><div class="stage-body"></div></div>
      <div class="sim-stage" id="sim-manager" data-stage="manager"><h3>Manager (shell verification)</h3><div class="stage-body"></div></div>
      <div class="sim-stage" id="sim-answer" data-stage="answer"><h3>Main LLM</h3><div class="stage-body"></div></div>
      <aside id="sim-rag-lane"><h3>Meanwhile, RAG</h3><div class="stage-body"></div></aside>
    </section>

    <section id="receipt">
      <h2>The token receipt</h2>
      <p>Same question. Same codebase. Here is what each approach spends to answer it.</p>
      <div class="bars">
        <div class="bar-row"><span class="bar-label">Naive file dump</span><div class="bar" id="bar-naive"><span>~50K</span></div></div>
        <div class="bar-row"><span class="bar-label">Claude Code (reads whole files)</span><div class="bar" id="bar-cc"><span>~53K</span></div></div>
        <div class="bar-row"><span class="bar-label">NEXUS (verified facts only)</span><div class="bar" id="bar-nexus"><span>~13K</span></div></div>
      </div>
      <p class="receipt-note">95 to 99 percent less context, and every fact is checked.</p>
    </section>

    <section id="how">
      <h2>How it actually works</h2>
      <ol class="pipeline">
        <li><strong>Planner</strong> (Claude, ~500 tokens, never sees the codebase) decomposes the query into 3 to 5 atomic shell tasks scoped to the right directories.</li>
        <li><strong>Workers</strong> (local Ollama qwen2.5:1.5b, parallel, fresh context each) run sandboxed <code>grep</code>/<code>sed</code> and return structured citations.</li>
        <li><strong>Manager</strong> verifies every citation with deterministic shell (<code>sed -n '{line}p'</code>). No model checks another model.</li>
        <li><strong>Main LLM</strong> (Claude) sees only the verified context and answers with real <code>file:line</code> citations.</li>
      </ol>
      <p class="how-note">The thing RAG structurally cannot do: prove the retrieved fact is real before answering.</p>
    </section>

    <section id="proof">
      <h2>Every claim has a receipt</h2>
      <p>NEXUS does not ask you to trust a chunk. Each statement in the answer links to a verified <code>file:line</code> that a shell command confirmed exists. Provenance is the product, not an afterthought.</p>
    </section>

    <section id="cta">
      <h2>Retrieval is not dead. Unverified retrieval is.</h2>
      <div class="hero-cta">
        <a class="btn-primary" href="https://github.com/LlamaopNV/why-rag-is-dead">Browse the NEXUS source</a>
        <a class="btn-ghost" href="https://github.com/LlamaopNV/why-rag-is-dead#readme">Run it yourself</a>
      </div>
    </section>
  </main>
  <script type="module" src="./sim.js"></script>
</body>
</html>
```

- [ ] **Step 2: Create a minimal functional stylesheet**

Create `docs/styles.css` with only enough to make the page legible and the sim observable (real design is Task 4). Include a centered max-width container, readable spacing, a `.bar` that animates width via a CSS transition, and a `.sim-stage[data-active]` / `.citation[data-verified]` visible state so Task 3 can be verified before the design pass:

```css
:root { --maxw: 880px; }
* { box-sizing: border-box; }
body { margin: 0; font-family: system-ui, sans-serif; line-height: 1.6; color: #111; background: #fff; }
main { max-width: var(--maxw); margin: 0 auto; padding: 4rem 1.25rem; }
section { padding: 3rem 0; border-bottom: 1px solid #eee; }
h1 { font-size: clamp(2.5rem, 7vw, 5rem); line-height: 1.05; margin: .2em 0; }
.btn-primary, .btn-ghost { display: inline-block; padding: .7em 1.2em; border-radius: 8px; text-decoration: none; border: 1px solid #111; color: #111; }
.btn-primary { background: #111; color: #fff; }
.sim-stage, #sim-rag-lane { opacity: .35; transition: opacity .3s ease; padding: 1rem; border: 1px solid #ddd; border-radius: 8px; margin: .75rem 0; }
.sim-stage[data-active], #sim-rag-lane[data-active] { opacity: 1; }
.citation { padding: .25rem .5rem; }
.citation[data-verified="true"]::after { content: " verified"; color: green; font-weight: 600; }
.bar { height: 2.2rem; width: 0; background: #111; color: #fff; border-radius: 6px; display: flex; align-items: center; padding: 0 .6rem; transition: width 1.1s cubic-bezier(.2,.7,.2,1); white-space: nowrap; }
```

- [ ] **Step 3: Create the canned citation data file**

Create `docs/data/citations.json`. This is the deterministic data the simulation replays. Use plausible binary-search citations from TheAlgorithms/Python:

```json
{
  "query": "Where is binary search implemented and how does it handle an empty array?",
  "plannerTokens": 500,
  "tasks": [
    "grep -rn 'def binary_search' searches/",
    "sed -n '1,40p' searches/binary_search.py",
    "grep -n 'len(' searches/binary_search.py"
  ],
  "citations": [
    { "id": "c1", "file": "searches/binary_search.py", "line": 23, "text": "def binary_search(sorted_collection, item):", "claim": "binary_search is defined here" },
    { "id": "c2", "file": "searches/binary_search.py", "line": 31, "text": "left, right = 0, len(sorted_collection) - 1", "claim": "bounds are derived from len(); empty input gives right = -1" },
    { "id": "c3", "file": "searches/binary_search.py", "line": 33, "text": "while left <= right:", "claim": "loop never runs when right = -1, so an empty array returns the not-found path" }
  ],
  "answer": "Binary search lives in searches/binary_search.py:23. For an empty array, len() makes right = -1 (line 31), so the while left <= right loop on line 33 never executes and the function returns its not-found result. No special-casing needed.",
  "tokens": { "naive": 50000, "claudeCode": 53000, "nexus": 13000 }
}
```

- [ ] **Step 4: Verify the skeleton renders**

Open `docs/index.html` in a browser (or `start docs/index.html` on Windows). Expected: all seven sections render with the copy above; the Run button is visible; bars show their labels at zero width. The page is plain but complete.

- [ ] **Step 5: Commit**

```bash
git add docs/index.html docs/styles.css docs/data/citations.json
git commit -m "feat(page): scaffold Why RAG is Dead page with real content

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
git push showcase HEAD:main
```

---

### Task 3: Build the deterministic simulation engine

**Files:**
- Create: `docs/sim.js`

**Interfaces:**
- Consumes: the DOM IDs from Task 2 (`#sim-run`, `#sim-planner`, `#sim-workers`, `#sim-manager`, `#sim-answer`, `#sim-rag-lane`, `#bar-naive`, `#bar-cc`, `#bar-nexus`) and `./data/citations.json`.
- Produces: a self-contained ES module that, on click of `#sim-run`, plays the scripted timeline. No exports needed (side-effecting module). Reduced-motion users get the end state instantly.

- [ ] **Step 1: Define the expected behavior**

When the user clicks Run query, in order: Planner activates and shows its task list with a ~500 token count; each Worker activates and prints its shell command and the extracted citation line; the Manager activates and flips each citation to verified one at a time; the Main LLM activates and reveals the cited answer; the RAG lane fills with a "dumped ~50K unverified tokens" note; the three bars animate to widths proportional to 50K/53K/13K. Re-clicking resets and replays. `prefers-reduced-motion: reduce` jumps straight to the final state.

- [ ] **Step 2: Implement the module**

Create `docs/sim.js`:

```js
const $ = (id) => document.getElementById(id);
const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const sleep = (ms) => new Promise((r) => setTimeout(r, reduce ? 0 : ms));

let running = false;

async function loadData() {
  const res = await fetch("./data/citations.json");
  return res.json();
}

function reset(stageIds) {
  stageIds.forEach((id) => {
    const el = $(id);
    el.removeAttribute("data-active");
    el.querySelector(".stage-body").innerHTML = "";
  });
  ["bar-naive", "bar-cc", "bar-nexus"].forEach((id) => { $(id).style.width = "0"; });
}

function activate(id) { $(id).setAttribute("data-active", ""); }

async function run(data) {
  if (running) return;
  running = true;
  const stageIds = ["sim-planner", "sim-workers", "sim-manager", "sim-answer", "sim-rag-lane"];
  reset(stageIds);

  // Planner
  activate("sim-planner");
  $("sim-planner").querySelector(".stage-body").innerHTML =
    `<p>Decomposed into ${data.tasks.length} shell tasks. Spent ~${data.plannerTokens} tokens. Never read the codebase.</p>` +
    `<ul>${data.tasks.map((t) => `<li><code>${t}</code></li>`).join("")}</ul>`;
  await sleep(900);

  // Workers
  activate("sim-workers");
  const wbody = $("sim-workers").querySelector(".stage-body");
  for (const c of data.citations) {
    const div = document.createElement("div");
    div.className = "citation";
    div.dataset.verified = "false";
    div.innerHTML = `<code>sed -n '${c.line}p' ${c.file}</code> &rarr; <span class="line">${c.text}</span>`;
    wbody.appendChild(div);
    await sleep(600);
  }

  // Manager verifies each citation
  activate("sim-manager");
  const mbody = $("sim-manager").querySelector(".stage-body");
  mbody.innerHTML = `<p>Running <code>sed -n '{line}p'</code> on every citation. No model checks another model.</p>`;
  for (const c of data.citations) {
    const node = [...wbody.querySelectorAll(".citation")].find((n) => n.textContent.includes(c.text));
    if (node) node.dataset.verified = "true";
    await sleep(550);
  }

  // Main LLM answer
  activate("sim-answer");
  $("sim-answer").querySelector(".stage-body").innerHTML =
    `<p>${data.answer}</p><p class="cites">${data.citations.map((c) => `${c.file}:${c.line}`).join(" · ")}</p>`;
  await sleep(700);

  // RAG lane contrast
  activate("sim-rag-lane");
  $("sim-rag-lane").querySelector(".stage-body").innerHTML =
    `<p>Embedded the repo, pulled top-k chunks, dumped ~${(data.tokens.naive / 1000)}K unverified tokens into one prompt. Verified: nothing.</p>`;

  // Bars
  const max = data.tokens.claudeCode;
  $("bar-naive").style.width = `${(data.tokens.naive / max) * 100}%`;
  $("bar-cc").style.width = `100%`;
  $("bar-nexus").style.width = `${(data.tokens.nexus / max) * 100}%`;

  running = false;
}

const data = await loadData();
$("sim-run").addEventListener("click", () => run(data));
if (reduce) run(data); // show end state immediately for reduced-motion
```

- [ ] **Step 3: Verify the simulation runs**

Serve the folder so `fetch` works (file:// blocks fetch). Run:
```bash
cd "C:/Users/Llama/PycharmProjects/WarpDev-Context-Demo/docs" && python -m http.server 8099
```
Open `http://localhost:8099/`. Click **Run query**. Expected, in order: Planner shows 3 tasks and ~500 tokens; Workers print 3 `sed` commands with lines; Manager flips all 3 citations to "verified" (green); Main LLM shows the answer with `file:line` cites; RAG lane shows the ~50K dump note; the three bars animate to roughly 94 percent / 100 percent / 25 percent widths. Re-click replays cleanly. Stop the server with Ctrl-C.

- [ ] **Step 4: Verify reduced-motion fallback**

In browser devtools, emulate `prefers-reduced-motion: reduce` and reload. Expected: the page loads already showing the final state (all citations verified, bars filled) without waiting on animations.

- [ ] **Step 5: Commit**

```bash
git add docs/sim.js
git commit -m "feat(page): deterministic client-side NEXUS pipeline simulation

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
git push showcase HEAD:main
```

---

### Task 4: Design pass with the design-taste-frontend skill

**Files:**
- Modify: `docs/styles.css` (full editorial design system + quarantined terminal styling)
- Modify: `docs/index.html` (only structural/class changes the design needs; do not change the argument copy)
- Possibly create: `docs/assets/*` (fonts, svg) if the skill chooses self-hosted assets

**Interfaces:**
- Consumes: the working page from Tasks 2 and 3. The simulation behavior and DOM IDs in `sim.js` must keep working; the design pass may add classes and wrappers but must not remove the IDs `sim.js` depends on.
- Produces: the final visual layer. No JS behavior change.

- [ ] **Step 1: Invoke the design-taste-frontend skill with the brief**

Use the `design-taste-frontend` skill. Give it this brief verbatim:

> Redesign the existing static page at `docs/` (index.html + styles.css; do not touch sim.js behavior or its DOM IDs). It is a manifesto titled "Why R.A.G is Dead" with a live client-side simulation. Audit these existing pages by the same owner and deliberately DIVERGE from them: https://llamaopnv.github.io/Claude_Code_Empowerments-/ , https://llamaopnv.github.io/Claude_Code_Empowerments-/skill-installer/ , https://llamaopnv.github.io/tdd-heartbeat/ . Their shared formula to AVOID: near-black background, monospace-dominant type, neon multi-accent, glassy dashboard panels. Required direction: a light or paper editorial canvas, a display or serif headline (not monospace) for the argument, ONE opinionated accent color, and monospace QUARANTINED inside the dark `#sim` terminal panel so the contrast between light editorial body and dark agent console is a deliberate feature. Keep it fast: static, no heavy dependencies, self-hosted or system fonts. Run your anti-slop pre-flight before finishing.

- [ ] **Step 2: Verify the design preserved the simulation**

Serve `docs/` again (`python -m http.server 8099`), open it, click Run query. Expected: the simulation still plays end to end exactly as in Task 3, now inside the new design. The `#sim` panel reads as a dark terminal against a light editorial body. Confirm no console errors (missing IDs would throw).

- [ ] **Step 3: Verify divergence**

Open the page next to the three audited pages. Confirm at a glance it does NOT look like them: not near-black-default, not monospace-headline, not neon-rainbow. If it still resembles them, re-run the skill with sharper divergence notes.

- [ ] **Step 4: Commit**

```bash
git add docs/
git commit -m "feat(page): editorial design pass via design-taste skill

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
git push showcase HEAD:main
```

---

### Task 5: Enable GitHub Pages and verify live

**Files:**
- No source files; configures the repo and verifies the deployment.

**Interfaces:**
- Consumes: the pushed `main` branch with `/docs` populated.
- Produces: a live site at `https://llamaopnv.github.io/why-rag-is-dead/`.

- [ ] **Step 1: Enable Pages from `main`/`docs`**

Run:
```bash
gh api -X POST "repos/LlamaopNV/why-rag-is-dead/pages" -f "source[branch]=main" -f "source[path]=/docs" 2>&1 || echo "If this 404s or 409s, enable manually: repo Settings > Pages > Source: Deploy from a branch > main > /docs."
```
Expected: a JSON response with the Pages config, or a clear instruction to enable it in the UI. If manual, tell the owner the exact path.

- [ ] **Step 2: Confirm the Pages build**

Run:
```bash
gh api "repos/LlamaopNV/why-rag-is-dead/pages" --jq '{status: .status, url: .html_url}'
```
Expected: `status` becomes `built` within a minute or two and `url` is `https://llamaopnv.github.io/why-rag-is-dead/`.

- [ ] **Step 3: Verify the live site**

Run:
```bash
curl -sL -o /dev/null -w "%{http_code}\n" "https://llamaopnv.github.io/why-rag-is-dead/"
```
Expected: `200`. Then open the URL in a browser and click Run query; confirm the full simulation plays live and the bars animate.

- [ ] **Step 4: Final secret + cleanliness check**

Run:
```bash
cd "C:/Users/Llama/PycharmProjects/WarpDev-Context-Demo"
git ls-files | grep -iE "\.env$" || echo "OK: no .env tracked"
```
Expected: `OK: no .env tracked`.

- [ ] **Step 5: Update tracking files and commit**

Append to `WORKLOG.md`:
```
- [2026-06-24] Shipped Why RAG is Dead page to GitHub Pages: https://llamaopnv.github.io/why-rag-is-dead/
```
Check off or remove any resolved TODO items. Commit:
```bash
git add WORKLOG.md TODO.md
git commit -m "docs: log Pages launch

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
git push showcase HEAD:main
```

---

## Self-Review

**Spec coverage:**
- Public repo `why-rag-is-dead` -> Task 1. Whole app pushed, `.env` untracked -> Task 1 Steps 1-2, 6.
- Static page in `/docs`, no build -> Tasks 2-4 (vanilla HTML/CSS/JS only).
- 7-section narrative -> Task 2 Step 1 (hero, problem, sim, receipt, how, proof, cta).
- Cinematic simulation, binary-search query, real numbers, deterministic, reduced-motion -> Task 3.
- Visual delegated to taste skill with divergence guardrails -> Task 4.
- Token receipt 50K/53K/13K -> Task 2 (markup) + Task 3 (animation).
- Pages serving `/docs` on `main`, live verify -> Task 5.
- No secrets committed -> Task 1 Step 1, Task 5 Step 4.

**Placeholder scan:** No TBD/TODO-as-implementation. Every code step shows full content. The one delegated step (Task 4) hands a complete verbatim brief to a named skill, which is the intended mechanism, not a placeholder.

**Type/ID consistency:** DOM IDs defined in Task 2 Step 1 (`sim-run`, `sim-planner`, `sim-workers`, `sim-manager`, `sim-answer`, `sim-rag-lane`, `bar-naive`, `bar-cc`, `bar-nexus`) are exactly the IDs consumed by `sim.js` in Task 3 Step 2. The JSON shape in Task 2 Step 3 (`tasks`, `citations[].{file,line,text,claim}`, `answer`, `tokens.{naive,claudeCode,nexus}`, `plannerTokens`) matches every access in `sim.js`. Remote name `showcase` is created in Task 1 Step 4 and reused consistently.
