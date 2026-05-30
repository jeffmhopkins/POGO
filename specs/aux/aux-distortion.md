# aux: Bandpass Distortion Circuit (SC / HC / WF)

> ✅ **Re-verified 2026-05-30** against the locked plugin (change 0018). Corrected for: distortion
> runs **BEFORE** the bandpass SVF (per band); **per-band** mode select (BP1/2/3_DIST_MODE), not
> global; DRIVE is a **THAT2180 VCA** per band (not a passive pot); no oversampling.

Design status: [ ] draft → [ ] reviewed → [ ] validated on prototype

## Overview

Per BP group, the band signal passes through a variable **DRIVE VCA** (THAT2180, see
aux-vca-cell) into three parallel distortion sub-circuits — soft clip (SC), hard clip (HC),
and wavefold (WF) — with a CD4053 analog multiplexer selecting the active mode. The distortion
sits **before** the bandpass SVF (the plugin reorders distortion ahead of the resonator, change
0017/0018), so each band distorts its drive signal and the SVF then filters the result. All
three distortion circuits run simultaneously; the CD4053 steers the selected one. **Mode is
per-band** — each group has its own `BP{n}_DIST_MODE` 3-position switch (BP1/BP2/BP3 are
independent), and its own DRIVE knob+CV.

Chosen because:
- Parallel pre-built paths eliminate mode-switch glitches (no transient when switching)
- CD4053 (triple 2-channel CMOS analog mux) is widely available in SOIC-16 and handles
  ±5V audio signals from a ±12V supply
- Three independent distortion modes closely mirror the DSP Distortion.hpp modes
- One CD4053 per BP group (3 total) gives independent per-group mode + drive

## Schematic


ASCII fallback (one BP group, one channel shown):

```
 BAND_IN (pre-SVF drive signal: LP1 band, or ALT-VCA for BP3)
       │
 [DRIVE VCA — THAT2180]  ◄── DRIVE knob + BP{n}_DIST CV → Ec+   (variable gain)
       │  V_drive
       ├───────────────────┬───────────────────┐
       ▼                   ▼                   ▼
 ┌─────────────┐   ┌─────────────┐   ┌─────────────────┐
 │  SOFT CLIP  │   │  HARD CLIP  │   │    WAVEFOLD     │
 │  (SC path)  │   │  (HC path)  │   │    (WF path)    │
 │ tanh approx │   │ zener clamp │   │  op-amp fold    │
 │ diode chain │   │ back-to-back│   │  network        │
 └──────┬──────┘   └──────┬──────┘   └────────┬────────┘
        │                 │                   │
        ▼                 ▼                   ▼
      Y_SC              Y_HC                Y_WF
        └─────────────────┴───────────────────┘
                          │
               ┌──────────▼──────────┐
               │     CD4053 MUX      │ ◄── BP{n}_DIST_MODE switch (per band)
               │  (one per group)    │     (2 control lines, per group)
               │  SC / HC / WF       │
               └──────────┬──────────┘
                          │
                     DIST_OUT  ──────►  BANDPASS SVF (this group)  ──►  band output
                                                                        │
                                            BP3 group only: post-SVF v1 → BP3_L/R_OUT tap
```

