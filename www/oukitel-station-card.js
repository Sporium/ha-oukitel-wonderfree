/*
 * Oukitel Station Card — a station-shaped control panel for the
 * Oukitel P2001E Plus (Wonderfree) integration.
 *
 * A single, self-contained custom Lovelace card (no build step, no deps):
 * a dark "LCD" head with a battery ring and live in/out power, over a
 * control deck of three tactile toggles for the AC / USB / DC outputs.
 */
const NS = "oukitel-station-card";

const DEFAULTS = {
  name: "Bemo",
  model: "P2001E Plus",
  soc: "sensor.bemo_battery_level",
  out: "sensor.bemo_total_out_power",
  in: "sensor.bemo_total_in_power",
  ac_in: "sensor.bemo_ac_in_power",
  temp: "sensor.bemo_device_temperature",
  charge_min: "sensor.bemo_charge_remaining_time",
  discharge_min: "sensor.bemo_discharge_remaining_time",
  ac: "switch.bemo_ac_output",
  usb: "switch.bemo_usb_output",
  dc: "switch.bemo_dc_output",
};

const num = (hass, id) => {
  const s = id && hass.states[id];
  if (!s) return null;
  const v = parseFloat(s.state);
  return Number.isFinite(v) ? v : null;
};
const isOn = (hass, id) => !!(id && hass.states[id] && hass.states[id].state === "on");
const avail = (hass, id) =>
  !!(id && hass.states[id] && !["unavailable", "unknown"].includes(hass.states[id].state));

const fmtMin = (m) => {
  if (m == null) return "—";
  m = Math.max(0, Math.round(m));
  const h = Math.floor(m / 60), mm = m % 60;
  return h ? `${h} h ${mm} m` : `${mm} m`;
};

class OukitelStationCard extends HTMLElement {
  setConfig(config) {
    this._cfg = { ...DEFAULTS, ...(config || {}) };
    this._built = false;
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
  }

  getCardSize() { return 6; }

  set hass(hass) {
    this._hass = hass;
    if (!this._built) this._build();
    this._update();
  }

  _toggle(id) {
    if (!avail(this._hass, id)) return;
    const [domain] = id.split(".");
    this._hass.callService(domain, "toggle", { entity_id: id });
    // haptic-ish optimistic feedback
    const el = this._deck && this._deck.querySelector(`[data-id="${id}"]`);
    if (el) { el.classList.add("pressed"); setTimeout(() => el.classList.remove("pressed"), 180); }
  }

