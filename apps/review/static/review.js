import { DrawingViewer } from "./drawing.js";

const $ = id => document.getElementById(id);
const state = { project: null, symbols: [], selected: null, placing: false, busy: false };
const money = new Intl.NumberFormat("nl-BE", { style: "currency", currency: "EUR" });
const viewer = new DrawingViewer($("drawing"), {
  select: selectSymbol,
  isPlacing: () => state.placing && !state.busy,
  place(x, y) {
    $("x").value = x.toFixed(2);
    $("y").value = y.toFixed(2);
  },
});

function projectUrl(suffix = "") {
  return `/projects/${encodeURIComponent(state.project.id)}${suffix}`;
}

async function request(url, options) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const error = new Error(typeof data?.detail === "string" ? data.detail : `Verzoek mislukt (HTTP ${response.status}).`);
    error.status = response.status;
    throw error;
  }
  return data;
}

function status(message = "", error = false) {
  $("status").textContent = message;
  $("status").hidden = !message;
  $("status").classList.toggle("error", error);
}

async function waitForAnalysis() {
  while (["uploaded", "processing"].includes(state.project.status)) {
    let run;
    try {
      run = await request(projectUrl("/pipeline"));
    } catch (error) {
      if (error.status !== 404) throw error;
    }
    const stage = run?.stages.find(item => item.stage_id === run.current_stage);
    const step = stage?.name || run?.current_stage;
    const progress = run ? `${Math.round(run.progress * 100)}%` : "";
    status(run ? ["Analyse bezig", step, progress].filter(Boolean).join(" · ") : "Analyse wacht op de worker…");
    await new Promise(resolve => setTimeout(resolve, 1800));
    const update = await request(projectUrl("/status"));
    state.project.status = update.status;
  }
  if (state.project.status !== "done") {
    const run = await request(projectUrl("/pipeline")).catch(() => null);
    throw new Error(run?.error || "De analyse is mislukt.");
  }
}

function renderMaterials(materials) {
  $("total").textContent = materials.total_price === null ? "" : `${money.format(materials.total_price)} excl. btw`;
  const rows = materials.items.map(item => {
    const row = document.createElement("tr");
    for (const value of [item.description, item.quantity, item.unit, item.total_price === null ? "—" : money.format(item.total_price)]) {
      row.insertCell().textContent = value;
    }
    return row;
  });
  if (!rows.length) {
    const row = document.createElement("tr");
    const cell = row.insertCell();
    cell.colSpan = 4;
    cell.textContent = "Geen materialen op basis van de huidige symbolen.";
    rows.push(row);
  }
  $("items").replaceChildren(...rows);
}

async function refreshReview() {
  const [symbols, materials] = await Promise.all([
    request(projectUrl("/review/symbols")),
    request(projectUrl("/materials?review=true")),
  ]);
  state.symbols = symbols;
  viewer.symbols = symbols;
  $("symbols").replaceChildren(...symbols.map((symbol, index) =>
    new Option(`${index + 1}. ${symbol.type}`, symbol.id)));
  $("count").textContent = symbols.length;
  selectSymbol(symbols.some(symbol => symbol.id === state.selected) ? state.selected : null);
  renderMaterials(materials);
}

function selectSymbol(id) {
  if (state.busy && id !== state.selected && id !== null) return;
  const symbol = state.symbols.find(item => item.id === id);
  state.selected = symbol?.id ?? null;
  state.placing = false;
  $("drawing").classList.remove("placing");
  $("symbols").value = state.selected ?? "";
  $("edit").hidden = !symbol;
  $("cancel").hidden = true;
  $("remove").hidden = !symbol;
  if (symbol) {
    $("edit-title").textContent = "Symbool wijzigen";
    const source = { human: "Handmatig", vector: "DXF-vector", detector: "Detectie", vlm: "Visueel model" };
    $("provenance").textContent = `${source[symbol.source] || symbol.source} · ${Math.round(symbol.confidence * 100)}% zekerheid`;
    $("type").value = symbol.type;
    $("x").value = symbol.x;
    $("y").value = symbol.y;
  }
  viewer.selected = state.selected;
  viewer.draw();
}

