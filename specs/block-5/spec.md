# Block 5: LP Filter 1
First 2-pole lowpass filter in the signal chain, with stereo tilt for independent L/R cutoff spread.

DSP source: `plugin/src/dsp/LPFilter.hpp`, `plugin/src/Pogo.cpp` (lines 391–400)

---

## 1. Intent

Block 5 is the first voltage-controlled tonal filter in the chain. It receives the signal from the
pre-LP1 VCA (Block VCA) and applies a 2-pole lowpass response with independent per-channel cutoff
control for stereo spread. At low resonance and high cutoff the block is transparent. As the cutoff
sweeps down, high-frequency content rolls off at 12 dB/oct. At high resonance a peak emerges at the
cutoff frequency; at maximum resonance the filter self-oscillates, producing a sine tone that tracks
1V/oct via the expo converter — making LP1 a playable oscillator.

The LP1_TILT parameter is the key differentiator from LP2 and HP: it creates stereo width by
spreading L and R cutoffs symmetrically in opposite directions. Positive tilt raises the L channel
cutoff while simultaneously lowering the R channel cutoff by the same amount, producing a living
stereo image from a mono source. At center (tilt = 0) both channels run identical cutoffs.

LP1's output feeds Block BP unless the ALT_BP_L/R jacks are patched, in which case the ALT signal
bypasses VCA and LP1 entirely and enters BP directly.

---

## 2. Theoretical Design and Topology

> ✅ **Re-verified 2026-05-30** against the locked plugin (change 0018; body rewritten
> 2026-05-29). Topology matches plugin ground truth: 2-pole Simper SVF, `f0 = 632·2^cutoffV`
> V/oct, per-channel THAT340 expo for true stereo tilt (L = +tilt, R = −tilt), and the
> resonance reaches **self-oscillation** (no Q cap) — matching the plugin. No behavioral edits.

### DSP-to-analog mapping

The DSP model (LPFilter.hpp) implements Andrew Simper's trapezoidal-integrated 2-pole SVF. The
discretization relationship `g = tan(π·f₀/fs)` is the bilinear pre-warp; inverting it yields the
analog prototype cutoff frequency:

```
ω₀_analog = g_m / C      (OTA-C integrator unity-gain frequency)
f₀ = ω₀ / (2π) = g_m / (2π·C)
```

The DSP frequency law `f₀ = f_ref × 2^(cutoffV)` with `f_ref = 632 Hz` maps directly to the
exponential V/oct converter:

```
I_abc = I_ref × exp(V_ctrl / V_T)    → I_abc doubles per +1V
g_m = I_abc / (2·V_T)                → g_m doubles per +1V
ω₀ = g_m / C                        → f₀ doubles per +1V (one octave) ✓
```

At f_ref = 632 Hz with C = 47 nF (C0G):

```
g_m_ref = f_ref × 2π × C = 632 × 2π × 47nF = 186.3 µS
I_abc_ref = g_m_ref × 2·V_T = 186.3µS × 52mV = 9.69 µA
```

### Transfer function (analog prototype)

Second-order lowpass (see `aux/aux-ota-c-svf.md`):

```
H_LP(s) =        ω₀²
          ──────────────────────────
          s² + (ω₀/Q)·s + ω₀²
```

DSP Q law:  `Q = 0.5 × 4000^resParam`  (resParam ∈ [0,1])

```
resParam = 0.0 → Q = 0.50  (overdamped)
resParam = 0.5 → Q ≈ 31.6
resParam = 1.0 → Q ≈ 2000  (near self-oscillation)
```

Hardware Q law:  `Q = 52mV / (I_abc_q × R_in)`  with R_in = 100 kΩ

```
I_abc_q = 0.74 µA → Q = 0.70  (Butterworth, flat passband)
I_abc_q = 0.26 µA → Q = 2.00
I_abc_q → 0       → Q → ∞   (self-oscillation)
```

**Accepted Q deviations:**
- Q_min: DSP Q_min = 0.5 at resParam = 0; hardware Q_min = 0.70 (Butterworth) because
  Iabc_q cannot fall below ~0.74 µA without LM13700 low-current nonlinearity. Hardware
  has no slightly-overdamped region; CCW-stop position yields maximally flat response.
