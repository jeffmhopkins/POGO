# Block 6: Triple Bandpass + Distortion
Three independent 2-pole OTA-C SVF bandpass resonators (formant filters F1/F2/F3) with per-group drive and a global distortion mode switch.

DSP source: `plugin/src/dsp/BandpassSVF.hpp`, `plugin/src/dsp/Distortion.hpp`, `plugin/src/Pogo.cpp` (lines 410–475)

---

## 1. Intent

Three bandpass resonators tuned to low (F1 ~200 Hz), mid (F2 ~1500 Hz), and high (F3 ~6000 Hz) formant regions. Together they act as a talking/formant filter, vowel shape sculptor, or comb-like resonator bank.

**BP_OFFSET** shifts all three groups together (master frequency offset); each group also has an independent FREQ offset relative to its f_ref. **BP_TILT** spreads L and R independently — L gets +tiltV, R gets −tiltV, creating stereo width by separating the formant positions in each channel.

**BP_MIX** dry/wet blend allows dialing from pure LP1 output (dry) to full formant stack (wet). At 50% (default) the formants add to the underlying LP1 texture.

**Distortion** runs post-SVF, pre-mix. One global `BP_DIST` switch selects Soft Clip / Hard Clip / Wavefold across all three groups simultaneously. Per-group `DRIVE` controls the distortion depth independently. The BP3 post-distortion tap (before mix) is available at `BP3_L/R_OUT` jacks.

**ALT path**: `ALT_BP_L/R` jacks feed the BP input directly (bypassing VCA + LP1), with `GAIN_BP3` pre-gain (1× or 5×). When ALT jacks are patched, BP processes the ALT signal instead of the LP1 output.


---

## 2. Theoretical Design and Topology

### SVF Groups (3 independent resonators)

Each group is a 2-pole state-variable filter (BP output only). Both DSP and hardware use one 2-pole OTA-C SVF per group per channel:

```
H_BP(s) = (ω₀/Q · s) / (s² + ω₀/Q · s + ω₀²)
```

Peak at s = jω₀: |H_BP(jω₀)| = 1 (constant unity, regardless of Q). Q controls bandwidth only, not peak amplitude.

**f_ref per group** (at 0V CV):
| Group | f_ref | Formant |
|---|---|---|
| BP1 | 200 Hz | Low vowel body (F1) |
| BP2 | 1500 Hz | Mid vowel / consonant (F2) |
| BP3 | 6000 Hz | High formant / sibilance (F3) |

**Frequency control:**
```
f₀ = f_ref[i] × 2^(BP_OFFSET + BP_FREQ_i + BP_TILT × ±1)
```
where BP_TILT applies +tiltV on L channel, −tiltV on R channel.

**Q control:**
```
DSP: Q = 0.5 × 400^qParam  (range 0.5–200; does NOT self-oscillate by design)
Hardware: Q = 52mV / (Iabc × R_in)
```
BP Q maximum is ~200 at hardware (Iabc → minimum before instability threshold). Self-oscillation is suppressed — BP groups are resonators, not oscillators.

### Distortion

Three modes selected by `BP_DIST` (global switch, 0/1/2):

**Soft Clip (mode 0):**
```
G = driveParam ≤ 0.20 ? (driveParam / 0.20)        (0→1× gain control)
      : exp((driveParam − 0.20) / 0.80 × 4)         (1×→~55× drive, same exp law)
y = Vth × tanh(G × x / Vth)    Vth = 0.28 (= 1.4V/5V; two 1N4148W per polarity)
```
Output bounded to ±Vth = ±1.4V at all drive levels. Linear below threshold; smooth tanh onset above. Diodes always in circuit; gain-control zone (≤9am) feeds the diode chain at reduced gain.

**Hard Clip (mode 1):**
```
g = 1 + d × 4    (1–5× linear gain)
y = clamp(g × x, −1.16, +1.16)    (±1.16 = ±5.8V/5V; zener 5.1V + 1N4148W Vf 0.7V)
```
Linear gain into hard rails at ±5.8V. Aggressive, brick-wall limiting.

**Wavefold (mode 2, Buchla-style):**
```
Vth = 0.28    (= 1.4V/5V; two 1N4148W per polarity in passive clamp)
y = (1 + d × 4) × x                    (1–5× pre-gain)
output = Vth × asin(sin(π/2 / Vth × y)) × 2/π
```
Passive diode clamp at ±Vth, then V_out = 2×V_clamp − V_in (slope reversal at ±1.4V). At max drive and full-scale input: ~18 folds vs ~3 folds at ±5V threshold. Dense Buchla-style folding.

