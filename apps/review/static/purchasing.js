import { downloadCsv } from "./csv.js";

function materialKey(item) {
  return JSON.stringify([item.description, item.etim_code, item.unit]);
}

export function groupMaterials(items) {
  const grouped = new Map();
  for (const item of items) {
    const key = materialKey(item);
    const current = grouped.get(key);
    if (current) current.quantity += item.quantity;
    else grouped.set(key, { ...item });
  }
  return [...grouped.values()].filter(item => item.quantity > 0);
}

export function orderRow(item, settings) {
  const packSize = Number(settings.packSize);
  const price = Number(settings.price);
  const sku = settings.sku.trim();
  if (!sku || !Number.isSafeInteger(packSize) || packSize < 1 ||
      (settings.price !== "" && (!Number.isFinite(price) || price < 0))) return null;
  const packs = Math.ceil(item.quantity / packSize);
  return [sku, item.description, item.unit, item.quantity, packSize, packs, packs * packSize,
    settings.price === "" ? "" : price, settings.price === "" ? "" : Number((price * packs).toFixed(2))];
}

export class Purchasing {
  constructor(panel) {
    this.panel = panel;
    this.entries = [];
    try {
      this.catalog = new Map(JSON.parse(localStorage.getItem("imjan-purchasing") || "[]"));
    } catch {
      this.catalog = new Map();
    }
    panel.querySelector("form").addEventListener("submit", event => {
      event.preventDefault();
      const rows = this.entries.map(({ item, fields }) => orderRow(item, this.values(fields)));
      if (rows.some(row => row === null)) {
        panel.querySelector("[role=status]").textContent = "Vul voor elk materiaal een SKU en geldige verpakkingsgrootte in.";
        return;
      }
      downloadCsv("leveranciersbestelling.csv", [
        ["SKU", "Omschrijving", "Eenheid", "Nodig", "Per verpakking", "Verpakkingen", "Te bestellen", "Prijs per verpakking (EUR)", "Totaal excl. btw (EUR)"],
        ...rows,
      ]);
    });
  }

  values(fields) {
    return Object.fromEntries(Object.entries(fields).map(([key, field]) => [key, field.value.trim()]));
  }

  render(items) {
    const body = this.panel.querySelector("tbody");
    body.replaceChildren();
    this.entries = groupMaterials(items).map(item => {
      const key = materialKey(item);
      const saved = this.catalog.get(key) ?? { sku: "", packSize: "1", price: "" };
      const row = body.insertRow();
      row.insertCell().textContent = item.description;
      row.insertCell().textContent = `${item.quantity} ${item.unit}`;
      const fields = {};
      for (const [name, label] of [["sku", "Leveranciers-SKU"], ["packSize", "Aantal per verpakking"], ["price", "Prijs per verpakking"]]) {
        const field = document.createElement("input");
        field.setAttribute("aria-label", `${label} voor ${item.description}`);
        field.value = saved[name] ?? "";
        if (name !== "sku") {
          field.type = "number";
          field.min = name === "packSize" ? "1" : "0";
          field.step = name === "packSize" ? "1" : "0.01";
        }
        field.required = name !== "price";
        row.insertCell().append(field);
        fields[name] = field;
      }
      const packs = row.insertCell();
      const update = () => {
        const size = fields.packSize.valueAsNumber;
        packs.textContent = Number.isSafeInteger(size) && size > 0 ? Math.ceil(item.quantity / size) : "—";
        this.catalog.set(key, this.values(fields));
        this.panel.querySelector("[role=status]").textContent = "";
        try {
          localStorage.setItem("imjan-purchasing", JSON.stringify([...this.catalog]));
        } catch {
          this.panel.querySelector("[role=status]").textContent = "Instellingen konden alleen voor deze sessie worden bewaard.";
        }
      };
      for (const field of Object.values(fields)) field.addEventListener("input", update);
      const size = fields.packSize.valueAsNumber;
      packs.textContent = Number.isSafeInteger(size) && size > 0 ? Math.ceil(item.quantity / size) : "—";
      return { item, fields };
    });
    this.panel.hidden = !this.entries.length;
  }
}
