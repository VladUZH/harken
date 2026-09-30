// Progressive enhancement: filter the mention feed without a page reload.
// The server already renders the full feed; this swaps it for a filtered view
// by calling the JSON API. No framework, no CDN.
(function () {
  // CSP blocks inline onchange handlers; wire switchers from this script instead.
  document.querySelectorAll("select[data-auto-submit]").forEach((select) => {
    select.addEventListener("change", () => {
      select.form?.submit();
    });
  });

  const scanForm = document.getElementById("scan-form");
  if (scanForm) {
    const scanStatus = document.getElementById("scan-status");
    const scanButtons = scanForm.querySelectorAll('button[type="submit"]');

    scanForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const query = scanForm.elements.query.value.trim();
      const sources = Array.from(scanForm.querySelectorAll('input[name="source"]:checked')).map(
        (input) => input.value
      );
      const mode = event.submitter && event.submitter.value === "backfill" ? "backfill" : "incremental";
      const projectId = scanForm.dataset.projectId ? Number(scanForm.dataset.projectId) : null;
      scanStatus.classList.remove("error", "warning");
      if (!query) {
        scanStatus.textContent = "Enter a keyword.";
        scanStatus.classList.add("error");
        scanForm.elements.query.focus();
        return;
      }
      if (!sources.length) {
        scanStatus.textContent = "Select at least one source.";
        scanStatus.classList.add("error");
        return;
      }

      scanButtons.forEach((button) => { button.disabled = true; });
      scanForm.setAttribute("aria-busy", "true");
      scanStatus.textContent = mode === "backfill" ? "Fetching older pages…" : "Scanning latest mentions…";
      try {
        const response = await fetch("/api/track", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Harken-CSRF": scanForm.dataset.csrf,
          },
          body: JSON.stringify({ query, sources, mode, pages: 3, project_id: projectId }),
        });
        const body = await response.json();
        if (!response.ok) {
          const detail = typeof body.detail === "string" ? body.detail : `HTTP ${response.status}`;
          throw new Error(detail);
        }
        const failures = Object.keys(body.errors || {});
        const successCount = sources.length - failures.length;
        if (successCount < 1) {
          scanStatus.textContent = failures.map((name) => `${name}: ${body.errors[name]}`).join(" · ");
          scanStatus.classList.add("error");
          return;
        }
        const suffix = failures.length
          ? ` · ${failures.length} source warning${failures.length === 1 ? "" : "s"}`
          : "";
        scanStatus.classList.toggle("warning", failures.length > 0);
        scanStatus.textContent = `${body.new} new from ${body.fetched} fetched${suffix}`;
        window.setTimeout(() => {
          const params = new URLSearchParams({ q: query });
          if (projectId) params.set("p", String(projectId));
          window.location.assign("/?" + params.toString());
        }, 350);
      } catch (error) {
        scanStatus.textContent = error.message || "Scan failed.";
        scanStatus.classList.add("error");
      } finally {
        scanButtons.forEach((button) => { button.disabled = false; });
        scanForm.removeAttribute("aria-busy");
      }
    });
  }

  const projectPanel = document.querySelector(".project-panel");
  if (projectPanel) {
    const projectStatus = document.getElementById("project-status");
    const projectDeleteDialog = document.getElementById("project-delete-dialog");
    const csrf = projectPanel.dataset.csrf;

    function setProjectStatus(message, kind = "") {
      if (!projectStatus) return;
      projectStatus.classList.remove("error", "warning");
      if (kind) projectStatus.classList.add(kind);
      projectStatus.textContent = message;
    }

    async function projectRequest(url, method, body) {
      const response = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json", "X-Harken-CSRF": csrf },
        body: body ? JSON.stringify(body) : undefined,
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || `HTTP ${response.status}`);
      return payload;
    }

    const createForm = document.getElementById("project-create-form");
    createForm?.addEventListener("submit", async (event) => {
      event.preventDefault();
      const name = createForm.elements.name.value.trim();
      if (!name) return;
      try {
        const project = await projectRequest("/api/projects", "POST", { name });
        window.location.assign("/?p=" + encodeURIComponent(project.id));
      } catch (error) {
        setProjectStatus(error.message || "Could not create project.", "error");
      }
    });

    const addForm = document.getElementById("project-add-form");
    addForm?.addEventListener("submit", async (event) => {
      event.preventDefault();
      const projectId = addForm.dataset.projectId;
      const query = addForm.elements.query.value;
      try {
        await projectRequest(`/api/projects/${projectId}/queries`, "POST", { query });
        window.location.assign("/?p=" + encodeURIComponent(projectId));
      } catch (error) {
        setProjectStatus(error.message || "Could not add keyword.", "error");
      }
    });

    projectPanel.addEventListener("click", async (event) => {
      const confirmProjectDelete = event.target.closest("[data-confirm-project-delete]");
      if (confirmProjectDelete) {
        confirmProjectDelete.disabled = true;
        try {
          await projectRequest(`/api/projects/${confirmProjectDelete.dataset.confirmProjectDelete}`, "DELETE");
          window.location.assign("/");
        } catch (error) {
          projectDeleteDialog?.close();
          setProjectStatus(error.message || "Could not delete project.", "error");
          confirmProjectDelete.disabled = false;
        }
        return;
      }
      const remove = event.target.closest("[data-project-remove]");
      const removeProjectId = projectPanel.dataset.projectId;
      if (remove && removeProjectId) {
        try {
          await projectRequest(`/api/projects/${removeProjectId}/queries`, "DELETE", {
            query: remove.dataset.projectRemove,
          });
          window.location.assign("/?p=" + encodeURIComponent(removeProjectId));
        } catch (error) {
          setProjectStatus(error.message || "Could not remove keyword.", "error");
        }
        return;
      }
      const removeProject = event.target.closest("[data-project-delete]");
      if (!removeProject) return;
      projectDeleteDialog?.showModal();
    });
  }

  const filters = document.getElementById("filters");
  const feed = document.getElementById("feed");
  if (!filters || !feed) return;

  const query = filters.dataset.query;
  const projectId = filters.dataset.projectId;
  const state = { sentiment: "", source: "" };
  const status = document.getElementById("feed-status");
  let requestId = 0;

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
    );
  }

  function card(m) {
    const sentiment = m.sentiment || "neutral";
    const parts = [];
    parts.push(`<li class="mention ${sentiment}"><span class="rail" aria-hidden="true"></span>`);
    parts.push(`<div class="m-top">`);
    parts.push(
      `<span class="m-src"><i class="srcbadge" style="--c: ${esc(m.source_color)}">${esc(m.source_glyph)}</i>${esc(m.source_label)}</span>`
    );
    if (m.author) parts.push(`<span class="m-author">${esc(m.author)}</span>`);
    parts.push(`<span class="m-time mono">${esc(m.reltime)}</span>`);
    if (m.score != null) parts.push(`<span class="m-score mono">▲ ${esc(m.score)}</span>`);
    parts.push(`<span class="m-spacer"></span>`);
    parts.push(`<span class="tag ${sentiment}">${esc(sentiment)}</span>`);
    if (projectId && !query && m.query) parts.push(`<span class="tag theme">${esc(m.query)}</span>`);
    if (m.theme) parts.push(`<span class="tag theme">${esc(m.theme)}</span>`);
    parts.push(`</div>`);
    if (m.title) parts.push(`<div class="m-title">${esc(m.title)}</div>`);
    if (m.text) parts.push(`<div class="m-text">${esc(m.text.slice(0, 300))}</div>`);
    if (m.url)
      parts.push(`<a class="m-link" href="${esc(m.url)}" target="_blank" rel="noopener noreferrer">view source ↗</a>`);
    parts.push(`</li>`);
    return parts.join("");
  }

  async function refresh() {
    const thisRequest = ++requestId;
    const params = new URLSearchParams({ limit: "200" });
    if (query) params.set("q", query);
    else if (projectId) params.set("p", projectId);
    if (state.sentiment) params.set("sentiment", state.sentiment);
    if (state.source) params.set("source", state.source);
    feed.style.opacity = "0.45";
    feed.setAttribute("aria-busy", "true");
    status?.classList.remove("error");
    try {
      const res = await fetch("/api/mentions?" + params.toString());
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const rows = await res.json();
      if (thisRequest !== requestId) return;
      feed.innerHTML = rows.length
        ? rows.map(card).join("")
        : `<li class="feed-empty">No mentions match this filter.</li>`;
      if (status) status.textContent = `Showing ${rows.length} mention${rows.length === 1 ? "" : "s"}.`;
    } catch (e) {
      if (thisRequest !== requestId) return;
      feed.innerHTML = `<li class="feed-empty error">Could not load mentions.</li>`;
      if (status) {
        status.classList.add("error");
        status.textContent = "Could not load mentions.";
      }
    } finally {
      if (thisRequest === requestId) {
        feed.style.opacity = "1";
        feed.removeAttribute("aria-busy");
      }
    }
  }

  filters.addEventListener("click", (e) => {
    const btn = e.target.closest(".chip");
    if (!btn) return;
    const dim = btn.dataset.filter; // "sentiment" | "source"
    const val = btn.dataset.value;

    if (dim === "sentiment") {
      state.sentiment = val;
      filters.querySelectorAll('[data-filter="sentiment"]').forEach((c) =>
        {
          const active = c.dataset.value === val;
          c.classList.toggle("active", active);
          c.setAttribute("aria-pressed", String(active));
        }
      );
    } else if (dim === "source") {
      // toggle source on/off
      state.source = state.source === val ? "" : val;
      filters.querySelectorAll('[data-filter="source"]').forEach((c) =>
        {
          const active = c.dataset.value === state.source;
          c.classList.toggle("active", active);
          c.setAttribute("aria-pressed", String(active));
        }
      );
    }
    refresh();
  });
})();
