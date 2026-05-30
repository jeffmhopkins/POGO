/* drc_cli.js — Node harness for the parity test (tools/test_parity.py).
 * Reads {comps, shapes} JSON on stdin, runs the SAME PogoDRC.pcbOverlaps the web
 * editor uses, and prints [{a,b,pen}] JSON. Lets CI assert the JS twin matches
 * panel_rules._check_pcb_overlaps exactly. */
const drc = require("./drc.js");
let s = "";
process.stdin.on("data", (d) => (s += d)).on("end", () => {
  const { comps, shapes } = JSON.parse(s);
  const out = drc.pcbOverlaps(comps, shapes).map((o) => ({
    a: o.a.id, b: o.b.id, pen: Math.round(o.pen * 100) / 100,
  }));
  process.stdout.write(JSON.stringify(out));
});
