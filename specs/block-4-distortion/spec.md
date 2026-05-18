# Block 4: Distortion

## Status
- Phase 1 (Audio Spec): [x] complete
- Phase 2 (Analog Model): [x] complete
- Phase 3 (Circuit Design): [x] complete

---

## Phase 1: Audio / Functional Specification

### Sonic Intent
Three independent distortion instances — one per APF group output — each with its own mode
and drive level. Each instance processes the stereo (L+R) output of its APF chain equally.
The three distorted group signals are summed after processing and passed to LP1.

This per-chain arrangement means each formant band can be distorted differently:
Group 1 (low) wavefolded for complex sub-harmonic content, Group 2 (mid) soft-clipped for
warmth, Group 3 (high) hard-clipped for bright edge — or any combination. The distortion
also feeds back into each group's APF feedback path when SOURCE = Post-Dist, creating a
tight self-referential loop where the distorted formant drives its own resonance.

- **Soft Clip**: Gentle, musical saturation. Adds warmth and odd harmonics. Sweet spot: 30–60%.
- **Hard Clip**: Aggressive transistor-style clipping, strong odd harmonics. Sweet spot: 20–50%.
- **Wavefold**: Buchla-style wavefolding. Increases harmonic complexity with drive. Sweet spot: 40–75%.

### Parameters

| Name | Range | Default | Taper | Description |
|---|---|---|---|---|
| MODE 1 | Switch: SC / HC / WF | SC | N/A | Distortion type for APF Group 1: Soft Clip / Hard Clip / Wavefold |
| MODE 2 | Switch: SC / HC / WF | SC | N/A | Distortion type for APF Group 2 |
| MODE 3 | Switch: SC / HC / WF | SC | N/A | Distortion type for APF Group 3 |
| DRIVE 1 | 0–100% | 30% | Logarithmic | Drive level for Group 1 distortion; applies equally to L and R |
| DRIVE 2 | 0–100% | 30% | Logarithmic | Drive level for Group 2 distortion; applies equally to L and R |
| DRIVE 3 | 0–100% | 30% | Logarithmic | Drive level for Group 3 distortion; applies equally to L and R |

### CV Modulation Targets

| Target | CV Range | Attenuverter | Notes |
|---|---|---|---|
| DRIVE 1 | 0–10 V | Yes | Group 1 drive amount; independent of Groups 2 and 3 |
| DRIVE 2 | 0–10 V | Yes | Group 2 drive amount |
| DRIVE 3 | 0–10 V | Yes | Group 3 drive amount |
| MODE 1/2/3 | — | None | Switch only; no CV |

### Signal Levels (I/O)
- Input: three independent stereo signals, one per APF group (±5 V each; APF is unity gain)
- Output: three distorted signals summed into one stereo signal → ±5 V nominal, up to ±10 V
  at high drive from multiple chains; summing stage must not clip before LP1

### Stereo Behavior
True stereo within each chain: L and R processed through identical circuits in parallel.
Each MODE switch and DRIVE knob applies equally to L and R of that chain.
No independent L/R controls. No cross-chain linking of MODE or DRIVE.

### Signal Flow
```
APF Group 1 (L+R) ──► [Distortion Chain 1: MODE 1, DRIVE 1] ──► DST1 out (L+R) ──┐
APF Group 2 (L+R) ──► [Distortion Chain 2: MODE 2, DRIVE 2] ──► DST2 out (L+R) ──┼──► sum ──► LP1
APF Group 3 (L+R) ──► [Distortion Chain 3: MODE 3, DRIVE 3] ──► DST3 out (L+R) ──┘
```
Each chain's output also feeds back into its own APF group's feedback path when SOURCE = Post-Dist.

### Edge Cases
- All three chains at DRIVE 100%: combined sum can exceed ±10 V; attenuate in the summing
  amp (gain ≈ 0.5 per chain into the sum) to keep combined output within ±10 V headroom.