Note the ordering: **DRIVE VCA → distortion cells → MUX → SVF**. The bandpass filters the
*already-distorted* signal (matching the plugin's DIST-before-SVF reorder). The BP3_L/R_OUT
jack taps the **post-SVF** band (band 3's v1), pre output-mix.

## Transfer Function

### DSP Reference (Distortion.hpp)

All modes take a signal normalized to ±1, then scale back to ±5V:

```
Drive parameter interpretation:
  driveParam ∈ [0, 1]
  If driveParam ≤ 0.20: linear region (0→1× effective gain, no distortion processing)
  If driveParam > 0.20: d = (driveParam − 0.20) / 0.80  → d ∈ [0, 1]

Mode 0 — SOFT (tanh):
  drive = exp(d × 4) − 1      range: 0 → 53.6×
  y = tanh(drive × x) / tanh(drive)

Mode 1 — HARD (hard clip):
  g = 1 + d × 4               range: 1× → 5×
  y = clamp(g × x, −1, +1)

Mode 2 — FOLD (wavefold):
  y = asin(sin(π/2 × (1 + d × 4) × x)) × 2/π
  Range of fold gain: 1× → 5×; Buchla-style triangle-to-sine folder
```

### Analog Approximations

**SC (Soft Clip):**
The tanh approximation is implemented with an op-amp gain stage followed by a
soft-limiting network (two or three diodes in series on each rail). The diode-string
threshold sets the soft clipping onset; the gain before the diodes controls the drive.
True tanh is not achievable passively; the diode approximation produces a similar
S-curve with slightly different harmonic profile — audibly similar, simpler to build.

```
Approximate circuit transfer:
  V_in → [R_in] → op-amp (+gain stage) → [diode soft-clip network] → V_out
  At low drive: op-amp gain is low → well below diode threshold → linear
  At high drive: output clips softly against diode forward voltage stack
```

**HC (Hard Clip):**
The plugin `hardClip` clamps to **±1.16 normalized** (`clamp((1+4d)·v, ±1.16)`), i.e. **±5.8 V**
at the ×5 audio scaling. The netlist realizes this with **two BZX84C5V1 zeners back-to-back**
(anode-to-anode), giving V_Z + V_F ≈ 5.1 V + 0.7 V ≈ **±5.8 V** — matching the plugin. (Schottky
diodes, ~±0.6 V, would clip far too early; zeners are used precisely to reach ±5.8 V.)

```
V_in → [R_in] → op-amp (+gain stage) → [BZX84C5V1 back-to-back, ±5.8V] → V_out
```

**WF (Wavefold):**
True symmetric precision folder: a passive diode clamp (±Vth = ±1.4V from 2× 1N4148W per
direction) feeds the op-amp non-inverting input, while the signal feeds (−) through R_g.
Output = 2×V_clamp − V_in → slope reversal at ±Vth. This is not gain compression; the
output slope genuinely reverses when the input exceeds threshold.

```
V_in → R_in → gain stage (Stage 1, half A) → V_fold_in

Passive clamp:
  V_fold_in → [R_clamp=10kΩ] → V_clamp
  V_clamp clamped to ±1.4V by 4× 1N4148W (2 per polarity)

Folder (Stage 2, half B):
  V_clamp  → (+) of op-amp
  V_fold_in → [R_g=10kΩ] → (−) of op-amp → [R_f=10kΩ] → V_out
  V_out = 2×V_clamp − V_fold_in
```

## Design Choices & Rationale

### Parallel Paths, MUX Output Selection

All three distortion circuits receive the same input simultaneously and process
it continuously. The CD4053 selects which output reaches the next stage. This:
- Avoids the pop/click of switching gain stages on and off
- Keeps the CD4053 in the signal path only for the selected mode, minimizing
  the on-resistance (Ron ≈ 200 Ω for CD4053) contribution to distortion
- Allows fast mode switching without muting — useful for live performance

### CD4053 Configuration

CD4053 (triple 2-channel analog MUX, SOIC-16):
- Three independent 2:1 multiplexer channels (A, B, C)
- Control pins S_A, S_B, S_C; INHIBIT pin (active low, tie to GND for always-on)
- With a 3-position switch and 2 digital control lines:
  - S_A selects SC vs HC (for channel A)
  - S_B selects fold-path enable/disable (for channel B)
  - Each BP group has its **own** CD4053 with its **own** `BP{n}_DIST_MODE` switch →
    mode is **per-band** (BP1, BP2, BP3 are independent; matches the plugin's three
    separate `BP1/BP2/BP3_DIST_MODE_PARAM`).

BP{n}_DIST_MODE switch (one per band): 3-position, 2 binary control lines:
  - Position 1 (SOFT): S_A=0, S_B=0
  - Position 2 (HARD): S_A=1, S_B=0
  - Position 3 (FOLD): S_A=0, S_B=1

### Signal Levels and CD4053 Supply

CD4053 must operate with audio signal swinging ±5V. For the CD4053 to pass ±5V
without signal-dependent Ron distortion, Vcc/Vee must bracket the signal range:
- Supply: Vcc = +12V, Vee = −12V (or Vdd = +5V, Vss = −5V with separate 5V regulators)
- Standard POGO ±12V supplies work; V_logic supply (V+ pin of CD4053) from +5V
  regulated rail or resistor divider from +12V with zener clamp
- INHIBIT pin tied to GND (active-low, so GND = not inhibited = MUX active)

### Bandwidth (no oversampling)

The plugin runs at the host sample rate with **no oversampling** (the earlier 2× scheme was
removed). Hardware operates in continuous time, so the only requirement is that each
distortion sub-circuit's bandwidth comfortably exceeds the audio band — design for >100 kHz
small-signal bandwidth so the nonlinearity's harmonics are not bandwidth-limited in the audio
range.

### BP3_L/R_OUT Tap

Because distortion now runs **before** the SVF, the BP3_L/R_OUT jacks tap the **post-SVF**
band-3 output (the v1/bandpass node, after DIST3→SVF3), pre output-mix — matching the plugin's
`bandpassL/R.prevOut[2]`. Route a buffered tap (aux-unity-buffer, G=+1) from band 3's SVF
output to the BP3_OUT jacks; the BP3_R jack normals to BP3_L when unpatched.

## Component Values (POGO-specific)

| Ref (generic) | Part | Package | Value | Notes |
|---|---|---|---|---|
| U_MUX_BP1 | CD4053BM96 | SOIC-16 | — | BP1 group mux; one per BP group |
| U_MUX_BP2 | CD4053BM96 | SOIC-16 | — | BP2 group mux |
| U_MUX_BP3 | CD4053BM96 | SOIC-16 | — | BP3 group mux |
| U_SC | TL072CDT | SOIC-8 | — | SC path gain + diode network op-amp |
| U_HC | TL072CDT | SOIC-8 | — | HC path gain stage |
| U_WF | TL072CDT | SOIC-8 | — | WF fold op-amp |
| D_HC_P, D_HC_N | BZX84C5V1 | SOT-23 | — | HC back-to-back zener clamp (±5.8V) |
| D_SC_1..4 | 1N4148W | SOD-123 | — | SC diode string (2 per rail, 4 total) |
| R_SC_in | Resistor | 0603 | 10 kΩ | SC input resistor |
| R_HC_in | Resistor | 0603 | 10 kΩ | HC input resistor |
| R_WF_in | Resistor | 0603 | 10 kΩ | WF pre-gain input R |
| R_clamp | Resistor | 0603 | 10 kΩ | WF passive clamp series R (limits diode current at threshold) |
| R_g | Resistor | 0603 | 10 kΩ | WF folder (−) input R |
| R_f | Resistor | 0603 | 10 kΩ | WF folder feedback R; R_g = R_f for G=+2 |
| D_WF_1..4 | 1N4148W | SOD-123 | — | WF clamp diodes: 4 per path (2 per polarity → Vth = ±1.4V) |
| U_DRIVE_VCA | THAT2180 (SIP-8) | — | — | Per-band DRIVE VCA (one stereo cell per group; see aux-vca-cell). 2/band → 6 total (U85–U90) |
| U_DRIVE_IV | TL074 | SOIC-14 | — | DRIVE VCA I/V converter + summer (U91–U93, one per band) |
| RV_DRIVE_OFS | Bourns 3224W | SMD | 500 Ω | DRIVE VCA Ec+ unity-gain offset trim (per channel: RV51–RV56) |
| C_VCC, C_VEE | Ceramic bypass | 0603 | 100 nF | Per CD4053 and op-amp supply pin |

### Drive Gain Mapping

DRIVE is implemented as a **THAT2180 dB-law VCA** per band (not a fixed gain stage), mirroring
the block-4 VCA cell. The DRIVE knob + `BP{n}_DIST` CV sum into the VCA's Ec+ control port; the
VCA's variable gain feeds the distortion cells.

```
DSP per-mode drive (Distortion.hpp):
  SOFT: drive = exp(d×4) − 1 → up to ≈ 53.6×
  HARD: g = 1 + d×4          → up to 5×
  FOLD: fold gain 1× → 5×

Hardware: a single shared dB-law VCA per band approximates these per-mode laws — the exact
knob→Ec+ dB mapping (and the knob≈0.20 ⇒ unity-gain bias) is a Phase-3R bring-up calibration
(same status as the block-4 Ec+ trim). The VCA replaces the earlier passive R_in/R_f drive pot.
```

## Performance Characteristics

| Parameter | Value | Condition |
|---|---|---|
| Distortion range (SC) | 0 to ~50× pre-gain | exp law; diode soft clip |
| Distortion range (HC) | 1× to 5× pre-gain | Linear gain, hard clip |
| Distortion range (WF) | 1× to 5× fold gain | Triangle-to-fold waveshaping |
| Mode-switch transient | None (parallel paths) | CD4053 glitch < 10 ns |
| CD4053 Ron | ~200 Ω | At ±12V supply |
| Signal bandwidth | >100 kHz | All paths |
| Supply current | ~8 mA | All 3 groups + MUX ICs |

## Known Gotchas / Assembly Notes

- CD4053 Ron (200 Ω) in series with the signal; this is typically insignificant
  when the next stage input impedance is ≥10 kΩ (Ron contributes <2% attenuation)
- CD4053 V_logic supply: if using 3.3V or 5V logic from a regulator, ensure the
  CMOS level on control pins meets CD4053 logic thresholds at the supply voltage used
- Distortion circuits all reference the same GND; ensure no ground loops between
  BP group sub-circuits (star ground topology at each group)
- SC diode string: 1N4148W forward voltage varies with current; actual clipping
  threshold will be drive-dependent (diode V_f increases at higher current).
  This is part of the soft-clip character and is desirable.
- HC path: BZX84C5V1 back-to-back clamp at ±5.8V (V_Z 5.1V + V_F 0.7V), matching the
  plugin's ±1.16 normalized hard-clip. The DRIVE VCA ahead of the cell sets how hard the
  signal is pushed into this fixed threshold (so drive, not the clamp, controls clip onset).
- WF path: the folder op-amp (Stage 2) is in standard G=+2 non-inverting configuration
  (V_clamp at (+), R_g/R_f divider at (−)). The passive diode clamp at (+) has no active
  elements and does not affect loop stability. No prototype stability verification required.
- BP3_L/R_OUT tap buffer: since distortion is now before the SVF, the unity buffer taps the
  **post-SVF** band-3 output (the filtered, already-distorted signal), matching the plugin's
  `prevOut[2]`; the BP3_R jack normals to BP3_L when unpatched

## Used By

| Block | Instance | Board | Notes |
|---|---|---|---|
| block-6 | DIST_BP1_L/R | Control | BP1 group SC/HC/WF + CD4053; both channels |
| block-6 | DIST_BP2_L/R | Control | BP2 group SC/HC/WF + CD4053; both channels |
| block-6 | DIST_BP3_L/R | Control | BP3 group SC/HC/WF + CD4053; BP3_OUT tap here |
