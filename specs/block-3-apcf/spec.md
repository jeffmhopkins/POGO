# Block 3: Triple 6-Stage All-Pass Comb Filter (APCF)

## Status
- Phase 1 (Audio Spec): [x] complete
- Phase 2 (Analog Model): [x] complete
- Phase 3 (Circuit Design): [x] complete

---

## Phase 1: Audio / Functional Specification

### Sonic Intent
Three independent groups of 6 first-order all-pass stages cascaded in series per stereo channel
— 18 all-pass stages total per channel. Mixed with the dry signal, they create the classic phaser
comb: a sweep of notches and peaks across the frequency spectrum. With three independent groups
tuned to different frequency ranges, the comb pattern spreads across the full audio band, producing
rich, formant-like resonances — like a vowel filter that breathes with modulation.

Each group covers a different zone:
- **Group 1**: Low formant (~100 Hz – 1 kHz)
- **Group 2**: Mid formant (~500 Hz – 5 kHz)
- **Group 3**: High formant (~2 kHz – 20 kHz)

With feedback, each group develops a distinct resonant peak at its center frequency. Sweeping
SPREAD opens or closes the distance between the three formants. Sweeping MASTER OFFSET moves all
three together like a filter sweep. STEREO WIDTH drifts the R channel's formants relative to L,
creating a shifting, spacious stereo field.

At minimum COMB BYPASS (pre-comb VCA fully closed): comb effect is off, signal passes through
via dry path only.
At maximum COMB BYPASS (pre-comb VCA fully open): all 18 stages always in circuit; maximum
notch depth.
At mid COMB BYPASS: classic phaser blend — notches audible but signal retains body.

### Parameters

| Name | Range | Default | Taper | Description |
|---|---|---|---|---|
| FREQ 1 | 20 Hz – 2 kHz center | 200 Hz | Logarithmic | Center frequency of Group 1 (low formant) |
| FREQ 2 | 200 Hz – 8 kHz center | 1.5 kHz | Logarithmic | Center frequency of Group 2 (mid formant) |
| FREQ 3 | 1 kHz – 20 kHz center | 6 kHz | Logarithmic | Center frequency of Group 3 (high formant) |
| SPREAD | 0 – 100% | 50% | Linear | Multiplies spacing between groups; 0% collapses all groups to same frequency |
| MASTER OFFSET | ±5 V equivalent | 0 | Linear | Shifts all 3 groups up or down together; acts as a master sweep (panel: MASTER OFFSET large knob) |
| FB 1 | 0 – 95% | 0% | Linear | Resonance depth of Group 1; >95% risks instability |
| FB 2 | 0 – 95% | 0% | Linear | Resonance depth of Group 2 |
| FB 3 | 0 – 95% | 0% | Linear | Resonance depth of Group 3 |
| FB DIST BLEND | 0 – 100% | 0% | Linear | Continuous crossfade: 0% = clean APF feedback (internal), 100% = post-distortion feedback |
| POLARITY | Switch: Positive / Off / Negative | Positive | N/A | Positive: standard notch deepening; Off: cuts all feedback regardless of FB knobs; Negative: phase-inverts feedback, turning notches into peaks |
| STEREO WIDTH | 0 – 100% | 0% | Linear | Frequency offset of R channel groups relative to L; 0% = mono, 100% = maximum stereo spread |
| COMB BYPASS | 0 – 100% | 50% | Linear | Pre-comb VCA level: 0% = signal bypasses comb (dry only), 100% = full comb in signal path |

### CV Modulation Targets

| Target | CV Range | Attenuverter | Notes |
|---|---|---|---|
| FREQ 1 | ±5 V (1V/oct) | Yes | Sweeps Group 1 center frequency exponentially |
| FREQ 2 | ±5 V (1V/oct) | Yes | Sweeps Group 2 center frequency exponentially |
| FREQ 3 | ±5 V (1V/oct) | Yes | Sweeps Group 3 center frequency exponentially |
| FB 1 | 0–10 V | Yes | Group 1 feedback depth independently |
| FB 2 | 0–10 V | Yes | Group 2 feedback depth independently |
| FB 3 | 0–10 V | Yes | Group 3 feedback depth independently |
| FB DIST BLEND | 0–10 V | Yes | Crossfade ratio; always active |
| COMB BYPASS | 0–10 V | Yes | Pre-comb VCA level; sweeps from bypassed to full comb |
| MASTER OFFSET | ±5 V (1V/oct) | Yes | Shifts all 3 group frequencies simultaneously; sums at each FREQ CV node |
| POLARITY | — | None | Switch only; no CV |

