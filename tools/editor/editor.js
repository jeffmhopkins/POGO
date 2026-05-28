/* POGO Panel Editor — interactive layout editor.
 *
 * Generated into design/panel-editor.html by tools/panel_editor.py. The page embeds:
 *   #panel-payload  →  { data, yaml_text, constants, kicad_templates, footprint_names }
 *
 * All geometry constants (courtyards, nut radii, design rules) come from panel_rules.py
 * via the payload, so the in-browser DRC matches `build_panel.py --check` exactly.
 *
 * Edit → drag/rotate/add/delete/HP/dividers → Export YAML → paste over
 * tools/panel-data.yaml → `python3 tools/build_panel.py --check` → rebuild.
 */
(function () {
  "use strict";

  // ── Payload ────────────────────────────────────────────────────────────────
  const PAYLOAD = JSON.parse(document.getElementById("panel-payload").textContent);
  const C   = PAYLOAD.constants;
  const DR  = C.design_rules;
  const KT  = PAYLOAD.kicad_templates;
  const FPN = PAYLOAD.footprint_names;
  const SCALE = 4;                       // px per mm for on-screen display

  const clone = (o) => JSON.parse(JSON.stringify(o));
  const D    = clone(PAYLOAD.data);      // working model (mutated by edits)
  const ORIG = clone(PAYLOAD.data);      // pristine copy for export diffing
  // Tag each existing zone with its original id (UI-only, never exported) so the
  // exporter can locate it in the source text even after a rename, and tell new
  // zones (no _orig_id) from existing ones.
  (D.zones || []).forEach((z) => { z._orig_id = z.id; });

  // Editor UI state
  const UI = {
    tool: "select",          // "select" | "pan" | "anchor"
    selId: null,             // selected component id
    selZone: null,           // selected zone id (mutually exclusive with selId)
    selSep: null,            // selected separator index (mutually exclusive with selId/selZone)
    snap: false,
    snapUnit: "mm",          // "mm" | "hp"
    snapVal: 0.5,            // step in the chosen unit (e.g. 0.5 mm, 2.25 HP)
    snapOriginId: null,      // component/divider id the snap grid counts from (null = panel 0,0)
    anchor: null,            // active anchor/align pick: {axis:'x'|'y'|'both', offX, offY, unit}
    armedAddType: null,      // palette type queued for click-to-place (unused: we add immediately)
    layers: { panel: true, keepout: false, nuts: false, pcb: false, kicad: false },
  };
  const HP_MM = 5.08;
  const undoStack = [];
  const redoStack = [];
  function snapshot() {
    undoStack.push(JSON.stringify({ d: D, xo: DR.x_offset }));
    if (undoStack.length > 100) undoStack.shift();
    redoStack.length = 0;
  }
  function applySnapshot(s) {
    const o = JSON.parse(s);
    // mutate D in place so references in closures stay valid
    for (const k of Object.keys(D)) delete D[k];
    Object.assign(D, o.d);
    DR.x_offset = o.xo;
  }
  function undo() { if (!undoStack.length) return; redoStack.push(JSON.stringify({ d: D, xo: DR.x_offset })); applySnapshot(undoStack.pop()); UI.selId = UI.selId && findComp(UI.selId) ? UI.selId : null; if (UI.selSep != null && (!D.separators || UI.selSep >= D.separators.length)) UI.selSep = null; render(); }
  function redo() { if (!redoStack.length) return; undoStack.push(JSON.stringify({ d: D, xo: DR.x_offset })); applySnapshot(redoStack.pop()); render(); }

  // ── Small helpers ────────────────────────────────────────────────────────────
  const f2 = (x) => Number(x).toFixed(2);
  const f3 = (x) => Number(x).toFixed(3);
  function fmtVal(v) {                    // mirrors build_panel._fmt_val
    if (v === Math.trunc(v)) return String(Math.trunc(v));
    let s = Number(v).toFixed(3);
    s = s.replace(/0+$/, "").replace(/\.$/, "");
    return s;
  }
  const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

  const PALETTE_TYPES = [
    "jack_input", "jack_output", "trimpot",
    "knob_medium", "knob_large", "knob_xl",
    "eg_2pos", "eg_3pos",
    "led", "led_labeled", "slider_V45", "text",
  ];

  function compLabel(c) {
    return c.id || c.label || c.cpp_id || c.cpp_param || "?";
  }
  function zoneOf(c) {
    for (const z of D.zones || []) {
      if ((z.components || []).indexOf(c) >= 0) return z;
    }
    return null;
  }
  function allComps() {                   // flat list with their owning zone
    const out = [];
    for (const z of D.zones || []) for (const c of z.components || []) out.push({ c, z });
    return out;
  }
  function findComp(id) {
    for (const z of D.zones || []) for (const c of z.components || []) if (c.id === id) return { c, z };
    return null;
  }

  // ── Resolution (port of build_panel._resolve_comp) ─────────────────────────
  function resolve(c, z) {
    let cx;
    if (c.col != null && z && z.x_start != null) {
      const pitch = z.col_pitch != null ? Number(z.col_pitch) : DR.jack_pitch;
      cx = Number(z.x_start) + (Number(c.col) + 0.5) * pitch;
    } else {
      cx = Number(c.cx);
    }
    if (DR.x_offset && cx != null && !Number.isNaN(cx)) cx += DR.x_offset;

    let cy = c.cy;
    const isJack = c.type === "jack_input" || c.type === "jack_output";
    if (cy === "_cv_jack_cy_" || (cy == null && isJack)) cy = DR.cv_jack_cy;
    else if (cy === "_att_cy_" || cy == null) cy = DR.att_cy;
    else if (typeof cy === "string" && cy[0] === "_") cy = isJack ? DR.cv_jack_cy : DR.att_cy;
    else cy = Number(cy);
    return { cx, cy };
  }
  // Raw (pre-x_offset) cx of a component as currently modelled.
  function rawCx(c, z) { return resolve(c, z).cx - (DR.x_offset || 0); }

  // ── Courtyard geometry (port of panel_rules) ───────────────────────────────
  const CY = C.courtyards;
  function courtyardConst(type) {
    if (C.type_sets.jack.includes(type)) return CY.JACK_CY;
    if (type === "trimpot") return CY.TRIMPOT_CY;
    if (C.type_sets.pot.includes(type)) return CY.POT_CY;
    if (C.type_sets.slider.includes(type)) return CY.SLIDER_V45_CY;
    if (C.type_sets.switch_v3.includes(type)) return CY.SWITCH_V3_CY;
    if (type === "switch_H3") return CY.SWITCH_H3_CY;
    if (type === "switch_H2") return CY.SWITCH_CY;
    if (C.type_sets.eg_2pos.includes(type)) return CY.EG1218_CY;
    if (C.type_sets.eg_3pos.includes(type)) return CY.EG2301_V_CY;
    if (C.type_sets.led.includes(type)) return CY.LED_CY;
    return null;
  }
  function rotateRect(rect, deg) {
    if (!deg) return rect.slice();
    const [x1, y1, x2, y2] = rect;
    let pts = [[x1, y1], [x2, y1], [x1, y2], [x2, y2]];
    if (deg === 90) pts = pts.map(([x, y]) => [y, -x]);
    else if (deg === 180) pts = pts.map(([x, y]) => [-x, -y]);
    else if (deg === 270) pts = pts.map(([x, y]) => [-y, x]);
    else return rect.slice();
    const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
    return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
  }
  function courtyard(cx, cy, type, deg) {
    const base = courtyardConst(type);
    if (!base) return null;
    const [x1, y1, x2, y2] = rotateRect(base, deg || 0);
    return [cx + x1, cy + y1, cx + x2, cy + y2];
  }
  function panelR(type) {
    const P = C.panel_r;
    if (C.type_sets.jack.includes(type)) return P.jack;
    if (type === "trimpot") return P.trimpot;
    if (C.type_sets.pot.includes(type)) return P.pot;
    if (C.type_sets.slider.includes(type)) return P.slider;
    if (C.type_sets.switch_v3.includes(type)) return P.switch_v3;
    if (type === "switch_H2" || type === "switch_H3") return P.switch_h;
    if (C.type_sets.led.includes(type)) return P.led;
    return 0;
  }
  // Signed min gap between two courtyard rects (mirrors panel_rules._rect_min_gap).
  function rectMinGap(r1, r2) {
    const sx = Math.max(0, Math.max(r1[0], r2[0]) - Math.min(r1[2], r2[2]));
    const sy = Math.max(0, Math.max(r1[1], r2[1]) - Math.min(r1[3], r2[3]));
    if (sx > 0 && sy > 0) return Math.hypot(sx, sy);
    if (sx > 0 || sy > 0) return Math.max(sx, sy);
    const ox = Math.min(r1[2], r2[2]) - Math.max(r1[0], r2[0]);
    const oy = Math.min(r1[3], r2[3]) - Math.max(r1[1], r2[1]);
    return -Math.min(ox, oy);
  }
  // Centre-to-centre, nut-edge clearance, and PCB courtyard gap (mirrors CLI --dist).
  function pairGap(A, B) {           // A,B = {cx,cy,type,rot}
    const dist = Math.hypot(B.cx - A.cx, B.cy - A.cy);
    const rA = panelR(A.type), rB = panelR(B.type);
    const nut = (rA > 0 && rB > 0) ? dist - (rA + rB) : null;
    const ra = courtyard(A.cx, A.cy, A.type, A.rot || 0);
    const rb = courtyard(B.cx, B.cy, B.type, B.rot || 0);
    const ct = (ra && rb) ? rectMinGap(ra, rb) : null;
    return { dist, nut, courtyard: ct };
  }
  function nearestComp(id, x, y) {   // nearest other component by centre distance
    let best = null, bd = Infinity;
    for (const { c, z } of allComps()) {
      if (c.id === id) continue;
      const r = resolve(c, z);
      const d = Math.hypot(r.cx - x, r.cy - y);
      if (d < bd) { bd = d; best = { c, cx: r.cx, cy: r.cy, type: c.type, rot: Number(c.rotate || 0) }; }
    }
    return best;
  }

  // ── DRC (port of panel_rules.check_all) ────────────────────────────────────
  // Returns { violations:[str...], badIds:Set }.  Strings match the Python output
  // so the editor report mirrors `build_panel.py --check`.
  // override (optional) = { id, cx, cy } resolved coords for an in-flight drag, so
  // live DRC reflects the dragged position without mutating the model.
  function runDRC(override) {
    const comps = allComps().map(({ c, z }) => {
      let cx, cy;
      if (override && c.id === override.id) { cx = override.cx; cy = override.cy; }
      else { const r = resolve(c, z); cx = r.cx; cy = r.cy; }
      return { c, cx, cy, type: c.type, rot: Number(c.rotate || 0), label: compLabel(c) };
    });
    const V = [];
    const items = [];                  // structured: {tag, text, ids:[...]}
    const bad = new Set();
    // Record one violation: append the (parity-identical) string AND a structured
    // item carrying the offending component ids (used for jump-to-violation).
    const rec = (text, ...cs) => {
      V.push(text);
      const tag = text.startsWith("[") ? text.slice(1, text.indexOf("]")) : "OTHER";
      const ids = [...new Set(cs.filter((c) => c && c.id).map((c) => c.id))];
      items.push({ tag, text, ids });
      cs.forEach((c) => { if (c && c.id) bad.add(c.id); });
    };

    const topKO = DR.top_keepout, botKO = DR.bot_keepout_start;

    // 1 ── nut keep-out
    for (const o of comps) {
      const { cx, cy, type, label } = o;
      // EG slide switches: rectangular slot, check y-extent against ±half-height
      if (C.type_sets.eg_2pos.includes(type) || C.type_sets.eg_3pos.includes(type)) {
        const tag = C.type_sets.eg_2pos.includes(type) ? "EG2POS" : "EG3POS";
        const ph = C.eg_panel_h[type];
        const top = cy - ph, bot = cy + ph;
        if (top < topKO) rec(`[NUT KEEPOUT] ${tag} '${label}' at cy=${f2(cy)}: slot top=${f2(top)} encroaches TOP keepout (${f2(topKO)})`, o.c);
        if (bot > botKO) rec(`[NUT KEEPOUT] ${tag} '${label}' at cy=${f2(cy)}: slot bottom=${f2(bot)} exceeds BOT keepout (${f2(botKO)})`, o.c);
        continue;
      }
      let r = null, kind = null;
      if (C.type_sets.jack.includes(type)) { r = DR.jack_nut_r; kind = "JACK"; }
      else if (C.type_sets.pot.includes(type)) { r = DR.pot_nut_r; kind = "POT"; }
      else if (C.type_sets.switch_h.includes(type)) { r = C.panel_r.switch_h; kind = "SWITCH"; }
      else if (C.type_sets.led.includes(type)) { r = C.panel_r.led; kind = "LED"; }
      if (r == null) continue;
      const top = cy - r, bot = cy + r;
      if (kind === "JACK" || kind === "POT") {
        if (top < topKO) rec(`[NUT KEEPOUT] ${kind} '${label}' @ cx=${f2(cx)},cy=${f2(cy)}: nut top=${f2(top)}mm breaches TOP keepout (${f2(topKO)}mm) — move down by ≥${f2(topKO - top)}mm`, o.c);
        if (bot > botKO) rec(`[NUT KEEPOUT] ${kind} '${label}' @ cx=${f2(cx)},cy=${f2(cy)}: nut bottom=${f2(bot)}mm breaches BOT keepout (${f2(botKO)}mm) — move up by ≥${f2(bot - botKO)}mm`, o.c);
      } else { // SWITCH / LED use the "hole" wording
        if (top < topKO) rec(`[NUT KEEPOUT] ${kind} '${label}' at cy=${f2(cy)}: hole top=${f2(top)} encroaches TOP keepout (${f2(topKO)})`, o.c);
        if (bot > botKO) rec(`[NUT KEEPOUT] ${kind} '${label}' at cy=${f2(cy)}: hole bottom=${f2(bot)} exceeds BOT keepout start (${f2(botKO)})`, o.c);
      }
    }

    // 2 ── panel-face nut / hole clearance (circles overlap)
    const circles = comps.map((o) => ({ ...o, r: panelR(o.type) })).filter((o) => o.r > 0);
    for (let i = 0; i < circles.length; i++) {
      for (let j = i + 1; j < circles.length; j++) {
        const a = circles[i], b = circles[j];
        const dist = Math.hypot(b.cx - a.cx, b.cy - a.cy);
        const need = a.r + b.r;
        if (dist < need) {
          const ov = need - dist;
          rec(`[NUT CLEARANCE] '${a.label}' (${a.type} @ cx=${f2(a.cx)},cy=${f2(a.cy)}, r=${a.r}mm) ↔ '${b.label}' (${b.type} @ cx=${f2(b.cx)},cy=${f2(b.cy)}, r=${b.r}mm) — panel circles overlap ${f2(ov)}mm (centre-to-centre=${f2(dist)}mm, need≥${f2(need)}mm; increase separation by ≥${f2(ov)}mm)`, a.c, b.c);
        }
      }
    }

    // 3 ── PCB courtyard overlaps
    const fp = comps.map((o) => ({ ...o, rect: courtyard(o.cx, o.cy, o.type, o.rot) })).filter((o) => o.rect);
    for (let i = 0; i < fp.length; i++) {
      for (let j = i + 1; j < fp.length; j++) {
        const a = fp[i], b = fp[j];
        const dx = Math.min(a.rect[2], b.rect[2]) - Math.max(a.rect[0], b.rect[0]);
        const dy = Math.min(a.rect[3], b.rect[3]) - Math.max(a.rect[1], b.rect[1]);
        if (dx > 0 && dy > 0) {
          const gap = -Math.min(dx, dy);
          rec(`[PCB OVERLAP] '${a.label}' (${a.type} @ cx=${f2(a.cx)},cy=${f2(a.cy)}) ↔ '${b.label}' (${b.type} @ cx=${f2(b.cx)},cy=${f2(b.cy)}) — courtyard overlap ${f2(dx)}×${f2(dy)}mm (gap=${f2(gap)}mm)`, a.c, b.c);
        }
      }
    }

    // 4 ── mounting-hole clearance
    const mhr = C.mounting_hole_clearance_mm;
    for (const o of fp) {
      const [x1, y1, x2, y2] = o.rect;
      for (const mh of D.mounting_holes || []) {
        const hx = Number(mh.cx), hy = Number(mh.cy);
        const nx = Math.max(x1, Math.min(hx, x2));
        const ny = Math.max(y1, Math.min(hy, y2));
        const dist = Math.hypot(hx - nx, hy - ny);
        if (dist < mhr) rec(`[MH CLEARANCE] '${o.label}' (${o.type} @ cx=${f2(o.cx)},cy=${f2(o.cy)}) PCB courtyard is ${f2(dist)}mm from mounting hole M3 @ (${fmtVal(hx)},${fmtVal(hy)}) — need ≥${mhr.toFixed(1)}mm; move component away by ≥${f2(mhr - dist)}mm`, o.c);
      }
    }

    // 5 ── PCB courtyard keep-out (rail intrusion)
    for (const o of fp) {
      const [, y1, , y2] = o.rect;
      const rotS = o.rot ? ` rotate=${o.rot}°` : "";
      if (y1 < topKO) rec(`[PCB KEEPOUT] '${o.label}' (${o.type} @ cx=${f2(o.cx)},cy=${f2(o.cy)}${rotS}) courtyard top=${f2(y1)}mm breaches TOP keepout (${f2(topKO)}mm) by ${f2(topKO - y1)}mm — move component down by ≥${f2(topKO - y1)}mm`, o.c);
      if (y2 > botKO) rec(`[PCB KEEPOUT] '${o.label}' (${o.type} @ cx=${f2(o.cx)},cy=${f2(o.cy)}${rotS}) courtyard bottom=${f2(y2)}mm breaches BOT keepout (${f2(botKO)}mm) by ${f2(y2 - botKO)}mm — move up by ≥${f2(y2 - botKO)}mm or add rotate:180`, o.c);
    }
    return { violations: V, badIds: bad, items };
  }

  // ── SVG component renderers (anchor-relative: origin = panel hole at 0,0) ───
  const COL = D.colors;
  const FONT = 'font-family="monospace"';
  // Rounded-rect label border (anchor-relative), shared by jacks and led_labeled.
  // Drawn when c.label_border is set; geometry from design_rules.output_rect_*.
  function labelBorderRect(c, labelDy) {
    const rw = c.rect_w != null ? Number(c.rect_w) : 7.0;
    const ry = labelDy + DR.output_rect_dy;
    return `<rect x="${(-rw / 2).toFixed(2)}" y="${ry.toFixed(2)}" width="${rw}" height="${DR.output_rect_h}" rx="${DR.output_rect_rx}" fill="none" stroke="${COL.output_rect_s}" stroke-width="0.3"/>`;
  }
  function rJack(c, io) {
    const fs = Number(c.font_size || 1.8);
    const ly = DR.jack_label_dy;
    let s = `<circle r="3.5" fill="none" stroke="${COL.jack_outer}" stroke-width="0.6"/>` +
            `<circle r="1.4" fill="${COL.jack_inner}" stroke="${COL.jack_inner_s}" stroke-width="0.4"/>`;
    if (c.label_border) s += labelBorderRect(c, ly);
    s += `<text y="${ly.toFixed(1)}" fill="${COL.jack_text}" ${FONT} font-size="${fs}" text-anchor="middle">${esc(c.label || "")}</text>`;
    return s;
  }
  function rTrimpot(c) {
    const fs = Number(c.label_font_size || 1.8);
    return `<circle r="2.5" fill="${COL.knob_fill}" stroke="${COL.knob_stroke}" stroke-width="0.5"/>` +
           `<line y2="${(-DR.indicator_length)}" stroke="${COL.indicator}" stroke-width="0.5"/>` +
           `<text y="${(2.5 + 3.0).toFixed(1)}" fill="${COL.control_text}" ${FONT} font-size="${fs}" text-anchor="middle">${esc(c.label || "")}</text>`;
  }
  function rKnob(c, r) {
    let sw = 0.5 + (r - 2.5) * 0.05, isw = 0.5 + (r - 2.5) * 0.06;
    if (r >= 9) { sw = 0.7; isw = 0.8; } else if (r >= 7) { sw = 0.6; isw = 0.7; }
    const lines = c.label_lines || [c.label || ""];
    const fill = c.label_fill || COL.control_text;
    let s = `<circle r="${r}" fill="${COL.knob_fill}" stroke="${COL.knob_stroke}" stroke-width="${sw.toFixed(1)}"/>` +
            `<line y2="${(-r)}" stroke="${COL.indicator}" stroke-width="${isw.toFixed(1)}"/>`;
    const base = r + 3.0;
    lines.forEach((ln, i) => {
      s += `<text y="${(base + i * 2.3).toFixed(1)}" fill="${fill}" ${FONT} font-size="1.8" text-anchor="middle">${esc(ln)}</text>`;
    });
    return s;
  }
  function rLed(c) {
    return `<circle r="1.2" fill="${c.led_fill || COL.led_fill}" stroke="${c.led_stroke || COL.led_stroke}" stroke-width="0.4"/>`;
  }
  function rLedLabeled(c) {
    const dy = c.label_dy != null ? Number(c.label_dy) : DR.jack_label_dy;
    const lf = c.label_fill || COL.jack_text;
    const fs = Number(c.font_size || 1.8);
    return rLed(c) + (c.label_border ? labelBorderRect(c, dy) : "") +
      `<text y="${dy.toFixed(1)}" fill="${lf}" ${FONT} font-size="${fs}" text-anchor="middle">${esc(c.label || "")}</text>`;
  }
  function rSwitchH(c, width, rawcx) {
    const labels = c.pos_labels || [], xs = c.pos_xs || [];
    const bx = -width / 2;
    let s = "";
    if (width === 9 && c.label_above != null) {
      const ay = c.label_above_y != null ? Number(c.label_above_y) - resolve(c, zoneOf(c)).cy : -3.5;
      s += `<text y="${ay}" fill="${COL.jack_text}" ${FONT} font-size="1.8" text-anchor="middle">${esc(c.label_above)}</text>`;
    }
    const slug = width === 9 ? bx + 0.5 : -1.75;
    s += `<rect x="${bx.toFixed(2)}" y="-1.2" width="${width}" height="2.4" rx="1.2" fill="${COL.switch_body}" stroke="${COL.jack_outer}" stroke-width="0.5"/>`;
    s += `<rect x="${slug.toFixed(2)}" y="-1.4" width="3.5" height="2.8" rx="0.8" fill="${COL.switch_slug}" stroke="${COL.switch_slug_s}" stroke-width="0.3"/>`;
    const cy = resolve(c, zoneOf(c)).cy;
    const posY = c.pos_y != null ? Number(c.pos_y) - cy : (width === 9 ? 4 : 5.3);
    labels.forEach((pl, i) => {
      const px = (xs[i] != null ? Number(xs[i]) - rawcx : 0);
      s += `<text x="${px}" y="${posY}" fill="${COL.jack_text}" ${FONT} font-size="1.6" text-anchor="middle">${esc(pl)}</text>`;
    });
    if (width === 12) {
      const lby = c.label_below_y != null ? Number(c.label_below_y) - cy : 8.8;
      s += `<text y="${lby}" fill="${COL.control_text}" ${FONT} font-size="1.8" text-anchor="middle">${esc(c.label_below || c.label || "")}</text>`;
    }
    return s;
  }
  function rSwitchV3(c) {
    const cy = resolve(c, zoneOf(c)).cy;
    const bh = Number(c.body_height || 12);
    const top = (c.cy_body_top != null ? Number(c.cy_body_top) - cy : -bh / 2);
    const slugOff = Number(c.slug_y_offset != null ? c.slug_y_offset : 4.25);
    let s = `<rect x="-1.2" y="${top.toFixed(2)}" width="2.4" height="${bh}" rx="1.2" fill="${COL.switch_body}" stroke="${COL.jack_outer}" stroke-width="0.5"/>`;
    s += `<rect x="-1.4" y="${(top + slugOff).toFixed(2)}" width="2.8" height="3.5" rx="0.8" fill="${COL.switch_slug}" stroke="${COL.switch_slug_s}" stroke-width="0.3"/>`;
    const labels = c.pos_labels || [], ys = c.pos_ys || [];
    labels.forEach((pl, i) => {
      const py = (ys[i] != null ? Number(ys[i]) - cy : (top + i * (bh / Math.max(1, labels.length - 1))));
      s += `<text x="1.4" y="${py}" fill="${COL.switch_label}" ${FONT} font-size="1.4" text-anchor="start">${esc(pl)}</text>`;
    });
    const lby = c.label_below_y != null ? Number(c.label_below_y) - cy : (bh / 2 + 3);
    s += `<text y="${lby}" fill="${COL.control_text}" ${FONT} font-size="1.8" text-anchor="middle">${esc(c.label_below || c.label || "")}</text>`;
    return s;
  }
  function rSlider(c) {
    const travel = 45.0, half = travel / 2, slotH = travel + 3.0, slotW = 2.5;
    let s = `<rect x="${(-slotW / 2).toFixed(2)}" y="${(-slotH / 2).toFixed(2)}" width="${slotW}" height="${slotH.toFixed(1)}" rx="1.2" fill="${COL.knob_fill}" stroke="${COL.knob_stroke}" stroke-width="0.4"/>`;
    s += `<line x1="-3.5" y1="${(-half).toFixed(2)}" x2="3.5" y2="${(-half).toFixed(2)}" stroke="${COL.knob_stroke}" stroke-width="0.5"/>`;
    s += `<line x1="-3.5" y1="${half.toFixed(2)}" x2="3.5" y2="${half.toFixed(2)}" stroke="${COL.knob_stroke}" stroke-width="0.5"/>`;
    s += `<line x1="-2" y1="0" x2="2" y2="0" stroke="${COL.indicator}" stroke-width="0.35"/>`;
    s += `<text y="${(-slotH / 2 - 3.5).toFixed(1)}" fill="${COL.jack_text}" ${FONT} font-size="1.8" text-anchor="middle">${esc(c.label || "")}</text>`;
    return s;
  }
  // E-Switch EG1218 — 2-pos horizontal slide (port of svg_eg_slide_h, anchor-relative).
  function rEg2pos(c, rawcx) {
    const bw = 11.6, bh = 4.0, pw = 3.5, ph = 4.8;
    const cy = resolve(c, zoneOf(c)).cy;
    let s = "";
    if (c.label_above != null) {
      const ay = c.label_above_y != null ? Number(c.label_above_y) - cy : -3.5;
      s += `<text y="${ay}" fill="${COL.jack_text}" ${FONT} font-size="1.8" text-anchor="middle">${esc(c.label_above)}</text>`;
    }
    s += `<rect x="${(-bw / 2).toFixed(2)}" y="${(-bh / 2).toFixed(2)}" width="${bw}" height="${bh}" rx="0.8" fill="${COL.switch_body}" stroke="${COL.jack_outer}" stroke-width="0.5"/>`;
    s += `<rect x="${(-bw / 2 + 0.8).toFixed(2)}" y="${(-ph / 2).toFixed(2)}" width="${pw}" height="${ph}" rx="0.6" fill="${COL.switch_slug}" stroke="${COL.switch_slug_s}" stroke-width="0.3"/>`;
    const labels = c.pos_labels || [], xs = c.pos_xs || [];
    const posY = c.pos_y != null ? Number(c.pos_y) - cy : 4;
    labels.forEach((pl, i) => {
      const px = xs[i] != null ? Number(xs[i]) - rawcx : 0;
      s += `<text x="${px}" y="${posY}" fill="${COL.jack_text}" ${FONT} font-size="1.6" text-anchor="middle">${esc(pl)}</text>`;
    });
    return s;
  }
  // E-Switch EG2301 — 3-pos vertical slide (port of svg_eg_slide_v, anchor-relative).
  function rEg3pos(c) {
    const bw = 6.5, bh = 16.0, tw = 2.0, pw = 7.3, ph = 4.0;
    const cy = resolve(c, zoneOf(c)).cy;
    let s = `<rect x="${(-bw / 2).toFixed(2)}" y="${(-bh / 2).toFixed(2)}" width="${bw}" height="${bh}" rx="0.8" fill="${COL.switch_body}" stroke="${COL.jack_outer}" stroke-width="0.5"/>`;
    s += `<rect x="${(-tw / 2).toFixed(2)}" y="${(-bh / 2).toFixed(2)}" width="${tw}" height="${bh}" rx="0.5" fill="${COL.panel_bg}" stroke="none"/>`;
    s += `<rect x="${(-pw / 2).toFixed(2)}" y="${(-ph / 2).toFixed(2)}" width="${pw}" height="${ph}" rx="0.6" fill="${COL.switch_slug}" stroke="${COL.switch_slug_s}" stroke-width="0.3"/>`;
    const lx = bw / 2 + 1.2;
    const labels = c.pos_labels || [], ys = c.pos_ys || [];
    labels.forEach((pl, i) => {
      const py = ys[i] != null ? Number(ys[i]) - cy : (-bh / 2 + i * (bh / Math.max(1, labels.length - 1)));
      s += `<text x="${lx.toFixed(2)}" y="${py}" fill="${COL.switch_label}" ${FONT} font-size="1.4" text-anchor="start">${esc(pl)}</text>`;
    });
    const lby = c.label_below_y != null ? Number(c.label_below_y) - cy : (bh / 2 + 3);
    s += `<text y="${lby}" fill="${COL.control_text}" ${FONT} font-size="1.8" text-anchor="middle">${esc(c.label_below || c.label || "")}</text>`;
    return s;
  }
  // Free-text annotation (anchor-relative: baseline at the component anchor).
  function rText(c) {
    const fs = Number(c.font_size || 2.0);
    const fill = c.fill || COL.control_text;
    const w = c.font_weight === "bold" ? ' font-weight="bold"' : "";
    const anc = c.text_anchor || "middle";
    return `<text y="0" fill="${fill}" ${FONT} font-size="${fs}" text-anchor="${anc}"${w}>${esc(c.label || "")}</text>`;
  }
  // Visual SVG (anchor-relative) for a component.
  function visual(c) {
    switch (c.type) {
      case "text":        return rText(c);
      case "jack_input":  return rJack(c, "input");
      case "jack_output": return rJack(c, "output");
      case "trimpot":     return rTrimpot(c);
      case "knob_medium": return rKnob(c, 4.5);
      case "knob_large":  return rKnob(c, 7.0);
      case "knob_xl":     return rKnob(c, 9.0);
      case "led":         return rLed(c);
      case "led_labeled": return rLedLabeled(c);
      case "eg_2pos":     return rEg2pos(c, rawCx(c, zoneOf(c)));
      case "eg_3pos":     return rEg3pos(c);
      case "switch_H2":   return rSwitchH(c, 9, rawCx(c, zoneOf(c)));
      case "switch_H3":   return rSwitchH(c, 12, rawCx(c, zoneOf(c)));
      case "switch_V3":   return rSwitchV3(c);
      case "slider_V45":  return rSlider(c);
      default:            return `<circle r="2" fill="none" stroke="#888"/>`;
    }
  }

  // ── Page chrome (background, separators, labels) ───────────────────────────
  function sepV(x, y1, y2, style) {
    if (style === "main_cyan") return `<line x1="${x}" y1="${y1}" x2="${x}" y2="${y2}" stroke="${COL.cyan}" stroke-width="0.5" opacity="0.55"/>`;
    if (style === "subdiv_gray") return `<line x1="${x}" y1="${y1}" x2="${x}" y2="${y2}" stroke="${COL.subdiv}" stroke-width="0.4"/>`;
    return `<line x1="${x}" y1="${y1}" x2="${x}" y2="${y2}" stroke="${COL.zone_div}" stroke-width="0.5"/>`;
  }
  function sepH(x1, x2, y, style) {
    const cyan = style === "main_cyan";
    return `<line x1="${x1}" y1="${y}" x2="${x2}" y2="${y}" stroke="${cyan ? COL.cyan : COL.zone_div}" stroke-width="0.5"${cyan ? ' opacity="0.55"' : ""}/>`;
  }
  function sepHLabeled(x1, x2, y, label, lx, style) {
    const fs = 2.0, halfW = label.length * fs * 0.65 / 2, gap = 2.0;
    const gl = lx - halfW - gap, gr = lx + halfW + gap;
    const cyan = style === "main_cyan";
    const stroke = cyan ? COL.cyan : COL.zone_div, extra = cyan ? ' opacity="0.55"' : "";
    let s = "";
    if (x1 < gl) s += `<line x1="${x1}" y1="${y}" x2="${gl.toFixed(2)}" y2="${y}" stroke="${stroke}" stroke-width="0.5"${extra}/>`;
    if (gr < x2) s += `<line x1="${gr.toFixed(2)}" y1="${y}" x2="${x2}" y2="${y}" stroke="${stroke}" stroke-width="0.5"${extra}/>`;
    s += `<text x="${lx}" y="${y}" fill="${COL.control_text}" ${FONT} font-size="${fs}" text-anchor="middle" dominant-baseline="middle">${esc(label)}</text>`;
    return s;
  }
  function chromeSVG() {
    const W = Number(D.meta.width_mm), H = Number(D.meta.height_mm), ox = DR.x_offset || 0;
    let s = "";
    s += `<rect x="0" y="0" width="${W}" height="${H}" fill="${COL.panel_bg}"/>`;
    s += `<rect x="0" y="0" width="${W}" height="9" fill="${COL.panel_strip}"/>`;
    s += `<rect x="0" y="${H - 9}" width="${W}" height="9" fill="${COL.panel_strip}"/>`;   // symmetric with top strip
    for (const mh of D.mounting_holes || [])
      s += `<circle cx="${mh.cx}" cy="${mh.cy}" r="1.6" fill="#0d0d0d" stroke="#2a2a2a" stroke-width="0.5"/>`;
    // title
    const tx = W / 2, title = D.meta.title || "";
    if (title.includes("·")) {
      const [a, b] = title.split(/·(.*)/s);
      s += `<text x="${tx.toFixed(2)}" y="5.75" fill="${COL.cyan}" ${FONT} font-size="3.5" font-weight="bold" text-anchor="middle">${esc(a)}<tspan fill="${D.meta.title_dot_color}">·</tspan>${esc(b)}</text>`;
    } else {
      s += `<text x="${tx.toFixed(2)}" y="5.75" fill="${COL.cyan}" ${FONT} font-size="3.5" font-weight="bold" text-anchor="middle">${esc(title)}</text>`;
    }
    s += `<text x="${tx.toFixed(2)}" y="127.5" fill="${COL.brand_text}" ${FONT} font-size="2.4" text-anchor="middle" letter-spacing="0.15">${esc(D.meta.brand || "")}</text>`;
    // separators
    for (const sp of D.separators || []) {
      if (sp.type === "v") s += sepV(sp.x + ox, sp.y1, sp.y2, sp.style);
      else if (sp.type === "h") {
        const x1 = sp.x1 + ox, x2 = sp.x2 + ox;
        if (sp.label != null) s += sepHLabeled(x1, x2, sp.y, sp.label, (sp.label_x != null ? sp.label_x : (sp.x1 + sp.x2) / 2) + ox, sp.style);
        else s += sepH(x1, x2, sp.y, sp.style);
      }
    }
    for (const zl of D.zone_labels || []) {
      s += `<text x="${zl.x}" y="${zl.y}" fill="${COL.cyan}" ${FONT} font-size="2.4" text-anchor="middle" font-weight="bold">${esc(zl.text)}</text>`;
      if (zl.subtitle) s += `<text x="${zl.x}" y="${zl.y + 4.5}" fill="${COL.brand_text}" ${FONT} font-size="1.6" text-anchor="middle">${esc(zl.subtitle)}</text>`;
    }
    // Endpoint handles for the selected separator (drawn on top of chrome)
    if (UI.selSep != null && (D.separators || [])[UI.selSep]) {
      const sp = D.separators[UI.selSep];
      const e = sepEndpointsResolved(sp);
      s += `<line class="sep-hl" x1="${f3(e.a.x)}" y1="${f3(e.a.y)}" x2="${f3(e.b.x)}" y2="${f3(e.b.y)}" stroke="${COL.cyan}" stroke-width="0.6" opacity="0.9"/>`;
      const handle = (p, end) => `<circle class="sep-handle" data-sep="${UI.selSep}" data-end="${end}" cx="${f3(p.x)}" cy="${f3(p.y)}" r="1.6"/>`;
      s += handle(e.a, "a") + handle(e.b, "b") + handle(e.mid, "mid");
    }
    return s;
  }
  // Resolved (on-screen) endpoints of a separator (x-family gets +x_offset; y has none).
  function sepEndpointsResolved(sp) {
    const ox = DR.x_offset || 0;
    if (sp.type === "v") {
      const x = sp.x + ox;
      return { a: { x, y: sp.y1 }, b: { x, y: sp.y2 }, mid: { x, y: (sp.y1 + sp.y2) / 2 } };
    }
    const x1 = sp.x1 + ox, x2 = sp.x2 + ox;
    return { a: { x: x1, y: sp.y }, b: { x: x2, y: sp.y }, mid: { x: (x1 + x2) / 2, y: sp.y } };
  }

  // ── Full SVG assembly ──────────────────────────────────────────────────────
  let svgEl = null;
  function buildSVG(badIds) {
    const W = Number(D.meta.width_mm), H = Number(D.meta.height_mm);
    const comps = allComps();

    // layer-panel: chrome + each component visual (+ transparent hit target).
    // Render the selected component LAST so it paints on top of its neighbours.
    let panel = chromeSVG();
    const ordered = comps.filter(({ c }) => c.id !== UI.selId).concat(comps.filter(({ c }) => c.id === UI.selId));
    for (const { c, z } of ordered) {
      const { cx, cy } = resolve(c, z);
      const hitR = Math.max(panelR(c.type), 2.2);
      const selCls = c.id === UI.selId ? " sel" : "";
      const badCls = badIds && badIds.has(c.id) ? " violation" : "";
      panel += `<g class="comp${selCls}${badCls}" data-cid="${esc(c.id)}" transform="translate(${f3(cx)},${f3(cy)})">` +
               visual(c) +
               `<circle class="hit" r="${hitR.toFixed(2)}"/></g>`;
    }

    // overlay layers
    const kot = DR.top_keepout, kob = DR.bot_keepout_start;
    let keepout = `<rect x="0" y="0" width="${W}" height="${kot}" fill="rgba(255,0,0,0.18)"/>` +
      `<rect x="0" y="${kob}" width="${W}" height="${H - kob}" fill="rgba(255,0,0,0.18)"/>` +
      `<line x1="0" y1="${kot}" x2="${W}" y2="${kot}" stroke="#ff4444" stroke-width="0.35" stroke-dasharray="1 0.7"/>` +
      `<line x1="0" y1="${kob}" x2="${W}" y2="${kob}" stroke="#ff4444" stroke-width="0.35" stroke-dasharray="1 0.7"/>`;

    let nuts = "", pcb = "", kicad = "";
    const nutColor = { jack: ["rgba(255,204,0,0.35)", "#ffcc00"], pot: ["rgba(100,180,255,0.35)", "#64b4ff"], switch: ["rgba(220,100,255,0.35)", "#dc64ff"], led: ["rgba(100,220,100,0.35)", "#64dc64"] };
    const pcbColor = { jack: ["rgba(255,204,0,0.15)", "#ffcc00"], pot: ["rgba(100,180,255,0.15)", "#64b4ff"], switch: ["rgba(220,100,255,0.15)", "#dc64ff"], led: ["rgba(100,220,100,0.15)", "#64dc64"], slider: ["rgba(0,210,180,0.15)", "#00d4b4"] };
    function cat(t) {
      if (C.type_sets.jack.includes(t)) return "jack";
      if (C.type_sets.pot.includes(t)) return "pot";
      if (t.startsWith("switch") || t.startsWith("eg_")) return "switch";
      if (C.type_sets.led.includes(t)) return "led";
      if (C.type_sets.slider.includes(t)) return "slider";
      return null;
    }
    for (const { c, z } of comps) {
      const { cx, cy } = resolve(c, z);
      const rot = Number(c.rotate || 0);
      const k = cat(c.type);
      const r = panelR(c.type);
      if (r > 0 && nutColor[k]) nuts += `<circle data-cid="${esc(c.id)}" cx="${f3(cx)}" cy="${f3(cy)}" r="${r}" fill="${nutColor[k][0]}" stroke="${nutColor[k][1]}" stroke-width="0.25"/>`;
      else if (r > 0) nuts += `<circle data-cid="${esc(c.id)}" cx="${f3(cx)}" cy="${f3(cy)}" r="${r}" fill="rgba(180,180,180,0.3)" stroke="#aaa" stroke-width="0.25"/>`;
      const rect = courtyard(cx, cy, c.type, rot);
      if (rect && pcbColor[k]) pcb += `<rect data-cid="${esc(c.id)}" x="${f3(rect[0])}" y="${f3(rect[1])}" width="${f3(rect[2] - rect[0])}" height="${f3(rect[3] - rect[1])}" fill="${pcbColor[k][0]}" stroke="${pcbColor[k][1]}" stroke-width="0.2" stroke-dasharray="0.8 0.4"/>`;
      const tpl = KT[c.type];
      if (tpl) {
        const tr = rot ? `translate(${f3(cx)},${f3(cy)}) rotate(${rot})` : `translate(${f3(cx)},${f3(cy)})`;
        kicad += `<g data-cid="${esc(c.id)}" data-rot="${rot}" transform="${tr}">${tpl}` +
          `<line x1="-1.8" y1="0" x2="1.8" y2="0" stroke="#00ff88" stroke-width="0.18"/><line x1="0" y1="-1.8" x2="0" y2="1.8" stroke="#00ff88" stroke-width="0.18"/></g>`;
      }
    }

    const dsp = (on) => on ? "" : ' style="display:none;"';
    const svg =
      `<svg xmlns="http://www.w3.org/2000/svg" width="${(W * SCALE).toFixed(0)}" height="${(H * SCALE).toFixed(0)}" viewBox="0 0 ${W} ${H}">` +
      `<g id="layer-panel"${dsp(UI.layers.panel)}>${panel}</g>` +
      `<g id="layer-keepout"${dsp(UI.layers.keepout)}>${keepout}</g>` +
      `<g id="layer-nuts"${dsp(UI.layers.nuts)}>${nuts}</g>` +
      `<g id="layer-pcb"${dsp(UI.layers.pcb)}>${pcb}</g>` +
      `<g id="layer-kicad"${dsp(UI.layers.kicad)}>${kicad}</g>` +
      `</svg>`;
    return svg;
  }

  // ── Render (full) ──────────────────────────────────────────────────────────
  let lastDRC = { violations: [], badIds: new Set() };
  function render() {
    lastDRC = runDRC();
    document.getElementById("canvas").innerHTML = buildSVG(lastDRC.badIds);
    svgEl = document.querySelector("#canvas svg");
    wireCanvas();
    renderTopbar();
    renderLeft();
    renderRight();
    renderDRCPanel();
  }

  // ── Canvas interaction ───────────────────────────────────────────────────────
  function clientToMm(e) {
    const pt = svgEl.createSVGPoint();
    pt.x = e.clientX; pt.y = e.clientY;
    const m = svgEl.getScreenCTM().inverse();
    const p = pt.matrixTransform(m);
    return { x: p.x, y: p.y };
  }
  function setCompTransform(id, cx, cy) {
    svgEl.querySelectorAll(`[data-cid="${cssEsc(id)}"]`).forEach((g) => {
      if (g.tagName === "circle" && g.classList.contains("hit")) return;
      if (g.tagName === "circle") { g.setAttribute("cx", f3(cx)); g.setAttribute("cy", f3(cy)); return; }
      if (g.tagName === "rect") return; // courtyard rects: refreshed on full render at drop
      const rot = g.dataset.rot;
      g.setAttribute("transform", rot && rot !== "0" ? `translate(${f3(cx)},${f3(cy)}) rotate(${rot})` : `translate(${f3(cx)},${f3(cy)})`);
    });
  }
  const cssEsc = (s) => (window.CSS && CSS.escape) ? CSS.escape(s) : String(s).replace(/["\\]/g, "\\$&");

  // ── Clearance HUD (shown while dragging) ───────────────────────────────────
  let hudEl = null;
  function hud() {
    if (!hudEl) { hudEl = document.createElement("div"); hudEl.id = "hud"; document.body.appendChild(hudEl); }
    return hudEl;
  }
  function showHUD(id, x, y) {
    const el = hud(); el.style.display = "block";
    const fmtG = (v, unit) => v == null ? "—" : `${v >= 0 ? "+" : ""}${f2(v)}${unit || "mm"}`;
    const n = nearestComp(id, x, y);
    let h = `<b>${esc(id)}</b>  cx=${f2(x)}  cy=${f2(y)}  (${(x / HP_MM).toFixed(2)} HP)`;
    if (n) {
      const g = pairGap({ cx: x, cy: y, type: findComp(id).c.type, rot: Number(findComp(id).c.rotate || 0) }, n);
      const nutCls = g.nut != null && g.nut < 0 ? "bad" : "";
      const ctCls = g.courtyard != null && g.courtyard < 0 ? "bad" : "";
      h += `<br>↔ <b>${esc(n.c.id || "?")}</b>  c-c ${f2(g.dist)}mm` +
        `  ·  nut <span class="${nutCls}">${fmtG(g.nut)}</span>` +
        `  ·  courtyard <span class="${ctCls}">${fmtG(g.courtyard)}</span>`;
    }
    el.innerHTML = h;
  }
  function hideHUD() { if (hudEl) hudEl.style.display = "none"; }

  let drag = null, pan = null, sepDrag = null;
  let spaceDown = false;
  function panActive() { return UI.tool === "pan" || spaceDown; }
  // Distance from point p to segment a-b (mm).
  function distToSeg(p, a, b) {
    const vx = b.x - a.x, vy = b.y - a.y;
    const L2 = vx * vx + vy * vy;
    let t = L2 ? ((p.x - a.x) * vx + (p.y - a.y) * vy) / L2 : 0;
    t = Math.max(0, Math.min(1, t));
    return Math.hypot(p.x - (a.x + t * vx), p.y - (a.y + t * vy));
  }
  function sepAtPoint(m) {                 // index of separator within ~1mm of point, or -1
    const seps = D.separators || [];
    let best = -1, bd = 1.0;
    for (let i = 0; i < seps.length; i++) {
      const e = sepEndpointsResolved(seps[i]);
      const d = distToSeg(m, e.a, e.b);
      if (d < bd) { bd = d; best = i; }
    }
    return best;
  }
  function wireCanvas() {
    const wrap = document.getElementById("canvas-wrap");
    svgEl.style.cursor = panActive() ? "grab" : (UI.tool === "anchor" ? "crosshair" : "default");

    // Background: select a separator under the cursor, else deselect, else pan.
    svgEl.addEventListener("pointerdown", (e) => {
      if (e.target.closest && e.target.closest(".comp")) return;       // component handles its own
      if (e.target.classList && e.target.classList.contains("sep-handle")) return;  // handle handles its own
      if (panActive()) {
        pan = { x: e.clientX, y: e.clientY, sl: wrap.scrollLeft, st: wrap.scrollTop };
        svgEl.setPointerCapture(e.pointerId); svgEl.style.cursor = "grabbing"; e.preventDefault();
      } else if (UI.tool === "anchor") {
        UI.anchor = null; UI.tool = "select"; render();   // click empty space cancels pick
      } else {
        const si = sepAtPoint(clientToMm(e));
        if (si >= 0) { selectSep(si); }
        else if (UI.selId || UI.selZone || UI.selSep != null) deselect();
      }
    });
    svgEl.addEventListener("pointermove", (e) => {
      if (!pan) return;
      wrap.scrollLeft = pan.sl - (e.clientX - pan.x);
      wrap.scrollTop = pan.st - (e.clientY - pan.y);
    });
    const endPan = () => { if (pan) { pan = null; svgEl.style.cursor = panActive() ? "grab" : "default"; } };
    svgEl.addEventListener("pointerup", endPan);
    svgEl.addEventListener("pointercancel", endPan);

    svgEl.querySelectorAll(".comp").forEach((g) => {
      g.addEventListener("pointerdown", (e) => {
        const id = g.dataset.cid;
        if (panActive()) return;                 // let background pan handler run
        e.preventDefault(); e.stopPropagation();
        if (UI.tool === "anchor") { applyAnchor(id); return; }
        UI.selId = id; UI.selZone = null; renderSelectionOnly();
        const lp = svgEl.querySelector("#layer-panel");   // bring to top (paints last)
        if (lp && g.parentNode === lp) lp.appendChild(g);
        const m = clientToMm(e);
        const f = findComp(id); const { cx, cy } = resolve(f.c, f.z);
        drag = { id, dx: m.x - cx, dy: m.y - cy, moved: false };
        g.setPointerCapture(e.pointerId);
      });
      g.addEventListener("pointermove", (e) => {
        if (!drag || drag.id !== g.dataset.cid) return;
        const m = clientToMm(e);
        const p = snapPos(m.x - drag.dx, m.y - drag.dy);
        drag.nx = p.x; drag.ny = p.y; drag.moved = true;
        setCompTransform(drag.id, p.x, p.y);
        const g2 = svgEl.querySelector(`.comp[data-cid="${cssEsc(drag.id)}"]`);
        if (g2) g2.setAttribute("transform", `translate(${f3(p.x)},${f3(p.y)})`);
        // live DRC: recolour violators against the dragged position (no model mutation)
        const bad = runDRC({ id: drag.id, cx: p.x, cy: p.y }).badIds;
        svgEl.querySelectorAll(".comp").forEach((gg) => gg.classList.toggle("violation", bad.has(gg.dataset.cid)));
        showHUD(drag.id, p.x, p.y);
      });
      const end = () => {
        if (!drag || drag.id !== g.dataset.cid) return;
        hideHUD();
        if (drag.moved && drag.nx != null) moveCompTo(drag.id, drag.nx, drag.ny);
        else { drag = null; renderRight(); }       // simple click = select (no move)
        drag = null;
      };
      g.addEventListener("pointerup", end);
      g.addEventListener("pointercancel", end);
    });

    // Separator endpoint handles
    svgEl.querySelectorAll(".sep-handle").forEach((h) => {
      h.addEventListener("pointerdown", (e) => {
        if (panActive()) return;
        e.preventDefault(); e.stopPropagation();
        sepDrag = { idx: Number(h.dataset.sep), end: h.dataset.end, snapped: false };
        h.setPointerCapture(e.pointerId);
      });
      h.addEventListener("pointermove", (e) => {
        if (!sepDrag || sepDrag.idx !== Number(h.dataset.sep) || sepDrag.end !== h.dataset.end) return;
        if (!sepDrag.snapped) { snapshot(); sepDrag.snapped = true; }
        const mm = clientToMm(e); const m = snapPos(mm.x, mm.y);
        moveSepEndpoint(sepDrag.idx, sepDrag.end, m.x, m.y);
        // Update the live SVG directly (NO full render — re-rendering would destroy
        // this handle and drop the pointer capture, breaking fast drags).
        const e2 = sepEndpointsResolved(D.separators[sepDrag.idx]);
        const hl = svgEl.querySelector(".sep-hl");
        if (hl) { hl.setAttribute("x1", f3(e2.a.x)); hl.setAttribute("y1", f3(e2.a.y)); hl.setAttribute("x2", f3(e2.b.x)); hl.setAttribute("y2", f3(e2.b.y)); }
        svgEl.querySelectorAll(".sep-handle").forEach((hh) => {
          const p = e2[hh.dataset.end]; if (p) { hh.setAttribute("cx", f3(p.x)); hh.setAttribute("cy", f3(p.y)); }
        });
        sepDrag.moved = true;
      });
      const sEnd = () => {
        if (!sepDrag || sepDrag.idx !== Number(h.dataset.sep)) return;
        const moved = sepDrag.moved; sepDrag = null;
        if (moved) render();            // rebuild cleanly (tree, inspector, DRC) on drop
      };
      h.addEventListener("pointerup", sEnd);
      h.addEventListener("pointercancel", sEnd);
    });
  }
  // Apply a resolved (on-screen) endpoint position to a separator (convert x→raw).
  function moveSepEndpoint(idx, end, rx, ry) {
    const sp = (D.separators || [])[idx]; if (!sp) return;
    const ox = DR.x_offset || 0;
    const W = Number(D.meta.width_mm), H = Number(D.meta.height_mm);
    const clampX = (v) => round3(Math.max(0, Math.min(W, v)) - ox);
    const clampYr = (v) => round3(Math.max(0, Math.min(H, v)));
    if (sp.type === "v") {
      if (end === "mid") sp.x = clampX(rx);
      else if (end === "a") sp.y1 = clampYr(ry);
      else sp.y2 = clampYr(ry);
    } else {
      const labelCentered = sp.label != null && sp.label_x != null && Math.abs(sp.label_x - (sp.x1 + sp.x2) / 2) < 0.01;
      if (end === "mid") sp.y = clampYr(ry);
      else if (end === "a") sp.x1 = clampX(rx);
      else sp.x2 = clampX(rx);
      if (labelCentered) sp.label_x = round3((sp.x1 + sp.x2) / 2);
    }
  }
  // Lightweight selection highlight without a full re-render (used on pointerdown).
  function renderSelectionOnly() {
    svgEl.querySelectorAll(".comp.sel").forEach((g) => g.classList.remove("sel"));
    const g = svgEl.querySelector(`.comp[data-cid="${cssEsc(UI.selId)}"]`);
    if (g) g.classList.add("sel");
    renderRight();
    document.querySelectorAll(".tree-comp.sel").forEach((e) => e.classList.remove("sel"));
    const t = document.querySelector(`.tree-comp[data-cid="${cssEsc(UI.selId)}"]`);
    if (t) t.classList.add("sel");
  }

  // ── Snap helpers ─────────────────────────────────────────────────────────────
  const round3 = (v) => Math.round(v * 1000) / 1000;
  function snapStepMm() { return UI.snapUnit === "hp" ? UI.snapVal * HP_MM : UI.snapVal; }
  function snapPos(nx, ny) {              // snap a resolved (on-screen) mm point
    if (!UI.snap) return { x: nx, y: ny };
    const step = snapStepMm();
    if (!(step > 0)) return { x: nx, y: ny };
    const o = UI.snapOrigin || { x: 0, y: 0 };
    return { x: o.x + Math.round((nx - o.x) / step) * step, y: o.y + Math.round((ny - o.y) / step) * step };
  }

  // ── Mutations ────────────────────────────────────────────────────────────────
  // Shift a component's ABSOLUTE auxiliary position fields so labels/position-marks
  // track the body when it moves. These store absolute panel coords (y) / raw x and
  // would otherwise drift relative to the moved cx/cy.
  function shiftAux(c, ddx, ddy) {
    if (ddy) {
      for (const k of ["label_below_y", "label_above_y", "cy_body_top", "pos_y"])
        if (c[k] != null) c[k] = round3(Number(c[k]) + ddy);
      if (Array.isArray(c.pos_ys)) c.pos_ys = c.pos_ys.map((v) => round3(Number(v) + ddy));
    }
    if (ddx && Array.isArray(c.pos_xs)) c.pos_xs = c.pos_xs.map((v) => round3(Number(v) + ddx));
  }
  function setCompResolved(c, resolvedCx, resolvedCy) {  // write model from on-screen coords
    const old = resolve(c, zoneOf(c));
    shiftAux(c, resolvedCx - old.cx, resolvedCy - old.cy);
    c.cx = round3(resolvedCx - (DR.x_offset || 0));
    delete c.col;                       // off the column grid → explicit cx
    c.cy = round3(resolvedCy);
    reassignZone(c);                    // keep tree membership = the zone it now sits in
  }
  // Raw (pre-x_offset) x-span [x0,x1) of a column-relative zone, else null.
  function zoneSpanRaw(z) {
    if (z.x_start == null) return null;
    const pitch = z.col_pitch != null ? Number(z.col_pitch) : DR.jack_pitch;
    const cols = z.cols != null ? Number(z.cols) : 0;
    if (!cols) return null;
    const x0 = Number(z.x_start);
    return [x0, x0 + cols * pitch];
  }
  function zoneForRawCx(rawcx) {
    for (const z of D.zones || []) { const s = zoneSpanRaw(z); if (s && rawcx >= s[0] - 0.001 && rawcx < s[1] + 0.001) return z; }
    return null;
  }
  // Representative raw-x of a separator (for associating it with a zone in the tree).
  const sepRepX = (sp) => sp.type === "v" ? Number(sp.x) : (Number(sp.x1) + Number(sp.x2)) / 2;
  const zoneOfSep = (sp) => zoneForRawCx(sepRepX(sp));
  // After an individual move, move the component object into the zone whose x-span
  // now contains it (so the component tree reflects its real location).
  function reassignZone(c) {
    const target = zoneForRawCx(Number(c.cx));
    if (!target) return;
    const cur = zoneOf(c);
    if (!cur || cur === target) return;
    const i = cur.components.indexOf(c);
    if (i >= 0) cur.components.splice(i, 1);
    (target.components = target.components || []).push(c);
  }
  function moveCompTo(id, resolvedCx, resolvedCy) {
    snapshot();
    setCompResolved(findComp(id).c, resolvedCx, resolvedCy);
    render();
  }
  function moveCompBy(id, ddx, ddy) {     // arrow-nudge in mm
    snapshot();
    const { c, z } = findComp(id);
    const r = resolve(c, z);
    const p = snapPos(r.cx + ddx, r.cy + ddy);
    setCompResolved(c, p.x, p.y);
    render();
  }
  function rotateComp(id) {
    snapshot();
    const { c } = findComp(id);
    const next = { 0: 90, 90: 180, 180: 270, 270: 0 }[Number(c.rotate || 0)];
    if (next === 0) delete c.rotate; else c.rotate = next;
    render();
  }
  function deleteComp(id) {
    snapshot();
    for (const z of D.zones || []) {
      const i = (z.components || []).findIndex((c) => c.id === id);
      if (i >= 0) { z.components.splice(i, 1); break; }
    }
    if (UI.selId === id) UI.selId = null;
    render();
  }
  // Revert a component to its as-built (ORIG) spec. No-op for added components.
  function revertComp(id) {
    const orig = (ORIG.zones || []).flatMap((z) => z.components || []).find((c) => c.id === id);
    if (!orig) return;
    snapshot();
    const { c } = findComp(id);
    for (const k of Object.keys(c)) delete c[k];
    Object.assign(c, clone(orig));
    render();
  }
  function targetZone() {                 // zone to add into, per current selection
    if (UI.selZone) { const z = (D.zones || []).find((z) => z.id === UI.selZone); if (z) return z; }
    if (UI.selId) { const r = findComp(UI.selId); if (r) return r.z; }
    return (D.zones || [])[0];
  }
  function addComp(type) {
    const z = targetZone();
    if (!z) { alert("No zone to add into."); return; }
    snapshot();
    let n = 1, id;
    do { id = `${type.toUpperCase()}_${n++}`; } while (findComp(id));
    const W = Number(D.meta.width_mm);
    const isJack = type.startsWith("jack");
    const c = {
      id, type,
      cx: round3(W / 2 - (DR.x_offset || 0)),
      cy: 60,
      label: type === "text" ? "TEXT" : type.replace(/_/g, " ").toUpperCase(),
    };
    if (type === "text") c.font_size = 2.0;
    else if (isJack) c.cpp_id = id + "_INPUT"; else c.cpp_param = id + "_PARAM";
    if (!z.components) z.components = [];
    z.components.push(c);
    UI.selId = id; UI.selZone = null; UI.selSep = null;
    render();
  }
  function addDivider(orient) {
    snapshot();
    const ox = DR.x_offset || 0, W = Number(D.meta.width_mm), H = Number(D.meta.height_mm);
    let sp;
    if (orient === "v") {
      sp = { type: "v", x: round3(W / 2 - ox), y1: 9, y2: round3(H - 4.5), style: "zone_div" };
    } else {
      // Horizontal divider spans the selected zone (so it nests under that zone).
      const s = zoneSpanRaw(targetZone() || {});
      const x1 = s ? s[0] : W * 0.25 - ox, x2 = s ? s[1] : W * 0.75 - ox;
      sp = { type: "h", x1: round3(x1), x2: round3(x2), y: round3(H / 2), style: "zone_div" };
    }
    (D.separators = D.separators || []).push(sp);
    selectSep(D.separators.length - 1);
  }
  function addZone() {
    snapshot();
    let n = 1, id;
    const has = (zid) => (D.zones || []).some((z) => z.id === zid);
    do { id = `zone_new_${n++}`; } while (has(id));
    // Default: a 3-column section starting just past the current content's right edge.
    let xs = 0;
    for (const { c, z } of allComps()) xs = Math.max(xs, rawCx(c, z));
    const x0 = round3(Math.min(xs + 11.43, Number(D.meta.width_mm) - 34.29));
    const z = { id, label: "New Zone", x_start: x0, col_pitch: 11.43, cols: 3, components: [] };
    (D.zones = D.zones || []).push(z);
    // Zones own their vertical boundary divider — create one at the zone's left edge.
    (D.separators = D.separators || []).push({ type: "v", x: x0, y1: 9, y2: round3(Number(D.meta.height_mm) - 4.5), style: "zone_div" });
    selectZone(id);
  }
  function deleteZone(zid) {
    const i = (D.zones || []).findIndex((z) => z.id === zid);
    if (i < 0) return;
    const z = D.zones[i];
    if ((z.components || []).length && !confirm(`Delete zone "${zid}" and its ${z.components.length} component(s)?`)) return;
    snapshot();
    D.zones.splice(i, 1);
    if (UI.selZone === zid) UI.selZone = null;
    render();
  }
  function selectComp(id) {
    UI.selId = id; UI.selZone = null; UI.selSep = null;
    if (UI.anchor) { applyAnchor(id); return; }
    render();
  }
  function selectZone(zid) {
    UI.selZone = zid; UI.selId = null; UI.selSep = null; UI.anchor = null;
    render();
  }
  function selectSep(i) { UI.selSep = i; UI.selId = null; UI.selZone = null; UI.anchor = null; render(); }
  function deselect() { UI.selId = null; UI.selZone = null; UI.selSep = null; UI.anchor = null; if (UI.tool === "anchor") UI.tool = "select"; render(); }
  const selSepObj = () => (UI.selSep != null ? (D.separators || [])[UI.selSep] : null);

  // ── Zone (section) operations — mirror Python shift_zone ───────────────────────
  function shiftZoneBy(zid, dx, dy) {
    const z = (D.zones || []).find((z) => z.id === zid); if (!z) return;
    snapshot();
    const oldXs = z.x_start != null ? Number(z.x_start) : null;
    if (dx && z.x_start != null) z.x_start = round3(Number(z.x_start) + dx);
    for (const c of z.components || []) {
      if (dx && c.cx != null && c.col == null) c.cx = round3(Number(c.cx) + dx);
      if (dy) { const r = resolve(c, z); c.cy = round3(r.cy + dy); }
      shiftAux(c, dx, dy);              // keep switch labels / position marks aligned
    }
    // Vertical dividers are tied to zones: move the boundary line at the old left edge.
    if (dx && oldXs != null)
      for (const sp of D.separators || []) if (sp.type === "v" && Math.abs(Number(sp.x) - oldXs) < 0.01) sp.x = round3(Number(sp.x) + dx);
    render();
  }
  function renameZone(oldId, field, value) {  // field: "id" | "label"
    const z = (D.zones || []).find((z) => z.id === oldId); if (!z) return;
    snapshot();
    if (field === "id") { z.id = value; if (UI.selZone === oldId) UI.selZone = value; }
    else z.label = value;
    render();
  }
  function setZoneXStart(zid, val) {
    const z = (D.zones || []).find((z) => z.id === zid); if (!z || z.x_start == null) return;
    shiftZoneBy(zid, Number(val) - Number(z.x_start), 0);
  }

  // ── Anchor / align ─────────────────────────────────────────────────────────────
  // UI.anchor = { mode:'align'|'place', axis:'x'|'y', origin:'pick'|'zero'|index, offX, offY, unit }
  function armAlign(axis) { if (!UI.selId) return; UI.anchor = { mode: "align", axis }; UI.tool = "anchor"; render(); }
  function dividerPoint(idx) {
    const sp = (D.separators || [])[idx]; if (!sp) return null;
    const ox = DR.x_offset || 0;
    if (sp.type === "v") return { x: sp.x + ox, y: (sp.y1 + sp.y2) / 2 };
    return { x: (sp.x1 + sp.x2) / 2 + ox, y: sp.y };
  }
  function applyAnchor(refId) {           // a component was clicked as the reference
    const a = UI.anchor; if (!a || !UI.selId) { UI.anchor = null; return; }
    const sel = findComp(UI.selId); const ref = findComp(refId);
    if (!sel || !ref || refId === UI.selId) { UI.anchor = null; UI.tool = "select"; render(); return; }
    const rp = resolve(ref.c, ref.z), sp = resolve(sel.c, sel.z);
    if (a.mode === "align") {
      if (a.axis === "x") setCompResolved(sel.c, rp.cx, sp.cy);
      else setCompResolved(sel.c, sp.cx, rp.cy);
    }
    UI.anchor = null; UI.tool = "select";
    snapshot(); render();
  }
  function placeRelative(originPt, offX, offY, unit) {  // explicit offset placement
    if (!UI.selId) return;
    const k = unit === "hp" ? HP_MM : 1;
    const sel = findComp(UI.selId);
    snapshot();
    setCompResolved(sel.c, originPt.x + offX * k, originPt.y + offY * k);
    render();
  }

  // ── Top bar ──────────────────────────────────────────────────────────────────
  function renderTopbar() {
    const pass = lastDRC.violations.length === 0;
    const lyr = (key, name) =>
      `<label class="lyr"><input type="checkbox" data-layer="${key}" ${UI.layers[key] ? "checked" : ""}> ${name}</label>`;
    const toolBtn = (t, name) => `<button data-tool="${t}" class="${UI.tool === t ? "primary" : ""}" title="${name}">${name}</button>`;
    const originLabel = UI.snapOrigin ? (UI.snapOriginId || "ref") : "0,0";
    document.getElementById("topbar").innerHTML =
      `<h1>POGO PANEL EDITOR</h1>` +
      `<div class="group">${toolBtn("select", "Select")}${toolBtn("pan", "Pan")}` +
      `<button id="undo" title="Undo (Ctrl+Z)"${undoStack.length ? "" : " disabled"}>↶</button>` +
      `<button id="redo" title="Redo (Ctrl+Shift+Z)"${redoStack.length ? "" : " disabled"}>↷</button></div>` +
      `<div class="sep"></div>` +
      `<div class="group">HP <input type="number" id="hp" min="2" max="84" step="1" value="${D.meta.hp}"> ` +
      `<button id="recenter" title="Recompute x_offset to centre content">Recenter</button>` +
      `<button id="panel-settings">Panel…</button></div>` +
      `<div class="sep"></div>` +
      `<div class="group">` + lyr("panel", "Panel") + lyr("keepout", "Keep-Out") + lyr("nuts", "Nuts") + lyr("pcb", "Courtyards") + lyr("kicad", "KiCad") + `</div>` +
      `<div class="sep"></div>` +
      `<div class="group"><label class="lyr"><input type="checkbox" id="snap" ${UI.snap ? "checked" : ""}> Snap</label>` +
      `<input type="number" id="snapVal" step="0.05" min="0.05" value="${UI.snapVal}" style="width:54px">` +
      `<select id="snapUnit"><option value="mm" ${UI.snapUnit === "mm" ? "selected" : ""}>mm</option><option value="hp" ${UI.snapUnit === "hp" ? "selected" : ""}>HP</option></select>` +
      `<button id="snapOrigin" title="Snap grid origin">grid: ${esc(originLabel)}</button></div>` +
      `<div class="sep"></div>` +
      `<div class="group"><button id="export" class="primary">Export YAML</button></div>` +
      `<div class="sep"></div>` +
      `<span class="badge ${pass ? "pass" : "fail"}">${pass ? "DRC PASS" : "DRC " + lastDRC.violations.length + " ✗"}</span>`;

    document.querySelectorAll("#topbar [data-tool]").forEach((b) =>
      b.addEventListener("click", () => { UI.tool = b.dataset.tool; UI.anchor = null; render(); }));
    document.getElementById("undo").addEventListener("click", undo);
    document.getElementById("redo").addEventListener("click", redo);
    document.querySelectorAll("#topbar input[data-layer]").forEach((cb) =>
      cb.addEventListener("change", () => {
        UI.layers[cb.dataset.layer] = cb.checked;
        const el = svgEl.querySelector("#layer-" + cb.dataset.layer);
        if (el) el.style.display = cb.checked ? "" : "none";
      }));
    document.getElementById("snap").addEventListener("change", (e) => { UI.snap = e.target.checked; });
    document.getElementById("snapVal").addEventListener("change", (e) => { UI.snapVal = Number(e.target.value) || 0.5; });
    document.getElementById("snapUnit").addEventListener("change", (e) => { UI.snapUnit = e.target.value; });
    document.getElementById("snapOrigin").addEventListener("click", () => {
      if (UI.snapOrigin) { UI.snapOrigin = null; UI.snapOriginId = null; }
      else if (UI.selId) { const f = findComp(UI.selId); const r = resolve(f.c, f.z); UI.snapOrigin = { x: r.cx, y: r.cy }; UI.snapOriginId = UI.selId; }
      else { alert("Select a component first to use it as the snap-grid origin."); return; }
      renderTopbar();
    });
    document.getElementById("hp").addEventListener("change", (e) => setHP(Number(e.target.value)));
    document.getElementById("recenter").addEventListener("click", recenter);
    document.getElementById("panel-settings").addEventListener("click", openPanelSettings);
    document.getElementById("export").addEventListener("click", openExport);
  }
  // ── Panel settings (rename board: title / brand) ───────────────────────────────
  function openPanelSettings() {
    const m = document.getElementById("export-modal");
    m.classList.remove("hidden");
    m.innerHTML = `<div class="box" style="height:auto"><h2>Panel settings</h2>` +
      `<div class="field"><label>title (meta.title — shown on panel; split on · for the colored dot)</label><input id="ps-title" type="text" value="${esc(D.meta.title || "")}"></div>` +
      `<div class="field"><label>brand (meta.brand — bottom strip)</label><input id="ps-brand" type="text" value="${esc(D.meta.brand || "")}"></div>` +
      `<div class="bar"><button id="ps-apply" class="primary">Apply</button><button id="ps-close">Close</button></div></div>`;
    document.getElementById("ps-close").addEventListener("click", () => m.classList.add("hidden"));
    document.getElementById("ps-apply").addEventListener("click", () => {
      snapshot();
      D.meta.title = document.getElementById("ps-title").value;
      D.meta.brand = document.getElementById("ps-brand").value;
      m.classList.add("hidden"); render();
    });
  }
  function setHP(hp) {
    if (!hp || hp < 2) return;
    snapshot();
    D.meta.hp = hp;
    const W = Math.round(hp * 5.08 * 100) / 100;
    D.meta.width_mm = W;
    D.meta.viewBox = `0 0 ${W} ${D.meta.height_mm}`;
    // right-edge mounting holes follow the new width
    for (const mh of D.mounting_holes || []) if (Number(mh.cx) > Number(ORIG.meta.width_mm) / 2) mh.cx = Math.round((W - 7.5) * 100) / 100;
    render();
  }
  function recenter() {
    // x_offset that centres the content span within the panel width
    const xs = [];
    for (const sp of D.separators || []) {
      if (sp.type === "v") xs.push(sp.x);
      else { xs.push(sp.x1, sp.x2); }
    }
    for (const { c, z } of allComps()) xs.push(rawCx(c, z));
    if (!xs.length) return;
    snapshot();
    const span = Math.max(...xs) - Math.min(...xs);
    const off = Math.round(((Number(D.meta.width_mm) - span) / 2 - Math.min(...xs)) * 1000) / 1000;
    DR.x_offset = off;
    D.design_rules.x_offset = off;
    render();
  }

  // ── Left sidebar (palette + tree) ──────────────────────────────────────────
  function sepRow(sp, i) {
    const desc = sp.type === "v" ? `▏ divider · x=${fmtVal(sp.x)}` : `— divider · y=${fmtVal(sp.y)}${sp.label ? ` · “${sp.label}”` : ""}`;
    return `<div class="tree-comp${UI.selSep === i ? " sel" : ""}" data-sep="${i}">${esc(desc)} <span class="ttype">${esc(sp.style)}</span></div>`;
  }
  function renderLeft() {
    let h = `<div class="panel-h">Add Component</div><div class="palette">`;
    for (const t of PALETTE_TYPES) h += `<div class="pal-item" draggable="false" data-add="${t}">${t.replace(/_/g, "&#8203;_")}</div>`;
    h += `</div><div class="field row" style="margin-bottom:12px">` +
      `<div><button id="add-div-h">+ Divider —</button></div>` +
      `<div><button id="add-zone">+ Zone (+ ▏)</button></div></div>`;
    // Group dividers by the zone whose x-span contains them; the rest go to "Other".
    const sepByZone = {}; const otherSeps = [];
    (D.separators || []).forEach((sp, i) => { const z = zoneOfSep(sp); (z ? (sepByZone[z.id] = sepByZone[z.id] || []) : otherSeps).push({ sp, i }); });
    h += `<div class="panel-h">Components</div>`;
    for (const z of D.zones || []) {
      h += `<div class="tree-zone"><div class="zname${z.id === UI.selZone ? " sel" : ""}" data-zid="${esc(z.id)}">${esc(z.id)}</div>`;
      for (const c of z.components || [])
        h += `<div class="tree-comp${c.id === UI.selId ? " sel" : ""}" data-cid="${esc(c.id)}">${esc(compLabel(c))} <span class="ttype">${esc(c.type)}</span></div>`;
      for (const { sp, i } of (sepByZone[z.id] || [])) h += sepRow(sp, i);
      h += `</div>`;
    }
    if (otherSeps.length) {
      h += `<div class="panel-h">Other dividers</div>`;
      for (const { sp, i } of otherSeps) h += sepRow(sp, i);
    }
    const left = document.getElementById("left");
    left.innerHTML = h;
    left.querySelectorAll("[data-add]").forEach((el) => el.addEventListener("click", () => addComp(el.dataset.add)));
    left.querySelectorAll(".tree-comp[data-cid]").forEach((el) => el.addEventListener("click", () => selectComp(el.dataset.cid)));
    left.querySelectorAll(".tree-comp[data-sep]").forEach((el) => el.addEventListener("click", () => selectSep(Number(el.dataset.sep))));
    left.querySelectorAll(".zname").forEach((el) => el.addEventListener("click", () => selectZone(el.dataset.zid)));
    document.getElementById("add-div-h").addEventListener("click", () => addDivider("h"));
    document.getElementById("add-zone").addEventListener("click", addZone);
  }

  // ── Right sidebar (inspector) ──────────────────────────────────────────────
  function fieldNum(label, val, onCommit, step) {
    return { label, val, onCommit, step: step || "0.01", kind: "num" };
  }
  function renderRight() {
    const right = document.getElementById("right");
    if (UI.selSep != null) { renderSepInspector(right); return; }
    if (UI.selZone) { renderZoneInspector(right); return; }
    if (!UI.selId) {
      right.innerHTML = `<div class="panel-h">Inspector</div><div class="hint">Select a component (panel or list), or a zone (zone name in the list).<br><br>Arrows = nudge · Shift+Arrow = bigger · Del = delete · Ctrl+Z/⇧Z = undo/redo · Space = pan.</div>`;
      return;
    }
    const ref = findComp(UI.selId);
    if (!ref) { right.innerHTML = `<div class="panel-h">Inspector</div>`; return; }
    const { c, z } = ref;
    const { cx, cy } = resolve(c, z);
    const fp = FPN[c.type] || "—";
    let h = `<div class="panel-h">Inspector</div>`;
    h += `<div class="field"><label>id</label><input id="i-id" type="text" value="${esc(c.id)}"></div>`;
    h += `<div class="field"><label>type</label><select id="i-type">${PALETTE_TYPES.map((t) => `<option ${t === c.type ? "selected" : ""}>${t}</option>`).join("")}</select></div>`;
    h += `<div class="field row"><div><label>cx (mm, resolved)</label><input id="i-cx" type="number" step="0.01" value="${f3(cx)}"></div>` +
         `<div><label>cy (mm)</label><input id="i-cy" type="number" step="0.01" value="${f3(cy)}"></div></div>`;
    if (c.col != null) h += `<div class="hint">column-relative (col ${c.col} in ${esc(z.id)}); editing cx/cy converts to explicit cx.</div>`;
    const isText = c.type === "text";
    if (!isText) h += `<div class="field"><label>rotate</label><button id="i-rot">${Number(c.rotate || 0)}° — cycle</button></div>`;
    h += `<div class="field"><label>${isText ? "text" : "label"}</label><input id="i-label" type="text" value="${esc(c.label || "")}"></div>`;
    h += `<div class="field"><label>font_size</label><input id="i-fs" type="number" step="0.1" value="${c.font_size != null ? c.font_size : (isText ? 2.0 : 1.8)}"></div>`;
    if (isText) {
      h += `<div class="field"><label>fill (color)</label><input id="i-fill" type="text" value="${esc(c.fill || COL.control_text)}"></div>`;
      h += `<div class="field row"><div><label>weight</label><select id="i-weight"><option value="normal" ${c.font_weight !== "bold" ? "selected" : ""}>normal</option><option value="bold" ${c.font_weight === "bold" ? "selected" : ""}>bold</option></select></div>` +
           `<div><label>anchor</label><select id="i-anchor">${["start", "middle", "end"].map((a) => `<option ${(c.text_anchor || "middle") === a ? "selected" : ""}>${a}</option>`).join("")}</select></div></div>`;
    }
    const cppKey = c.cpp_id != null ? "cpp_id" : (c.cpp_param != null ? "cpp_param" : (c.type.startsWith("jack") ? "cpp_id" : "cpp_param"));
    if (!isText) h += `<div class="field"><label>${cppKey}</label><input id="i-cpp" type="text" value="${esc(c[cppKey] || "")}"></div>`;
    const borderEligible = c.type.startsWith("jack") || c.type === "led_labeled";
    if (borderEligible) {
      h += `<div class="field"><label><input type="checkbox" id="i-border" ${c.label_border ? "checked" : ""}> label border</label></div>`;
      if (c.label_border) h += `<div class="field"><label>border width (rect_w mm)</label><input id="i-rectw" type="number" step="0.1" value="${c.rect_w != null ? c.rect_w : 7}"></div>`;
    }
    h += `<div class="field"><label>KiCad footprint</label><div class="ro">${esc(fp)}</div></div>`;
    // Align / anchor
    const anchoring = UI.anchor && UI.anchor.mode === "align";
    h += `<div class="panel-h" style="margin-top:10px">Align / place</div>`;
    h += anchoring
      ? `<div class="hint" style="color:#7fe7ff">Click a component to align ${UI.anchor.axis.toUpperCase()} to — Esc to cancel.</div>`
      : `<div class="field row"><div><button id="i-alignx">Align X to…</button></div><div><button id="i-aligny">Align Y to…</button></div></div>`;
    // Place relative to an origin (0,0 or a divider) by mm/HP offset
    const seps = (D.separators || []).map((sp, i) =>
      `<option value="sep${i}">divider ${i} (${sp.type}${sp.type === "v" ? " x=" + fmtVal(sp.x) : " y=" + fmtVal(sp.y)})</option>`).join("");
    h += `<div class="field"><label>place relative — origin</label><select id="i-orig"><option value="zero">panel 0,0</option>${seps}</select></div>`;
    h += `<div class="field row"><div><label>dx</label><input id="i-ox" type="number" step="0.01" value="0"></div>` +
         `<div><label>dy</label><input id="i-oy" type="number" step="0.01" value="0"></div>` +
         `<div><label>unit</label><select id="i-ou"><option value="mm">mm</option><option value="hp">HP</option></select></div></div>`;
    h += `<div class="field"><button id="i-place">Place at offset</button></div>`;
    // Revert / delete
    const isAdded = !(ORIG.zones || []).some((zz) => (zz.components || []).some((cc) => cc.id === c.id));
    h += `<div class="field row"><div><button id="i-revert"${isAdded ? " disabled title='no build spec (added in editor)'" : ""}>Revert to build spec</button></div>` +
         `<div><button id="i-del" class="danger">Delete</button></div></div>`;
    right.innerHTML = h;

    const commit = () => { render(); };
    const idEl = document.getElementById("i-id");
    idEl.addEventListener("change", () => {
      const nv = idEl.value.trim();
      if (nv && !(findComp(nv) && nv !== c.id)) { const old = c.id; c.id = nv; if (UI.selId === old) UI.selId = nv; commit(); }
      else { idEl.value = c.id; }
    });
    document.getElementById("i-type").addEventListener("change", (e) => { c.type = e.target.value; commit(); });
    const cxEl = document.getElementById("i-cx"), cyEl = document.getElementById("i-cy");
    const applyXY = () => moveCompTo(c.id, Number(cxEl.value), Number(cyEl.value));
    cxEl.addEventListener("change", applyXY);
    cyEl.addEventListener("change", applyXY);
    const rotEl = document.getElementById("i-rot");
    if (rotEl) rotEl.addEventListener("click", () => rotateComp(c.id));
    document.getElementById("i-label").addEventListener("change", (e) => { if (e.target.value) c.label = e.target.value; else delete c.label; commit(); });
    document.getElementById("i-fs").addEventListener("change", (e) => { c.font_size = Number(e.target.value); commit(); });
    if (isText) {
      document.getElementById("i-fill").addEventListener("change", (e) => { const v = e.target.value.trim(); if (v && v !== COL.control_text) c.fill = v; else delete c.fill; commit(); });
      document.getElementById("i-weight").addEventListener("change", (e) => { if (e.target.value === "bold") c.font_weight = "bold"; else delete c.font_weight; commit(); });
      document.getElementById("i-anchor").addEventListener("change", (e) => { if (e.target.value !== "middle") c.text_anchor = e.target.value; else delete c.text_anchor; commit(); });
    }
    const cppEl = document.getElementById("i-cpp");
    if (cppEl) cppEl.addEventListener("change", (e) => { c[cppKey] = e.target.value; commit(); });
    if (borderEligible) {
      document.getElementById("i-border").addEventListener("change", (e) => {
        snapshot(); if (e.target.checked) c.label_border = true; else { delete c.label_border; delete c.rect_w; } render();
      });
      const rw = document.getElementById("i-rectw");
      if (rw) rw.addEventListener("change", (e) => { snapshot(); const v = Number(e.target.value); if (v && v !== 7) c.rect_w = v; else delete c.rect_w; render(); });
    }
    if (!anchoring) {
      document.getElementById("i-alignx").addEventListener("click", () => armAlign("x"));
      document.getElementById("i-aligny").addEventListener("click", () => armAlign("y"));
    }
    document.getElementById("i-place").addEventListener("click", () => {
      const o = document.getElementById("i-orig").value;
      const origin = o === "zero" ? { x: 0, y: 0 } : dividerPoint(Number(o.slice(3)));
      if (!origin) return;
      placeRelative(origin, Number(document.getElementById("i-ox").value), Number(document.getElementById("i-oy").value), document.getElementById("i-ou").value);
    });
    const rev = document.getElementById("i-revert");
    if (rev && !rev.disabled) rev.addEventListener("click", () => revertComp(c.id));
    document.getElementById("i-del").addEventListener("click", () => deleteComp(c.id));
  }

  // ── Zone inspector (section move + rename) ─────────────────────────────────────
  function renderZoneInspector(right) {
    const z = (D.zones || []).find((z) => z.id === UI.selZone);
    if (!z) { right.innerHTML = `<div class="panel-h">Zone</div>`; return; }
    const nx = z.x_start != null ? round3(Number(z.x_start) + (z.cols != null ? z.cols : 0) * (z.col_pitch != null ? Number(z.col_pitch) : DR.jack_pitch)) : null;
    const xs = [];
    for (const c of z.components || []) xs.push(resolve(c, z).cx);
    const span = xs.length ? `${f2(Math.min(...xs))}–${f2(Math.max(...xs))}mm (${((Math.max(...xs) - Math.min(...xs)) / HP_MM).toFixed(2)} HP)` : "—";
    let h = `<div class="panel-h">Zone: ${esc(z.id)}</div>`;
    h += `<div class="field"><label>id</label><input id="z-id" type="text" value="${esc(z.id)}"></div>`;
    h += `<div class="field"><label>label</label><input id="z-label" type="text" value="${esc(z.label || "")}"></div>`;
    if (z.x_start != null)
      h += `<div class="field"><label>x_start (mm)</label><input id="z-xstart" type="number" step="0.01" value="${fmtVal(z.x_start)}"></div>`;
    h += `<div class="hint">components span: ${span}${nx != null ? ` · next x_start: ${f2(nx)}mm (${(nx / HP_MM).toFixed(2)} HP)` : ""}</div>`;
    h += `<div class="hint">Arrows move the whole section (Shift = 1 HP). x_start shift moves column-relative parts; explicit-cx parts shift with it.</div>`;
    h += `<div class="field row"><div><button data-zmove="-x">◀ −1mm</button></div><div><button data-zmove="+x">+1mm ▶</button></div></div>`;
    h += `<div class="field row"><div><button data-zmove="-y">▲ −1mm</button></div><div><button data-zmove="+y">+1mm ▼</button></div></div>`;
    h += `<div class="field"><button id="z-del" class="danger">Delete zone</button></div>`;
    right.innerHTML = h;
    document.getElementById("z-del").addEventListener("click", () => deleteZone(z.id));
    document.getElementById("z-id").addEventListener("change", (e) => {
      const nv = e.target.value.trim();
      if (nv && nv !== z.id && !(D.zones || []).some((q) => q.id === nv)) renameZone(z.id, "id", nv);
      else e.target.value = z.id;
    });
    document.getElementById("z-label").addEventListener("change", (e) => renameZone(z.id, "label", e.target.value));
    const xe = document.getElementById("z-xstart");
    if (xe) xe.addEventListener("change", (e) => setZoneXStart(z.id, Number(e.target.value)));
    right.querySelectorAll("[data-zmove]").forEach((b) => b.addEventListener("click", () => {
      const d = b.dataset.zmove;
      shiftZoneBy(z.id, d === "-x" ? -1 : d === "+x" ? 1 : 0, d === "-y" ? -1 : d === "+y" ? 1 : 0);
    }));
  }

  // ── Separator inspector (style, endpoints, delete) ─────────────────────────────
  function renderSepInspector(right) {
    const sp = selSepObj();
    if (!sp) { right.innerHTML = `<div class="panel-h">Separator</div>`; return; }
    const styles = ["zone_div", "main_cyan", "subdiv_gray"];
    let h = `<div class="panel-h">Separator ${UI.selSep} (${sp.type})</div>`;
    h += `<div class="hint">Drag the end handles on the panel to change length; the middle handle moves it sideways. Values below are raw (pre-x_offset).</div>`;
    h += `<div class="field"><label>style</label><select id="s-style">${styles.map((s) => `<option ${s === sp.style ? "selected" : ""}>${s}</option>`).join("")}</select></div>`;
    const numF = (key, lbl) => `<div><label>${lbl}</label><input class="s-num" data-key="${key}" type="number" step="0.01" value="${fmtVal(sp[key])}"></div>`;
    if (sp.type === "v") h += `<div class="field"><label>x (lateral)</label><input class="s-num" data-key="x" type="number" step="0.01" value="${fmtVal(sp.x)}"></div>` +
      `<div class="field row">${numF("y1", "y1 (top)")}${numF("y2", "y2 (bottom)")}</div>`;
    else h += `<div class="field"><label>y (vertical)</label><input class="s-num" data-key="y" type="number" step="0.01" value="${fmtVal(sp.y)}"></div>` +
      `<div class="field row">${numF("x1", "x1 (left)")}${numF("x2", "x2 (right)")}</div>`;
    if (sp.type === "h") {
      h += `<div class="field"><label>label (optional)</label><input id="s-label" type="text" value="${esc(sp.label || "")}"></div>`;
      if (sp.label != null) h += `<div class="field"><label>label_x</label><input class="s-num" data-key="label_x" type="number" step="0.01" value="${fmtVal(sp.label_x != null ? sp.label_x : (sp.x1 + sp.x2) / 2)}"></div>`;
    }
    h += `<div class="field"><button id="s-del" class="danger">Delete separator</button></div>`;
    right.innerHTML = h;
    document.getElementById("s-style").addEventListener("change", (e) => { snapshot(); sp.style = e.target.value; render(); });
    right.querySelectorAll(".s-num").forEach((el) => el.addEventListener("change", () => { snapshot(); sp[el.dataset.key] = round3(Number(el.value)); render(); }));
    const lbl = document.getElementById("s-label");
    if (lbl) lbl.addEventListener("change", (e) => {
      snapshot();
      if (e.target.value) { sp.label = e.target.value; if (sp.label_x == null) sp.label_x = round3((sp.x1 + sp.x2) / 2); }
      else { delete sp.label; delete sp.label_x; }
      render();
    });
    document.getElementById("s-del").addEventListener("click", () => { snapshot(); D.separators.splice(UI.selSep, 1); UI.selSep = null; render(); });
  }

  // ── DRC panel ──────────────────────────────────────────────────────────────
  function renderDRCPanel() {
    const el = document.getElementById("drc-panel");
    const items = lastDRC.items || [];
    if (!items.length) { el.innerHTML = `<div style="color:#44ff44">No DRC violations.</div>`; return; }
    const groups = {};
    items.forEach((it, i) => { (groups[it.tag] = groups[it.tag] || []).push({ it, i }); });
    const color = { "NUT KEEPOUT": "#ff6666", "NUT CLEARANCE": "#ff88aa", "PCB OVERLAP": "#ffaa44", "MH CLEARANCE": "#ffdd55", "PCB KEEPOUT": "#88aaff", "OTHER": "#cc99ff" };
    let h = "";
    for (const tag of Object.keys(groups).sort()) {
      const col = color[tag] || "#cc99ff";
      h += `<details open><summary style="color:${col}">${tag} (${groups[tag].length})</summary><ul>` +
        groups[tag].map(({ it, i }) => `<li style="color:${col}" class="drc-item" data-vi="${i}" title="Click to select the component">${esc(it.text)}</li>`).join("") + `</ul></details>`;
    }
    el.innerHTML = h;
    el.querySelectorAll(".drc-item").forEach((li) => li.addEventListener("click", () => {
      const it = items[Number(li.dataset.vi)];
      if (it && it.ids.length) jumpTo(it.ids[0]);
    }));
  }
  function jumpTo(id) {
    if (!findComp(id)) return;
    selectComp(id);                       // selects + re-renders (highlights in panel + tree)
    const g = svgEl && svgEl.querySelector(`.comp[data-cid="${cssEsc(id)}"]`);
    if (g && g.scrollIntoView) g.scrollIntoView({ behavior: "smooth", block: "center", inline: "center" });
  }

  // ══ YAML export (comment-preserving line patching) ═════════════════════════
  // Mirrors build_panel._apply_yaml_patches and extends it with insert/remove,
  // col→cx conversion, adds, deletes, meta + separator edits.
  function exportYAML() {
    let lines = PAYLOAD.yaml_text.split("\n");

    // helpers ------------------------------------------------------------------
    const indentOf = (s) => s.length - s.replace(/^\s+/, "").length;
    function findIdLine(id) {
      const re = new RegExp("^(\\s*)(?:- )?id:\\s+" + id.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "\\s*$");
      for (let i = 0; i < lines.length; i++) { const m = lines[i].match(re); if (m) return { i, indent: m[1].length }; }
      return null;
    }
    function blockEnd(idLine, idIndent) {
      for (let j = idLine + 1; j < lines.length; j++) {
        const s = lines[j].trim();
        if (!s) continue;
        if (indentOf(lines[j]) <= idIndent && s.startsWith("-")) return j;
        if (indentOf(lines[j]) < idIndent) return j;
      }
      return lines.length;
    }
    function findKey(idLine, end, key) {
      const re = new RegExp("^(\\s+)" + key + ":\\s*(.*?)(\\s*(?:#.*)?)$");
      for (let j = idLine + 1; j < end; j++) {
        const s = lines[j].trim();
        if (s.startsWith("-") && indentOf(lines[j]) <= indentOf(lines[idLine])) break;
        const m = lines[j].match(re);
        if (m) return { j, indent: m[1], comment: m[3] };
      }
      return null;
    }
    function patchKey(id, key, newVal) {
      const idl = findIdLine(id); if (!idl) return;
      const end = blockEnd(idl.i, idl.indent);
      const k = findKey(idl.i, end, key);
      if (k) lines[k.j] = `${k.indent}${key}: ${newVal}${k.comment}`;
      else insertKey(id, key, newVal);
    }
    function insertKey(id, key, newVal) {
      const idl = findIdLine(id); if (!idl) return;
      // field indent = id-field indent; match an existing sibling field's indent if present
      const end = blockEnd(idl.i, idl.indent);
      let fieldIndent = " ".repeat(idl.indent + 2);
      for (let j = idl.i + 1; j < end; j++) { const s = lines[j].trim(); if (s && !s.startsWith("-")) { fieldIndent = " ".repeat(indentOf(lines[j])); break; } }
      lines.splice(idl.i + 1, 0, `${fieldIndent}${key}: ${newVal}`);
    }
    function removeKey(id, key) {
      const idl = findIdLine(id); if (!idl) return;
      const end = blockEnd(idl.i, idl.indent);
      const k = findKey(idl.i, end, key);
      if (k) lines.splice(k.j, 1);
    }
    function renameColToCx(id, cxVal) {        // replace `col: N` line with `cx: <val>`
      const idl = findIdLine(id); if (!idl) return;
      const end = blockEnd(idl.i, idl.indent);
      const k = findKey(idl.i, end, "col");
      if (k) lines[k.j] = `${k.indent}cx: ${cxVal}`;
      else patchKey(id, "cx", cxVal);
    }

    const origById = {};
    const compOrigZone = {};                   // component id → ORIGINAL owning zone id
    for (const z of ORIG.zones || []) for (const c of z.components || []) { origById[c.id] = c; compOrigZone[c.id] = z.id; }
    const curById = {};
    const curZoneOf = {};                      // component id → current D zone (object)
    for (const z of D.zones || []) for (const c of z.components || []) { curById[c.id] = c; curZoneOf[c.id] = z; }
    // A surviving component is RELOCATED if its current zone maps to a different
    // original zone than where it started (incl. moving into a new zone).
    const relocated = new Set();
    for (const id of Object.keys(curById)) {
      if (!origById[id]) continue;
      if (compOrigZone[id] !== (curZoneOf[id]._orig_id || null)) relocated.add(id);
    }

    // 1 ── deletions (and remove the old block of each relocated component)
    for (const id of Object.keys(origById)) {
      if (!curById[id] || relocated.has(id)) {
        const idl = findIdLine(id);
        if (idl) { const end = blockEnd(idl.i, idl.indent); lines.splice(idl.i, end - idl.i); }
      }
    }
    // 2 ── field patches for surviving, NON-relocated components (relocated ones are
    //      rewritten in full at their new location below)
    for (const id of Object.keys(curById)) {
      const cur = curById[id], orig = origById[id];
      if (!orig || relocated.has(id)) continue;
      // cx
      const origCol = orig.col != null && orig.cx == null;
      if (cur.cx != null) {
        if (origCol) renameColToCx(id, fmtVal(cur.cx));
        else if (String(orig.cx) !== String(cur.cx)) patchKey(id, "cx", fmtVal(cur.cx));
      }
      // cy
      if (String(orig.cy) !== String(cur.cy) && cur.cy != null)
        patchKey(id, "cy", typeof cur.cy === "string" ? cur.cy : fmtVal(cur.cy));
      // rotate
      const oRot = Number(orig.rotate || 0), nRot = Number(cur.rotate || 0);
      if (oRot !== nRot) { if (nRot === 0) removeKey(id, "rotate"); else if (orig.rotate != null) patchKey(id, "rotate", String(nRot)); else insertKey(id, "rotate", String(nRot)); }
      // label / font_size / cpp
      if ((orig.label || "") !== (cur.label || "")) { if (cur.label) patchKey(id, "label", quoteIfNeeded(cur.label)); else removeKey(id, "label"); }
      if (String(orig.font_size) !== String(cur.font_size) && cur.font_size != null) patchKey(id, "font_size", fmtVal(cur.font_size));
      for (const k of ["cpp_id", "cpp_param"]) if (cur[k] != null && String(orig[k]) !== String(cur[k])) patchKey(id, k, quoteIfNeeded(cur[k]));
      // label_border (boolean) — emit literal true / remove when off
      if (Boolean(orig.label_border) !== Boolean(cur.label_border)) {
        if (cur.label_border) patchKey(id, "label_border", "true"); else removeKey(id, "label_border");
      }
      // rect_w (number)
      if (String(orig.rect_w) !== String(cur.rect_w)) {
        if (cur.rect_w != null) patchKey(id, "rect_w", fmtVal(cur.rect_w)); else removeKey(id, "rect_w");
      }
      // absolute auxiliary position fields (shifted by shiftAux on move) — persist so
      // the built panel matches the editor. Scalars:
      for (const k of ["label_below_y", "label_above_y", "cy_body_top", "pos_y"])
        if (String(orig[k]) !== String(cur[k])) { if (cur[k] != null) patchKey(id, k, fmtVal(cur[k])); else removeKey(id, k); }
      // Arrays (flow sequences):
      for (const k of ["pos_xs", "pos_ys"])
        if (JSON.stringify(orig[k]) !== JSON.stringify(cur[k])) { if (cur[k] != null) patchKey(id, k, flowSeq(cur[k])); else removeKey(id, k); }
      // Text-component font fields (strings):
      for (const k of ["fill", "font_weight", "text_anchor"])
        if ((orig[k] || "") !== (cur[k] || "")) { if (cur[k]) patchKey(id, k, quoteIfNeeded(cur[k])); else removeKey(id, k); }
    }
    // Zones keyed by their ORIGINAL id (z._orig_id); new zones have none.
    const origZoneById = {};
    for (const oz of ORIG.zones || []) origZoneById[oz.id] = oz;
    const liveOrigIds = new Set((D.zones || []).map((z) => z._orig_id).filter(Boolean));
    // 3a ── deleted zones: remove the whole block from the text
    for (const oz of ORIG.zones || []) if (!liveOrigIds.has(oz.id)) removeZoneBlock(oz.id);
    // 3b ── inserts into EXISTING zones: new components AND relocated ones (whose old
    //       block was removed above). Located by the zone's original id.
    for (const z of D.zones || []) {
      if (!z._orig_id) continue;                  // new zone → handled by insertZone
      for (const c of z.components || []) if (!origById[c.id] || relocated.has(c.id)) insertComponent(z._orig_id, c);
    }
    // 3c ── new zones: append the whole zone block (with its components)
    for (const z of D.zones || []) if (!z._orig_id) insertZone(z);
    // 4 ── zone x_start / label patches for existing zones (gated; located by orig id)
    for (const z of D.zones || []) {
      const o = z._orig_id ? origZoneById[z._orig_id] : null; if (!o) continue;
      if (o.x_start != null && String(o.x_start) !== String(z.x_start)) patchZoneKey(z._orig_id, "x_start", fmtVal(z.x_start));
      if ((o.label || "") !== (z.label || "")) patchZoneKey(z._orig_id, "label", quoteIfNeeded(z.label || ""));
    }
    // 5 ── zone id renames LAST (so steps 3–4 still match the original text)
    for (const z of D.zones || []) if (z._orig_id && z._orig_id !== z.id) patchZoneId(z._orig_id, z.id);
    // 6 ── meta + design_rules (only patch what changed → no-op export stays byte-identical)
    if (String(ORIG.meta.hp) !== String(D.meta.hp)) patchTop("hp", fmtVal(D.meta.hp), 2);
    if (String(ORIG.meta.width_mm) !== String(D.meta.width_mm)) patchTop("width_mm", fmtVal(D.meta.width_mm), 2);
    if (String(ORIG.meta.viewBox) !== String(D.meta.viewBox)) patchTop("viewBox", `"${D.meta.viewBox}"`, 2);
    if ((ORIG.meta.title || "") !== (D.meta.title || "")) patchTop("title", quoteIfNeeded(D.meta.title || ""), 2);
    if ((ORIG.meta.brand || "") !== (D.meta.brand || "")) patchTop("brand", quoteIfNeeded(D.meta.brand || ""), 2);
    if (String(ORIG.design_rules.x_offset) !== String(DR.x_offset)) patchTop("x_offset", fmtVal(DR.x_offset), 2);
    // mounting hole x (right edge) if changed
    syncMountingHoles();
    // 7 ── separators: patch changed lines in place (preserves comments); only
    //      fall back to wholesale regen when the list grew/shrank.
    if (JSON.stringify(ORIG.separators) !== JSON.stringify(D.separators)) patchSeparators();

    return lines.join("\n");

    // local mutators -----------------------------------------------------------
    function quoteIfNeeded(v) {
      const s = String(v);
      return /^[\w.+×\-/]+$/.test(s) && !/^\d/.test(s) ? s : `"${s.replace(/"/g, '\\"')}"`;
    }
    function flowSeq(a) {   // YAML flow sequence: numbers via fmtVal, strings quoted
      return "[" + a.map((v) => typeof v === "number" ? fmtVal(v) : quoteIfNeeded(v)).join(", ") + "]";
    }
    function patchTop(key, newVal, indent) {
      const re = new RegExp("^(\\s{" + indent + "})" + key + ":\\s*(.*?)(\\s*(?:#.*)?)$");
      for (let i = 0; i < lines.length; i++) { const m = lines[i].match(re); if (m) { lines[i] = `${m[1]}${key}: ${newVal}${m[3]}`; return; } }
    }
    function reEsc(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); }
    // Zone `- id:` lines are at indent 2 with a mandatory `- ` prefix — target them
    // specifically so we never collide with component `id:` lines (indent ≥ 6).
    function findZoneIdLine(zoneId) {
      const re = new RegExp("^(\\s{2})- id:\\s+" + reEsc(zoneId) + "\\s*$");
      for (let i = 0; i < lines.length; i++) if (re.test(lines[i])) return i;
      return -1;
    }
    function patchZoneId(oldId, newId) {
      const i = findZoneIdLine(oldId); if (i < 0) return;
      lines[i] = lines[i].replace(new RegExp("(- id:\\s+)" + reEsc(oldId) + "(\\s*)$"), `$1${newId}$2`);
    }
    function patchZoneKey(zoneId, key, newVal) {
      const zi = findZoneIdLine(zoneId); if (zi < 0) return;
      // scope: zone header region — stop at this zone's `components:`, the next zone, or a top-level key
      let end = lines.length;
      for (let j = zi + 1; j < lines.length; j++) {
        const s = lines[j].trim();
        if (/^components:\s*$/.test(s)) { end = j; break; }
        if (indentOf(lines[j]) <= 2 && s.startsWith("-")) { end = j; break; }
        if (indentOf(lines[j]) < 2 && s && !s.startsWith("#")) { end = j; break; }
      }
      const re = new RegExp("^(\\s{4})" + key + ":\\s*(.*?)(\\s*(?:#.*)?)$");
      for (let j = zi + 1; j < end; j++) { const m = lines[j].match(re); if (m) { lines[j] = `${m[1]}${key}: ${newVal}${m[3]}`; return; } }
      lines.splice(zi + 1, 0, `    ${key}: ${newVal}`);   // insert at zone-field indent
    }
    function isQuoteKey(k) { return ["label", "cpp_id", "cpp_param", "led_fill", "led_stroke", "fill"].includes(k); }
    function componentBlock(c, itemIndent) {     // → array of YAML lines for one component
      const fieldIndent = itemIndent + "  ";
      const blk = [`${itemIndent}- id: ${c.id}`];
      const order = ["type", "cx", "cy", "rotate", "label", "font_size", "fill", "font_weight",
        "text_anchor", "label_border", "rect_w", "label_below_y", "label_above_y", "cy_body_top",
        "pos_y", "pos_xs", "pos_ys", "cpp_id", "cpp_param", "led_fill", "led_stroke"];
      for (const k of order) {
        if (c[k] == null) continue;
        const v = Array.isArray(c[k]) ? flowSeq(c[k])
          : isQuoteKey(k) ? quoteIfNeeded(c[k])
          : (typeof c[k] === "number" ? fmtVal(c[k]) : c[k]);
        blk.push(`${fieldIndent}${k}: ${v}`);
      }
      return blk;
    }
    function insertComponent(zoneId, c) {
      const idl = findIdLine(zoneId); if (!idl) return;
      // find this zone's `components:` and the end of the zone block
      let compsLine = -1, zoneEnd = lines.length;
      for (let j = idl.i + 1; j < lines.length; j++) {
        const s = lines[j].trim();
        if (indentOf(lines[j]) <= idl.indent && s.startsWith("-")) { zoneEnd = j; break; }
        if (indentOf(lines[j]) <= idl.indent && s && !s.startsWith("#")) { /* next top-level key */ if (indentOf(lines[j]) < idl.indent) { zoneEnd = j; break; } }
        if (/^\s+components:\s*$/.test(lines[j])) compsLine = j;
      }
      // find insertion point = last non-blank line before zoneEnd
      let ins = zoneEnd;
      while (ins - 1 > (compsLine >= 0 ? compsLine : idl.i) && !lines[ins - 1].trim()) ins--;
      const itemIndent = compsLine >= 0 ? " ".repeat(indentOf(lines[compsLine]) + 2) : " ".repeat(idl.indent + 4);
      lines.splice(ins, 0, ...componentBlock(c, itemIndent));
    }
    function insertZone(z) {
      // append a new zone block at the end of the `zones:` list
      let zi = -1;
      for (let i = 0; i < lines.length; i++) if (/^zones:\s*$/.test(lines[i])) { zi = i; break; }
      if (zi < 0) return;
      let end = lines.length;
      for (let j = zi + 1; j < lines.length; j++) {
        const s = lines[j].trim();
        if (indentOf(lines[j]) === 0 && s && !s.startsWith("#")) { end = j; break; }
      }
      let ins = end; while (ins - 1 > zi && !lines[ins - 1].trim()) ins--;
      const blk = ["", `  - id: ${z.id}`];
      for (const k of ["label", "x_start", "col_pitch", "cols"])
        if (z[k] != null) blk.push(`    ${k}: ${k === "label" ? quoteIfNeeded(z[k]) : fmtVal(z[k])}`);
      if ((z.components || []).length) {
        blk.push(`    components:`);
        for (const c of z.components) blk.push(...componentBlock(c, "      "));
      } else {
        blk.push(`    components: []`);
      }
      lines.splice(ins, 0, ...blk);
    }
    function removeZoneBlock(zoneId) {
      const i = findZoneIdLine(zoneId); if (i < 0) return;
      let end = lines.length;
      for (let j = i + 1; j < lines.length; j++) {
        const s = lines[j].trim();
        if (indentOf(lines[j]) <= 2 && s.startsWith("-")) { end = j; break; }
        if (indentOf(lines[j]) === 0 && s && !s.startsWith("#")) { end = j; break; }
      }
      lines.splice(i, end - i);
    }
    function syncMountingHoles() {
      // patch the right-edge mounting-hole cx values to match the model
      const origMH = ORIG.mounting_holes || [], curMH = D.mounting_holes || [];
      if (JSON.stringify(origMH) === JSON.stringify(curMH)) return;
      let idx = 0;
      for (let i = 0; i < lines.length; i++) {
        const m = lines[i].match(/^(\s*- \{cx:\s*)([-\d.]+)(,\s*cy:\s*)([-\d.]+)(\s*\})\s*$/);
        if (m && curMH[idx]) { lines[i] = `${m[1]}${fmtVal(curMH[idx].cx)}${m[3]}${fmtVal(curMH[idx].cy)}${m[5]}`; idx++; }
      }
    }
    function sepBlock() {                  // {start, end, sepLineIdxs[]} for the separators: list
      let start = -1, end = lines.length;
      for (let i = 0; i < lines.length; i++) {
        if (/^separators:\s*$/.test(lines[i])) { start = i; }
        else if (start >= 0 && indentOf(lines[i]) === 0 && lines[i].trim() && !lines[i].trim().startsWith("#")) { end = i; break; }
      }
      if (start < 0) return null;
      const sepLineIdxs = [];
      for (let i = start + 1; i < end; i++) if (/^\s*-\s*\{/.test(lines[i])) sepLineIdxs.push(i);
      return { start, end, sepLineIdxs };
    }
    function patchSeparators() {
      const blk = sepBlock();
      if (!blk) return;
      const L = blk.sepLineIdxs, m = L.length;
      const D2 = D.separators || [], O = ORIG.separators || [];
      if (m !== O.length) {
        // Source line count doesn't match the baseline — rebuild wholesale (rare).
        const body = D2.map((sp) => "  - " + flowMap(sp));
        lines.splice(blk.start + 1, blk.end - (blk.start + 1), ...body, "");
        return;
      }
      // Index-aligned: patch changed lines, append new, delete trailing — never
      // touches the interspersed comment lines, so derivation notes are preserved.
      const overlap = Math.min(m, D2.length);
      for (let i = 0; i < overlap; i++) {
        if (JSON.stringify(D2[i]) === JSON.stringify(O[i])) continue;
        const indent = lines[L[i]].match(/^(\s*)-/)[1];
        lines[L[i]] = `${indent}- ${flowMap(D2[i])}`;
      }
      if (D2.length > m) {                    // appended dividers
        const indent = m ? lines[L[m - 1]].match(/^(\s*)-/)[1] : "  ";
        const insAt = m ? L[m - 1] + 1 : blk.start + 1;
        const add = [];
        for (let i = m; i < D2.length; i++) add.push(`${indent}- ${flowMap(D2[i])}`);
        lines.splice(insAt, 0, ...add);
      } else if (D2.length < m) {             // removed (delete extra source lines, bottom-up)
        for (let i = m - 1; i >= D2.length; i--) lines.splice(L[i], 1);
      }
    }
    function flowMap(o) {
      const parts = [];
      for (const k of Object.keys(o)) {
        const v = o[k];
        parts.push(`${k}: ${typeof v === "number" ? fmtVal(v) : (k === "label" ? `"${v}"` : v)}`);
      }
      return "{" + parts.join(", ") + "}";
    }
  }

  function openExport() {
    const m = document.getElementById("export-modal");
    let text;
    try { text = exportYAML(); }
    catch (e) { text = "# export error: " + e.message + "\n" + (e.stack || ""); }
    m.classList.remove("hidden");
    m.innerHTML = `<div class="box"><h2>panel-data.yaml — copy over tools/panel-data.yaml</h2>` +
      `<textarea id="yaml-out" spellcheck="false">${esc(text)}</textarea>` +
      `<div class="bar"><span class="hint" style="flex:1">Then run <code>python3 tools/build_panel.py --check</code> to validate.</span>` +
      `<button id="yaml-copy" class="primary">Copy</button><button id="yaml-dl">Download</button><button id="yaml-close">Close</button></div></div>`;
    document.getElementById("yaml-close").addEventListener("click", () => m.classList.add("hidden"));
    document.getElementById("yaml-copy").addEventListener("click", () => {
      const ta = document.getElementById("yaml-out"); ta.select();
      navigator.clipboard ? navigator.clipboard.writeText(ta.value) : document.execCommand("copy");
      const b = document.getElementById("yaml-copy"); b.textContent = "Copied!"; setTimeout(() => (b.textContent = "Copy"), 1200);
    });
    document.getElementById("yaml-dl").addEventListener("click", () => {
      const blob = new Blob([document.getElementById("yaml-out").value], { type: "text/yaml" });
      const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "panel-data.yaml"; a.click();
    });
  }

  // ── Global keyboard (installed once; survives re-render) ────────────────────
  function typingTarget() {
    const a = document.activeElement;
    if (!a) return false;
    const t = (a.tagName || "").toUpperCase();
    return t === "INPUT" || t === "TEXTAREA" || t === "SELECT" || a.isContentEditable;
  }
  function modalOpen() {
    const m = document.getElementById("export-modal");
    return m && !m.classList.contains("hidden");
  }
  function installGlobalKeys() {
    document.addEventListener("keydown", (e) => {
      // Space-hold → temporary pan (only when not typing)
      if (e.code === "Space" && !typingTarget() && !modalOpen()) {
        if (!spaceDown) { spaceDown = true; if (svgEl) svgEl.style.cursor = "grab"; }
        e.preventDefault(); return;
      }
      const meta = e.ctrlKey || e.metaKey;
      if (meta && (e.key === "z" || e.key === "Z")) { e.preventDefault(); if (e.shiftKey) redo(); else undo(); return; }
      if (meta && (e.key === "y" || e.key === "Y")) { e.preventDefault(); redo(); return; }
      if (typingTarget() || modalOpen()) return;

      if (e.key === "Escape") {
        if (UI.anchor || UI.tool === "anchor") { UI.anchor = null; UI.tool = "select"; render(); }
        else if (UI.selId || UI.selZone) deselect();
        e.preventDefault(); return;
      }
      if (e.key === "Delete" || e.key === "Backspace") {
        if (UI.selId) { deleteComp(UI.selId); e.preventDefault(); }
        else if (UI.selSep != null) { snapshot(); D.separators.splice(UI.selSep, 1); UI.selSep = null; render(); e.preventDefault(); }
        return;
      }
      const arrows = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] };
      if (arrows[e.key] && (UI.selId || UI.selZone)) {
        e.preventDefault();
        let step = UI.snap ? snapStepMm() : (UI.snapUnit === "hp" ? UI.snapVal * HP_MM : 0.25);
        if (e.shiftKey) step = UI.snap ? step * 4 : HP_MM;   // big step = 1 HP when not snapping
        const [sx, sy] = arrows[e.key];
        if (UI.selId) moveCompBy(UI.selId, sx * step, sy * step);
        else shiftZoneBy(UI.selZone, sx * step, sy * step);
      }
    });
    document.addEventListener("keyup", (e) => {
      if (e.code === "Space") { spaceDown = false; if (svgEl && !pan) svgEl.style.cursor = UI.tool === "pan" ? "grab" : (UI.tool === "anchor" ? "crosshair" : "default"); }
    });
  }

  // ── Boot ──────────────────────────────────────────────────────────────────
  installGlobalKeys();
  render();
})();