### BP_MIX blend

```
BP_out = clamp(LP1_output + mix × sum(distorted_groups), −12, +12)
```
Dry is always present at unity. Wet adds on top. Mix=0: LP1 only. Mix=max: LP1 + full wet (up to 6 dB louder than a crossfade). Hardware op-amp rails limit output; DSP clamps at ±12V. Default mix=0.5.

### Oversampling

None. Hardware SVF and distortion run at audio rate; analog hardware is inherently alias-free. DSP matches: no oversampling applied to BP section.

### DSP/Hardware Alignment

DSP and hardware are aligned on all BP signal-processing behaviors:
- 2-pole SVF per group per channel (both)
- Unity BP peak gain regardless of Q (both)
- Additive BP_MIX: dry at unity, wet added on top (both)
- No oversampling (both)
- Distortion thresholds: SC ±1.4V, HC ±5.8V, WF ±1.4V (both)

→ See aux-ota-c-svf.md for SVF topology; aux-distortion.md for distortion cells.

---

## 3. Physical Design

### OTA-C SVF instances

Three groups × two channels (L + R) = **6 OTA-C SVF instances**. Each instance requires:
- 1× LM13700 OTA cell as integrator (one IC = 2 cells = one group, one channel)
- 1× TL072 half as SUM_AMP

Grouping per IC:
- Per group: `BP_OTA_G1_L`, `BP_OTA_G1_R` etc. — one LM13700 per group per channel (dual OTA: cell A + cell B = integrator + Q VCA, OR cell A/B for two channels of same group)
- Conservative count: 3 groups × 2 channels × 1 LM13700 = **6× LM13700** for integrators + Q VCAs

**Q (resonance) at SUM_AMP:**
Standard SVF BP peak is 1× (constant unity, independent of Q). No normalization is applied. Q controls bandwidth only; high-Q formants have the same peak level as low-Q formants. This is the natural hardware OTA-C SVF behavior and is preserved in the DSP.

**Stereo tilt implementation:**
- BP_TILT generates +V_tilt (from mod bus via attenuverter)
- +V_tilt added to L-channel expo converter offset sum
- −V_tilt generated by TL072 inverting unity buffer; added to R-channel expo converter offset sum
- One TL072 half used as tilt inverter (shared across all 3 groups, same tilt offset applied to all)

**Expo converters:**
- One THAT340 per group (BP1, BP2, BP3) — 3× THAT340 total — each shared between L and R channels
- Different f_ref per group requires separate expo trims (RV_BP1_REF, RV_BP2_REF, RV_BP3_REF)

**Distortion hardware (see aux-distortion.md):**
- Three sub-circuit chains per group: SC / HC / WF all running simultaneously
- CD4053 triple 2-channel analog mux per group selects which mode's output passes
- All 3 CD4053 select pins tied together → BP_DIST switch controls all groups simultaneously
- One 3-position slide switch (PogoSwitchH3) → 2 select lines to all 3 CD4053 ICs
- Distortion runs post-SVF at audio rate (no oversampling in analog hardware)
- BP3 output tap: taken after distortion stage on group 3, available at BP3_L/R_OUT jacks

**Oversampling:**
- None. Hardware and DSP both run at base sample rate. Analog hardware is inherently alias-free; no oversampling required.

**Board assignment:** BP SVF and distortion on audio board. BP control pots and jacks on control board. THAT340s on audio board near their respective SVF clusters.

### Q Normalization — Design Decision

Hardware OTA-C SVF produces |H_BP(jω₀)| = 1 (constant unity peak). Q controls bandwidth only. A 1/Q² normalization would require a VCA per group per channel (6 cells), significantly increasing complexity. Decision: hardware unity peak is preserved in both hardware and DSP. High-Q formants are louder — this is musically desirable (tight resonances stand out) and is the expected behavior of analog formant filters.

### Distortion Sub-Circuit Design (SC / HC / WF)

One set of three sub-circuit paths (SC + HC + WF) per group, per channel = 6 sets total.
All paths share a common DRIVE control signal per group (one pot + CV per group, summed at
mod bus). All three paths run continuously; the CD4053 selects which output reaches BP_MIX.

#### SC Path (Soft Clip)

Inverting gain stage followed by antiparallel diode-pair feedback (tanh approximation):