### Signal Levels (I/O)
- Input: ±5 V audio (from Block 2; up to ±10.5 V if Block 1 is in BOOST mode)
- Output: ±5 V audio (all-pass stages are unity gain by definition; no signal level change)
- With feedback: resonance can increase apparent level at the formant frequencies by several dB;
  keep output stage headroom at ±10 V

### Stereo Behavior
True stereo: independent signal paths for L and R through all 18 stages per channel.
FREQ 1/2/3 knobs and SPREAD control both channels identically.
STEREO WIDTH offsets R channel group frequencies: `ω_R = ω_L × 2^(WIDTH_V / 1V)` where WIDTH_V
is a small positive or negative voltage derived from the WIDTH knob.
COMB BYPASS applies identically to both channels.

### Edge Cases
- FB at maximum (95%): near-self-oscillation; output level rises sharply. The 95% hard
  limit in the circuit must be enforced by a resistor floor in the feedback path — do not allow
  full 100% positive feedback.
- COMB BYPASS at 0%: pre-comb VCA closed; signal bypasses phase-shift influence. When fully
  bypassed, no op-amp noise from the wet path reaches the output.
- SPREAD at 0%: all three groups are set to the same frequency; the three sets of notches align,
  producing a deeper but narrower comb effect at one frequency region.
- FB DIST BLEND at 0%: uses only the clean APF output as the feedback source (equivalent to
  the former "Internal" SOURCE setting). At 100%: post-distortion signal drives all feedback
  (equivalent to former "Post-Dist" setting). Intermediate values continuously interpolate.

---

## Phase 2: Analog Behavior Model

### Transfer Function

**Single 1st-order all-pass stage:**
```
H_APF(s) = (s − ω₀) / (s + ω₀)
```
- Magnitude: |H_APF(jω)| = 1 for all ω (unity gain — all-pass)
- Phase: φ(ω) = π − 2 arctan(ω / ω₀)
  - At ω → 0:   φ = π   (180° phase shift)
  - At ω = ω₀:  φ = π/2 (90° phase shift)
  - At ω → ∞:   φ = 0   (0° phase shift)

**Six cascaded APF stages (one group), same center frequency ω₀:**
```
H_6(s) = [(s − ω₀) / (s + ω₀)]^6
```
- Magnitude: still unity for all ω
- Phase: φ_6(ω) = 6 × [π − 2 arctan(ω / ω₀)]

**Notch locations in the phaser output:**
When H_6 is mixed with the dry signal (V_dry + V_wet), cancellation occurs where phase shift = (2n+1)π:
```
6 × [π − 2 arctan(ω_notch / ω₀)] = (2n+1)π
arctan(ω_notch / ω₀) = (5 − 2n)π / 12
ω_notch_n = ω₀ × tan((5 − 2n)π / 12)
```
For 6 stages (at equal COMB BYPASS), this produces 3 notch pairs across the spectrum.

**Three groups, each with independent ω₀:**
```
Group 1: ω₀_1 = 2π × f₁,   f₁ controlled by FREQ 1 + MASTER OFFSET + modulation
Group 2: ω₀_2 = 2π × f₂,   f₂ controlled by FREQ 2 + MASTER OFFSET + modulation
Group 3: ω₀_3 = 2π × f₃,   f₃ controlled by FREQ 3 + MASTER OFFSET + modulation
```

SPREAD scales the distances:
```
f₁_eff = f₁_base × 2^(−SPREAD × k)
f₂_eff = f₂_base   (reference, unaffected)
f₃_eff = f₃_base × 2^(+SPREAD × k)
```
where k is a scaling factor set so that at SPREAD = 100%, the groups are maximally spread
(Group 1 near 20 Hz, Group 3 near 20 kHz).

