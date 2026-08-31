/*
 * Glow Light Card — full RGB control for a light: a live-colour glow bar,
 * a draggable HS colour wheel, brightness, quick presets and effect modes.
 * Vanilla custom element, no dependencies.
 */
const NS = "glow-light-card";

const PRESETS = [
  { name: "Warm",  rgb: [255, 170, 80] },
  { name: "White", rgb: [255, 241, 224] },
  { name: "Red",   rgb: [255, 59, 48] },
  { name: "Green", rgb: [40, 205, 65] },
  { name: "Cyan",  rgb: [50, 210, 200] },
  { name: "Blue",  rgb: [10, 132, 255] },
  { name: "Violet",rgb: [175, 82, 222] },
  { name: "Pink",  rgb: [255, 90, 175] },
];

const rgbStr = (c) => (Array.isArray(c) && c.length === 3 ? `rgb(${c[0]},${c[1]},${c[2]})` : "rgb(120,130,145)");
const near = (a, b) => Array.isArray(a) && Array.isArray(b) &&
  Math.abs(a[0]-b[0]) + Math.abs(a[1]-b[1]) + Math.abs(a[2]-b[2]) < 24;

function hsv2rgb(h, s, v) {
  const c = v * s, x = c * (1 - Math.abs(((h / 60) % 2) - 1)), m = v - c;
  let r=0,g=0,b=0;
  if (h < 60)      { r=c; g=x; }
  else if (h <120) { r=x; g=c; }
  else if (h <180) { g=c; b=x; }
  else if (h <240) { g=x; b=c; }
  else if (h <300) { r=x; b=c; }
  else             { r=c; b=x; }
  return [Math.round((r+m)*255), Math.round((g+m)*255), Math.round((b+m)*255)];
}

class GlowLightCard extends HTMLElement {
  setConfig(config) {
    if (!config || !config.entity) throw new Error("Set an 'entity' (a light.*)");
    this._cfg = { name: "", effect_names: {}, ...config };
    this._built = false;
    this._drag = false;
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
  }
  getCardSize() { return 8; }
  set hass(hass) { this._hass = hass; if (!this._built) this._build(); this._update(); }

  get _state() { return this._hass && this._hass.states[this._cfg.entity]; }
  _call(service, data = {}) {
    if (!this._state) return;
    this._hass.callService("light", service, { entity_id: this._cfg.entity, ...data });
  }

  _drawWheel() {
    const cv = this.shadowRoot.getElementById("wheel");
    const dpr = window.devicePixelRatio || 1;
    const size = 190;
    const W = Math.round(size * dpr);
    cv.width = W; cv.height = W;
    cv.style.width = size + "px"; cv.style.height = size + "px";
    const ctx = cv.getContext("2d");
    const R = W / 2;                       // device px, for drawing
    const img = ctx.createImageData(W, W); // full-resolution buffer
    for (let y = 0; y < W; y++) {
      for (let x = 0; x < W; x++) {
        const dx = x - R, dy = y - R, r = Math.sqrt(dx*dx + dy*dy);
        const i = (y * W + x) * 4;
        if (r <= R) {
          let h = Math.atan2(dy, dx) * 180 / Math.PI; if (h < 0) h += 360;
          const s = Math.min(1, r / R);
          const [rr, gg, bb] = hsv2rgb(h, s, 1);
          const edge = Math.min(1, (R - r) / (2 * dpr)); // AA edge
          img.data[i] = rr; img.data[i+1] = gg; img.data[i+2] = bb; img.data[i+3] = 255 * edge;
        } else { img.data[i+3] = 0; }
      }
    }
    ctx.putImageData(img, 0, 0);
    this._wheelR = size / 2;               // CSS px, for knob positioning
  }

  _pointFromHS(hs) {
    const R = this._wheelR || 95;
    const h = (hs && hs[0]) || 0, s = ((hs && hs[1]) || 0) / 100;
    const a = h * Math.PI / 180;
    return { x: R + Math.cos(a) * s * R, y: R + Math.sin(a) * s * R };
  }
  _hsFromPoint(x, y) {
    const R = this._wheelR || 95;
    const dx = x - R, dy = y - R;
    let h = Math.atan2(dy, dx) * 180 / Math.PI; if (h < 0) h += 360;
    const s = Math.min(1, Math.sqrt(dx*dx + dy*dy) / R) * 100;
    return [h, s];
  }

