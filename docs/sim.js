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
