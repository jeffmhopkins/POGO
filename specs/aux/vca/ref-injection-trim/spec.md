# aux: Ref-Injection Trim (HIGH-3 ±ref divider + Ec+ voltage injection)

**Type:** `vca` · part of the [aux circuit library](../../_LIBRARY.md)

Design status: [x] draft → [ ] reviewed → [ ] validated on prototype

## Overview

A **voltage-injection trim** for a high-impedance current-control port (the THAT2180 `Ec+`
pin, ≈6.1 mV/dB). It has two parts:

1. A shared **±ref divider** — `R_top` from ±12 V, loaded by the trim-pot bridge between the
   `+ref` and `−ref` rails — produces a small symmetric ±ref (representative ±1.2 V).
2. A per-cell **injection summer** at `Ec+` — the buffered control voltage `V_ctrl` reaches
   `Ec+` through `R_ec`, and the trim-pot wiper reaches `Ec+` through `R_inj`. The R_ec/R_inj
   ratio sets how much voltage the wiper *injects* (the trim authority), in dB at Ec+.

This is the HIGH-3 fix (change 0020/0025): a *series rheostat* into a high-Z port can only set
~0.004 dB — it is useless — whereas voltage injection across a calibrated ±ref gives ±~2 dB of
real unity-null authority. The cell is shared by the block-4 VCA Ec+ unity trim and the six
block-6 DRIVE-VCA Ec+ bias trims.

> **[NV] — THAT2180 dB conversion.** The Ec+ → dB constant (≈6.1 mV/dB) is an unmeasured device
> constant. The sims therefore check the ±ref **LEVEL** (set by the divider Rs — non-vacuous)
> and the injection **authority/ratio** (the ±range the wiper adds at Ec+, set by R_ec/R_inj),
> NOT the absolute dB. The dB figures in this spec are derived through the nominal 6.1 mV/dB for
> illustration only.

## Schematic

```
  Shared ±ref divider (symmetric; the trim-pot bridge is the lower leg):
    +12V ─[R_top]─ REF_P (+1.2V) ─┬─[ trim pots: N×10k end-to-end ]─┬─ REF_N (−1.2V) ─[R_top]─ −12V
                                  (REF_P↔REF_N bridge = R_pot/N)

  Per-cell injection at Ec+ (high-Z, ≈10 MΩ port):
    V_ctrl (buffered) ──[ R_ec 10k ]──┐
                                      ├──► Ec+ (THAT2180 pin 2)
    trim wiper (REF_P..REF_N) ─[R_inj 1M]┘
```

The trim pot does double duty: all cells' pots in parallel form the divider's lower bridge leg
(so the ±ref level depends on how many pots load it), and each pot's wiper is the per-cell
injection source.

## Transfer Function

```
±ref level (symmetric, REF_P = −REF_N = x; bridge = R_bridge between the two rails):
  node eqn at REF_P:  (12 − x)/R_top = 2x/R_bridge
  → representative R_top = 11.3k, R_bridge = 2.5k (four 10k pots ∥):
      2500·(12 − x) = 2·11300·x  → x = 1.195 V  ≈ +1.2 V

Injection authority at Ec+ (high-Z port, both sources sum by superposition):
  Ec+ ≈ V_ctrl·(R_inj/(R_ec+R_inj)) + V_wiper·(R_ec/(R_ec+R_inj))
  with R_ec = 10k, R_inj = 1M:  wiper coefficient = 10k/1.01M ≈ 0.0099
  → wiper swept ±1.195 V injects Ec+ ≈ ±11.8 mV  → ±~1.9 dB at 6.1 mV/dB  [NV]
```

Both load-bearing facts are *non-vacuous*: the ±ref level emerges from `R_top` against the
modeled pot bridge (regressing R_top to the old 45k3 collapses it to ±0.32 V), and the wiper
injection authority emerges from the `R_ec`/`R_inj` ratio (the deck reads the actual Ec+ voltage
the network delivers, converted through the nominal mV/dB — the dB is [NV], the ratio is not).

