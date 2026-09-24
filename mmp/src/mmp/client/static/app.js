// MMP Reference Client — chat UI + MCP Apps host (io.modelcontextprotocol/ui, 2026-01-26).
// The conversation lives only in this page (variable `messages`); nothing is stored anywhere.
(() => {
  "use strict";
  const $ = (s) => document.querySelector(s);
  const log = $("#log");
  let config = null;
  let bfs = null;
  let messages = [];
  let situation = null;
  const resources = new Map();

  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const el = (html) => { const t = document.createElement("template"); t.innerHTML = html.trim(); return t.content.firstElementChild; };
  const scroll = () => window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });

  async function api(path, body) {
    const r = await fetch(path, body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {});
    const data = await r.json().catch(() => ({ error: `HTTP ${r.status}` }));
    if (!r.ok) throw new Error(data.error || `HTTP ${r.status}`);
    return data;
  }

  function muni() { return (config.municipalities || []).find((m) => m.bfs === bfs) || { name: "?" }; }

  function renderBadge() {
    const b = $("#badge");
    if (config.sovereign) {
      b.className = "badge-bar sovereign";
      b.innerHTML = `<svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><rect x="3" y="8" width="12" height="8" rx="1.5"/><path d="M6 8V5.5a3 3 0 016 0V8"/></svg><span>Läuft auf Schweizer Public AI. Ihre Frage bleibt in der Schweiz.</span>`;
    } else if (config.mode === "rules") {
      b.className = "badge-bar other";
      b.textContent = "Demo-Modus ohne Sprachmodell (regelbasiert). Für den echten Assistenten PUBLIC_AI_API_KEY setzen.";
    } else {
      b.className = "badge-bar other";
      b.textContent = `Modell: ${config.model}. Vom Betreiber nicht als souverän deklariert – Ihre Frage kann die Schweiz verlassen.`;
    }
  }

  function welcome() {
    log.innerHTML = "";
    const m = muni();
    log.append(el(`<div class="bubble bot">Grüezi! Ich kenne die Dienstleistungen der Gemeinde ${esc(m.name)}. Beschreiben Sie Ihre Situation in eigenen Worten – ich zeige Ihnen, was zu tun ist.</div>`));
    const chips = el(`<div><div class="chips-label">Häufige Anliegen</div><div class="chips"></div></div>`);
    for (const text of [`Umzug nach ${m.name}`, "Kehricht & Entsorgung", "Kinderbetreuung"]) {
      const c = el(`<button class="chip" type="button">${esc(text)}</button>`);
      c.addEventListener("click", () => { $("#q").value = text; $("#q").focus(); });
      chips.querySelector(".chips").append(c);
    }
    log.append(chips);
  }

  // ---------------------------------------------------------------- chat turn
  async function sendMessage(text) {
    text = text.trim();
    if (!text) return;
    messages.push({ role: "user", content: text });
    log.append(el(`<div class="bubble me">${esc(text)}</div>`));
    const typing = el(`<div class="typing">Suche in den Angaben der Gemeinde …</div>`);
    log.append(typing); scroll();
    $("#send").disabled = true;
    try {
      const res = await api("/api/chat", { bfs, messages });
      typing.remove();
      situation = res.situation || situation;
      const reply = res.reply || (res.blocks && res.blocks.length ? "" : "Dazu habe ich nichts gefunden.");
      if (reply) { log.append(el(`<div class="bubble bot">${esc(reply)}</div>`)); messages.push({ role: "assistant", content: reply }); }
      for (const block of res.blocks || []) await renderBlock(block);
    } catch (e) {
      typing.remove();
      log.append(el(`<div class="error">${esc(e.message)}</div>`));
    } finally { $("#send").disabled = false; scroll(); }
  }

  let cardSlot = null;
  async function renderBlock(block) {
    if (block.type === "overview") renderOverview(block);
    else if (block.type === "previous") renderPrevious(block);
    else if (block.type === "app") { cardSlot = el(`<div class="card-slot"></div>`); log.append(cardSlot); await mountApp(cardSlot, block); }
    else if (block.type === "gap") renderGap(block);
  }

  function itemHtml(it) {
    return `<button class="item" type="button" data-id="${esc(it.id)}" data-bfs="${esc(it.bfs || bfs)}">
      <span class="meta"><span class="tier ${it.tier === "wayfinding" ? "way" : "info"}">${it.tier === "wayfinding" ? "Wegweiser" : "Information"}</span>
      <span class="mono">${it.ech0070 && it.ech0070 !== "unmapped" ? `eCH-0070 · ${esc(it.ech0070)}` : "nicht zugeordnet"}</span></span>
      <span class="title"><span>${esc(it.title)}</span><svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M7 4l5 5-5 5"/></svg></span>
      <span class="subtitle ${it.urgent ? "urgent" : ""}">${esc(it.subtitle)}</span></button>`;
  }

  function wireItems(root) {
    root.querySelectorAll(".item").forEach((btn) => btn.addEventListener("click", async () => {
      root.closest(".log").querySelectorAll(".item").forEach((b) => b.removeAttribute("aria-current"));
      btn.setAttribute("aria-current", "true");
      const target = cardSlot || log.appendChild(el(`<div class="card-slot"></div>`));
      target.innerHTML = `<div class="typing">Service Card wird geladen …</div>`;
      try {
        const block = await api("/api/card", { bfs: Number(btn.dataset.bfs), service_id: btn.dataset.id, messages, situation });
        target.innerHTML = "";
        await mountApp(target, block);
        target.scrollIntoView({ behavior: "smooth", block: "start" });
      } catch (e) { target.innerHTML = `<div class="error">${esc(e.message)}</div>`; }
    }));
  }

  function renderOverview(block) {
    const node = el(`<div class="items">
      <div class="notice"><svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true" style="flex-shrink:0;margin-top:1px"><circle cx="9" cy="9" r="7"/><path d="M9 5v5M9 12.5v.5"/></svg><span>${esc(block.notice)}</span></div>
      ${block.items.map(itemHtml).join("")}</div>`);
    const first = node.querySelector(".item"); if (first) first.setAttribute("aria-current", "true");
    log.append(node); wireItems(node);
  }

  function renderPrevious(block) {
    let node;
    if (block.item) {
      node = el(`<div class="dashed"><b>Auch bei Ihrer bisherigen Gemeinde ${esc(block.name)}</b>
        <span>Vor der Anmeldung muss die Abmeldung erfolgen. ${esc(block.name)} ist ebenfalls über MMP erreichbar:</span>
        <div class="items">${itemHtml(block.item)}</div></div>`);
      wireItems(node);
    } else if (block.name) {
      node = el(`<div class="dashed"><b>Auch bei Ihrer bisherigen Gemeinde</b><span>Wegzug in ${esc(block.name)} abmelden – ${esc(block.name)} ist noch nicht über MMP erreichbar. Bitte direkt bei der Gemeinde nachsehen.</span></div>`);
    } else {
      node = el(`<div class="dashed"><b>Auch bei Ihrer bisherigen Gemeinde</b><span>Wegzug abmelden – ich kann die Leistung Ihrer bisherigen Gemeinde abrufen, sobald Sie mir sagen, welche es ist.</span></div>`);
    }
    log.append(node);
  }

  function renderGap(block) {
    const c = block.contact || {};
    const tel = c.phone ? c.phone.replace(/\s/g, "") : null;
    const node = el(`<div class="items">
      ${c.office ? `<div class="bubble bot" style="max-width:100%">Verbindlich Auskunft gibt voraussichtlich:</div>
      <div class="contact"><b>${esc(c.office)}</b><span class="mono" style="font-size:13px">${esc([c.phone, c.email].filter(Boolean).join(" · "))}</span>
        <div class="btnrow">${tel ? `<a class="btn" href="tel:${esc(tel)}">Anrufen</a>` : ""}${c.email ? `<a class="btn" href="mailto:${esc(c.email)}">E-Mail entwerfen</a>` : ""}</div></div>` : ""}
      ${block.topic ? `<div class="dashed"><b>Diese Lücke dem MMP-Betreiber melden?</b>
        <span>Gemeldet wird nur dieses Thema – ohne Ihren Namen und ohne Ihre Situation. Sie können es vorher anpassen.</span>
        <label class="visually-hidden" for="gt">Thema</label><input id="gt" class="topic" maxlength="120" value="${esc(block.topic)}">
        <div class="btnrow"><button class="btn fill" data-act="send">Anonym melden</button><button class="btn plain" data-act="no">Nein danke</button></div>
        <span class="status" role="status" style="font-size:13px"></span></div>` : ""}</div>`);
    log.append(node);
    const box = node.querySelector(".dashed"); if (!box) return;
    box.querySelector('[data-act="no"]').addEventListener("click", () => { box.innerHTML = `<span>Nicht gemeldet.</span>`; });
    box.querySelector('[data-act="send"]').addEventListener("click", async () => {
      const topic = box.querySelector("input").value.trim();
      try {
        const r = await api("/api/tools/call", { name: "report_gap", arguments: { bfs: block.bfs, topic } });
        const text = (r.content && r.content[0] && r.content[0].text) || "";
        box.innerHTML = r.isError ? `<span class="error">${esc(text)}</span>` : `<span>${esc(text)}</span>`;
      } catch (e) { box.querySelector(".status").textContent = e.message; }
    });
  }

  // ---------------------------------------------------------------- MCP Apps host
  async function resource(uri) {
    if (!resources.has(uri)) {
      const r = await fetch(`/api/ui-resource?uri=${encodeURIComponent(uri)}`);
      if (!r.ok) throw new Error("Service Card konnte nicht geladen werden");
      resources.set(uri, await r.text());
    }
    return resources.get(uri);
  }

  function linkAllowed(url, block) {
    let u; try { u = new URL(url); } catch { return false; }
    if (u.protocol === "tel:" || u.protocol === "mailto:") return true;
    if (u.protocol !== "https:" && u.protocol !== "http:") return false;
    const m = (block.result.structuredContent || {}).municipality || {};
    const domains = [...(m.official_domains || []), ...(config.handoff_allowlist || [])];
    const host = u.hostname.toLowerCase();
    return domains.some((d) => host === d || host.endsWith("." + d));
  }

  async function mountApp(container, block) {
    const html = await resource(block.resource_uri);
    const frame = document.createElement("iframe");
    frame.className = "app-frame";
    frame.title = "Service Card";
    // Opaque origin: no cookies, no access to this page, no network via same-origin.
    frame.setAttribute("sandbox", "allow-scripts allow-modals allow-popups allow-popups-to-escape-sandbox");
    frame.srcdoc = html;
    container.append(frame);
    const post = (msg) => frame.contentWindow && frame.contentWindow.postMessage(msg, "*");
    const reply = (id, result) => post({ jsonrpc: "2.0", id, result });
    const fail = (id, message) => post({ jsonrpc: "2.0", id, error: { code: -32000, message } });

    const onMessage = async (event) => {
      if (event.source !== frame.contentWindow) return;
      const msg = event.data || {};
      if (msg.jsonrpc !== "2.0") return;
      switch (msg.method) {
        case "ui/initialize":
          reply(msg.id, {
            protocolVersion: "2026-01-26",
            hostInfo: { name: "MMP Reference Client", version: "0.1.0" },
            hostCapabilities: { openLinks: {}, serverTools: {} },
            hostContext: {
              theme: matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light",
              displayMode: "inline", availableDisplayModes: ["inline"], locale: "de-CH",
              containerDimensions: { width: container.clientWidth },
              mmp: block.context || {},   // Citizen situation: local only, never sent to the MMP server
            },
          });
          break;
        case "ui/notifications/initialized":
          post({ jsonrpc: "2.0", method: "ui/notifications/tool-input", params: { arguments: block.arguments } });
          post({ jsonrpc: "2.0", method: "ui/notifications/tool-result", params: block.result });
          break;
        case "ui/notifications/size-changed":
          if (msg.params && msg.params.height) frame.style.height = `${Math.min(msg.params.height + 4, 4000)}px`;
          break;
        case "ui/open-link": {
          const url = msg.params && msg.params.url;
          if (!linkAllowed(url, block)) { fail(msg.id, "Link führt nicht auf eine offizielle Domain und wird nicht geöffnet."); break; }
          window.open(url, "_blank", "noopener,noreferrer");
          reply(msg.id, {});
          break;
        }
        case "tools/call":
          try { reply(msg.id, await api("/api/tools/call", msg.params)); } catch (e) { fail(msg.id, e.message); }
          break;
        case "ui/message": {
          const text = msg.params && msg.params.content && msg.params.content.text;
          if (text) sendMessage(String(text).slice(0, 500));
          reply(msg.id, {});
          break;
        }
        default:
          if (msg.id !== undefined) post({ jsonrpc: "2.0", id: msg.id, error: { code: -32601, message: "Method not found" } });
      }
    };
    window.addEventListener("message", onMessage);
  }

  // ---------------------------------------------------------------- boot
  async function boot() {
    try { config = await api("/api/config"); }
    catch (e) { log.append(el(`<div class="error">${esc(e.message)}</div>`)); return; }
    const select = $("#muni");
    const params = new URLSearchParams(location.search);
    bfs = Number(params.get("bfs")) || config.default_bfs;
    if (!config.municipalities.some((m) => m.bfs === bfs) && config.municipalities.length) bfs = config.municipalities[0].bfs;
    for (const m of config.municipalities) select.append(new Option(`Gemeinde ${m.name}`, m.bfs, false, m.bfs === bfs));
    select.addEventListener("change", () => { bfs = Number(select.value); messages = []; situation = null; cardSlot = null; welcome(); });
    $("#reset").addEventListener("click", () => { messages = []; situation = null; cardSlot = null; welcome(); });
    renderBadge(); welcome();
    const prefill = params.get("q"); if (prefill) $("#q").value = prefill;
  }
  $("#composer").addEventListener("submit", (e) => { e.preventDefault(); const t = $("#q").value; $("#q").value = ""; sendMessage(t); });
  $("#q").addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); $("#composer").requestSubmit(); } });
  boot();
})();