  _build() {
    const c = this._cfg;
    const root = this.shadowRoot;
    root.innerHTML = `
      <style>
        :host{
          --accent-ac:#ffb020; --accent-usb:#3ea6ff; --accent-dc:#2fd27a;
          --ink:#e8ecf1; --ink-dim:#96a0ad; --line:rgba(255,255,255,.10);
          --shell-1:#2b3037; --shell-2:#20242a; --lcd-1:#0e1418; --lcd-2:#0a0f13;
          display:block;
        }
        .wrap{
          position:relative; border-radius:26px; padding:16px 16px 18px;
          background:
            radial-gradient(140% 120% at 50% -20%, rgba(255,255,255,.08), transparent 60%),
            linear-gradient(180deg,var(--shell-1),var(--shell-2));
          box-shadow:0 22px 50px -24px rgba(0,0,0,.75), inset 0 1px 0 rgba(255,255,255,.06),
                     inset 0 0 0 1px rgba(0,0,0,.35);
          font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Ubuntu,sans-serif;
          color:var(--ink); overflow:hidden;
        }
        /* carry handle nub echoing the real unit */
        .handle{position:absolute;top:6px;left:50%;transform:translateX(-50%);
          width:118px;height:9px;border-radius:6px;
          background:linear-gradient(180deg,rgba(255,255,255,.14),rgba(255,255,255,.02));
          box-shadow:inset 0 -1px 2px rgba(0,0,0,.5);}
        .head{display:flex;align-items:center;justify-content:space-between;margin:10px 4px 14px}
        .title{display:flex;flex-direction:column;line-height:1.1}
        .title b{font-size:16px;letter-spacing:.2px}
        .title span{font-size:11px;color:var(--ink-dim);margin-top:2px;text-transform:uppercase;letter-spacing:1.4px}
        .status{display:flex;align-items:center;gap:7px;font-size:12px;color:var(--ink-dim)}
        .dot{width:9px;height:9px;border-radius:50%;background:#4b5563;box-shadow:0 0 0 0 rgba(0,0,0,0)}
        .dot.online{background:var(--accent-dc);box-shadow:0 0 10px 1px rgba(47,210,122,.7)}

        /* LCD screen */
        .lcd{position:relative;display:grid;grid-template-columns:auto 1fr;gap:18px;align-items:center;
          padding:18px;border-radius:18px;
          background:linear-gradient(180deg,var(--lcd-1),var(--lcd-2));
          box-shadow:inset 0 2px 10px rgba(0,0,0,.7), inset 0 0 0 1px rgba(255,255,255,.04);}
        .lcd::after{content:"";position:absolute;inset:0;border-radius:18px;pointer-events:none;
          background:linear-gradient(180deg,rgba(255,255,255,.05),transparent 30%);}
        .ring{position:relative;width:118px;height:118px;flex:none}
        .ring svg{transform:rotate(-90deg)}
        .ring .pct{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center}
        .ring .pct b{font-size:30px;font-variant-numeric:tabular-nums;letter-spacing:.5px}
        .ring .pct small{font-size:10px;color:var(--ink-dim);letter-spacing:1.5px;margin-top:1px}
        .flows{display:grid;gap:10px;min-width:0}
        .flow{display:flex;align-items:center;gap:10px}
        .flow .ic{width:34px;height:34px;border-radius:10px;display:grid;place-items:center;flex:none;
          background:rgba(255,255,255,.05);box-shadow:inset 0 0 0 1px var(--line)}
        .flow .ic svg{width:19px;height:19px}
        .flow .txt{display:flex;flex-direction:column;line-height:1.15;min-width:0}
        .flow .txt b{font-size:19px;font-variant-numeric:tabular-nums}
        .flow .txt span{font-size:10.5px;color:var(--ink-dim);text-transform:uppercase;letter-spacing:1.3px}
        .flow.out .ic{color:var(--accent-ac)} .flow.in .ic{color:var(--accent-dc)} .flow.rt .ic{color:var(--accent-usb)}
        .subline{display:flex;gap:16px;margin:12px 6px 2px;color:var(--ink-dim);font-size:12px;flex-wrap:wrap}
        .subline b{color:var(--ink);font-variant-numeric:tabular-nums;font-weight:600}

        /* control deck */
        .deck{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:16px}
        .tile{position:relative;cursor:pointer;user-select:none;border-radius:16px;padding:16px 12px 13px;
          display:flex;flex-direction:column;align-items:center;gap:9px;
          background:linear-gradient(180deg,rgba(255,255,255,.045),rgba(255,255,255,.015));
          box-shadow:inset 0 0 0 1px var(--line), 0 8px 18px -14px rgba(0,0,0,.9);
          transition:transform .12s ease, box-shadow .2s ease, background .25s ease;}
        .tile:active,.tile.pressed{transform:scale(.965)}
        .tile .glyph{width:44px;height:44px;border-radius:13px;display:grid;place-items:center;
          color:var(--ink-dim);background:rgba(255,255,255,.04);
          box-shadow:inset 0 0 0 1px var(--line);transition:all .25s ease}
        .tile .glyph svg{width:25px;height:25px}
        .tile .lab{font-size:12.5px;font-weight:600;letter-spacing:.3px}
        .tile .st{font-size:10.5px;color:var(--ink-dim);text-transform:uppercase;letter-spacing:1.4px}
        .tile .led{position:absolute;top:12px;right:12px;width:8px;height:8px;border-radius:50%;
          background:#3b4048;transition:all .25s ease}
        .tile.on{background:linear-gradient(180deg,var(--tint-20),rgba(255,255,255,.02))}
        .tile.on .glyph{color:#0c0f12;background:linear-gradient(180deg,var(--tint),var(--tint-dk));
          box-shadow:0 6px 16px -6px var(--tint-glow), inset 0 0 0 1px rgba(255,255,255,.25)}
        .tile.on .st{color:var(--tint)}
        .tile.on .led{background:var(--tint);box-shadow:0 0 10px 1px var(--tint-glow)}
        .tile.off:hover{background:linear-gradient(180deg,rgba(255,255,255,.075),rgba(255,255,255,.02))}
        .tile[disabled]{opacity:.4;pointer-events:none}
        .tile.ac{--tint:var(--accent-ac);--tint-dk:#d98a12;--tint-20:rgba(255,176,32,.16);--tint-glow:rgba(255,176,32,.6)}
        .tile.usb{--tint:var(--accent-usb);--tint-dk:#1f7fd6;--tint-20:rgba(62,166,255,.16);--tint-glow:rgba(62,166,255,.6)}
        .tile.dc{--tint:var(--accent-dc);--tint-dk:#1fa85e;--tint-20:rgba(47,210,122,.16);--tint-glow:rgba(47,210,122,.6)}
        @media (max-width:420px){ .lcd{grid-template-columns:1fr;justify-items:center;text-align:center}
          .flows{width:100%} }
      </style>
      <div class="wrap">
        <div class="handle"></div>
        <div class="head">
          <div class="title"><b>${c.name}</b><span>${c.model}</span></div>
          <div class="status"><span class="dot" id="dot"></span><span id="stTxt">—</span></div>
        </div>
        <div class="lcd">
          <div class="ring">
            <svg width="118" height="118" viewBox="0 0 118 118">
              <circle cx="59" cy="59" r="52" fill="none" stroke="rgba(255,255,255,.08)" stroke-width="10"/>
              <circle id="arc" cx="59" cy="59" r="52" fill="none" stroke="url(#g)" stroke-width="10"
                stroke-linecap="round" stroke-dasharray="326.7" stroke-dashoffset="326.7"/>
              <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0" stop-color="#2fd27a"/><stop offset="1" stop-color="#38e0c0"/>
              </linearGradient></defs>
            </svg>
            <div class="pct"><b id="soc">—</b><small>BATTERY</small></div>
          </div>
          <div class="flows">
            <div class="flow out">
              <div class="ic">${ICON.bolt}</div>
              <div class="txt"><b id="outW">—</b><span>Output</span></div>
            </div>
            <div class="flow in">
              <div class="ic">${ICON.plug}</div>
              <div class="txt"><b id="inW">—</b><span>Input</span></div>
            </div>
            <div class="flow rt">
              <div class="ic">${ICON.clock}</div>
              <div class="txt"><b id="rtW">—</b><span id="rtLab">Runtime</span></div>
            </div>
          </div>
        </div>
        <div class="subline">
          <div id="eta"></div><div id="tempTxt"></div><div id="acinTxt"></div>
        </div>
        <div class="deck" id="deck">
          ${tile("ac", "AC", ICON.socket, c.ac)}
          ${tile("usb", "USB", ICON.usb, c.usb)}
          ${tile("dc", "DC 12V", ICON.car, c.dc)}
        </div>
      </div>`;

    this._deck = root.getElementById("deck");
    root.querySelectorAll(".tile").forEach((t) =>
      t.addEventListener("click", () => this._toggle(t.dataset.id)));
    this._built = true;
  }