**MASTER OFFSET:** shifts all three groups simultaneously by adding an exponential offset:
```
f_n_eff = f_n_base × 2^(V_offset / 1V)
```
This is a 1V/octave exponential relationship applied to all three groups in common.

**STEREO WIDTH:** offsets R channel frequencies by a fixed ratio:
```
f_n_R = f_n_L × 2^(V_width / 1V)
```
At WIDTH = 50%, approximately +2 semitones offset. At WIDTH = 100%, approximately +5 semitones.

### Feedback (Resonance) Model

Each group has an independent feedback path with gain g (0 ≤ g < 1):
```
V_fb_source = (1 − FB_DIST_BLEND) × V_apf_out + FB_DIST_BLEND × V_post_dist
V_fb_signal = POLARITY_select(V_fb_source)   [+1, 0, or −1 × V_fb_source]
V_out_group = H_6(s) × [V_in + g × V_fb_signal]
V_out_group = H_6(s) × V_in / (1 − g × POLARITY × H_6(s))
```

FB DIST BLEND is always active and continuously selects the feedback source:
```
FB_DIST_BLEND = 0:    V_fb_source = V_apf_out        (clean APF feedback)
FB_DIST_BLEND = 0.5:  V_fb_source = 0.5×V_apf_out + 0.5×V_post_dist  (equal blend)
FB_DIST_BLEND = 1:    V_fb_source = V_post_dist       (post-distortion feedback)
```

**POLARITY selection:**
```
Positive:   V_fb_signal = +V_fb_source   (standard, deepens notches)
Off:        V_fb_signal = 0              (g effectively = 0 regardless of FB knob)
Negative:   V_fb_signal = −V_fb_source  (inverts feedback; notches become peaks)
```

At g → 1 with Positive polarity: self-oscillation at notch frequencies.
At g → 1 with Negative polarity: self-oscillation at peak frequencies (inverse comb).
Circuit must limit g ≤ 0.95 via resistor floor in the feedback summing network.

### Frequency Response (Combined Output)

With COMB BYPASS controlling pre-comb VCA level:
```
V_output = V_bypass_signal + V_comb_processed
```
Where the COMB BYPASS VCA controls how much of the comb-processed signal is passed.
At COMB BYPASS = 0: fully bypassed, comb output muted.
At a notch frequency with COMB BYPASS = 100%: maximum notch depth. With feedback, the peaks between
notches are emphasized.

### OTA-Based Voltage Control

Each all-pass stage uses an OTA (one cell of LM13700) as the variable element:
```
ω₀ = g_m / C_apf
g_m = I_abc / (2 × V_T)    where V_T ≈ 26 mV at room temperature
     = I_abc × 19.2 (A/A)
```
So `ω₀ = (I_abc × 19.2) / C_apf`

The control voltage (from the FREQ knob + CV) is converted to an exponential current I_abc via
an expo converter. This gives the 1V/octave exponential frequency sweep.

---

## Phase 3: Circuit Design

### Topology
OTA-based first-order all-pass stages. Each stage uses one OTA cell of an LM13700 (dual OTA,
SOIC-16) plus one op-amp half. Six stages per group, three groups, two channels = 36 OTA cells
and 36 op-amp halves total.

**IC count per channel:**
- 18 OTA cells needed → 9× LM13700 per channel → 18× LM13700 total (L + R)
- 18 op-amp halves for all-pass stages per channel → 9× TL072 per channel → 18× TL072 total
- 3× expo converter circuits (one per group, shared L/R since L and R track same ω₀)
- 3× op-amp for expo converters → ~2× TL072 (with 2 halves spare)
- 3× feedback summing amplifiers (one per group, L and R separate) → 3× TL072 per channel
- COMB BYPASS VCA: V2164-based; 1× per channel

Total approximate IC count: 18× LM13700, ~24× TL072/TL074, expo transistors.
This block is the most component-dense block in the module. Plan for 2–3 PCBs.

#### Single All-Pass Stage (per OTA cell)