```
                 R_SC_fb_fixed (10 kΩ)
              ┌──────────────────────────────┐
              │   RV_DRIVE (0–470 kΩ log)    │
              ├──────────────────────────────┤
              │         (in feedback path)    │
              │                               │
 BP_out ──[R_SC_in = 10 kΩ]──►(−) TL072 ──►─┴─── SC_out
                                   │
                               D_SC_3│D_SC_4 (1N4148W antiparallel pairs)
                               D_SC_1│D_SC_2
                                   │
                                  GND

Diodes: two 1N4148W in series per direction (4 total per path)
  V_clip = 2 × V_f_1N4148 ≈ 2 × 0.7V = 1.4V (soft clip threshold)

DRIVE varies feedback resistance:
  RV_DRIVE = 0 (full CCW): R_fb = R_SC_fb_fixed = 10 kΩ → gain = 10/10 = 1× (linear)
  RV_DRIVE = max (full CW): R_fb = 10 kΩ + 470 kΩ = 480 kΩ → gain = 480/10 = 48× (heavy sat)
```

At low drive: signal below 1.4V threshold → diodes off → output follows linear gain law.
At high drive: pre-amp amplifies to many multiples of 1.4V → diodes conduct → output
limited to ±1.4V, producing soft saturation. Tanh-like characteristic due to incremental
diode conductance. Polarity preserved (inverting amp + final inverting buffer restores sign).

Components per SC path: 1× TL072 half (SC gain amp), 4× 1N4148W (SOD-123), 2× resistors.

#### HC Path (Hard Clip)

Inverting gain stage with variable gain followed by back-to-back zener clamp:

```
 BP_out ──[R_HC_in = 10 kΩ]──►(−) TL072 ──►───────── HC_out
                                    │               │
                               R_HC_fb              │
                     (10 kΩ + RV_DRIVE 47 kΩ log)  │
                                                    │
                             D_HC_Z1 ── D_HC_Z2     │
                             (BZX84C5V1, SOT-23)    │
                             back-to-back to GND     │

Zener pair: one in breakdown (5.1V), one in forward conduction (0.7V) → V_clip = ±5.8V

DRIVE varies gain:
  RV_DRIVE = 0: R_fb = 10 kΩ → gain = 10/10 = 1× → ±5V signal → stays below ±5.8V clip (near-linear)
  RV_DRIVE = max: R_fb = 10+47 = 57 kΩ → gain = 57/10 = 5.7× → ±5V signal → ±28.5V → clips at ±5.8V
```

At low drive: input ±5V with gain 1× gives ±5V output; just below zener threshold (5.8V) — near-linear.
At high drive: gain up to ~5.7×; input is amplified well beyond threshold → hard clip at ±5.8V
(corresponding to ±1V threshold at the input, i.e., signals above 1V clip against the zeners).

Components per HC path: 1× TL072 half (HC gain amp), 2× BZX84C5V1 zener (SOT-23), 2× resistors.

**Note:** Zener clip threshold of ±5.8V vs DSP target of ±5V. Deviation is ±0.8V (16%).
Acceptable for a distortion effect. Document and close.

#### WF Path (Wavefold)

True symmetric precision folder approximating DSP `asin(sin(π/2 × gain × x)) × 2/π`.

Uses a passive diode clamp + op-amp subtractor topology that produces true slope reversal at
±Vth (1.4 V). This is not gain compression — the output slope inverts at threshold.

```
Stage 1 — pre-gain (variable fold depth):
 BP_out ──[R_WF_in = 10 kΩ]──►(−) TL072-A ──► V_fold_in
                                    │
                               R_WF_fb: 10 kΩ + RV_DRIVE 47 kΩ → gain 1×–5.7×
 (inverting; polarity consistent with SC/HC paths)

Stage 2 — symmetric precision folder:
 Passive diode clamp:
   V_fold_in ──[R_clamp = 10 kΩ]──┬── V_clamp
                                    │
              D_WF_1 ──►|── D_WF_2 ──►|──┐
                                           ├── AGND
              D_WF_3 ─◄|── D_WF_4 ─◄|──┘
   (D_WF_1–4: 1N4148W, SOD-123; two per direction → Vth = ±2×0.7V = ±1.4V)
   Clamp action: V_clamp = V_fold_in when |V_fold_in| ≤ 1.4V
                 V_clamp = +1.4V    when V_fold_in > +1.4V
                 V_clamp = −1.4V    when V_fold_in < −1.4V

 Op-amp folder (TL072-B, non-inverting reference = V_clamp):
   V_clamp ──────────────────────────►(+)
   V_fold_in ──[R_g = 10 kΩ]─────────►(−)──── TL072-B ──[R_f = 10 kΩ]──► WF_out
                                        (−) receives negative feedback from output via R_f
```

