# Block 2: Envelope Follower

## Status
- Phase 1 (Audio Spec): [x] complete
- Phase 2 (Analog Model): [x] complete
- Phase 3 (Circuit Design): [x] complete

---

## Phase 1: Audio / Functional Specification

### Sonic Intent
Derives CV envelopes from the post-gain / pre-comb audio signal. Two independent envelope
followers — one per channel — each producing a 0–10 V CV that tracks the amplitude of the
audio in real time. These envelopes are the primary modulation source for the entire module:
they let the audio signal modulate itself, creating filter sweeps, distortion changes, and
formant shifts that are tightly coupled to the dynamics of the input.

At fast attack / fast release: percussive, tight CV that punches with every transient.
At slow attack / slow release: smooth, sustained CV that swells with the overall level.

### Parameters

| Name | Range | Default | Taper | Description |
|---|---|---|---|---|
| ATTACK | 0.1 ms – 200 ms | ~10 ms | Logarithmic | How fast the envelope rises to track a new amplitude peak |
| RELEASE | 5 ms – 2 s | ~200 ms | Logarithmic | How fast the envelope falls when the signal drops |

Two channels share linked ATTACK and RELEASE knobs (one pair of knobs for both L and R).
L and R envelope followers operate on their respective signals independently but track the same time constants.

### Panel Controls and Jacks

| Control / Jack | Type | Description |
|---|---|---|
| ATTACK | Pot (16mm or 9mm) | Shared attack time for L and R followers |
| RELEASE | Pot | Shared release time for L and R followers |
| ENV OUT L | Output jack | 0–10 V envelope CV from left channel |
| ENV OUT R | Output jack | 0–10 V envelope CV from right channel |
| MOD SOURCE SEL | 3-position switch | Selects which ENV feeds mod bus default: L / R / L+R sum |

### CV Modulation Targets
None — envelope follower does not receive modulation. It is a CV source.

### Signal Levels (I/O)
- Input: ±5 V audio from Block 1 (may be up to ±10.5 V in BOOST mode)
- Output: 0–10 V unipolar CV
  - 0 V when input is silence
  - 10 V when input is at full Eurorack level (±5 V peak = 5 V peak absolute → scaled to 10 V)

### Stereo Behavior
Two independent envelope follower circuits. L follows L audio, R follows R audio.
Both use the same ATTACK and RELEASE time constants (shared knobs).

### Edge Cases
- Boosted input (up to ±10.5 V): the full-wave rectifier handles this; output clips at 10 V
  via output clamping — acceptable behavior
- DC-offset input: the rectifier will produce a non-zero output; avoid DC-coupled sources
  with large offsets. Add input DC blocking if needed (see Phase 3)
- Very fast transients (attack < 0.5 ms): may cause brief overshoot in the output; acceptable

---

## Phase 2: Analog Behavior Model

### Transfer Function
The envelope follower is a nonlinear, time-variant circuit. Its behavior in stages:

**Stage 1: Full-wave precision rectifier**
```
V_rect = |V_in|
```
A precision rectifier using op-amp + diodes corrects for diode forward voltage drop,
giving accurate rectification down to millivolt-level signals.

**Stage 2: Peak detector with asymmetric RC**
```
On rising edge  (V_rect > V_peak): charge via attack RC   → τ_a = R_atk × C_hold
On falling edge (V_rect < V_peak): discharge via release RC → τ_r = R_rel × C_hold
```
The hold capacitor C_hold charges quickly (attack) and discharges slowly (release).

Time constant to pot value mapping (logarithmic taper):
- Attack:  τ_a = 0.1 ms → 200 ms (pot R_atk: 0 → ~50 kΩ, C_hold = 2 µF)
  - Pot minimum (0Ω): τ = 0 + R_diode_series × C ≈ 0.1 ms (residual diode + trace R)
  - Pot maximum (50 kΩ): τ = 50kΩ × 2µF = 100 ms; add 100 kΩ end resistor → 200 ms max
- Release: τ_r = 5 ms → 2 s (pot R_rel: ~2.5 kΩ → ~1 MΩ, C_hold = 2 µF)
  - Minimum: 2.5 kΩ × 2 µF = 5 ms
  - Maximum: 1 MΩ × 2 µF = 2 s

**Stage 3: Output scaling amplifier**
```
V_env = k × V_peak,   k chosen so that V_env = 10 V when V_peak = 5 V (full-scale Eurorack)
k = 10 V / 5 V = 2
```
Non-inverting amplifier, G = 2: `V_env = 2 × V_peak`

Output is clamped to 0–10 V (lower clamp: rail-to-rail op-amp won't go below 0; upper clamp:
10 V Zener or op-amp supply limit).

### Frequency Response
The envelope follower is not a frequency-selective circuit in the audio sense. Its bandwidth is
set by the attack/release time constants, which define how fast it tracks amplitude changes.

---

## Phase 3: Circuit Design

### Topology
Classic precision envelope follower: full-wave rectifier → peak detector → scaling amplifier.
Uses three op-amps per channel (one rectifier stage = 2 op-amp halves, one scaling amp = 1 half).
Total: 6 op-amp halves for L+R → use TL074 (quad, SOIC-14) × 1 for L, × 1 for R — or share
across two TL074s if layout permits.

#### Full-Wave Precision Rectifier (per channel)

```
         [D1]
V_in ──┬──K──A── (−) EF1A ─── V_rect_half
       │           (out)◄────[D2]────┘
       │            (+) ──── GND
       │
       └──(+) EF1B ──(out) ── V_pos_half ──[R_sum1]──┬── V_rect (full-wave)
           (−)◄──── (out)                            │
                                        [R_sum2]─────┘
                                         ↑
                                      V_rect_half
```