  _build() {
    const c = this._cfg, st = this._state;
    const name = c.name || (st && st.attributes.friendly_name) || "Light";
    const effects = (st && st.attributes.effect_list) || [];
    this.shadowRoot.innerHTML = `
      <style>
        :host{ --ink:#e8ecf1; --ink-dim:#96a0ad; --line:rgba(255,255,255,.10);
          --shell-1:#2b3037; --shell-2:#20242a; display:block; }
        .wrap{ position:relative; border-radius:24px; padding:18px;
          background:radial-gradient(130% 120% at 50% -10%, rgba(255,255,255,.07), transparent 60%),
            linear-gradient(180deg,var(--shell-1),var(--shell-2));
          box-shadow:0 20px 46px -24px rgba(0,0,0,.7), inset 0 1px 0 rgba(255,255,255,.06);
          font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; color:var(--ink); }
        .head{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px}
        .title{display:flex;flex-direction:column;line-height:1.15}
        .title b{font-size:16px}
        .title span{font-size:11.5px;color:var(--ink-dim);text-transform:uppercase;letter-spacing:1.3px;margin-top:2px}
        .power{width:44px;height:44px;border-radius:14px;border:none;cursor:pointer;display:grid;place-items:center;
          color:var(--ink-dim);background:rgba(255,255,255,.05);box-shadow:inset 0 0 0 1px var(--line);transition:all .25s ease}
        .power svg{width:22px;height:22px} .power.on{color:#0c0f12}
        .bar{height:52px;border-radius:16px;margin-bottom:16px;position:relative;overflow:hidden;
          background:#0c1013;box-shadow:inset 0 0 0 1px var(--line);transition:box-shadow .3s ease}
        .bar .fill{position:absolute;inset:0;opacity:0;transition:opacity .3s ease, background .3s ease}
        .bar .seg{position:absolute;top:0;bottom:0;width:8px;border-radius:4px;background:rgba(255,255,255,.22)}
        .wheelWrap{display:flex;justify-content:center;margin:2px 0 16px;position:relative}
        .wheelBox{position:relative;width:190px;height:190px;touch-action:none}
        #wheel{border-radius:50%;box-shadow:0 8px 24px -8px rgba(0,0,0,.7), inset 0 0 0 1px rgba(255,255,255,.08);display:block}
        .knob{position:absolute;width:26px;height:26px;border-radius:50%;transform:translate(-50%,-50%);
          border:3px solid #fff;box-shadow:0 2px 8px rgba(0,0,0,.6);pointer-events:none;transition:opacity .2s ease}
        .row{display:flex;align-items:center;gap:12px;margin-bottom:16px}
        .row .ic{color:var(--ink-dim);flex:none;display:grid;place-items:center} .row .ic svg{width:20px;height:20px}
        input[type=range]{-webkit-appearance:none;appearance:none;width:100%;height:10px;border-radius:6px;
          background:rgba(255,255,255,.10);outline:none;cursor:pointer}
        input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:24px;height:24px;border-radius:50%;
          background:#fff;box-shadow:0 3px 8px rgba(0,0,0,.5), 0 0 0 4px rgba(255,255,255,.12);cursor:pointer}
        input[type=range]::-moz-range-thumb{width:24px;height:24px;border:none;border-radius:50%;background:#fff}
        .pct{min-width:44px;text-align:right;font-variant-numeric:tabular-nums;font-size:14px}
        .lbl{font-size:11px;color:var(--ink-dim);text-transform:uppercase;letter-spacing:1.3px;margin:0 2px 8px}
        .swatches{display:grid;grid-template-columns:repeat(8,1fr);gap:9px;margin-bottom:16px}
        .sw{aspect-ratio:1;border-radius:11px;border:none;cursor:pointer;box-shadow:inset 0 0 0 1px rgba(0,0,0,.35);transition:transform .12s ease}
        .sw:active{transform:scale(.9)}
        .sw.active{box-shadow:0 0 0 2px var(--ink), 0 0 12px 1px var(--sel)}
        .fx{display:flex;gap:8px;overflow-x:auto;padding-bottom:4px;scrollbar-width:none}
        .fx::-webkit-scrollbar{display:none}
        .chip{flex:none;min-width:46px;padding:9px 12px;border-radius:12px;border:none;cursor:pointer;
          font-size:12.5px;font-weight:600;color:var(--ink-dim);background:rgba(255,255,255,.05);
          box-shadow:inset 0 0 0 1px var(--line);transition:all .2s ease}
        .chip:active{transform:scale(.94)}
        .chip.active{color:#0c0f12;background:linear-gradient(180deg,#7cc6ff,#3ea6ff);box-shadow:0 6px 14px -6px rgba(62,166,255,.6)}
        .off .bar,.off .wheelBox,.off input,.off .swatches,.off .fx{opacity:.5}
        @media (max-width:380px){ .swatches{grid-template-columns:repeat(4,1fr)} }
      </style>
      <div class="wrap" id="wrap">
        <div class="head">
          <div class="title"><b>${name}</b><span id="stTxt">—</span></div>
          <button class="power" id="power" title="Toggle">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M12 3v9M7.5 6.5a7 7 0 1 0 9 0"/></svg>
          </button>
        </div>
        <div class="bar" id="bar"><div class="fill" id="fill"></div>
          ${Array.from({length:12}).map((_,i)=>`<div class="seg" style="left:${6+i*8.2}%"></div>`).join("")}
        </div>
        <div class="wheelWrap"><div class="wheelBox" id="wheelBox">
          <canvas id="wheel"></canvas><div class="knob" id="knob"></div>
        </div></div>
        <div class="row">
          <span class="ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4.5"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5 19 19M19 5l-1.5 1.5M6.5 17.5 5 19"/></svg></span>
          <input type="range" id="bri" min="1" max="100" value="50"><span class="pct" id="briTxt">—</span>
        </div>
        <div class="lbl">Presets</div>
        <div class="swatches" id="sw">
          ${PRESETS.map((p,i)=>`<button class="sw" data-i="${i}" style="background:${rgbStr(p.rgb)}" title="${p.name}"></button>`).join("")}
        </div>
        ${effects.length ? `<div class="lbl">Modes</div><div class="fx" id="fx">
          ${effects.map(e=>`<button class="chip" data-fx="${e}">${(c.effect_names && c.effect_names[e]) || (e==="0"?"Static":"FX "+e)}</button>`).join("")}
        </div>` : ""}
      </div>`;

    const R = this.shadowRoot;
    R.getElementById("power").addEventListener("click", () => this._call("toggle"));
    R.getElementById("bar").addEventListener("click", () => this._call("toggle"));
    const bri = R.getElementById("bri");
    bri.addEventListener("input", (e) => { R.getElementById("briTxt").textContent = `${e.target.value}%`; });
    bri.addEventListener("change", (e) => this._call("turn_on", { brightness_pct: Number(e.target.value) }));
    R.getElementById("sw").querySelectorAll(".sw").forEach((b) =>
      b.addEventListener("click", () => this._call("turn_on", { rgb_color: PRESETS[+b.dataset.i].rgb })));
    const fx = R.getElementById("fx");
    if (fx) fx.querySelectorAll(".chip").forEach((b) =>
      b.addEventListener("click", () => this._call("turn_on", { effect: b.dataset.fx })));

    this._drawWheel();
    this._bindWheel();
    this._built = true;
  }