**Transfer function:**
```
WF_out = 2 × V_clamp − V_fold_in

 |V_fold_in| ≤ 1.4V: V_clamp = V_fold_in → WF_out = V_fold_in          (linear)
 V_fold_in  > +1.4V: V_clamp = +1.4V    → WF_out = 2.8V − V_fold_in   (fold down)
 V_fold_in  < −1.4V: V_clamp = −1.4V    → WF_out = −2.8V − V_fold_in  (fold up)
```

This is a true slope reversal at ±1.4 V, matching the asin(sin(x)) shape for a single fold.
At DRIVE=max (gain 5.7×), a ±5V input signal reaches ±28V pre-fold → multiple reflections
across the ±1.4V window → dense odd-harmonic spectrum.

**Stability:** TL072-B is in standard negative feedback (output → R_f → (−) input).
V_clamp at (+) is a passive resistor-diode network with no active elements; it presents a
source impedance of R_clamp = 10 kΩ at (+), which has no impact on loop stability.
Phase margin is identical to a standard G=+2 non-inverting configuration. No stability
concern — no prototype verification required for this stage.

**Diode Vth variation:** 1N4148W Vf ≈ 0.6–0.7 V depending on current.
At R_clamp = 10 kΩ and V_fold_in = 3V: I_clamp ≈ (3−1.4)/10kΩ = 160 µA → Vf ≈ 0.60V → Vth ≈ 1.2V.
Fold threshold shifts slightly with drive level (soft onset, similar to Buchla-style folders).
Intentional characteristic; not a defect.

Components per WF path: 2× TL072 halves (pre-gain + folder; same IC, no additional ICs),
4× 1N4148W (SOD-123), 4× resistors (R_WF_in, R_WF_fb_fixed, R_clamp, R_g = R_f = 10 kΩ).

**Note on wiper bypass caps:** A 47 pF cap from each RV_DRIVE wiper to AGND is recommended
(pole at R_wiper_max × C ≈ 11.75 kΩ × 47 pF → f_pole ≈ 288 kHz). Kills RF pickup; no
effect on control-rate drive changes.

### CD4053 Mux Wiring

One CD4053 (SOIC-16) per group, 3 total (BP_DIST_MUX_1, _2, _3). All three have their
S_A and S_B control pins tied together (global mode select from SW_DIST panel switch).

**Power supply wiring:**
```
VDD (+12V supply) → pin 16 of each CD4053 (analog/digital supply)
VSS (−12V supply) → pin 7 of each CD4053 (negative analog rail)
VEE (GND)         → pin 8 of each CD4053 (digital ground; sets logic threshold at ~VDD/2)
INH pin (pin 6)   → GND (active-low inhibit; tied LOW = always enabled)
```

The CD4053 passes signals from VSS to VDD on each analog channel. With ±12V supply,
the audio signal can swing ±5V without signal-dependent R_on distortion.

**Control line encoding (2 binary lines → 3 modes):**
```
SW_DIST position → S_A line, S_B line:
  Soft Clip:  S_A = 0,  S_B = 0   → Channel X passes SC_out; Channel Y passes X-output
  Hard Clip:  S_A = 1,  S_B = 0   → Channel X passes HC_out; Channel Y passes X-output
  Wavefold:   S_A = x,  S_B = 1   → Channel Y selects WF_out (overrides Channel X)
```

**Channel assignment within each CD4053:**
```
Channel X (control S_A):
  X0 input ← SC_out
  X1 input ← HC_out
  X output → Channel Y input Y0

Channel Y (control S_B):
  Y0 input ← Channel X output
  Y1 input ← WF_out
  Y output → DIST_out (→ BP_MIX input)

Channel Z: spare (inputs tied to GND; output unused)
```

When S_B = 1: Channel Y selects WF regardless of S_A — wavefold mode overrides.
When S_B = 0: Channel Y passes Channel X output, which is SC or HC depending on S_A.

SW_DIST is a 3-position slide switch (PogoSwitchH3) generating S_A and S_B:
- Position 0 (Soft):  S_A=low, S_B=low   (0V = logic LOW; from GND)
- Position 1 (Hard):  S_A=high, S_B=low  (+5V = logic HIGH; from +5V regulator or +12V with R+zener)
- Position 2 (Fold):  S_A=low, S_B=high