```
V_in ──┬──[R_ref]──(−) TL072A ──── V_out
       │                 (+)◄────────┤
       └──[OTA_out]──[C_apf]────────┘

OTA (LM13700 cell):
  (+in): V_in
  (−in): GND (or virtual ground via buffer)
  (Iabc): exponential control current from expo converter
  (out): OTA output current → charges C_apf
```

Standard inverting all-pass op-amp topology with OTA as the time-constant element:
- R_ref: fixed reference resistor (sets passband gain balance)
- C_apf: sets frequency range; C_apf = g_m / ω₀_max

**Component values (Group 1, range 100 Hz – 1 kHz):**
- Use I_abc_nom = 10 µA (operating point, same as LP1/LP2/HP filters)
- g_m = 10 µA / (2 × 26 mV) = 192 µS
- ω₀_max = 2π × 1000 = 6283 rad/s
- C_apf = g_m / ω₀_max = 192 µS / 6283 = 30.6 nF → use **33 nF** (C0G 0603) ✓ available

For Group 2 (500 Hz – 5 kHz, ω₀_max = 31416 rad/s):
  C_apf = 192 µS / 31416 = 6.1 nF → use **6.8 nF** (C0G 0603) ✓ available

For Group 3 (2 kHz – 20 kHz, ω₀_max = 125664 rad/s):
  C_apf = 192 µS / 125664 = 1.53 nF → use **1.5 nF** (C0G 0603) ✓ available

Note: earlier derivation used I_abc_max = 500 µA, giving 1000× smaller values (nF instead of µF).
The correct derivation uses the nominal operating current (10 µA). All three values are C0G 0603.
R_ref = 1/g_m at nominal I_abc = 10 kΩ to 100 kΩ range (set empirically)

#### Expo Converter (per group)

```
V_freq (from knob + CV sum) → [expo transistor pair] → I_abc → LM13700 Iabc pin
```
- Use matched NPN transistor pair (THAT340 or LM394) for temperature-stable expo conversion
- Trim pot for 1V/oct tracking calibration
- Reference current: set by resistor from +12 V to expo transistor base

#### Feedback Path (per group — FB DIST BLEND + POLARITY)

Each group's feedback circuit has two stages: FB DIST BLEND crossfade → polarity → amount.

**Stage 1: FB DIST BLEND continuous crossfade (shared across all 3 groups)**

```
V_apf_out ──[R_a]──┬──(−) BLEND_AMP ──(out)── V_fb_source
V_post_dist ─[R_b]──┘
```

Continuous resistive crossfade with op-amp buffer:
- FB DIST BLEND pot wiper drives complementary summing: R_a and R_b vary inversely
- At 0%: only V_apf_out active — clean APF feedback
- At 50%: equal blend of both sources
- At 100%: only V_post_dist active — post-distortion feedback
- One BLEND_AMP op-amp serves all three groups simultaneously (FB DIST BLEND is global)
- V_post_dist is tapped directly from Block 4's output stage; route as a shielded signal

**Stage 2: POLARITY selection (shared across all 3 groups via one POLARITY switch)**

```
V_fb_source ──(+) POL_INV ──(out)── V_fb_pos   (unity gain buffer)
V_fb_source ──(−) POL_INV ──(out)── V_fb_neg   (inverting, gain = −1)
              [POLARITY switch selects: V_fb_pos / GND / V_fb_neg]
```

- Positive → routes V_fb_pos into per-group amount stage
- Off → routes GND (no feedback signal regardless of FB knob)
- Negative → routes V_fb_neg (phase-inverted)

One TL072 half as the inverter; the POLARITY switch is a 3-position panel switch routing
the appropriate signal to all three per-group feedback amount stages.

**Stage 3: Feedback amount (independent per group, ×3)**

```
V_fb_polar ──[R_fb_fixed]──┬──(−) summing amp ──► V_fb_sum → Group input
                            │
                        [FB knob pot + CV attenuverter]
                            │
                           GND
```

FB knob and CV attenuverter set the effective gain g in the feedback path.
End-stop resistor (R_fb_min) in the pot circuit ensures g ≤ 0.95 at maximum setting.
Three independent summing amps — one per group (using TL072 halves).