- Q_max: the plugin self-oscillates (Q → 2000, a playable 1 V/oct-tracking sine — see §1).
  Hardware **must reach self-oscillation to match the plugin**: as V_res rises, Iabc_q → 0
  and Q → ∞. The "~50" figure is the Q at the *onset* of sustained oscillation (Iabc_q
  < 0.01 µA, aux-q-control.md), **not** a ceiling. `RV5` (RV_QMAX) trims V_bias so that
  full-CW RES lands just past the self-oscillation onset (clean, stable sine). There is
  **no intentional Q cap** — an earlier "Q limited to ~50 for stability" note was wrong
  and is superseded; capping at Q≈50 would be a real behavioral divergence from the plugin.
The Q_min deviation is accepted; the self-oscillation ceiling is matched. Musical behavior
(sweep, peak, self-oscillation) is preserved; the exact Q floor and self-osc onset are
calibration targets (RV5), not tonal defects.

The *mid-sweep* Q curve also differs in shape: the plugin uses `Q = 0.5·4000^resParam`
(exponential in the knob), while the hardware Q ≈ `0.52 / Iabc_q(µA)` is hyperbolic in the
control current (approximately exponential at high Q). Only the endpoints (Q_min and the
self-oscillation onset) are matched by calibration; the intermediate resonance-vs-rotation
curve is an approximation, not bit-exact — an accepted DSP↔analog deviation.

### Stereo tilt

From Pogo.cpp lines 391–400:

```cpp
float lp1TiltV = params[LP1_TILT_PARAM].getValue() * 5.f   // [−1,+1] knob → ±5 V/oct
                 + modDest(LP1_TILT_INPUT, LP1_TILT_ATT_PARAM);
float bandL = lp1L.process(vcaOutL, lp1FreqBase + lp1TiltV, lp1Res, fs);
float bandR = lp1R.process(vcaOutR, lp1FreqBase - lp1TiltV, lp1Res, fs);
```

L and R cutoffs diverge symmetrically around the shared base frequency:

```
f_L = 632 Hz × 2^(V_freq + V_tilt)
f_R = 632 Hz × 2^(V_freq − V_tilt)
```

At V_tilt = +1V: f_L is one octave above f_R. At V_tilt = +5V: five-octave spread.

### Hardware tilt implementation (FINALIZED 2026-05-29: per-channel expo)

Stereo tilt requires independent L/R cutoff, which a single expo core cannot produce (one
THAT340 = one Iabc = one frequency). So LP1 uses **two expo converters — one per channel**
(U14 = L, U64 = R). The tilt CV arrives at a summing node; an inverting buffer (TL072 U13-A,
G = −1) generates −V_tilt from +V_tilt. The **L** expo base receives V_freq + V_tilt; the **R**
expo base receives V_freq − V_tilt → `f_L`/`f_R` diverge by ±V_tilt octaves (exact, octave-
accurate). `RV6` (RV_LP1_TILT_NULL) nulls the center-detent L/R mismatch. The earlier
"single shared THAT340 with per-channel V_ctrl summers" description was electrically
impossible (one transistor base cannot hold two control voltages) and is superseded;
`aux/aux-expo-converter.md` flagged this as the Phase-3R decision, now resolved.

Note: the LM13700 integrator Darlington output buffers (used as the v1/v2 state-variable
outputs) require emitter pulldown resistors to V− (R68–R71, 10 kΩ) — added 2026-05-29; the
prior spec/BOM omitted them, which would have left the buffers unable to sink current.

See `aux/aux-ota-c-svf.md`, `aux/aux-expo-converter.md`, `aux/aux-q-control.md`.

### ALT path bypass

When ALT_BP_L and/or ALT_BP_R are patched, Block BP receives the ALT signal directly. LP1 and
the VCA are bypassed for those channels. LP1 continues to process its input (the VCA output)
but its output is ignored in the signal chain until the ALT jacks are unpatched.

---

## 3. Physical Design

> ✅ **Re-verified 2026-05-30** against the locked plugin (change 0018). Component values,
> per-channel expo (U14/U64), shared U9/U10 Q-VCAs (co-owned by block-8), and the SVF netlist
> verified consistent with §2 and the plugin. Doc corrections only (banner, Q-curve note,
> RV5/RV6 values).