## Design Choices & Rationale

- **Injection, not a series rheostat:** a series R into the ≈10 MΩ Ec+ port drops essentially no
  voltage (the port draws ~50 nA bias) → ~0 dB authority. Injecting from a low-Z wiper through
  R_inj against the buffered V_ctrl through R_ec creates a real summing node with usable gain.
- **R_top sized for the PARALLEL pot bridge (change 0025):** the divider's lower leg is *all*
  the cells' pots end-to-end in parallel. Sizing R_top for a single pot (45k3) gave only ±0.32 V
  (~±0.5 dB) — the SPICE-math gate caught this. With N=4 pots (2.5k bridge) R_top = 11.3k gives
  the intended ±1.2 V; block-6 DRIVE uses N=2 pots (5k bridge) → R_top = 22.6k. Same ±1.2 V.
- **R_inj ≫ R_ec (1M vs 10k):** the injection is a fine trim — small authority (±~2 dB) so the
  wiper sets unity precisely without overwhelming the main control voltage. V_ctrl dominates Ec+.
- **Buffer V_ctrl before fan-out:** multiple cells share one V_ctrl; a buffer keeps the per-cell
  R_ec loads from interacting.

## Component Values (POGO-specific)

| Ref (generic) | Part | Package | Value | Notes |
|---|---|---|---|---|
| R_top (×2) | Resistor | 0603 | 11.3 kΩ (block-4) / 22.6 kΩ (block-6) | ±ref divider top; sized to the pot-bridge N |
| RV_trim | Bourns 3224W | SMD | 10 kΩ | Per-cell unity/bias trim; pot bridges REF_P↔REF_N, wiper = injection source |
| R_ec | Resistor | 0603 | 10 kΩ | Buffered V_ctrl → Ec+ summing R |
| R_inj | Resistor | 0603 | 1 MΩ | Trim wiper → Ec+ injection R (sets ±~2 dB authority) |

(Generic representative values; live refs: block-4 R233/R234 (±ref top), RV1/RV2/RV46/RV47 (pots),
R235/R236 (R_ec), R239/R240 (R_inj); block-6 DRIVE mirrors with R243–R260 + REF_P/N {1,2,3}.)

## Performance Characteristics

| Parameter | Value | Condition |
|---|---|---|
| ±ref level | ±1.195 V | R_top vs parallel pot bridge |
| Injection authority | ±~2 dB at Ec+ | R_ec/R_inj = 10k/1M; ±1.195 V wiper [NV] |
| Trim resolution | fine | R_inj = 1 MΩ keeps slope gentle |
| Port model | ≈10 MΩ ∥ 50 nA | THAT2180 Ec+ |

## Known Gotchas / Assembly Notes

- **The pot count sets R_top.** Adding/removing a cell changes the bridge resistance and must be
  matched by re-sizing R_top, or the ±ref level (and thus authority) drifts. This is the change
  0025 trap — documented in the sim.
- The ±ref must be symmetric (`R_top` equal on both rails) or the unity null lands off-zero.
- 6.1 mV/dB Ec+ is noise-sensitive: keep R_inj/R_ec close to the IC, short Ec+ trace.

## Used By

| Block | Instance | Board | Notes |
|---|---|---|---|
| block-4 | VCA Ec+ unity trim (main L/R + ALT L/R) | audio | N=4 pots → R_top 11.3 kΩ → ±1.2 V; ±~2 dB unity null |
| block-6 | DRIVE-VCA Ec+ bias trim (×6, dist1/2/3 L/R) | audio | N=2 pots/ref → R_top 22.6 kΩ → ±1.2 V; same authority |

Composed into: `aux/vca/vca-cell` (the VCA's Ec+ HIGH-3 trim).
Plugin law: `plugin/src/dsp/VcaBlock.hpp` — unity at control=1; analog Ec+ ≈ 6.1 mV/dB ([NV]).
