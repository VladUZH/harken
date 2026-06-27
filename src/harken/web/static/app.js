// Progressive enhancement: filter the mention feed without a page reload.
// The server already renders the full feed; this swaps it for a filtered view
// by calling the JSON API. No framework, no CDN.
(function () {
  const filters = document.getElementById("filters");
  const feed = document.getElementById("feed");
  if (!filters || !feed) return;

  const query = filters.dataset.query;
  const state = { sentiment: "", source: "" };

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
    if (m.theme) parts.push(`<span class="tag theme">${esc(m.theme)}</span>`);
    parts.push(`</div>`);
    if (m.title) parts.push(`<div class="m-title">${esc(m.title)}</div>`);
    if (m.text) parts.push(`<div class="m-text">${esc(m.text.slice(0, 300))}</div>`);
    if (m.url)
      parts.push(`<a class="m-link" href="${esc(m.url)}" target="_blank" rel="noopener">view source ↗</a>`);
    parts.push(`</li>`);
    return parts.join("");
  }

  async function refresh() {
    const params = new URLSearchParams({ q: query, limit: "200" });
    if (state.sentiment) params.set("sentiment", state.sentiment);
    if (state.source) params.set("source", state.source);
    feed.style.opacity = "0.45";
    try {
      const res = await fetch("/api/mentions?" + params.toString());
      const rows = await res.json();
      feed.innerHTML = rows.length
        ? rows.map(card).join("")
        : `<li class="feed-empty">No mentions match this filter.</li>`;
    } catch (e) {
      feed.innerHTML = `<li class="feed-empty">Could not load mentions.</li>`;
    } finally {
      feed.style.opacity = "1";
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
        c.classList.toggle("active", c.dataset.value === val)
      );
    } else if (dim === "source") {
      // toggle source on/off
      state.source = state.source === val ? "" : val;
      filters.querySelectorAll('[data-filter="source"]').forEach((c) =>
        c.classList.toggle("active", c.dataset.value === state.source)
      );
    }
    refresh();
  });
})();
