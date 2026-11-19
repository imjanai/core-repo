export class Installation {
  constructor(panel, request, focus) {
    this.panel = panel;
    this.request = request;
    this.focus = focus;
    this.items = [];
    this.pending = new Set();
    this.element("group").addEventListener("change", () => this.render());
    this.element("open-only").addEventListener("change", () => this.render());
  }

  element(id) { return this.panel.querySelector(`#installation-${id}`); }

  async load(projectId) {
    if (this.projectId !== projectId) {
      this.panel.open = false;
      this.items = [];
    }
    this.projectId = projectId;
    const loadId = this.loadId = (this.loadId || 0) + 1;
    try {
      const items = await this.request(this.url());
      if (this.loadId !== loadId) return;
      this.items = items;
      this.element("status").textContent = "";
    } catch (error) {
      if (this.loadId !== loadId) return;
      this.element("status").textContent = error.message;
    }
    this.panel.hidden = false;
    this.render();
  }

  url() { return `/projects/${encodeURIComponent(this.projectId)}/installation`; }

  render() {
    const done = this.items.filter(item => item.installed).length;
    this.element("progress").textContent = `· ${done} van ${this.items.length} geïnstalleerd`;
    const groups = new Map();
    const byRoom = this.element("group").value === "room";
    const onlyOpen = this.element("open-only").checked;
    for (const item of this.items) {
      if (onlyOpen && item.installed) continue;
      const name = byRoom ? item.room || "Geen ruimte" : item.symbol.circuit || "Geen kring";
      if (!groups.has(name)) groups.set(name, []);
      groups.get(name).push(item);
    }
    const wrapper = this.element("items");
    wrapper.replaceChildren();
    if (!groups.size) {
      wrapper.textContent = this.items.length ? "Geen openstaande punten." : "Geen symbolen om af te vinken.";
      return;
    }
    for (const [name, items] of [...groups.entries()].sort(([a], [b]) => a.localeCompare(b, "nl"))) {
      const heading = document.createElement("h3");
      heading.textContent = name;
      wrapper.append(heading);
      for (const item of items) {
        const { symbol } = item;
        const row = document.createElement("div");
        row.className = "installation-row";
        const label = document.createElement("label");
        const check = document.createElement("input");
        check.type = "checkbox";
        check.checked = item.installed;
        check.disabled = this.pending.has(symbol.id);
        check.addEventListener("change", () => this.update(item, check));
        label.append(check, `${symbol.type} · ${symbol.x}, ${symbol.y} mm`);
        const view = document.createElement("button");
        view.textContent = "Op tekening";
        view.addEventListener("click", () => this.focus(symbol, symbol.id));
        row.append(label, view);
        wrapper.append(row);
      }
    }
  }

  async update(item, check) {
    const projectId = this.projectId;
    const id = item.symbol.id;
    this.pending.add(id);
    check.disabled = true;
    try {
      await this.request(`${this.url()}/${encodeURIComponent(id)}`, {
        method: "PUT", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ installed: check.checked }),
      });
      if (this.projectId !== projectId) return;
      const current = this.items.find(row => row.symbol.id === id);
      if (current) current.installed = check.checked;
      this.element("status").textContent = "";
    } catch (error) {
      if (this.projectId === projectId) this.element("status").textContent = error.message;
    } finally {
      this.pending.delete(id);
      if (this.projectId === projectId) this.render();
    }
  }
}
