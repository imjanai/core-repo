const statuses = { done: "Klaar", processing: "Bezig", uploaded: "In wachtrij", failed: "Mislukt" };
const date = new Intl.DateTimeFormat("nl-BE", { dateStyle: "short", timeStyle: "short" });

export function reviewUrl(current, previous = null) {
  const params = new URLSearchParams({ project: current });
  if (previous) params.set("previous", previous);
  return `/review/?${params}`;
}

export function mountLibrary(panel, request) {
  const find = id => panel.querySelector(`#library-${id}`);
  const selection = { previous: null, current: null };
  let page = 1;
  let total = 0;
  let requestId = 0;
  const pageSize = 8;
  const status = find("status");

  function showSelection() {
    const { previous, current } = selection;
    find("selection").textContent = (previous || current)
      ? `Vorige: ${previous?.name || "nog kiezen"} · Huidige: ${current?.name || "nog kiezen"}`
      : "Kies de vorige en huidige tekening.";
    find("compare").disabled = !previous || !current;
  }

  function render(projects) {
    const table = find("projects");
    table.replaceChildren();
    for (const project of projects) {
      const row = table.insertRow();
      const link = document.createElement("a");
      link.href = reviewUrl(project.id);
      link.textContent = project.name || "Naamloos project";
      row.insertCell().append(link);
      const timestamp = new Date(project.created_at);
      row.insertCell().textContent = Number.isNaN(timestamp.valueOf()) ? "—" : date.format(timestamp);
      row.insertCell().textContent = statuses[project.status] || project.status;
      const actions = row.insertCell();
      if (project.status !== "done") continue;

      for (const [role, label] of [["previous", "Als vorige"], ["current", "Als huidige"]]) {
        const button = document.createElement("button");
        button.textContent = label;
        button.setAttribute("aria-pressed", String(selection[role]?.id === project.id));
        button.addEventListener("click", () => {
          const other = role === "previous" ? "current" : "previous";
          if (selection[other]?.id === project.id) selection[other] = null;
          selection[role] = selection[role]?.id === project.id ? null : project;
          showSelection();
          for (const item of table.querySelectorAll("[aria-pressed]")) {
            item.setAttribute("aria-pressed", String(selection[item.dataset.role]?.id === item.dataset.project));
          }
        });
        button.dataset.role = role;
        button.dataset.project = project.id;
        actions.append(button, " ");
      }
    }
  }

  async function load() {
    const id = ++requestId;
    const params = new URLSearchParams({
      file_type: "dxf", page, page_size: pageSize, include_download_url: "false",
      q: find("query").value, status: find("filter").value,
    });
    if (!params.get("status")) params.delete("status");
    status.textContent = "Projecten laden…";
    find("back").disabled = true;
    find("next").disabled = true;
    try {
      const result = await request(`/projects?${params}`);
      if (id !== requestId) return;
      total = result.total;
      const last = Math.max(1, Math.ceil(total / pageSize));
      if (page > last) {
        page = last;
        return load();
      }
      render(result.items);
      find("page").textContent = `Pagina ${page} van ${last}`;
      status.textContent = total ? "" : "Geen DXF-projecten gevonden.";
      find("back").disabled = page <= 1;
      find("next").disabled = page >= last;
    } catch (error) {
      if (id === requestId) status.textContent = error.message;
    }
  }

  panel.addEventListener("toggle", () => { if (panel.open) load(); });
  find("search").addEventListener("submit", event => {
    event.preventDefault();
    page = 1;
    load();
  });
  find("back").addEventListener("click", () => { if (page > 1) { page -= 1; load(); } });
  find("next").addEventListener("click", () => { if (page * pageSize < total) { page += 1; load(); } });
  find("compare").addEventListener("click", () => {
    if (selection.current && selection.previous) {
      location.assign(reviewUrl(selection.current.id, selection.previous.id));
    }
  });
}
