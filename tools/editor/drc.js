/* drc.js — pure (DOM-free) PCB-overlap geometry, the JS twin of panel_rules.py.
 *
 * Single source of the editor's collision algorithm. Loaded both in the browser
 * (attached to window.PogoDRC by panel_editor.py, used by editor.js runDRC §3) and
 * under Node (module.exports) by the parity test tools/test_parity.py, which asserts
 * this reproduces panel_rules._check_pcb_overlaps on the real panel. Keep the three
 * functions byte-faithful to their Python counterparts (_rotate_rect, _rect_overlap,
 * _check_pcb_overlaps). NO DOM / window references in here.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.PogoDRC = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  // CW, matching the SVG draw transform and panel_rules._rotate_rect: (x,y)->(-y,x) at 90°.
  function rotateRect(rect, deg) {
    if (!deg) return rect.slice();
    const [x1, y1, x2, y2] = rect;
    let pts = [[x1, y1], [x2, y1], [x1, y2], [x2, y2]];
    if (deg === 90) pts = pts.map(([x, y]) => [-y, x]);
    else if (deg === 180) pts = pts.map(([x, y]) => [-x, -y]);
    else if (deg === 270) pts = pts.map(([x, y]) => [y, -x]);
    else return rect.slice();
    const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
    return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
  }

  // [dx, dy] overlap extents (positive on both axes ⇒ rectangles overlap).
  function rectOverlap(a, b) {
    return [
      Math.min(a[2], b[2]) - Math.max(a[0], b[0]),
      Math.min(a[3], b[3]) - Math.max(a[1], b[1]),
    ];
  }

  // Anchor-relative shape rects → panel-positioned rects (rotate about anchor, translate).
  function footprintRects(shapes, cx, cy, deg) {
    if (!shapes) return [];
    return shapes.map((r) => {
      const [x1, y1, x2, y2] = rotateRect(r, deg || 0);
      return [cx + x1, cy + y1, cx + x2, cy + y2];
    });
  }

  // Signed min gap (mirror panel_rules._rect_min_gap): + = edge gap, − = overlap depth.
  function rectMinGap(a, b) {
    const sx = Math.max(0, Math.max(a[0], b[0]) - Math.min(a[2], b[2]));
    const sy = Math.max(0, Math.max(a[1], b[1]) - Math.min(a[3], b[3]));
    if (sx > 0 && sy > 0) return Math.hypot(sx, sy);
    if (sx > 0 || sy > 0) return Math.max(sx, sy);
    const ox = Math.min(a[2], b[2]) - Math.max(a[0], b[0]);
    const oy = Math.min(a[3], b[3]) - Math.max(a[1], b[1]);
    return -Math.min(ox, oy);
  }

  // Twin of panel_rules._check_pcb_overlaps. comps: [{id,type,cx,cy,rot|rotate}].
  // shapesByType: { type: {body:[...], pads:[...], legs:[...]} }. clr = pad clearance (mm).
  // Returns [{a,b,bodyPen,padEnc}]: body OVERLAP and/or copper closer than clr (leg-vs-leg
  // excluded). Penetration/encroachment are positive on violation.
  function pcbOverlaps(comps, shapesByType, clr) {
    clr = (clr == null) ? 0.2 : clr;
    const fp = [];
    for (const c of comps) {
      const deg = (c.rot != null ? c.rot : c.rotate) || 0;
      const sh = shapesByType[c.type];
      if (!sh) continue;
      const body = footprintRects(sh.body, c.cx, c.cy, deg);
      const pads = footprintRects(sh.pads, c.cx, c.cy, deg);
      const legs = footprintRects(sh.legs, c.cx, c.cy, deg);
      if (body.length || pads.length || legs.length) fp.push({ c, body, pads, legs });
    }
    const out = [];
    for (let i = 0; i < fp.length; i++) {
      for (let j = i + 1; j < fp.length; j++) {
        const A = fp[i], B = fp[j];
        let bodyPen = 0;
        for (const x of A.body) for (const y of B.body) {
          const [dx, dy] = rectOverlap(x, y);
          if (dx > 0 && dy > 0) bodyPen = Math.max(bodyPen, Math.min(dx, dy));
        }
        let padEnc = 0;  // copper closer than clr; leg-vs-leg excluded
        for (const x of A.pads) for (const y of B.pads.concat(B.legs)) padEnc = Math.max(padEnc, clr - rectMinGap(x, y));
        for (const x of A.legs) for (const y of B.pads) padEnc = Math.max(padEnc, clr - rectMinGap(x, y));
        if (bodyPen > 0 || padEnc > 0) out.push({ a: A.c, b: B.c, bodyPen, padEnc });
      }
    }
    return out;
  }

  return { rotateRect, rectOverlap, rectMinGap, footprintRects, pcbOverlaps };
});