#### COMB BYPASS VCA

Pre-comb VCA controls the level of signal entering the comb filter chain. At 0V (COMB BYPASS = 0),
the comb-processed signal is muted and only the dry path passes. At 10V, full comb processing
feeds into the signal path.

LM13700 OTA crossfade — 2× LM13700 (4 OTA cells for L bypass, L comb, R bypass, R comb):

```
V_BYPASS_CV ──[complementary Iabc driver]──► Cell A Iabc (dry path, decreasing)
                                          ──► Cell B Iabc (comb path, increasing)

Dry path:    V_in ──► LM13700_CB1 cell A I_out ──► SUM_AMP → V_out
Comb path:   V_comb ──► LM13700_CB1 cell B I_out ──► SUM_AMP (same node)
(L channel — LM13700_CB1; R channel — LM13700_CB2, same structure)
```

Complementary Iabc driver: op-amp difference stage (TL072 half) generates:
  Cell A Iabc = (V_ref − V_BYPASS_CV) / R_Iabc   (full at CV=0, zero at CV=V_ref)
  Cell B Iabc = V_BYPASS_CV / R_Iabc               (zero at CV=0, full at CV=V_ref)
Both cells sum current into the same SUM_AMP virtual-ground node for a smooth crossfade.

#### STEREO WIDTH

A simple exponential offset applied to the R channel expo converter reference only:
- WIDTH knob → small DC offset voltage added to V_freq_R only (not V_freq_L)
- Op-amp summer adds WIDTH_V to the R expo converter input
- WIDTH = 0: R expo is same as L → mono
- WIDTH max: R expo input is shifted, R ω₀ is higher (or lower) by several semitones

### IC / Component Selection (key ICs)

| Reference | Part Number | Package | Qty | Notes |
|---|---|---|---|---|
| OTA_x | LM13700M | SOIC-16 | 18 | Dual OTA; 1 per 2 APF stages; 9 per channel |
| APF_AMP_x | TL072CDT | SOIC-8 | 18 | Dual op-amp; 1 per 2 APF stages; 9 per channel |
| EXPO_x | THAT340 | SOIC-8 | 3 | Matched NPN pair for expo converter (1 per group); LM394 discontinued — THAT340 only |
| LM13700_CB1 | LM13700M | SOIC-16 | 1 | COMB BYPASS VCA — L channel: cell A = L dry path, cell B = L comb path |
| LM13700_CB2 | LM13700M | SOIC-16 | 1 | COMB BYPASS VCA — R channel: cell A = R dry path, cell B = R comb path |
| FB_AMP_x | TL074CDT | SOIC-14 | 3 | Per-group feedback summing amp + BLEND_AMP + POL_INV (≈3 quads needed) |
| MIX_AMP_x | TL074CDT | SOIC-14 | 2 | Summing, width offset, general purpose |
| C_apf_G1 | C0G / NP0 | 0603 | 12 | 33 nF (6 per channel × 2 channels) — Group 1, 100 Hz–1 kHz |
| C_apf_G2 | C0G / NP0 | 0603 | 12 | 6.8 nF — Group 2, 500 Hz–5 kHz |
| C_apf_G3 | C0G / NP0 | 0603 | 12 | 1.5 nF — Group 3, 2 kHz–20 kHz |
| C_hf_x | C0G / NP0 | 0603 | 36 | 22 pF HF-suppression at each OTA output node; 18 OTA cells per channel × 2 channels = 36 total. **Must be placed within 1 mm of OTA output pin** — see noise-audit.md M4 |
| R_lin_x | — | 0603 | 72 | 1 kΩ linearizing resistors at each OTA differential input; 2 per cell × 18 cells × 2 channels = 72 total |
| C_iabc_x | C0G / NP0 | 0402 | 36 | 10 nF bypass cap from each LM13700 Iabc pin to GND; 18 OTA cells per channel × 2 channels = 36 total. Place within 2 mm of Iabc pin. Filters HF noise on expo current lines from ribbon cable. See noise-audit.md H3 |
| SW_POL | 3-pos panel switch | Panel | 1 | POLARITY: Positive / Off / Negative (mechanical) |
| R_pol_bleed | — | 0603 | 10 kΩ | 1 | Bleeder resistor from POLARITY switch "Off" contact to GND. Prevents switch contact leakage current from appearing at feedback summing node when POLARITY = Off. See noise-audit.md H4 |
| RV_FB_DIST_BLEND | Lin pot | 9mm | 1 | FB DIST BLEND crossfade: 0% = clean APF fb, 100% = post-dist fb |

