# POGO — Analog Design Review

> **Re-performed 2026-05-30 (change 0018)** by analysis + adversarial agents against the current
> ground truth (`specs/components.yaml`, the block nets, `plugin/src`). Supersedes the
> 2026-05-27 review (which predated the change-0018 additions: ALT-BP VCA, per-band DRIVE VCAs,
> CLIP comparators, breathing-LED drivers, block-6 7-way split). Figures are typical-Icc estimates,
> not bench measurements — calibration/Phase-3R items are flagged as such.

---

## 1. Active-device census (whole module)

From `specs/components.yaml` (718 ref rows; shared parts counted once physically):

| Part | Count | Package | Typical Icc used |
|---|---|---|---|
| OPA1612 | 15 | SOIC-8 | 7.3 mA/pkg (3.6 mA/ch) |
| TL072CDT | 31 | SOIC-8 | 1.4 mA/pkg |
| TL074CDT | 12 | SOIC-14 | 2.6 mA/pkg |
| LM13700M | 18 | SOIC-16 | ~5 mA/pkg (working; Iabc-dependent) |
| THAT2180 | 10 | SIP-8 (THT) | ~4 mA/pkg |
| THAT340S14-U | 10 | SOIC-14 | ~0.5 mA/pkg (bias network) |
| CD4053B | 7 | SOIC-16 | ~0.05 mA/pkg |
| MMBT3904 | 2 | SOT-23 | ~3 mA each (+12V only) |

---

## 2. Power budget (per rail, typical)

Per-rail symmetric except the 2 LED-driver NPNs (collector from +12V only).

| Block | +12V | −12V | Dominant draw |
|---|---|---|---|
| A — Input buf | ~7 mA | ~7 mA | 1× OPA1612 |
| 1 — Pre-gain | ~15 mA | ~15 mA | 2× OPA1612 |
| 2 — Dual LFO | ~9 mA | ~3 mA | 2× TL072 + 2× MMBT3904 (LED, +12V only) |
| 3 — Mod bus | ~16 mA | ~16 mA | 6× TL074 |
| 4 — VCA | ~20 mA | ~20 mA | 4× THAT2180 (main + ALT-BP) + 3× TL072 |
| 5 — LP1 | ~37 mA | ~37 mA | 4× LM13700 + 2× OPA1612 + 2× THAT340 |
| 6 — BP + Dist | ~161 mA | ~161 mA | 9× LM13700 + 6× OPA1612 + 6× THAT340 + 6× THAT2180 (DRIVE) + dist/CLIP TL072/TL074 + 7× CD4053 |
| 7 — HP | ~33 mA | ~33 mA | 3× LM13700 + 2× OPA1612 + 1× THAT340 |
| 8 — LP2 | ~28 mA | ~28 mA | 2× LM13700 + 2× OPA1612 + 1× THAT340 |
| B — Output buf | ~3 mA | ~3 mA | 2× TL072 |
| **Total** | **~329 mA** | **~323 mA** | |

(The +12V/−12V difference of ~6 mA is the two block-2 LED-driver NPNs, which draw from +12V only.)

**Findings:**
- **Use a ≥400 mA/rail bus.** Typical draw (~329 mA) exceeds the previous "≥300 mA" recommendation;
  allow headroom for LM13700 / THAT2180 peaks and LED transients.
- **Block 6 is ~161 mA — about half the module.** The per-band DRIVE engine (6× THAT2180 + 3× TL074
  I/V) and CLIP comparators (3× TL074) add ~48 mA/rail that the 2026-05-27 budget did not have.
- Dominant uncertainty is the LM13700 figure (18 units): at 4 mA/pkg total ≈ 308 mA, at 6 mA/pkg ≈
  344 mA — either way > 300 mA.

---

## 3. Trim / calibration inventory

33 audio-board calibration trims (`Bourns 3224W`). (Control-board RV* are panel pots, not trims.)

| Block | Trims | Purpose |
|---|---|---|
| 4 VCA | RV1, RV2 (main), RV46, RV47 (ALT) | THAT2180 Ec+ unity-gain offset (500 Ω) |
| 5 LP1 | RV3/RV22 (f_ref L/R), RV4/RV23 (1V/oct L/R), RV5 (Q_max), RV6 (tilt null) | per-channel expo + shared Q |
| 6 BP×3 | RV7–RV15 (f_ref/1V-oct/Q_max ×3 groups), RV24/RV25 (R-ch expo) | per-band expo + Q |
| 6 DRIVE | RV51–RV56 | per-band DRIVE-VCA Ec+ offset (500 Ω) |
| 7 HP | RV16 (f_ref), RV17 (1V/oct), RV18 (Q_max) | mono expo + Q |
| 8 LP2 | RV19 (f_ref), RV20 (1V/oct), RV21 (Q_max) | mono expo + Q |

