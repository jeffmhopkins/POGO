# aux: Q (Resonance) Control for OTA-C SVF

> ✅ **Re-verified 2026-05-30** (content rewritten 2026-05-29) against the locked plugin via
> block-5. LM13700 Q-cell reaches self-oscillation (Q → ∞ as Iabc_q → 0), matching the plugin's
> `Q = 0.5·4000^res`; Q_min ≈ 0.70 (Butterworth) is an accepted analog floor. Shared by LP1/LP2/HP.
> 🔧 **Change 0020 §D/M5:** R_Iabc **1M→100k** — the LM13700 amplifier-bias (Iabc) pin sits ~2·V_BE above V− (≈ −10.8V at −12V rails), NOT GND, so Iabc=(V_ires−V_pin)/R_Iabc. The old 1M-from-~0V delivered ~14× too much Iabc (Q pinned at min). The IRES_AMP must drive V_ires into the ~−10.0..−10.8V window (steep ~0.8V control band → fine/multi-turn V_bias trim); that negative-drive bias network + clamp polarity is a Phase-3R bring-up item. SPICE: specs/sim/q_cell.cir.

Design status: [x] draft → [ ] reviewed → [ ] validated on prototype

## Overview

Controls the resonance (Q factor) of the OTA-C SVF by injecting a current-controlled
feedback signal at the summing amplifier virtual ground. A dedicated LM13700 OTA cell
produces the Q-feedback current. The resonance control voltage is inverted so that
higher panel resonance knob position produces higher Q, which requires lower Iabc.

Chosen because:
- Using an OTA cell for Q feedback mirrors the integrator OTA topology — consistent
  design throughout the filter
- The LM13700 contains two OTA cells: one cell per filter stage, allowing LP1 and LP2
  to share one IC for Q control (IC_Q_AB), with HP using a second IC (IC_Q_C)
- Inverting the control relationship (higher knob = lower Iabc) is handled by a single
  op-amp half with a pull-up resistor, requiring no additional active ICs

## Schematic


ASCII fallback (one filter stage shown):

```
  RES knob / CV ──────────────► IRES_AMP (inverting driver)
                                         │
  V_bias ──[R_QBIAS]──┬──(−)─[TL072]────┤
                       │                 │
  V_res ──[R_QINV]────┘    (+)─GND      │
                                         ▼
                                    V_ires (increasing V_res → decreasing V_ires)
                                         │
                                    [R_Iabc 1MΩ]
                                         │
                                    Iabc_q (current into LM13700 Q cell)
                                         │
                              ┌──────────▼────────────┐
                              │   LM13700 (Q cell)    │
                              │   IN+ ← BP output (V1)│
                              │   IN− ← SUM_AMP (−)  │
                              │   OUT → SUM_AMP (−)   │
                              │   Iabc = Iabc_q        │
                              └───────────────────────┘
                              (Q feedback current injected at virtual ground)
```

IRES_AMP detail:

```
        R_QBIAS (100kΩ)         R_f_q (100kΩ)
 V_bias ──────────────┬──(−)──[TL072]──┬── V_ires
                      │                │
 V_res ──[R_QINV]────┘     (+)─GND    │

 V_ires = −(V_bias × R_f_q/R_QBIAS + V_res × R_f_q/R_QINV)

 With R_QBIAS = R_QINV = R_f_q:
   V_ires = −(V_bias + V_res)

 As V_res increases from 0 → 5V:
   V_ires decreases → V_ires / R_Iabc decreases → Iabc_q decreases → Q increases ✓
```

## Transfer Function

### Q Formula

The OTA-C SVF resonance is set by:

```
Q = V_T / (Iabc_q × R_in)

With V_T = 52mV (2 × 26mV, both sides of differential pair) and R_in = 100 kΩ:

Q = 52mV / (Iabc_q × 100kΩ)
Q = 0.52 / (Iabc_q in µA)
```

Key Q operating points:

