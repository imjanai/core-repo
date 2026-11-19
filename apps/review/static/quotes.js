const currency = new Intl.NumberFormat("nl-BE", { style: "currency", currency: "EUR" });
const dates = new Intl.DateTimeFormat("nl-BE", { dateStyle: "short", timeStyle: "short" });
const key = item => JSON.stringify([item.description, item.unit, item.etim_code]);
const displayMoney = cents => currency.format(cents / 100);
const cents = input => Math.round(input.valueAsNumber * 100);
const quoteUrl = id => `/quotes/${encodeURIComponent(id)}/pdf`;

export class Quotes {
  constructor(panel, request) {
    this.panel = panel;
    this.request = request;
    this.items = [];
    this.element("form").addEventListener("input", () => this.showTotal());
    this.element("form").addEventListener("submit", event => {
      event.preventDefault();
      this.save();
    });
    this.element("compare").addEventListener("submit", event => {
      event.preventDefault();
      const baseline = this.element("baseline").value;
      const current = this.element("current").value;
      if (baseline === current) {
        this.status("Kies twee verschillende offerteversies.");
        return;
      }
      location.assign(`${quoteUrl(current)}?${new URLSearchParams({ baseline })}`);
    });
  }

  element(id) { return this.panel.querySelector(`#quote-${id}`); }

  status(message) { this.element("status").textContent = message; }

  url(projectId) { return `/projects/${encodeURIComponent(projectId)}/quotes`; }

  async load(projectId, previousId) {
    const sameProject = this.projectId === projectId;
    this.projectId = projectId;
    this.previousId = previousId;
    const loadId = this.loadId = (this.loadId || 0) + 1;
    this.element("save").disabled = true;
    this.status("");
    if (!sameProject) {
      this.panel.open = false;
      this.element("form").reset();
      this.items = [];
    }
    this.panel.hidden = false;
    try {
      const [draft, current, previous] = await Promise.all([
        this.request(`${this.url(projectId)}/draft`),
        this.request(this.url(projectId)),
        previousId ? this.request(this.url(previousId)).catch(() => []) : [],
      ]);
      if (loadId !== this.loadId) return;
      const last = current[0] || previous[0];
      const previousPrices = new Map(last?.materials.map(item => [key(item), item.unit_price]));
      const edits = new Map(this.items.map(({ item, input }) => [key(item), input.value]));
      const body = this.element("materials");
      body.replaceChildren();
      this.items = draft.map(item => {
        const row = body.insertRow();
        row.insertCell().textContent = item.description;
        row.insertCell().textContent = `${item.quantity} ${item.unit}`;
        const input = document.createElement("input");
        input.type = "number";
        input.min = "0";
        input.max = "1000000000";
        input.step = ".01";
        input.required = true;
        input.setAttribute("aria-label", `Eenheidsprijs voor ${item.description}`);
        const price = previousPrices.get(key(item)) ?? item.unit_price;
        input.value = edits.get(key(item)) ?? (price === null ? "" : (price / 100).toFixed(2));
        row.insertCell().append(input);
        return { item, input };
      });
      if (!sameProject) {
        this.element("title").value = `Offerte ${current.length + 1}`;
        this.element("customer").value = last?.customer || "";
        if (last) {
          this.element("hours").value = last.labour_hours;
          this.element("rate").value = (last.hourly_rate / 100).toFixed(2);
          this.element("fee").value = (last.fixed_fee / 100).toFixed(2);
        }
      }
      this.renderVersions(current, previous);
      this.showTotal();
      this.element("save").disabled = false;
    } catch (error) {
      if (loadId === this.loadId) this.status(error.message);
    }
  }

  showTotal() {
    const prices = this.items.map(({ item, input }) => item.quantity * cents(input));
    const labour = Math.round(cents(this.element("hours")) * cents(this.element("rate")) / 100);
    const total = prices.reduce((sum, price) => sum + price, labour + cents(this.element("fee")));
    this.element("total").textContent = Number.isFinite(total)
      ? `Totaal excl. btw · ${displayMoney(total)}` : "Vul de ontbrekende prijzen in voor een totaal.";
  }

  renderVersions(current, previous) {
    const list = this.element("versions");
    list.replaceChildren();
    this.element("empty").hidden = current.length > 0;
    for (const quote of current) {
      const row = document.createElement("li");
      const link = document.createElement("a");
      link.href = quoteUrl(quote.id);
      link.textContent = `${quote.title} · ${dates.format(new Date(quote.created_at))} · PDF`;
      row.append(link);
      list.append(row);
    }
    const baseline = this.element("baseline");
    const latest = this.element("current");
    baseline.replaceChildren(...[...previous, ...current].map(quote =>
      new Option(`${quote.project_name} · ${quote.title} · ${quote.id.slice(0, 8)}`, quote.id)));
    latest.replaceChildren(...current.map(quote => new Option(`${quote.title} · ${quote.id.slice(0, 8)}`, quote.id)));
    const firstAlternative = [...baseline.options].find(item => item.value !== latest.value);
    if (firstAlternative) baseline.value = firstAlternative.value;
    this.element("compare").hidden = !current.length || !firstAlternative;
  }

  async save() {
    const projectId = this.projectId;
    const title = this.element("title").value.trim();
    if (!title) {
      this.status("Vul een naam of versie in.");
      return;
    }
    this.element("save").disabled = true;
    try {
      await this.request(this.url(projectId), {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title, customer: this.element("customer").value.trim(),
          materials: this.items.map(({ item, input }) => ({ ...item, unit_price: cents(input) })),
          labour_hours: this.element("hours").value, hourly_rate: cents(this.element("rate")),
          fixed_fee: cents(this.element("fee")),
        }),
      });
      if (projectId !== this.projectId) return;
      await this.load(projectId, this.previousId);
      this.status("Offerteversie opgeslagen.");
    } catch (error) {
      if (projectId === this.projectId) this.status(error.message);
    } finally {
      if (projectId === this.projectId) this.element("save").disabled = false;
    }
  }
}
