# aux: Attenuverter (Bipolar Modulation Scaling)

Design status: [ ] draft → [ ] reviewed → [ ] validated on prototype

## Overview

Bipolar attenuator that scales an input signal from −1× (full CCW) through 0 (center)
to +1× (full CW). Used at all 22 modulation destinations. An inverting unity-gain op-amp
half generates the negative voltage rail needed by the pot wiper sweep. A tip-switching
override jack replaces the mod bus input when patched, allowing per-destination CV
injection directly at any mod point.

Chosen because:
- Single pot + one op-amp inverter is the minimal bipolar attenuator topology
- Center-zero behavior (cutting all modulation at 12 o'clock) is expected by users
- Override jack with tip-switching is standard Eurorack practice; when unpatched
  the normalled signal (mod bus) flows; when patched the incoming CV takes over
- TL074CDT (quad op-amp SOIC-14) allows 4 attenuverter inverters per IC, making the
  22-destination count feasible with 6 TL074 ICs (shared among destinations)

## Schematic


ASCII fallback (one destination shown):

```
Inverter (one TL074 half):

               R_inv_in (10kΩ)        R_inv_f (10kΩ)
 V_att ──────────[────────]──┬──(−)──[────────]──┬── −V_att
                             │                    │ (feedback)
                        (+)──┴─ AGND              │

Pot wiper:

 −V_att ──────────── [POT CW end] ─────────────────────────────┐
                           │                                    │
                     [wiper] ──────────────────────────────► V_mod_out
                           │
  +V_att ──────────── [POT CCW end] ─────────────────────────────┘

  (Note: CW end → V_att source, CCW end → −V_att; CW = +1×, CCW = −1×, center = 0)

Override jack (tip-switching, normally closed to mod bus):

 MOD_BUS ──[100Ω]──[BAT54S]──┬──────────────────────────────────┐
                              │  (override jack, tip-switching)   │
 OVERRIDE_CV ──[100Ω]──[BAT54S]──► (tip contact, open = NC)     │
                              │                                   │
                        when unpatched: mod bus → pot input        │
                        when patched: override CV → pot input      │
                                                           [POT] ──► V_mod_out
```

## Transfer Function

```
V_mod_out = θ × V_att

where θ ∈ [−1, +1] is the pot rotation (−1 = CCW, 0 = center, +1 = CW)

V_att = the mod bus (or override CV) signal, after input protection

Pot wiper sweeps between −V_att and +V_att:
  Full CW (θ = +1): V_mod_out = +V_att (in-phase, full scale)
  Center (θ = 0):   V_mod_out = 0 (mod cut)
  Full CCW (θ = −1): V_mod_out = −V_att (inverted, full scale)
```

The attenuverter output V_mod_out feeds the modulation summer at the CV destination
(e.g., the expo converter input summing node for a frequency destination, or the
IRES_AMP input for a Q destination).

## Design Choices & Rationale

### Pot Wiper Between +V and −V

A standard single-ended pot (R to wiper to GND) only attenuates. To achieve bipolar
operation, the pot must sweep between a positive and a negative voltage. Generating
−V_att from +V_att with an inverting unity-gain op-amp (G=−1) uses one TL074 half —
cheap and reliable. The pot end resistors (if needed) set the minimum/maximum output
to slightly less than ±1× to prevent the wiper riding on the rail.

### Center Detent

Panel pots should have a physical center detent at 12 o'clock for the 0-modulation
position. This is a mechanical/sourcing requirement, not a circuit requirement. Center
position corresponds to the wiper being exactly at the pot midpoint (equal resistance
to each end), producing V_mod_out = 0 only if −V_att and +V_att are equal and opposite.
This requires the inverter gain to be exactly −1, which depends on R_inv_in = R_inv_f.
Use 1% resistors for this pair.

### TL074 for Inverters

22 mod destinations × 1 inverter each = 22 op-amp halves needed.
TL074CDT (quad op-amp, SOIC-14) provides 4 halves per IC.
22 / 4 = 5.5 → 6 TL074 ICs, providing 2 spare halves for utility functions.

These inverter op-amps can be grouped on a dedicated "modulation distribution" portion
of the control board rather than distributed among individual block sub-circuits.

### Override Jack (Tip-Switching Normalling)

The override jack uses a tip-switching (normally closed) mechanical switch:
- When no patch cable is inserted: the tip-switch contact is closed; the circuit
  sees the mod bus through the NC contact (normalized connection)
- When a patch cable is inserted: the tip-switch opens the NC contact; the circuit
  sees the patched CV instead

This is standard Eurorack normalling. The jack body is the ring terminal (GND for
unbalanced mono cables); the tip is the signal.

### Input Protection at Each Attenuverter Input

Both the mod bus path and the override jack path have:
- 100 Ω series resistor: limits short-circuit current
- BAT54S Schottky clamp: clamps to ±(Vcc + 0.3V) ≈ ±12.3V

This protects the TL074 inverter input from overvoltage. Two BAT54S devices are used
per destination (one per input path), for 22 × 2 = 44 BAT54S total in the mod bus
section. These are 0603-compatible in SOT-23; manageable board area.

## Component Values (POGO-specific)

| Ref (generic) | Part | Package | Value | Notes |
|---|---|---|---|---|
| U_ATT_1..6 | TL074CDT | SOIC-14 | — | Quad op-amp; 4 inverters per IC; 6 ICs for 22 dest |
| R_inv_in | Resistor | 0603 | 10 kΩ | Inverter input resistor; 1% tolerance |
| R_inv_f | Resistor | 0603 | 10 kΩ | Inverter feedback resistor; 1% tolerance; must match R_inv_in |
| RV_ATT | Pot | 9mm T18 | 100 kΩ | Panel attenuverter pot; linear taper with center detent |
| R_cv_mb | Resistor | 0603 | 100 Ω | Mod bus path series protection |
| R_cv_ov | Resistor | 0603 | 100 Ω | Override jack path series protection |
| D_mb | BAT54S | SOT-23 | — | Mod bus input clamp |
| D_ov | BAT54S | SOT-23 | — | Override jack input clamp |
| J_ov | Tip-switching mono jack | PJ301M-12 | — | 3.5mm Eurorack panel jack with NC tip switch |
| C_VCC, C_VEE | Ceramic bypass | 0603 | 100 nF | Per TL074 supply pin |

### Destination Count

| Category | Destinations | Override Jacks |
|---|---|---|
| Frequency (LP1, LP2, HP, BP1, BP2, BP3) | 6 | 6 |
| Q/Resonance (LP1, LP2, HP, BP groups) | 5 | 5 |
| BP offset, mix, tilt, pol | 4 | 4 |
| VCA (amt, ofs, gain) | 3 | 3 |
| Pre-gain, general | 4 | 4 |
| **Total** | **22** | **22** |

## Performance Characteristics

| Parameter | Value | Condition |
|---|---|---|
| Gain range | −1× to +1× | Full pot sweep |
| Center null depth | >60 dB | With 1% matched R_inv_in, R_inv_f |
| Input range | ±10V (mod bus) | Clamped from ±12V rail |
| Output range | ±10V | Depends on V_att level |
| Inverter bandwidth | >1 MHz | TL074 at G=−1 |
| Pot noise | <1 µV/Hz | Typical panel pot |

## Known Gotchas / Assembly Notes

- R_inv_in and R_inv_f must be matched (1%) for G = −1 accuracy; a 1% mismatch
  causes +/−1% gain error, meaning center null is only ~40 dB — use 0.1% or
  trim if deep null at center is critical
- The tip-switching jack normalling contact can add a small resistance (~50–200 Ω)
  in series with the mod bus path; this is negligible given source impedance of the
  mod bus processor output (~50 Ω from op-amp)
- All 22 attenuverter pots are linear taper (not audio/log); the human perception of
  modulation depth is roughly linear in most synthesis contexts
- TL074 common-mode input range: same caveat as TL072 — inputs must remain above
  the negative supply minus ~1V; all mod bus signals are within ±10V on ±12V supply
- Ground layout: BAT54S anode must connect to AGND, not DGND; use the star analog
  ground from the power header
- Override jack tip-switch mechanical life: PJ301M-12 is rated for 10,000 insertions —
  adequate for a patch module but note for longevity

## Used By

| Block | Instance | Board | Notes |
|---|---|---|---|
| block-3 | ATT_1 .. ATT_22 | Control | All 22 modulation destinations |
| block-5 | ATT_LP1_FREQ, ATT_LP1_RES | Control | LP1 frequency and resonance destinations |
| block-7 | ATT_HP_FREQ, ATT_HP_RES | Control | HP frequency and resonance destinations |
| block-8 | ATT_LP2_FREQ, ATT_LP2_RES | Control | LP2 frequency and resonance destinations |
| block-6 | ATT_BP_OFFSET, ATT_BP_TILT, ATT_BP1..3_FREQ, ATT_BP1..3_Q | Control | BP group destinations |
| block-4 | ATT_VCA_AMT, ATT_VCA_OFS, ATT_VCA_IN | Control | VCA destinations |