- MODE switching live: brief click possible from mechanical switching. Accepted behavior.
- One chain's DRIVE at 0%: that group passes through clean; the other two are distorted.
  Useful for selectively distorting high or low formants while preserving the other.

---

## Phase 2: Analog Behavior Model

### Mode 1: Soft Clip Transfer Function

```
y = tanh(d × x) / tanh(d)

where x = normalized input (−1 to +1 = ±5 V full scale)
      d = drive factor; d = exp(DRIVE_knob × k)   (log taper mapping)
      y = normalized output
```

- At d → 0: y ≈ x (linear pass-through)
- At d = 1: y = tanh(x) / tanh(1) — onset of soft saturation
- At d → ∞: y = sign(x) (hard limit — approaches Mode 2 at maximum)

Symmetrical clipping → primarily odd harmonics (3rd, 5th, 7th, ...).
Even harmonics negligible unless input DC offset present.

### Mode 2: Hard Clip Transfer Function

```
y = clamp(d × x, −1, +1)

where clamp(z, lo, hi) = max(lo, min(hi, z))
```

- At d = 1: clipping only occurs at ±full scale (±5 V); subtle effect
- At d = 5: clips at ±1V (±1 V input), strong rectangular waveform content
- At d → ∞: output approaches ±1 (square wave)

Symmetrical hard clip → strong odd harmonics with no even content.
Transition from linear to flat is abrupt (unlike Mode 1).

### Mode 3: Wavefold Transfer Function

```
y = fold(d × x)

fold(z) = 4/π × arcsin(sin(π/2 × z))   [triangle-wave folding approximation]
```

Alternative (piecewise): each time the signal exceeds ±1, it reflects back:
```
fold(z): if |z| ≤ 1: y = z
         if 1 < |z| ≤ 3: y = 2 − z (for positive z)
         if 3 < |z| ≤ 5: y = −4 + z (for positive z)
         ... (repeating)
```

- At d = 1: no folding (signal stays within ±1)
- At d = 2: single fold; signal that would exceed +1 is reflected back down
- At d = 4–5: multiple folds; complex spectral content

Wavefolding is asymmetric at odd drive levels and symmetric at even drive levels, producing
a mix of even and odd harmonics depending on DRIVE setting. This is the primary timbral
interest of this mode.

---

## Phase 3: Circuit Design

### Topology
Three independent distortion instances (one per APF chain) followed by a summing stage.
Each instance contains three parallel mode sub-circuits (Soft Clip, Hard Clip, Wavefold)
switched by its own 3-position panel switch via a CD4053 analog mux.

No CV mode control — MODE switches are mechanical only.

#### Per-Chain Circuit (×3 chains)

**Soft Clip sub-circuit (1× TL072, L on half A, R on half B):**
```
V_in_L ──[R_in]──(−) TL072A ──(out)── V_sc_L
                   (+)=GND
                   (out)◄──[D1+D2 anti-parallel]──(−)
                   (out)◄──[R_f]──────────────────(−)

V_in_R: identical on TL072B
```
DRIVE knob varies R_in; diodes are 1N4148WS anti-parallel pairs.

**Hard Clip sub-circuit (1× TL072, L on half A, R on half B):**
```
V_in_L ──[R_drive]──(−) TL072A ──(out)── V_hc_L
                      (+)=GND
                      (out)◄──[R_f]──(−)
                      (out)──[Z1+Z2 anti-parallel, 5.1 V]──GND

V_in_R: identical on TL072B
```
DRIVE knob varies R_drive; zeners are BZX84-C5V1 (SOT-23).

**Wavefold sub-circuit (1× TL074, 2 halves per channel):**
```
V_in_L ──[gain stage]──► [fold stage 1]──► [fold stage 2]──► V_wf_L
(2 op-amp halves per channel: L uses halves A+B, R uses halves C+D)
```
DRIVE knob sets input gain before folding stages.
Reference: MFOS Wavefolder / Buchla 259 topology.