  _update() {
    const h = this._hass, c = this._cfg, R = this.shadowRoot;
    const soc = num(h, c.soc);
    // ring
    const arc = R.getElementById("arc");
    const CIRC = 2 * Math.PI * 52;
    const p = soc == null ? 0 : Math.max(0, Math.min(100, soc));
    arc.style.strokeDashoffset = `${CIRC * (1 - p / 100)}`;
    const col = p >= 50 ? ["#2fd27a", "#38e0c0"] : p >= 20 ? ["#ffb020", "#ffd166"] : ["#ff5a5a", "#ff8080"];
    const grad = R.querySelector("#g");
    grad.children[0].setAttribute("stop-color", col[0]);
    grad.children[1].setAttribute("stop-color", col[1]);
    R.getElementById("soc").textContent = soc == null ? "—" : `${Math.round(soc)}%`;

    const out = num(h, c.out), inp = num(h, c.in);
    R.getElementById("outW").textContent = out == null ? "—" : `${Math.round(out)} W`;
    R.getElementById("inW").textContent = inp == null ? "—" : `${Math.round(inp)} W`;

    // online + eta + temp + ac in
    const online = avail(h, c.soc) && (h.states[c.soc] || {}).state !== "unavailable";
    R.getElementById("dot").className = "dot" + (online ? " online" : "");
    R.getElementById("stTxt").textContent = online ? "Online" : "Offline";

    const charging = (inp || 0) > 1;
    const eta = charging ? num(h, c.charge_min) : num(h, c.discharge_min);
    R.getElementById("rtW").textContent = eta == null ? "—" : fmtMin(eta);
    R.getElementById("rtLab").textContent = charging ? "Time to full" : "Runtime left";
    const etaEl = R.getElementById("eta"); if (etaEl) etaEl.innerHTML = "";
    const t = num(h, c.temp);
    R.getElementById("tempTxt").innerHTML = t == null ? "" : `Temp <b>${Math.round(t)}°C</b>`;
    const acin = num(h, c.ac_in);
    R.getElementById("acinTxt").innerHTML = acin == null ? "" : `Grid&nbsp;in <b>${Math.round(acin)} W</b>`;

    // tiles
    for (const [k, id] of [["ac", c.ac], ["usb", c.usb], ["dc", c.dc]]) {
      const tile = R.querySelector(`.tile.${k}`);
      if (!tile) continue;
      const on = isOn(h, id), ok = avail(h, id);
      tile.classList.toggle("on", on);
      tile.classList.toggle("off", !on);
      tile.toggleAttribute("disabled", !ok);
      tile.querySelector(".st").textContent = !ok ? "N/A" : on ? "On" : "Off";
    }
  }
}