  _bindWheel() {
    const box = this.shadowRoot.getElementById("wheelBox");
    const knob = this.shadowRoot.getElementById("knob");
    const at = (ev) => {
      const r = box.getBoundingClientRect();
      const px = (ev.touches ? ev.touches[0].clientX : ev.clientX) - r.left;
      const py = (ev.touches ? ev.touches[0].clientY : ev.clientY) - r.top;
      return this._hsFromPoint(px, py);
    };
    const place = (hs) => {
      const p = this._pointFromHS(hs);
      knob.style.left = p.x + "px"; knob.style.top = p.y + "px";
      knob.style.background = rgbStr(hsv2rgb(hs[0], hs[1]/100, 1));
    };
    const down = (ev) => {
      if (!this._state || this._state.state === "unavailable") return;
      this._drag = true; ev.preventDefault();
      const hs = at(ev); place(hs);
    };
    const move = (ev) => { if (this._drag) { ev.preventDefault(); place(at(ev)); } };
    const up = (ev) => {
      if (!this._drag) return; this._drag = false;
      const hs = at(ev.changedTouches ? ev : ev);
      this._call("turn_on", { hs_color: [Math.round(hs[0]*100)/100, Math.round(hs[1]*100)/100] });
    };
    box.addEventListener("pointerdown", down);
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  }

