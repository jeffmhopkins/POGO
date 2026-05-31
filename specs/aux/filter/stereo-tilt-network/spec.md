# aux: Stereo Tilt Network (± Spread Around a Base CV)

**Type:** `filter` · **primitive** · part of the [aux circuit library](../../_LIBRARY.md)

> Authored 2026-05-31 (change 0033). The reusable "stereo spread" primitive extracted from
> block-5 LP1 (`LP1_TILT`) and block-6 BP (`BP_TILT`). Splits one base cutoff/CV into a
> symmetric L/R pair — **L = base + tilt, R = base − tilt** — so a mono source opens into a
> stereo image whose width is one knob.

Design status: [x] draft → [ ] reviewed → [ ] validated on prototype

## Overview

The **stereo tilt network** takes a single base control voltage (`V_base`, the per-channel-common
cutoff/offset CV) and a single bipolar tilt voltage (`V_tilt`) and produces **two** CVs that
straddle the base symmetrically:

```
V_L = V_base + V_tilt        (left  channel cutoff/offset CV)
V_R = V_base − V_tilt        (right channel cutoff/offset CV)
```

The base is the **midpoint**; the tilt is the **half-difference**. At `V_tilt = 0` both outputs
collapse onto `V_base` (`V_L = V_R`, no spread — mono). As `|V_tilt|` grows the two channels diverge
in *opposite* directions, so the centre frequency / centre offset is preserved while the stereo
width opens. Because the downstream expo converter is 1 V/oct, a tilt of ±1 V puts the two channels
one octave apart and the spread is octave-symmetric about the base.

This is the smallest reusable POGO "stereo spread" element. It needs exactly one extra op-amp
section beyond the base path: an **inverting unity buffer** that makes `−V_tilt` for the R channel;
the L channel adds `+V_tilt` directly. The two summing nodes are otherwise identical.

## Schematic

ASCII (one tilt source, two channel summers; base path shown feeding both):

```
                                   R_base_L
   V_base ───────────────┬───────[───────]──┐
                         │                   │      R_f
                         │           (L)  ───┼────[───────]──┐
   V_tilt ──┬────────────┼────[───────]──────┘                │
            │            │     R_tilt_L      ├──(−) ──────────┤  V_L = −(V_base + V_tilt)·(R_f/R_in)
            │            │                   │  Eop_L         │   (sign restored downstream;
            │            │            (+)────┤        ────────┘    |G| = R_f/R_in = 1 → V_L = V_base+V_tilt)
            │            │             AGND
            │            │
            │            │       R_inv          ← inverting unity buffer: −V_tilt
            └──[───────]─┴─(−)──[───────]──┐    (R_inv = R_invf → G = −1)
               R_invin       │  Eop_INV    │
                         (+)──┤      ───────┴── −V_tilt
                          AGND
                                   R_base_R
   V_base ───────────────┬───────[───────]──┐
                         │                   │      R_f
                         │           (R)  ───┼────[───────]──┐
   −V_tilt ─────────────────[───────]────────┘                │
                          │   R_tilt_R       ├──(−) ──────────┤  V_R = −(V_base − V_tilt)·(R_f/R_in)
                          │                  │  Eop_R         │   → V_R = V_base − V_tilt
                   (+)────┤        ──────────┘
                    AGND
```

In block-5's finalized implementation this sum is done **passively** at the tempco-shunted, low-Z
expo base (equal series Rs sum `V_base` and `±V_tilt` with 1:1 octave weight — no L/R summing
op-amp; only the TL072 `−V_tilt` inverter survives). The active ± summer above is the canonical
generic form; the passive form is the block-5 specialization (see "Known Gotchas").

## Transfer Function

```
Define:  V_base  = common base cutoff/offset CV   (per channel identical)
         V_tilt  = bipolar spread voltage          (one knob, ±range)

Inverting unity buffer (R_invin = R_invf):   V_negtilt = −V_tilt

L channel summer (weights 1):   V_L = V_base + V_tilt
R channel summer (weights 1):   V_R = V_base − V_tilt     (uses V_negtilt)

→  midpoint  (V_L + V_R)/2 = V_base        (base preserved, spread-independent)
→  spread    (V_L − V_R)/2 = V_tilt        (half-difference = tilt)
→  at V_tilt = 0:   V_L = V_R = V_base     (mono, no spread)
```

The unity (weight-1) sum is the `inverting-summer` primitive with all input resistors equal to the
feedback resistor (`R_base = R_tilt = R_f` → each weight `R_f/R_in = 1`); the polarity is restored
downstream exactly as for any POGO summer. The **spread emerges from the summing-resistor weights**:
if `R_tilt` ≠ `R_base` the tilt weight changes and the L/R divergence per volt of tilt moves with it.

### DSP / plugin law it realizes

```
block-5 LP1 (Pogo.cpp:398-403):
  lp1TiltV = LP1_TILT × 5            // −1…+1 knob → ±5 V/oct tilt
  bandL = lp1L.process(…, lp1FreqBase + lp1TiltV, …)   // L = base + tilt
  bandR = lp1R.process(…, lp1FreqBase − lp1TiltV, …)   // R = base − tilt
  → f_L = 632 Hz × 2^(V_freq + V_tilt),  f_R = 632 Hz × 2^(V_freq − V_tilt)

block-6 BP (Pogo.cpp:466-467):
  tiltL[i] =  (bpTiltCv + groupTiltV[i])   // L gets +
  tiltR[i] = −(bpTiltCv + groupTiltV[i])   // R gets −
  groupTiltV[i] = BPi_TILT + modDest(…) × 0.22   // per-band CV attenuated ×0.22, summed onto global BP_TILT
```

