/* drc_cli.js — Node harness for the parity test (tools/test_parity.py).
 * Reads {comps, shapes, clr} JSON on stdin, runs the SAME PogoDRC.pcbOverlaps the web
 * editor uses, and prints [{a,b,body,pad}] JSON (body-overlap depth + pad-clearance
 * encroachment, both mm). Lets CI assert the JS twin matches panel_rules. */
const drc = require("./drc.js");
let s = "";
process.stdin.on("data", (d) => (s += d)).on("end", () => {
  const { comps, shapes, clr } = JSON.parse(s);
  const out = drc.pcbOverlaps(comps, shapes, clr).map((o) => ({
    a: o.a.id, b: o.b.id,
    body: Math.round(o.bodyPen * 100) / 100,
    pad: Math.round(o.padEnc * 100) / 100,
  }));
  process.stdout.write(JSON.stringify(out));
});