  _update() {
    const R = this.shadowRoot, st = this._state;
    const on = st && st.state === "on";
    const avail = st && st.state !== "unavailable";
    const rgb = st && st.attributes.rgb_color;
    const hs = st && st.attributes.hs_color;
    const bri = st && st.attributes.brightness;
    const pct = bri != null ? Math.round((bri / 255) * 100) : null;
    const eff = st && st.attributes.effect;

    R.getElementById("wrap").classList.toggle("off", !on);
    R.getElementById("stTxt").textContent = !avail ? "Unavailable" : on ? "On" : "Off";

    const power = R.getElementById("power");
    power.classList.toggle("on", !!on);
    power.style.background = on ? rgbStr(rgb) : "";
    power.style.boxShadow = on ? `0 6px 16px -6px ${rgbStr(rgb)}, inset 0 0 0 1px rgba(255,255,255,.25)` : "";
    power.toggleAttribute("disabled", !avail);

    const bar = R.getElementById("bar"), fill = R.getElementById("fill");
    if (on) {
      const col = rgbStr(rgb);
      fill.style.background = col; fill.style.opacity = pct != null ? Math.max(0.25, pct/100) : 0.85;
      bar.style.boxShadow = `inset 0 0 0 1px var(--line), 0 0 26px -2px ${col}`;
    } else { fill.style.opacity = 0; bar.style.boxShadow = "inset 0 0 0 1px var(--line)"; }

    // knob follows current hs (unless dragging)
    const knob = R.getElementById("knob");
    if (!this._drag) {
      if (on && hs) {
        const p = this._pointFromHS(hs);
        knob.style.left = p.x + "px"; knob.style.top = p.y + "px";
        knob.style.background = rgbStr(rgb); knob.style.opacity = 1;
      } else if (on) { const p=this._pointFromHS([0,0]); knob.style.left=p.x+"px"; knob.style.top=p.y+"px"; knob.style.background="#888"; knob.style.opacity=1; }
        else { knob.style.opacity = 0; }
    }

    const briEl = R.getElementById("bri");
    if (document.activeElement !== briEl && pct != null) briEl.value = pct;
    R.getElementById("briTxt").textContent = pct != null ? `${pct}%` : (on ? "—" : "Off");

    R.getElementById("sw").querySelectorAll(".sw").forEach((b) => {
      const p = PRESETS[+b.dataset.i];
      const active = on && near(rgb, p.rgb);
      b.classList.toggle("active", active);
      if (active) b.style.setProperty("--sel", rgbStr(p.rgb));
    });
    const fx = R.getElementById("fx");
    if (fx) fx.querySelectorAll(".chip").forEach((b) =>
      b.classList.toggle("active", on && eff != null && String(eff) === b.dataset.fx));
  }
}

if (!customElements.get(NS)) customElements.define(NS, GlowLightCard);
window.customCards = window.customCards || [];
window.customCards.push({ type: NS, name: "Glow Light Card", description: "RGB light control: colour wheel, brightness, presets, effect modes" });
console.info("%c GLOW-LIGHT-CARD %c loaded", "background:#0a84ff;color:#fff;border-radius:3px 0 0 3px;padding:2px 6px", "background:#20242a;color:#e8ecf1;border-radius:0 3px 3px 0;padding:2px 6px");