```
Iabc_q = 0.74 µA → Q = 0.52 / 0.74 = 0.70  (Butterworth / flat response, minimum resonance)
Iabc_q = 0.52 µA → Q = 1.00  (Chebyshev onset)
Iabc_q = 0.26 µA → Q = 2.00
Iabc_q = 0.10 µA → Q = 5.20
Iabc_q → 0       → Q → ∞    (self-oscillation)
```

### DSP Q Mapping (reference)

```
LP1, LP2, HP:
  Q = 0.5 × 4000^resParam
  resParam ∈ [0, 1]
  Q range: 0.5 (flat) → 2000 (near self-osc)
  Top ~5% of resParam range is self-oscillation territory

BP groups:
  Q = 0.5 × 400^qParam
  qParam ∈ [0, 1]
  Q range: 0.5 → 200
  Output normalized by 1/Q so peak amplitude ≈ 1/Q (constant loudness behavior)
```

**Q_min deviation (accepted):** DSP Q_min = 0.5 at resParam/qParam = 0. Hardware Q_min = 0.70
(Butterworth) because Iabc_q cannot go below ~0.74 µA without entering LM13700 low-current
nonlinearity territory. Practical effect: hardware has no slightly-overdamped region (0.5 < Q < 0.707);
the CCW-stop resonance position already yields maximally flat (Butterworth) response. This is the
conventional analog filter design target and is audibly negligible.

### IRES_AMP Mapping

```
V_ires = −(V_bias + V_res)  where V_res ∈ [0, 5V] for full CW resonance
Iabc_q = |V_ires| / R_Iabc = (V_bias + V_res) / R_Iabc

Wait — requires V_ires to DECREASE as V_res increases (to increase Q).
Correct implementation: V_bias is positive, V_res is positive, and:

  V_ires = V_bias − (R_f_q / R_QINV) × V_res

So as V_res increases, V_ires decreases.
When V_ires reaches near-zero, Iabc_q → 0 → self-oscillation.
RV_QMAX sets V_bias to calibrate the onset of self-oscillation at full CW.
```

### Iabc Range

```
At minimum resonance (V_res = 0):
  Iabc_q = 0.74 µA → Q = 0.70 (Butterworth)
  V_ires = V_bias = Iabc_q × R_Iabc = 0.74µA × 1MΩ = 0.74V
  → V_bias calibration target = 0.74V (set by RV_QMAX)

At maximum resonance (before self-osc, V_res = 4.5V):
  Iabc_q ≈ 0.04 µA → Q ≈ 13
  V_ires ≈ 0.04V

At self-osc (V_res ≥ 4.75V):
  Iabc_q < 0.01 µA → Q > 50 → sustained oscillation
```

## Design Choices & Rationale

### Inverting Iabc Driver

Higher resonance knob position must produce lower Iabc (higher Q). Rather than using
a log-taper pot with complex end resistor networks, a simple inverting summing amplifier
maps the control voltage to a decreasing output. This is straightforward to trim via
RV_QMAX and is highly linear in the intermediate range.

### Q OTA Cell Placement

The Q feedback OTA injects a current proportional to V1 (BP output) back into the
SUM_AMP virtual ground. This is equivalent to the DSP term `k × v1` in the HP output
summing expression. The feedback current subtracts from the error signal at the summing
node, adding a resonant peak at ω₀.

### LM13700 Cell Sharing

Each LM13700 SOIC-16 contains two independent OTA cells. For Q control:
- IC_Q_AB: cell A = LP1 Q, cell B = LP2 Q (one IC handles both LP stages)
- IC_Q_C: cell A = HP Q L, cell B = HP Q R (mono Q; change 0018 — was cell B spare)
- BP groups: each group needs a Q cell per channel (6 Q cells for 3 groups × 2 channels)
  → 3 LM13700 ICs for BP Q control (one per group, both channels share an IC)

### RV_QMAX Trim

Bourns 3224W 100 kΩ SMD trimpot. Adjusts V_bias to set:
- Q = 0.70 at V_res = 0 (minimum resonance = Butterworth)
- Onset of self-oscillation at maximum knob CW position (~95–100% of travel)