The +5V logic rail for CD4053 control inputs: taken from a 78L05 regulator (or 5.1V zener
from +12V with 1kΩ series R) on the audio board. Logic signal swings 0V–5V, which is within
the CD4053 VIH threshold at VDD=+12V.

### BP_MIX Blend Circuit

The DSP: `V_out = (1 − mix) × V_dry + mix × V_wet`  
where V_dry = LP1 signal (entering block-6), V_wet = sum of three distorted BP groups.

**BP summing stage (V_wet):**

One TL072 inverting summer combines distortion outputs of all three groups (per channel):
```
DIST_BP1_out ──[R_sum = 33 kΩ]──┐
DIST_BP2_out ──[R_sum = 33 kΩ]──┼──►(−) TL072 ──[R_f = 33 kΩ]──► V_wet_inv
DIST_BP3_out ──[R_sum = 33 kΩ]──┘         │
                                         (+) = GND
```
V_wet_inv = −(BP1 + BP2 + BP3) / 3 (normalized). Signal inverted; corrected at BP_POL stage or
BP_MIX output buffer.

**BP_MIX summing amp:**

A TL072 inverting summer with the MIX pot controlling the wet-to-dry ratio:
```
V_dry ──[R_dry = 100 kΩ]────────────────────────┐
                                                  ├──►(−) TL072 ──[R_mix_f = 100 kΩ]──► V_mix_inv
V_wet_inv ──[R_wet_pot = RV_BP_MIX wiper × 100k]─┘
                                                (+) = GND
```

RV_BP_MIX (linear-taper 100 kΩ): controls R_wet from 0 (full CCW, no wet) to 100 kΩ (full CW).
V_mix_inv = −(V_dry + V_wet_inv × R_mix_f/R_wet)

At MIX=0 (R_wet = ∞): V_mix_inv = −V_dry (dry only)
At MIX=max (R_wet = 100k): V_mix_inv = −V_dry − V_wet_inv = −V_dry + V_wet (polarity corrected)

A unity-gain inverting buffer (TL072 half B) after the mix amp restores final polarity:
V_bp_out_pre_pol = +V_dry when MIX=0, → dry + wet at MIX=max.

**Note:** DSP matches hardware: dry is always present at unity, wet is added on top. At MIX=max: output = dry + wet (up to 6 dB louder than a crossfade at equal level). DSP clamps at ±12V; hardware limited by op-amp rails.

### BP_POL Polarity Switch

The DSP applies BP_POL ∈ {+1, −1} to the BP output before summing into the signal chain.

Hardware: SW_POL (2-position slide) selects between the direct path and an inverting buffer.

```
V_bp_out_pre_pol ──────────────────────────────────────────┐
                                                           SW_POL
V_bp_out_pre_pol ──[R_pol_in = 100 kΩ]──►(−) TL072 ──►──┘    ──► V_bp_out
                                              │
                                         [R_pol_fb = 100 kΩ] (G = −1)
                                         (+) = GND
```

The spare half of BP_TILT_INV TL072CDT (half B) is used as the G=−1 polarity inverter:
- Half A of BP_TILT_INV: generates −V_tilt (already assigned)
- Half B of BP_TILT_INV: polarity inverter (G=−1) for BP_POL

SW_POL (PogoSwitchH2) selects between V_bp_out_pre_pol (positive polarity, default) and
the output of the G=−1 stage (negative polarity). The switch is a standard 1P2T (SPDT)
slide/toggle on the panel.

**Board assignment:** BP_MIX summing amp and BP_POL inverter on audio board. SW_POL panel
wiring routes to control board via ribbon connector.

### Trim Pots

| Ref | Range | Purpose |
|---|---|---|
| RV_BP1_REF | 500 kΩ; ±25% f_ref | BP1 cutoff reference (target: 200 Hz at 0V); in series with R_IREF_A 1 MΩ |
| RV_BP2_REF | 500 kΩ; ±25% f_ref | BP2 cutoff reference (target: 1500 Hz at 0V); in series with R_IREF_A 1 MΩ |
| RV_BP3_REF | 500 kΩ; ±25% f_ref | BP3 cutoff reference (target: 6000 Hz at 0V); in series with R_IREF_A 1 MΩ |
| RV_BP1_1VOCT | 20 kΩ; ±10% tracking | BP1 expo 1V/oct calibration |
| RV_BP2_1VOCT | 20 kΩ; ±10% tracking | BP2 expo 1V/oct calibration |
| RV_BP3_1VOCT | 20 kΩ; ±10% tracking | BP3 expo 1V/oct calibration |
| RV_BP1_QMAX | V_bias | BP1 Q maximum point |
| RV_BP2_QMAX | V_bias | BP2 Q maximum point |
| RV_BP3_QMAX | V_bias | BP3 Q maximum point |

