# Design: "Why R.A.G is Dead" — landing page + live pipeline simulation

Date: 2026-06-24
Status: Approved (brainstorming), pending spec review
Owner: Olivier (LlamaopNV)

## Goal

Publish a public showcase that argues retrieval-augmented generation is the wrong
abstraction, and demonstrates NEXUS's verified-microagent workflow as the
replacement. The page must feel alive and convincing, run entirely client-side on
GitHub Pages, and look deliberately distinct from the owner's existing pages.

One-line claim: retrieval should not mean stuffing chunks into context. It should
mean verified microagents fetching only what is true.

## Scope

In scope:
- A new public GitHub repo `LlamaopNV/why-rag-is-dead`.
- The entire existing NEXUS app pushed to that repo (so the page links to real,
  browsable source).
- A self-contained static landing page in `/docs` with a cinematic, scripted
  simulation of the NEXUS pipeline.
- GitHub Pages enabled, serving `/docs` from the default branch (`main`).

Out of scope:
- Any live backend, Claude API call, or Ollama execution from the page. GitHub
  Pages is static hosting; the simulation is canned and deterministic.
- Changing the NEXUS app's own behavior. The app ships as-is (current branch work
  committed first).
- A build toolchain for the page. The page is vanilla HTML/CSS/JS, no bundler.

## Repo and deployment architecture

- Create public repo `LlamaopNV/why-rag-is-dead` via `gh`.
- Commit the in-progress work on the current branch first (modified backend/
  frontend files plus the new `claude_code_benchmark.py` and `BenchmarkStatus.tsx`).
  Confirm `nexus/.env` stays untracked (it is gitignored and currently untracked).
- Push the whole repo (app + page) to the new remote.
- Default branch: `main`.
- Landing page lives in `/docs` as a single self-contained static site:
  `docs/index.html`, `docs/styles.css`, `docs/sim.js` (plus any assets). No build
  step, no GitHub Actions, no framework. This is the most robust Pages setup.
- Enable Pages via `gh api` (or instruct the owner if the API path is gated),
  source = `main` branch, `/docs` folder.

Secrets: no API keys, tokens, or `.env` values are written anywhere in the page or
committed. The page references only public, non-secret data.

## Page narrative (scroll structure)

1. **Hero** — the claim "Why R.A.G is Dead." Subhead reframes retrieval as verified
   microagent fetching.
2. **The problem** — RAG's failure modes: hallucinated/irrelevant chunks, no
   provenance, context-window bloat. Sets up the foil.
3. **The live simulation** (centerpiece) — see below.
4. **The token receipt** — animated comparison bars: Naive dump ~50K, Claude Code
   ~53K, NEXUS ~13K. The "95-99% less context" payoff.
5. **How it actually works** — the four-stage pipeline diagram
   (Planner -> Workers -> Manager -> Main LLM), with shell verification called out
   as the thing RAG structurally cannot do.
6. **Proof / provenance** — every claim links to a real `file:line`; contrast with
   RAG's unverifiable chunks.
7. **CTA** — links to the repo, the architecture, and run-it-yourself instructions.

## The simulation (centerpiece)

A scripted, deterministic, client-side cinematic. It always completes; it never
calls a network service.

- Trigger: a **Run query** button. Replayable.
- Query (fixed): "Where is binary search implemented and how does it handle an
  empty array?" run against the demo codebase (TheAlgorithms/Python).
- Timeline, driven by a JS state machine over a hardcoded script using NEXUS's real
  numbers:
  1. **Planner** emits ~500 tokens, decomposes the query into 3-5 atomic shell
     tasks scoped to relevant directories. Token counter ticks.
  2. **Workers** spin up in parallel, each showing a sandboxed `grep`/`sed` command
     and the line it extracted, formatted as a structured citation.
  3. **Manager** runs `sed -n '{line}p'` on each citation; each flips from "claimed"
     to a verified state one by one (deterministic shell verification, no LLM).
  4. **Main LLM** streams a cited answer; every citation is a real `file:line`.
  5. A parallel **RAG lane** dumps ~50K tokens of unverified chunks, for contrast.
  6. Token counters and comparison bars resolve to the final receipt.
- All content is canned in `sim.js` as a timeline/script. No randomness that could
  desync; timing is scripted with deterministic delays.

The simulation panel is the one place monospace and a dark "terminal" treatment are
used, intentionally quarantined from the editorial body.

## Visual direction

Delegated to the design-taste-frontend skill, which runs its own audit and anti-slop
pre-flight. Hard constraints derived from auditing the owner's existing pages:

Existing pages audited:
- `Claude_Code_Empowerments-` and `/skill-installer/`: bg `#0a0a0b` near-black,
  Geist + Geist Mono (mono-forward), amber `#e8a33d` plus rainbow accents, dark dev
  panels.
- `tdd-heartbeat`: bg `#06080b` near-black, mono-forward, neon vitals palette
  (green/cyan/blue/amber/red), glassy translucent panels.

Shared house style to AVOID repeating: near-black background, monospace-dominant
type, neon multi-accent, glassy panels, dashboard layout.

Divergence guardrails for the new page:
- **Editorial, not dashboard.** A light / paper / high-contrast non-black canvas,
  framed as a manifesto/obituary for RAG, with magazine-grade typography.
- **Serif or distinctive display headline**, not monospace, for the argument.
- **One opinionated accent color**, not a neon rainbow.
- **Monospace allowed but quarantined** inside the dark simulated-terminal panel, so
  the light editorial body and the dark terminal contrast becomes a feature.
- Fast: static, no heavy dependencies.

The taste skill makes final color/type/layout calls within these guardrails.

## Components (page)

- `docs/index.html` — semantic structure for the seven sections; the simulation
  panel markup with labelled stage regions and counters.
- `docs/styles.css` — the editorial design system (light canvas, display headline,
  single accent) plus the quarantined dark terminal styling.
- `docs/sim.js` — the deterministic timeline state machine: stage transitions, token
  counters, citation verification flips, RAG-vs-NEXUS bar animation, replay.

Each is independently understandable: HTML is structure, CSS is the look, JS is the
one behavior (the simulation). No shared mutable state beyond the DOM the simulation
drives.

## Data (canned)

The simulation script in `sim.js` holds: the query, the planner task list, per-worker
shell commands and extracted lines (binary search citations in the demo codebase),
the manager verification steps, the streamed cited answer, and the four token totals
(Naive ~50K, Claude Code ~53K, NEXUS ~13K, Planner ~500). These mirror the README's
published numbers; no claim exceeds what the app already states.

## Error handling

- The page never makes network calls during the simulation, so there are no runtime
  fetch failures to handle. The Run button is idempotent and re-runnable.
- If reduced-motion is preferred by the OS, the simulation jumps to its end state
  instead of animating (accessibility).
- Pages enablement: if the `gh api` Pages call is unavailable in this environment,
  the spec's fallback is to instruct the owner to enable Pages in repo settings
  (`main` / `/docs`).

## Testing / verification

- Open `docs/index.html` locally and run the simulation end to end; confirm all
  stages reach the verified state and the token bars resolve to the stated numbers.
- Confirm reduced-motion path lands on the final state.
- After push and Pages enable, load the live URL and confirm it renders and runs.
- Confirm `.env` and any secret remain untracked (`git ls-files | grep .env` empty).
- Run the taste skill's pre-flight check before declaring the visual done.

## Open questions

None blocking. Visual specifics are intentionally delegated to the taste skill within
the guardrails above.