**Findings:**
- **RV9/RV12/RV15/RV21 (BP1/2/3 + LP2 Q_max) were unassigned** (`part: ~`, no value). Fixed in this
  change to `Bourns 3224W, 100kΩ`, matching the analogous RV5 (LP1) and RV18 (HP).
- **No CLIP-threshold trim.** The BP CLIP comparators (U94–U96) use a fixed ±4 V window. Since the
  CLIP LEDs are cosmetic indicators, an untrimmed threshold is acceptable (tolerance is visual only).
- LP1 has dual L/R f_ref+1V/oct trims (true stereo tilt) but a single shared Q_max (RV5), consistent
  with the shared Q-cell — L/R resonance onset cannot be independently matched. Acceptable by design.

---

## 4. Parts sourcing / availability

| Part | Count | Risk |
|---|---|---|
| THAT2180 (SIP-8, THT) | 10 | **Single-source (THAT Corp); no SMD variant; hand-placed THT.** Largest assembly + cost driver. |
| THAT340S14-U (SOIC-14) | 10 | Single-source (THAT Corp matched-NPN array); at least SMD. |
| CD4053B (SOIC-16) | 7 | **TI part marked EOL** — substitute CD4053BNSR/equivalent (pinout unchanged). |
| OPA1612 (SOIC-8) | 15 | TI premium audio op-amp; in production. |
| LM13700M (SOIC-16) | 18 | Long-lived, second-sourced; low risk. |
| TL072 / TL074 | 31 / 12 | Jellybean; low risk. |
| MMBT3904 (SOT-23) | 2 | Jellybean. |

**Findings:**
- **Top risks: (1) CD4053B EOL (7 units) — actionable substitution; (2) THAT2180 single-source + THT
  at 10 units** (the dominant sourcing/assembly concern post-0018 — grew from 2 with the ALT-BP cell
  and the 6 per-band DRIVE VCAs).
- All sourced parts in `components/parts/*` carry symbol + footprint + mpn + datasheet; footprints
  resolve. The MMBT3904 datasheet is a product-page URL (no cached PDF/sha256) — allowed, but less
  pinned than the ICs.

---

## 5. Noise analysis

- **Allocation is correct.** OPA1612 (1.1 nV/√Hz, 15 units) is on every noise-critical node: input
  buffers, pre-gain (incl. the 5× stage), and every filter SUM_AMP / output buffer (the high-Q
  resonant loops, where SUM_AMP noise is multiplied by resonance gain). TL072/TL074 are on the
  non-critical mod-bus, LFO, distortion, tilt-inverter, I/V, and output-buffer nodes.
- The 5× pre-gain (block-1) deliberately uses 4.7 kΩ/18 kΩ (vs 12 k/47 k) to cut OPA1612
  current-noise×R from 20.4 → 8.0 nV/√Hz RTI — a good decision on the most noise-sensitive stage.
- **No over-spec** (no OPA1612 wasted on a low-stakes node).
- One node to watch on the prototype: the block-4 VCA I/V converters (U6/U80, TL072) carry full
  post-VCA audio at unity gain; the downstream LP1 SUM_AMP is OPA1612, so TL072 noise here is not
  strongly amplified — not a defect, but the first place to look if the noise floor disappoints.

---

## 6. Open / Phase-3R items (design risks)

- **DRIVE law** (block-6): a single dB-law THAT2180 VCA per band approximates the plugin's per-mode
  gain (soft ≈ exp, hard/fold linear). Exact knob→Ec+ dB mapping + the knob≈0.20 ⇒ unity bias are
  prototype-calibration items (same status as the block-4 Ec+ trim).
- **CD4053 logic level** vs ±12 V analog rail is marginal (V_IH ≈ 0.7·VDD); a 5 V logic rail or
  level shift may be needed — prototype-verify.
- **CLIP comparator threshold** (±4 V) is fixed/untrimmed (cosmetic LED only).
- **Two-scaler mix phase**: wet is arranged to add with dry; exact wet-vs-dry phase across
  frequency/mode and the pot tapers are bring-up items.
- **Power bus**: provision ≥400 mA/rail.
