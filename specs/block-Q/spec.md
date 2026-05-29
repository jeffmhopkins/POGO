# Block Q: Shared LP1/LP2 Resonance VCAs (shared-q)
Cross-block sheet — the two LM13700 Q-feedback VCAs (U9 L, U10 R) shared by LP1 (block-5)
and LP2 (block-8). Not a signal block; it owns the shared Q cells so neither filter block does.

Netlist: `specs/block-Q/shared-q.nets.yaml` → generates `kicad/pogo-shared-q.kicad_sch`.

---

## 1. Intent

LP1 and LP2 each need a resonance (Q) VCA per channel. Rather than duplicate them in both
filter blocks, the two stereo LM13700s live here:

- **U9** = L-channel Q VCA: cell A = LP1 Q (L), cell B = LP2 Q (L)
- **U10** = R-channel Q VCA: cell A = LP1 Q (R), cell B = LP2 Q (R)

Each Q-feedback OTA cell (per `aux-q-control.md`): In+ ← the filter's v1/BP node; In− and Out →
the filter's SUM_AMP virtual ground (injecting the damping current); Iabc ← V_ires via R_Iabc
(which lives in the filter block and arrives as a boundary net). The Darlington output buffers
and linearizing-diode bias pins are unused.

Cell-A nets (`LP1_*`) are owned/driven by block-5; cell-B nets (`LP2_*`) by block-8. This sheet
connects to both via boundary nets (`LP1_V1_*`, `LP1_SUMINV_*`, `LP1_QIABC_*`, and the `LP2_*`
equivalents). `components.yaml` groups U9/U10 + their decoupling under `block: block-Q`.

> Block-6's bandpass Q VCAs are **not** shared — each BP group owns its own pair (U67–U69),
> so they live in block-6, not here.

## 2–4

This sheet has no independent DSP/topology of its own beyond the `aux-q-control.md` cell it
instantiates twice; see that aux entry for the transfer function and component values, and
`specs/block-5/spec.md` / `specs/block-8/spec.md` for how each filter drives it. Component set:
see the generated BOM (`kicad/pogo-bom.csv`), rows with `Block = block-Q`.