Simplified: use a standard Graetz-type op-amp precision rectifier (two op-amp stages).
D1, D2: 1N4148 (SOD-323 SMD).

#### Peak Detector with Asymmetric RC (per channel)

```
V_rect ──[D_atk]──┬──[D_rel_rev]──[R_rel(pot)]──┐
                  │                              │
                [R_atk(pot)]                    ─┤─ C_hold (2 µF)
                  │                              │
                  └──────────────────────────────┘
                                                 │
                                            V_peak ──► scaling amp
```

- D_atk (1N4148): allows charging during attack only
- D_rel_rev (1N4148, reversed): allows discharging during release only
- R_atk = ATTACK pot (100 Ω minimum end resistor + log-taper pot)
- R_rel = RELEASE pot (2.5 kΩ minimum end resistor + log-taper pot)
- C_hold = 2.2 µF film capacitor (polypropylene or polyester, low leakage)

#### Output Scaling Amplifier

Non-inverting: G = 2 (R_f = 10 kΩ, R_in = 10 kΩ → G = 1 + 10/10 = 2)

Output: 0–10 V. Upper clamp via 10 V Zener diode (BZX84-C10, SOT-23) across output to GND,
or use an op-amp with +12 V supply and limit R to output.

Output jack driven through 1 kΩ series resistor (standard Eurorack output protection).

#### MOD SOURCE SEL Switch

3-position miniature switch (sub-mini toggle or right-angle PCB slide switch):
- Position L: ENV OUT L jack normalizes to MOD SOURCE input
- Position R: ENV OUT R jack normalizes to MOD SOURCE input
- Position L+R: both ENV signals are summed via equal resistors (two 20 kΩ resistors into
  a summing op-amp, gain = 1) then connected to MOD SOURCE normalizing node

The normalizing is done through tip-switching of the MOD SOURCE input jack (see shared/cv-input-protection.md).

### IC / Component Selection

| Reference | Part Number | Package | Value | Qty | Notes |
|---|---|---|---|---|---|
| EF1 (L channel) | TL074CDT | SOIC-14 | — | 1 | Quad op-amp: rectifier (2 halves) + peak amp (1 half) + sum amp (1 half) |
| EF2 (R channel) | TL074CDT | SOIC-14 | — | 1 | Same as EF1 for R channel |
| D_atk L/R (×2) | 1N4148WS | SOD-323 | — | 2 | Attack charge diodes |
| D_rel L/R (×2) | 1N4148WS | SOD-323 | — | 2 | Release discharge diodes |
| D_rect L/R (×4) | 1N4148WS | SOD-323 | — | 4 | Precision rectifier diodes |
| C_hold L/R | — | 5mm pitch | 2.2 µF | 2 | Film cap (polyester or polypropylene, low leakage); through-hole |
| RV_ATK | Log-taper pot | 9mm PCB | 100 kΩ | 1 | Attack time; shared L+R |
| RV_REL | Log-taper pot | 9mm PCB | 1 MΩ | 1 | Release time; shared L+R |
| R_atk_end | — | 0603 | 100 Ω | 2 | Series end-stop on attack pot (sets minimum τ_a) |
| R_rel_end | — | 0603 | 2.4 kΩ | 2 | Series end-stop on release pot (sets minimum τ_r) |
| R_scale | — | 0603 | 10 kΩ | 4 | Gain-of-2 scaling amp feedback and input resistors |
| D_clamp | BZX84-C10 | SOT-23 | 10 V | 2 | Output 10 V clamp zener, one per channel |
| R_out L/R | — | 0603 | 1 kΩ | 2 | Output series resistor to jacks |
| C_VCC, C_VEE | — | 0603 | 100 nF | 4 | Supply decoupling (2 per IC) |
| SW_SEL | Sub-mini toggle | Panel | 3-pos | 1 | Mod source selection: L / L+R / R |

### Trim Pots

| Reference | Range | Purpose | Adjustment Procedure |
|---|---|---|---|
| RV_ENV_SCALE_L | ×0.9 – ×1.1 | Output level calibration for L | Feed ±5 V sine at 1 kHz; adjust until ENV OUT L reads 10 V peak |
| RV_ENV_SCALE_R | ×0.9 – ×1.1 | Output level calibration for R | Same as L |

Use 10 kΩ cermet trim pot (Bourns 3224W, SMD) in series with the gain-setting R_in of the scaling amplifier.

### Power Draw Estimate
- Two TL074 ICs: ~1.4 mA × 4 halves × 2 packages = ~11 mA quiescent
- +12 V: ~12 mA | −12 V: ~12 mA

### Schematic Notes (see schematic.svg)
- C_hold film caps must have low dielectric absorption — avoid ceramic caps here
- Route attack and release pot wiper signals with low trace resistance (use wider traces)
- MOD SOURCE SEL switch: label clearly on schematic and silk-screen
- Normalling signal from SW_SEL output should arrive at TIP SWITCH lug of MOD SOURCE jack

### Known Circuit Challenges
- Log-taper pots for attack/release: standard log pots have ~10% of rotation covering the
  bottom decade of the range. If feel is too "cramped" at slow times, use a linear pot with
  an RC shaping network to create pseudo-log response
- 2.2 µF film cap is physically large; consider 1 µF with adjusted R values if space is tight
- Diode leakage on C_hold at slow release settings: at room temperature 1N4148 leakage is
  negligible, but budget for it in the minimum release time. Use low-leakage diodes (1N4148
  is fine)
- Input DC blocking: if the signal chain can pass significant DC offset, add a 10 µF
  series capacitor (AC coupling) before the precision rectifier. Leave footprint unpopulated
  and bridged by default; populate if DC offset proves problematic during bring-up.