### Integrator Cap Derivation

BP1 (f_ref = 200 Hz): C = 192µS/(2π×200) = 153 nF → use 150 nF (C0G, 0805)
BP2 (f_ref = 1500 Hz): C = 192µS/(2π×1500) = 20.4 nF → use 22 nF (C0G, 0603)
BP3 (f_ref = 6000 Hz): C = 192µS/(2π×6000) = 5.1 nF → use 4.7 nF (C0G, 0603)

(Exact values adjusted via RV_BPx_REF trim; derive from nominal at I_abc = 10µA.)

### Power Draw Estimate

- 6× LM13700M (SVF integrators + Q VCAs): ~4 mA × 6 = ~24 mA  (TI: 4 mA typ per package)
- 6× OPA1612 (SUM_AMPs, dual SOIC-8): 5.5 mA × 6 = 33 mA  (Iq = 2.75 mA/channel × 2 ch/IC)
- Distortion op-amps — 18 TL072CDT ICs (6 SC + 6 HC + 6 WF; one SOIC-8 per group per channel; half A = signal path, half B = spare or shared): ~3 mA × 18 = ~54 mA
- BP_MIX + tilt/pol — 5 TL072CDT ICs (1 tilt/pol inverter + 2 wet-summer + 2 MIX polarity buffer): ~3 mA × 5 = ~15 mA
- 3× THAT340S14-U (expo converters): ~3 mA
- 3× CD4053BM96 (distortion mux, CMOS quiescent ≈ 0): ~0 mA
- **+12V: ~129 mA | −12V: ~129 mA**

Note: the dominant power draw is 23 TL072CDT packages (18 distortion + 5 MIX/tilt). Each IC
draws ~2.8 mA quiescent regardless of how many of its two halves are active. This is the
highest single-block draw in the module and must be accounted for in the bus power budget.

---

## 4. Component Requirements