> 🔧 **Change 0020 (CV-conditioning fixes) — the netlist now reflects these; values updated here:**
> - **§A Expo V/oct divider (C1):** the expo base previously saw the V/oct CV through series R only
>   (no shunt → railed). Added a base divider: `R_VOCT` (R63/R66) **47k→49.9k** + a **Vishay TFPT
>   1k tempco** shunt (R231/R232) base→GND. Centers 17.92 mV/oct (V_T·ln2) at mid-trim (SPICE
>   `expo_voct.cir`). The tempco (+4110 ppm/K) is the temp-comp the THAT340 does NOT provide internally.
> - **§B Stereo tilt (C3):** tilt now sums **passively** with V_freq at the tempco-shunted base via an
>   equal series R — `R55/R56` **100k→54.9k** (=R_VOCT+RV_mid → 1:1 octave weight; SPICE
>   `lp1_tilt_passive.cir`: freq=tilt=17.57 mV/V). **No op-amp summer needed.** U13-A still makes −V_tilt
>   for the R channel; RV6 null retained.
> - **§C OTA state-variable tap (H5):** v1/v2 now tap the **unbuffered** LM13700 OTA outputs (pins 5/12),
>   not the Darlington buffers (8/9) which injected ~1.26 V temp-dependent DC into the next OTA input
>   (SPICE `ota_svf_loop.cir`). Buffer emitter-pulldowns R68–R71 removed; buffer pins unused. f_ref
>   unchanged (cap stays on the OTA output node).
> - **§D Q-cell R_Iabc (M5):** `R57/R58` **1M→100k** — the LM13700 Iabc pin sits ~2·V_BE above V−
>   (≈ −10.8 V, not GND), so 1 MΩ delivered ~14× too much I_abc. (The matching IRES_AMP negative-V_ires
>   drive + clamp polarity is a trim-backed Phase-3R bring-up item — see change 0020 §D.)

### Component derivations

**Integrator capacitors C1, C2 (per channel, ×2 channels = 4 total):**

```
Target f_ref = 632 Hz at I_abc = 9.69 µA
g_m = 9.69µA / 52mV = 186.3 µS
C = g_m / ω₀_ref = 186.3µS / (2π × 632) = 47.0 nF → use 47 nF C0G/NP0 0603
```

C0G/NP0 mandatory — X7R drifts with temperature and voltage, causing audible pitch drift.

**Input resistors R_IN_SUM (per channel):** 100 kΩ — sets the g_m reference scale and provides
the virtual-ground termination for the SUM_AMP.

**Linearizing resistors R_LIN_A, R_LIN_B (per OTA cell, per channel):** 1 kΩ — extends the OTA
linear range from ±26 mV to ±(26mV + I_abc × 1kΩ/2) ≈ ±31 mV at 10 µA.

**I_ref network R_IREF_A + RV_REF:** 1 MΩ (R_IREF_A, fixed 0603) in series with 500 kΩ (RV_REF, rheostat)
gives R_total 1000 kΩ–1500 kΩ, midpoint 1250 kΩ at pot center → I_ref ≈ 9.6 µA.
Calibration target 9.69 µA requires R_total = 1238 kΩ → RV_REF ≈ 238 kΩ (47.6% of travel).
Covers worst-case component stack (R_IREF_A ±5% + C_int ±5%) within pot range. See aux-expo-converter.md.

**Q control resistors R_Iabc:** 100 kΩ per channel (R57/R58; change 0020 §D/M5, was 1 MΩ) —
converts the IRES_AMP output into I_abc_q across the LM13700 I_abc pin (≈ −10.8 V). With the
IRES_AMP output ≈ 70 mV above the pin, I_abc_q ≈ 0.7 µA → Q ≈ 0.74 (near-Butterworth). The SPICE
`q_cell.cir` deck derives Q from the live 100 kΩ netlist value (binds R57/R58), not this prose.

**Tilt summer resistors (R_TILT_SUM_L, R_TILT_SUM_R, R_TILT_INV):** 100 kΩ each — the tilt
pot wiper (+V_tilt) feeds L expo summer directly. The inverting half of TL072 (G = −1) generates
−V_tilt for the R expo summer. Summing resistors set 1:1 ratio between V_freq and ±V_tilt at
each expo input.