const ICON = {
  bolt: `<svg viewBox="0 0 24 24" fill="currentColor"><path d="M13 2 4 14h6l-1 8 9-12h-6l1-8Z"/></svg>`,
  plug: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M9 2v6M15 2v6M7 8h10v3a5 5 0 0 1-10 0V8ZM12 16v6"/></svg>`,
  socket: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="9" cy="12" r="1.4" fill="currentColor" stroke="none"/><circle cx="15" cy="12" r="1.4" fill="currentColor" stroke="none"/></svg>`,
  usb: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v14M12 22a2 2 0 0 0 2-2M8 8l4-4 4 4M9 12h6v4a3 3 0 0 1-6 0v-4Z"/></svg>`,
  clock: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>`,
  car: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 13l1.5-4.5A2 2 0 0 1 8.4 7h7.2a2 2 0 0 1 1.9 1.5L19 13v5h-2v-2H7v2H5v-5Z"/><circle cx="8" cy="16" r="1"/><circle cx="16" cy="16" r="1"/></svg>`,
};

function tile(cls, label, glyph, id) {
  return `<div class="tile ${cls} off" data-id="${id}">
    <span class="led"></span>
    <div class="glyph">${glyph}</div>
    <div class="lab">${label}</div>
    <div class="st">Off</div>
  </div>`;
}

if (!customElements.get(NS)) customElements.define(NS, OukitelStationCard);
window.customCards = window.customCards || [];
window.customCards.push({
  type: NS,
  name: "Oukitel Station Card",
  description: "Station-shaped control panel for the Oukitel P2001E Plus",
  preview: false,
});
console.info("%c OUKITEL-STATION-CARD %c loaded", "background:#2fd27a;color:#0c0f12;border-radius:3px 0 0 3px;padding:2px 6px", "background:#20242a;color:#e8ecf1;border-radius:0 3px 3px 0;padding:2px 6px");