### Trim Pots

| Reference | Range | Purpose | Adjustment Procedure |
|---|---|---|---|
| RV_1VOCT_G1 | ±20% | Group 1 expo converter 1V/oct calibration | Sweep FREQ 1 CV by 1V; verify exact octave change in notch frequency |
| RV_1VOCT_G2 | ±20% | Group 2 expo converter 1V/oct calibration | Same |
| RV_1VOCT_G3 | ±20% | Group 3 expo converter 1V/oct calibration | Same |
| RV_FB_MAX_1 | 0.90–0.99 | Max feedback limit for Group 1 | Set so oscillation onset is just barely reachable |
| RV_FB_MAX_2 | 0.90–0.99 | Max feedback limit for Group 2 | Same |
| RV_FB_MAX_3 | 0.90–0.99 | Max feedback limit for Group 3 | Same |

### Power Draw Estimate
- 18× LM13700 (APF stages) + 2× LM13700 (COMB BYPASS VCA) = 20× LM13700: ~68 mA
- 18× TL072 + ~4× TL074: ~30 mA
- +12 V: ~55 mA | −12 V: ~55 mA (significant — plan thermal management)

### Known Circuit Challenges
- **IC count**: 18 LM13700 + 18 TL072 is large. Plan 2–3 stacked PCBs with ribbon cable.
- **Expo converter matching**: THAT340 matched NPN pair required for stable 1V/oct tracking across temperature. LM394 is discontinued — use THAT340 only. A single general-purpose transistor will drift.
- **HF oscillation**: OTA stages at high Iabc (high frequency) can self-oscillate due to parasitic capacitance. Add small (22 pF) capacitors at each OTA output node and keep traces short.
- **Crosstalk L/R**: L and R share the same group frequencies but have separate OTA signal paths. Route L and R ground planes separately; do not route L signal adjacent to R signal on PCB.
- **V_post_dist routing**: the distortion output (Block 4) must be routed to the APF feedback section without picking up noise. Use a shielded wire or dedicated PCB trace with guard ring; keep away from OTA signal nodes.
- **FB DIST BLEND crossfade**: the continuous crossfade replaces the CD4053 SOURCE switch. Use a complementary-gain resistive crossfade (pot + op-amp summer). The BLEND_AMP output must be buffered before the per-group feedback amp stages.
- **COMB BYPASS complementary Iabc driver**: the op-amp difference stage that generates complementary Iabc currents must have matched resistors (0.1% preferred, 1% acceptable) to ensure dry+comb currents sum to a constant total — otherwise the output level changes as COMB BYPASS sweeps.
- **POLARITY Off position (RESOLVED)**: when POLARITY = Off, GND must be cleanly connected to the feedback summing node. Switch contact leakage (1–10 nA typical for panel toggle switches) through R_fb_fixed (100 kΩ) = up to 1 mV at the summing node — audible bleed-through at high FB settings. **Fix**: R_pol_bleed = 10 kΩ to GND at the "Off" contact. 10 nA through 10 kΩ = 0.1 µV — inaudible. See noise-audit.md H4.
- **Negative feedback stability**: with POLARITY = Negative, the feedback becomes degenerative in the normal sense but regenerative at the complementary frequencies. At high g, the system may still self-oscillate but at different frequencies than positive feedback — verify stability across the full FB range in simulation before PCB layout.
- **Calibration burden**: 6 trim pots (3 expo + 3 feedback limits) plus 3 independent feedback CV attenuverters. Document calibration order clearly: expo converters first, then feedback limits.