async function openProject(project) {
  state.project = project;
  $("project-name").textContent = project.name || "DXF-project";
  $("workspace").hidden = true;
  $("materials").hidden = true;
  state.selected = null;
  await waitForAnalysis();
  const preview = request(projectUrl("/review/drawing")).catch(error => ({ paths: [], error: error.message }));
  const types = await request("/review/symbol-types");
  $("type").replaceChildren(...types.map(type => new Option(type, type)));
  await refreshReview();
  const drawing = await preview;
  $("drawing-note").textContent = drawing.error || (drawing.truncated
    ? "De tekening is ingekort. Sleep om te verschuiven en scroll om in te zoomen."
    : "Sleep om te verschuiven. Scroll om in te zoomen.");
  $("xlsx").href = projectUrl("/materials?review=true&format=xlsx");
  $("pdf").href = projectUrl("/materials?review=true&format=pdf");
  $("workspace").hidden = false;
  $("materials").hidden = false;
  viewer.load(drawing.paths);
  status();
}

async function runUpload(action) {
  $("start").disabled = true;
  try {
    await action();
  } catch (error) {
    status(error.message, true);
  } finally {
    $("start").disabled = false;
  }
}

$("upload").addEventListener("submit", event => {
  event.preventDefault();
  const file = $("file").files[0];
  if (!file?.name.toLowerCase().endsWith(".dxf")) {
    status("Kies een DXF-bestand.", true);
    return;
  }
  runUpload(async () => {
    status("DXF uploaden…");
    const body = new FormData();
    body.set("file", file);
    const project = await request("/projects", { method: "POST", body });
    const url = new URL(location.href);
    url.searchParams.set("project", project.id);
    history.replaceState(null, "", url);
    await openProject(project);
  });
});

const existingProject = new URL(location.href).searchParams.get("project");
if (existingProject) {
  runUpload(async () => {
    status("Project laden…");
    const project = await request(`/projects/${encodeURIComponent(existingProject)}`);
    if (project.file_type !== "dxf") throw new Error("Kies een DXF-project.");
    await openProject(project);
  });
}

$("symbols").addEventListener("change", event => selectSymbol(event.target.value));
$("zoom-in").addEventListener("click", () => viewer.zoom(1.3));
$("zoom-out").addEventListener("click", () => viewer.zoom(1 / 1.3));
$("fit").addEventListener("click", () => viewer.fit());
$("cancel").addEventListener("click", () => selectSymbol(null));

$("add").addEventListener("click", () => {
  selectSymbol(null);
  state.placing = true;
  $("drawing").classList.add("placing");
  $("edit").hidden = false;
  $("cancel").hidden = false;
  $("edit-title").textContent = "Symbool toevoegen";
  $("provenance").textContent = "Klik op de tekening of vul de coördinaten in.";
  $("type").selectedIndex = 0;
  $("x").value = "";
  $("y").value = "";
  $("type").focus();
});

async function saveCorrection(correction) {
  if (state.busy) return;
  state.busy = true;
  for (const id of ["start", "add", "save", "remove", "cancel", "symbols"]) $(id).disabled = true;
  status("Correctie opslaan…");
  let saved = false;
  try {
    const result = await request(projectUrl("/corrections?review=true"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(correction),
    });
    saved = true;
    if (correction.action === "add") state.selected = result.id;
    await refreshReview();
    status("Correctie opgeslagen.");
  } catch (error) {
    if (error.status === 409) await refreshReview().catch(() => {});
    status(saved ? "Correctie opgeslagen. Vernieuw de pagina om de review opnieuw te laden." : error.message, true);
  } finally {
    state.busy = false;
    for (const id of ["start", "add", "save", "remove", "cancel", "symbols"]) $(id).disabled = false;
  }
}

$("edit").addEventListener("submit", event => {
  event.preventDefault();
  const symbol = state.symbols.find(item => item.id === state.selected);
  const new_type = $("type").value;
  const new_x = $("x").valueAsNumber;
  const new_y = $("y").valueAsNumber;
  if (!symbol) {
    saveCorrection({ action: "add", new_type, new_x, new_y });
  } else if (new_type !== symbol.type) {
    saveCorrection({ action: "change_type", symbol_id: symbol.id, new_type, new_x, new_y });
  } else if (new_x !== symbol.x || new_y !== symbol.y) {
    saveCorrection({ action: "move", symbol_id: symbol.id, new_x, new_y });
  }
});

$("remove").addEventListener("click", () => {
  if (state.selected) saveCorrection({ action: "remove", symbol_id: state.selected });
});
