import { downloadCsv } from "./csv.js";

const labels = { added: "Toegevoegd", removed: "Verwijderd", moved: "Verplaatst", retyped: "Type gewijzigd", uncertain: "Controle nodig" };

export function renderComparison(panel, comparison, inspect) {
  panel.querySelector("#previous-name").textContent = comparison.previous_name;
  const counts = {};
  const list = panel.querySelector("#symbol-changes");
  list.replaceChildren();
  for (const change of comparison.changes) {
    counts[change.kind] = (counts[change.kind] || 0) + 1;
    const row = document.createElement("li");
    const button = document.createElement("button");
    const from = change.before?.type;
    const to = change.after?.type;
    const symbol = change.after ?? change.before;
    const name = from && to && from !== to ? `${from} → ${to}` : symbol.type;
    button.textContent = `${labels[change.kind]} · ${name} · ${symbol.x}, ${symbol.y} mm`;
    button.addEventListener("click", () => inspect(symbol, change.after?.id));
    row.append(button);
    list.append(row);
  }
  panel.querySelector("#revision-summary").textContent = Object.entries(counts)
    .map(([kind, count]) => `${labels[kind]} ${count}`).join(" · ") || "Geen symboolwijzigingen.";
  const materialRows = panel.querySelector("#material-changes");
  materialRows.replaceChildren();
  for (const item of comparison.materials) {
    const row = materialRows.insertRow();
    for (const value of [item.description, item.before, item.after, item.delta > 0 ? `+${item.delta}` : item.delta, item.unit]) {
      row.insertCell().textContent = value;
    }
  }
  panel.querySelector("#no-material-changes").hidden = comparison.materials.length > 0;
  panel.querySelector("#revision-csv").disabled = !comparison.materials.length;
  panel.querySelector("#revision-csv").onclick = () => downloadCsv("materiaaldelta.csv", [
    ["Omschrijving", "ETIM", "Eenheid", "Vorige", "Huidige", "Verschil"],
    ...comparison.materials.map(item => [item.description, item.etim_code, item.unit, item.before, item.after, item.delta]),
  ]);
  panel.hidden = false;
}