**MODE switch and mux (1× CD4053 per chain):**
- CD4053 triple SPDT routes V_sc / V_hc / V_wf to chain output based on MODE switch position
- Panel switch directly drives CD4053 A/B select inputs (no comparator needed — mechanical only)
- Unity-gain output buffer (spare TL072 half) isolates CD4053 series resistance from downstream

#### Output Summing Stage

Three chain outputs (L and R separately) summed into one stereo signal:
```
V_dst1_L ──[R_sum]──┐
V_dst2_L ──[R_sum]──┼──(−) SUM_AMP_L ──(out)── V_combined_L → LP1
V_dst3_L ──[R_sum]──┘
```
Gain of summing amp: G = R_f_sum / R_sum. Set G = 0.5 per chain (R_f_sum = R_sum/2) so that
three chains at full drive give a combined output ≤ ±10 V.
Same configuration for R channel using second TL072 or second half of the SUM_AMP TL074.

1× TL074 serves as both L and R summing amps (halves A and B) plus two output buffers.

### IC / Component Selection

| Reference | Part Number | Package | Qty | Notes |
|---|---|---|---|---|
| SC_N (×3) | TL072CDT | SOIC-8 | 3 | Soft clip; 1 per chain; half A = L, half B = R |
| HC_N (×3) | TL072CDT | SOIC-8 | 3 | Hard clip; 1 per chain; same split |
| WF_N (×3) | TL074CDT | SOIC-14 | 3 | Wavefold; 1 per chain; A+B = L stages, C+D = R stages |
| MUX_N (×3) | CD4053 | SOIC-16 | 3 | Mode mux; 1 per chain; mechanical switch drives select pins |
| SUM_AMP | TL074CDT | SOIC-14 | 1 | L+R summing amps (halves A+B) + output buffers (halves C+D) |
| D_sc (×6) | 1N4148WS | SOD-323 | 6 | Soft clip diodes; 2 per chain (1 anti-parallel pair per channel shared) |
| Z_hc (×6) | BZX84-C5V1 | SOT-23 | 6 | Hard clip zeners; 2 per chain |
| SW_MODE_N (×3) | 3-pos switch | Panel | 3 | MODE 1, MODE 2, MODE 3 (one per chain) |
| RV_DRV_N (×3) | Log pot | 9mm | 3 | DRIVE 1, DRIVE 2, DRIVE 3 (one per chain, shared L+R) |

### Trim Pots

| Reference | Range | Purpose | Adjustment |
|---|---|---|---|
| RV_HC_THRESH_N (×3) | ±1 V | Hard clip threshold per chain | Adjust until symmetrical clip at ±5 V |
| RV_WF_GAIN_N (×3) | ×0.8–×1.2 | Wavefold input gain per chain | Fold onset at DRIVE = 50% |

### Power Draw Estimate
- 6× TL072 + 4× TL074 + 3× CD4053: ~25 mA
- +12 V: ~25 mA | −12 V: ~25 mA

### Known Circuit Challenges
- **Summing headroom**: three chains summed at high drive can exceed op-amp rail. Set summing
  gain to 0.5× per chain (attenuate by half before summing) so worst-case sum is ±7.5 V.
  Verify in VCV prototype that this gain doesn't reduce perceived loudness too much; adjust R_sum.
- **CD4053 series resistance**: ~100 Ω at ±5 V supply. Buffer each CD4053 output with a
  unity-gain op-amp half before the summing stage.
- **Post-Dist feedback routing**: each chain's output (before the summing amp) must be tapped
  and routed back to Block 3's SOURCE selector for that group. Label these tap points clearly
  on the schematic; route as shielded traces to avoid inter-chain crosstalk.
- **Diode and zener matching per chain**: use components from the same batch within each chain.
  Cross-chain matching is less critical since the chains process different formant bands.