## Component Values (POGO-specific)

| Ref (generic) | Part | Package | Value | Notes |
|---|---|---|---|---|
| U_Q_AB | LM13700M | SOIC-16 | — | Cell A = LP1 Q-cell; Cell B = LP2 Q-cell |
| U_Q_C | LM13700M | SOIC-16 | — | Cell A = HP Q L; Cell B = HP Q R (both active, mono Q) |
| U_Q_BP1..3 | LM13700M | SOIC-16 | — | One per BP group; cell A = L channel, cell B = R channel |
| U_IRES | TL072CDT | SOIC-8 | — | Half A = IRES_AMP per filter; can share TL072 with SUM_AMP |
| R_Iabc | Resistor | 0603 | 1 MΩ | V_ires → Iabc conversion; 0.74V / 1MΩ = 0.74 µA at flat Q |
| R_QBIAS | Resistor | 0603 | 100 kΩ | Sets V_bias contribution to IRES_AMP |
| R_QINV | Resistor | 0603 | 100 kΩ | Sets V_res scaling at IRES_AMP |
| R_f_q | Resistor | 0603 | 100 kΩ | IRES_AMP feedback resistor |
| RV_QMAX | Bourns 3224W | SMD | 100 kΩ | V_bias trim; sets Butterworth Q point and self-osc onset |
| C_VCC, C_VEE | Ceramic bypass | 0603 | 100 nF | Per LM13700 supply pin |

## Performance Characteristics

| Parameter | Value | Condition |
|---|---|---|
| Q range (LP/HP) | 0.70 – ∞ (self-osc) | resParam 0 → 1 |
| Q range (BP) | 0.70 – ~200 | qParam 0 → 1 |
| Q at flat response | 0.70 | Iabc_q = 0.74 µA (trimmed) |
| Self-osc onset | ~95% CW | After RV_QMAX calibration |
| Q control law | Hyperbolic (1/Iabc) | Approximately exponential at high Q |
| Iabc_q range | 0.01 µA – 0.74 µA | Full resonance sweep |

## Known Gotchas / Assembly Notes

- R_Iabc (1 MΩ) at high impedance — keep trace short, away from audio signal paths
- At near self-oscillation, any coupling from audio into the Iabc_q node will create
  audible pitch modulation of the self-oscillation frequency; shield trace if needed
- IRES_AMP output must be clamped to prevent negative V_ires from reverse-biasing the
  Q cell Iabc pin; add a BAT54 diode from V_ires to GND (anode at GND, cathode at V_ires)
  to clamp V_ires ≥ 0
- Self-oscillation amplitude is limited by OTA output voltage swing (±(Vcc−2V) ≈ ±10V);
  the oscillation will be at f₀ determined by the expo converter setting
- For BP blocks: per-group Q is set by a per-group pot (FOCUS_N) plus the global
  BP resonance CV; the Q OTA cell Iabc must sum both contributions
- BP Q normalization (1/Q² gain compensation from DSP) is not yet specified for hardware;
  mark as Phase 3R open item
- Linearity of IRES_AMP is critical at very low V_ires; use a rail-to-rail input/output
  op-amp (or ensure TL072 operates well above its common-mode minimum at +12V supply)

## Used By

| Block | Instance | Board | Notes |
|---|---|---|---|
| block-5 | IC_Q_AB | audio | LP1 Q (cell A=L, cell B=R Iabc, shared U9/U10) |
| block-8 | IC_Q_AB | audio | LP2 Q (shared U9/U10 with block-5) |
| block-7 | IC_Q_C (U51) | audio | HP Q (cell A=L, cell B=R; one IC) |
| block-6 | BP1_Q (per channel) | Control | BP1 Q cell; one LM13700 for L+R |
| block-6 | BP2_Q (per channel) | Control | BP2 Q cell; one LM13700 for L+R |
| block-6 | BP3_Q (per channel) | Control | BP3 Q cell; one LM13700 for L+R |