| Ref | Part | Package | Value | Qty | Board | Block | Function |
|---|---|---|---|---|---|---|---|
| BP1_OTA_L, BP1_OTA_R | LM13700M | SOIC-16 | — | 2 | audio | block-6 | BP1 integrator + Q VCA (L and R, one IC each) |
| BP2_OTA_L, BP2_OTA_R | LM13700M | SOIC-16 | — | 2 | audio | block-6 | BP2 integrator + Q VCA (L and R) |
| BP3_OTA_L, BP3_OTA_R | LM13700M | SOIC-16 | — | 2 | audio | block-6 | BP3 integrator + Q VCA (L and R) |
| BP_SUM_G1_L, BP_SUM_G1_R | OPA1612 | SOIC-8 | — | 2 | audio | block-6 | BP1 SUM_AMP + output buffer (L and R); 1.1 nV/√Hz; pin-compatible with TL072CDT |
| BP_SUM_G2_L, BP_SUM_G2_R | OPA1612 | SOIC-8 | — | 2 | audio | block-6 | BP2 SUM_AMP + output buffer (L and R); 1.1 nV/√Hz |
| BP_SUM_G3_L, BP_SUM_G3_R | OPA1612 | SOIC-8 | — | 2 | audio | block-6 | BP3 SUM_AMP + output buffer (L and R); 1.1 nV/√Hz |
| BP_TILT_INV | TL072CDT | SOIC-8 | — | 1 | audio | block-6 | Half A = −V_tilt inverter; half B = BP_POL G=−1 inverter |
| BP1_EXPO, BP2_EXPO, BP3_EXPO | THAT340S14-U | SOIC-14 | — | 3 | audio | block-6 | V/oct expo converter per group (L+R shared) |
| BP_DIST_MUX_1, _2, _3 | CD4053BM96 | SOIC-16 | — | 3 | audio | block-6 | SC/HC/WF mode mux per group; S_A/S_B tied globally |
| R_5V_REG | resistor | 0603 | 1 kΩ | 1 | audio | block-6 | Series R for +5V logic rail (from +12V → 78L05 or zener) |
| D_5V | BZX84C5V1 | SOT-23 | 5.1V | 1 | audio | block-6 | Zener shunt for CD4053 logic supply rail |
| *— SC sub-circuit (per group, per channel: 6 sets) —* | | | | | | | |
| BP_SC_AMP_G1–G3_L/R | TL072CDT | SOIC-8 | — | 6 | audio | block-6 | SC gain amp; half A per channel; half B spare or shared |
| R_SC_in | resistor | 0603 | 10 kΩ | 12 | audio | block-6 | SC input resistor (1 per channel per group) |
| R_SC_fb_fixed | resistor | 0603 | 10 kΩ | 12 | audio | block-6 | SC minimum feedback R (ensures G≥1× at zero drive) |
| RV_DRIVE_SC_G1–G3 | log-taper pot | 9 mm | 470 kΩ | 6 | control | block-6 | SC DRIVE per group (shared with HC/WF; same pot) |
| D_SC_1N4148 | 1N4148W | SOD-123 | — | 48 | audio | block-6 | SC diodes: 4 per path (2 antiparallel pairs), 12 paths |
| *— HC sub-circuit (per group, per channel: 6 sets) —* | | | | | | | |
| BP_HC_AMP_G1–G3_L/R | TL072CDT | SOIC-8 | — | 6 | audio | block-6 | HC gain amp; half A per channel; half B spare or shared |
| R_HC_in | resistor | 0603 | 10 kΩ | 12 | audio | block-6 | HC input resistor |
| R_HC_fb_fixed | resistor | 0603 | 10 kΩ | 12 | audio | block-6 | HC minimum feedback R |
| RV_DRIVE_HC_G1–G3 | log-taper pot | 9 mm | 47 kΩ | 6 | control | block-6 | HC DRIVE per group (can share pot with SC if dual-gang) |
| D_HC_Z | BZX84C5V1 | SOT-23 | 5.1V | 12 | audio | block-6 | HC zener clamp: 2 back-to-back per path → ±5.8V clip |
| *— WF sub-circuit (per group, per channel: 6 sets) —* | | | | | | | |
| BP_WF_AMP_G1–G3_L/R | TL072CDT | SOIC-8 | — | 6 | audio | block-6 | WF pre-gain (half A) + symmetric folder (half B); 1 IC per path |
| R_WF_in | resistor | 0603 | 10 kΩ | 12 | audio | block-6 | WF pre-gain input R |
| R_WF_fb_fixed | resistor | 0603 | 10 kΩ | 12 | audio | block-6 | WF pre-gain minimum feedback R |
| R_clamp | resistor | 0603 | 10 kΩ | 12 | audio | block-6 | WF clamp network series R (limits diode current) |
| R_g | resistor | 0603 | 10 kΩ | 12 | audio | block-6 | WF folder (−) input resistor |
| R_f | resistor | 0603 | 10 kΩ | 12 | audio | block-6 | WF folder feedback resistor; R_g = R_f → G=+2 at (+) |
| D_WF_1N4148 | 1N4148W | SOD-123 | — | 48 | audio | block-6 | WF passive clamp: 4 per path (2 per polarity); Vth = ±1.4V |
| C_WF_wiper | ceramic, X7R | 0603 | 47 pF | 12 | audio | block-6 | RV_DRIVE wiper bypass cap; pole ≈288 kHz; anti-RF on each path |
| *— BP_MIX circuit —* | | | | | | | |
| BP_WET_SUM_L, _R | TL072CDT | SOIC-8 | — | 2 | audio | block-6 | Half A = BP1+BP2+BP3 wet summer; half B = MIX output buffer |
| BP_MIX_BUF_L, _R | TL072CDT | SOIC-8 | — | 2 | audio | block-6 | Half A = MIX output polarity buffer; half B = spare |
| R_sum | resistor | 0603 | 33 kΩ | 12 | audio | block-6 | BP wet summer input R (3 inputs × L + R × 2 channels) |
| R_dry | resistor | 0603 | 100 kΩ | 2 | audio | block-6 | MIX dry input R (L and R) |
| R_mix_f | resistor | 0603 | 100 kΩ | 2 | audio | block-6 | MIX feedback R |
| R_pol_in | resistor | 0603 | 100 kΩ | 2 | audio | block-6 | BP_POL G=−1 inverter input R (L and R); uses BP_TILT_INV half B |
| R_pol_fb | resistor | 0603 | 100 kΩ | 2 | audio | block-6 | BP_POL inverter feedback R |
| *— SVF passives —* | | | | | | | |
| C_int_BP1 | C0G/NP0 | 0805 | 150 nF | 4 | audio | block-6 | BP1 integrator caps (2 per channel × L+R); C0G mandatory |
| C_int_BP2 | C0G/NP0 | 0603 | 22 nF | 4 | audio | block-6 | BP2 integrator caps; C0G mandatory |
| C_int_BP3 | C0G/NP0 | 0603 | 4.7 nF | 4 | audio | block-6 | BP3 integrator caps; C0G mandatory |
| R_in_BP | resistor | 0603 | 100 kΩ | 6 | audio | block-6 | SUM_AMP input R (one per group per channel) |
| R_lin_BP | resistor | 0603 | 1 kΩ | 12 | audio | block-6 | OTA linearizing R (one per OTA cell, 2 cells × 6 ICs) |
| *— Calibration trimmers —* | | | | | | | |
| R_IREF_A_BP1, _2, _3 | resistor | 0603 | 1 MΩ | 3 | audio | block-6 | Fixed I_ref network R per group; in series with RV_BPx_REF; R_total at midpoint = 1250 kΩ → 9.6 µA |
| R_VOCT_BP1, _2, _3 | resistor | 0603 | 47 kΩ | 3 | audio | block-6 | EXPO V/oct scaling R per group (1% tolerance); with RV_1VOCT = 7.5 kΩ: 1kΩ/(47+7.5+1)kΩ = 18.0 mV/V ✓ |
| R_E_BP1, _2, _3 | resistor | 0603 | 1 kΩ | 3 | audio | block-6 | EXPO emitter degeneration per group; lower leg of 1V/oct attenuator |
| RV_BP1_REF, _2, _3 | Bourns 3224W | SMD | 500 kΩ | 3 | audio | block-6 | f_ref trim rheostat per group; in series with R_IREF_A; ±25% range |
| RV_BP1_1VOCT, _2, _3 | Bourns 3224W | SMD | 20 kΩ | 3 | audio | block-6 | 1V/oct tracking trim per group; ±10% range |
| RV_BP1_QMAX, _2, _3 | trimpot, SMD | 3296W | — | 3 | audio | block-6 | Q maximum bias per group |
| *— Panel controls —* | | | | | | | |
| SW_DIST | 3-pos slide | panel | — | 1 | panel | block-6 | BP_DIST: Soft/Hard/Fold; drives S_A + S_B to all CD4053 |
| SW_POL | 2-pos SPDT slide | panel | — | 1 | panel | block-6 | BP_POL: +/− polarity select |
| RV_BP_OFFSET | XL knob | 9 mm | — | 1 | control | block-6 | BP_OFFSET master freq offset (±5V/oct) |
| RV_BP_MIX | large knob, linear | 100 kΩ | — | 1 | control | block-6 | BP_MIX dry/wet level |
| RV_BP_FREQ_ATT | trimpot | 9 mm | — | 1 | control | block-6 | BP_FREQ_ATT master attenuverter |
| RV_BP_TILT_ATT | trimpot | 9 mm | — | 1 | control | block-6 | BP_TILT_ATT stereo spread attenuverter |
| RV_BP1_FREQ, _2, _3 | knob | 9 mm | — | 3 | control | block-6 | Per-group freq offset |
| RV_BP1_FOCUS, _2, _3 | knob | 9 mm | — | 3 | control | block-6 | Per-group Q (Focus) |
| RV_BP1_DIST, _2, _3 | knob, log | 9 mm | 470 kΩ | 3 | control | block-6 | Per-group DRIVE (shared SC/HC/WF pot) |
| RV_BP1_FREQ_ATT through _3_DIST_ATT | trimpot | 9 mm | — | 9 | control | block-6 | Per-group CV attenuverters (freq, focus, drive × 3) |
| J_BP3_L, J_BP3_R | PJ301M-12 | panel | — | 2 | panel | block-6 | BP3 formant tap output (post-distortion, pre-mix) |
| J_BP_FREQ_IN, J_BP_TILT_IN | PJ301M-12 | panel | — | 2 | panel | block-6 | BP master freq + tilt CV override jacks |
| J_BP1_FREQ_IN through J_BP3_DIST_IN | PJ301M-12 | panel | — | 9 | panel | block-6 | Per-group CV override jacks (freq, focus, drive) |