**Trim pot RV_LP1_TILT_NULL:** 10 kΩ Bourns 3224W SMD — nulls the center-detent tilt offset
so both channels match at tilt = 0. Adjust for equal L and R cutoff (matching sine frequency
at self-oscillation).

### Calibration trim pots

| Ref | Value | Purpose | Procedure |
|---|---|---|---|
| RV_REF | 500 kΩ | f_ref calibration | Apply 0V CV; trim until f₀ = 632 Hz; in series with R_IREF_A 1 MΩ; set to ~238 kΩ (47.6% CW) |
| RV_1VOCT | 20 kΩ | 1V/oct tracking | Apply +5V CV; trim until f₀ = 632 × 2⁵ = 20.2 kHz |
| RV_QMAX | 100 kΩ | Self-osc onset | Turn RES to max; trim for clean stable self-oscillation at full CW |
| RV_LP1_TILT_NULL | 10 kΩ | Tilt center null | Tilt knob at center; trim until L and R cutoffs match |

### Signal routing

```
Block VCA out L  →  LP1_L SVF (SUM_AMP-A + OTA-A1 + OTA-A2)  →  LP1 out L  →  Block BP in L
Block VCA out R  →  LP1_R SVF (SUM_AMP-B + OTA-B1 + OTA-B2)  →  LP1 out R  →  Block BP in R

ALT_BP_L patched: LP1 out L is bypassed; ALT_BP_L → Block BP in L
ALT_BP_R patched: LP1 out R is bypassed; ALT_BP_R → Block BP in R (normalles to ALT_BP_L if only L patched)
```

Tilt routing:

```
LP1_TILT knob wiper  →  R_TILT_SUM_L (100kΩ) →  L expo summer (+V_tilt addend)
                     →  TL072 G=−1 inv buffer  →  R_TILT_SUM_R (100kΩ) →  R expo summer (−V_tilt addend)
LP1_TILT_INPUT jack + LP1_TILT_ATT attenuverter  →  same tilt bus (sums into V_tilt before distribution)
```

### Board assignment

Audio board. Place LP1_L and LP1_R SVF circuits adjacent to Block VCA outputs. EXPO_LP1
(THAT340) placed centrally between L and R expo summer inputs to equalize trace lengths for
I_abc routing. U9/U10 (the shared LP1/LP2 Q-VCAs) placed between the LP1 and LP2 OTA sections.

### Power Draw Estimate

- 2× LM13700M (LP1 L/R integrators): ~4 mA × 2 = 8 mA  (TI: 4 mA typ per package)
- 2× LM13700M U9/U10 (shared LP1+LP2 Q-VCAs, counted here): ~4 mA × 2 = 8 mA
- 2× OPA1612 (SUM_AMP L/R, dual SOIC-8): 5.5 mA × 2 = 11 mA  (Iq = 2.75 mA/channel × 2 ch/IC)
- 1× TL072CDT (IRES_AMP + tilt inverter): ~3 mA  (TI: 1.4 mA/ch × 2 = 2.8 mA)
- 2× THAT340S14-U (EXPO_LP1 L = U14, R = U64; per-channel for true tilt): ~1 mA × 2 = 2 mA
- **+12V: ~32 mA | −12V: ~32 mA**  (8+8+11+3+2; the 2nd expo adds ~1 mA vs the prior 1-expo tally)

Note: U9/U10 are shared with block-8 (they provide LP2 Q on cell B). They are counted once
here (block-5); block-8's power estimate excludes them accordingly.

---

## 4. Component Requirements

Component set: see the generated BOM `kicad/pogo-bom.csv` (rows with `Block = block-5`),
sourced from `specs/components.yaml` (the per-ref design manifest) and enriched by the
`components/` registry (MPN, footprint, datasheet). Verification status: `specs/STATUS.md`.

**Shared resource:** this block **hosts** the LP1/LP2 resonance Q-VCAs `U9` (L) / `U10` (R) —
co-owned by block-8 (`components.yaml`: `block: [block-5, block-8]`, `shared: true`). Cell A = LP1 Q
(internal here); cell B = LP2 Q, reached by block-8 via boundary nets `LP2_V1/SUMINV/QIABC_*`.