Both blocks are the same ±-difference law `L = base + tilt, R = base − tilt`. The ×0.22 in block-6
is the per-band CV attenuation feeding the *tilt source* `V_tilt`; it scales what enters the network,
not the ±-split law itself, so the generic primitive carries the split and the ×0.22 lives in the
block's tilt-bus front end.

## Design Choices & Rationale

### One Inverter, Two Symmetric Summers

The only asymmetry between channels is the sign of the tilt addend. Generating a single `−V_tilt`
with one inverting unity buffer (the `inverting-summer` primitive, `R_in = R_f`) and feeding `+V_tilt`
to L / `−V_tilt` to R keeps the two channel summers byte-identical — same `R_base`, same `R_tilt`,
same `R_f` — which is what guarantees the spread is *symmetric* about the base (the midpoint stays
on `V_base` regardless of tilt). A mismatched pair would tilt the base itself.

### Equal Octave Weight (Base : Tilt = 1 : 1)

Because the downstream conversion is 1 V/oct, the tilt must enter the base summer with the **same
volts-per-octave weight** as `V_base` for "±1 V tilt = ±1 octave spread" to hold. That means
`R_tilt = R_base` (equal weights). In block-5 the passive form achieves this with
`R_TILT = R_VOCT + RV_mid` (54.9 kΩ) so the tilt series R matches the freq series R — the
`lp1_tilt_passive` block deck confirms `freq_mv == tilt_mv` (17.57 mV/V each, 1:1).

### Centre Null Trim

At `V_tilt = 0` both channels must land on *exactly* the same cutoff; any op-amp offset or resistor
mismatch in the `−V_tilt` inverter shows up as a residual L/R detune at the centre detent. POGO adds
a small null trim (block-5 `RV_LP1_TILT_NULL`, 10 kΩ) to zero the centre-detent mismatch.

## Component Values (POGO-specific)

Representative generic values (live per-block values are in each using block's netlist):

| Ref (generic) | Part | Package | Value | Notes |
|---|---|---|---|---|
| Eop_L / Eop_R | TL072CDT | SOIC-8 | — | One section per channel summer (or passive node in block-5) |
| Eop_INV | TL072CDT | SOIC-8 | — | `−V_tilt` inverting unity buffer (shared L→R) |
| R_base_L/R | Resistor | 0603 | 100 kΩ | Base CV into each channel summer (weight = R_f/R_base = 1) |
| R_tilt_L/R | Resistor | 0603 | 100 kΩ | Tilt CV into each channel summer (= R_base → 1:1 octave weight) |
| R_f | Resistor | 0603 | 100 kΩ | Feedback; sets the common scale (= R_in → unity weight) |
| R_invin = R_invf | Resistor | 0603 | 100 kΩ matched | `−V_tilt` inverter; match 1 % (0.1 % for deep centre null) |
| (null trim) | Bourns 3224W | SMD pot | 10 kΩ | Centre-detent L/R mismatch null |

block-5 passive specialization: `R_VOCT` 49.9 kΩ + `RV_1VOCT_mid` 5 kΩ (freq series),
`R_TILT` 54.9 kΩ (tilt series, = R_VOCT + RV_mid for 1:1), `R_TEMPCO` 1 kΩ shunt.

## Performance Characteristics

| Parameter | Value | Condition |
|---|---|---|
| Split law | V_L = base + tilt, V_R = base − tilt | Exact (equal weights) |
| Spread per volt | ±1 V/oct per V of tilt | 1:1 octave weight, 1 V/oct downstream |
| Base preservation | midpoint = base, tilt-independent | Symmetric ± pair |
| Mono at tilt = 0 | V_L = V_R = base | No spread |
| Centre null | trim to <1 % detune | RV null absorbs offset/mismatch |

## Known Gotchas / Assembly Notes

- **Match the `−V_tilt` inverter (R_in = R_f).** A mismatch makes `|−V_tilt| ≠ |+V_tilt|`, which
  detunes the base midpoint (the spread is no longer symmetric). 1 % typical, 0.1 % / trim for a
  deep centre null.
- **Equal octave weight is load-bearing:** `R_tilt = R_base`. If they differ, ±1 V of tilt no longer
  equals ±1 octave and the "knob is octaves" calibration breaks.
- **Passive vs active form:** when the base node is already low-Z (block-5's tempco-shunted expo
  base), the ± sum can be done passively through equal series Rs — saves the two channel op-amps;
  only the `−V_tilt` inverter remains. The generic active form is the fallback when the base node
  is not low-Z.
- The split is applied **before** the per-channel expo converter, so L and R need independent expo
  cores (one cannot share a single expo core and still produce two cutoffs) — see block-5 §2.

## Used By

| Composed cell / Block | Instance | Board | Notes |
|---|---|---|---|
| block-5 (LP1) | LP1_TILT stereo spread | audio | Passive ± sum at tempco-shunted expo base; `−V_tilt` via TL072 U13-A; `RV_LP1_TILT_NULL` centre trim |
| block-6 (BP) | BP_TILT + per-band BPi_TILT | audio | Global ± split shared across 3 bands; per-band CV ×0.22 into the tilt source; one TL072 half makes `−V_tilt` for all 3 |
| aux/modulation/inverting-summer | `−V_tilt` buffer + channel summers | — | Composes the unity inverter (R_in=R_f) and the weight-1 summers |
