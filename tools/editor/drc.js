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

  // Twin of panel_rules._check_pcb_overlaps. comps: [{id,type,cx,cy,rot}].
  // shapesByType: { type: [[x1,y1,x2,y2], ...] }. Returns [{a,b,pen}] (pen = deepest
  // penetration = max over colliding feature-pairs of min(dx,dy)), in i<j order.
  function pcbOverlaps(comps, shapesByType) {
    const fp = [];
    for (const c of comps) {
      // accept either field name: the editor builds `rot`, panel-data/Python use `rotate`.
      const deg = (c.rot != null ? c.rot : c.rotate) || 0;
      const rects = footprintRects(shapesByType[c.type], c.cx, c.cy, deg);
      if (rects.length) fp.push({ c, rects });
    }
    const out = [];
    for (let i = 0; i < fp.length; i++) {
      for (let j = i + 1; j < fp.length; j++) {
        let pen = 0;
        for (const ra of fp[i].rects) {
          for (const rb of fp[j].rects) {
            const [dx, dy] = rectOverlap(ra, rb);
            if (dx > 0 && dy > 0) pen = Math.max(pen, Math.min(dx, dy));
          }
        }
        if (pen > 0) out.push({ a: fp[i].c, b: fp[j].c, pen });
      }
    }
    return out;
  }

  return { rotateRect, rectOverlap, footprintRects, pcbOverlaps };
});
