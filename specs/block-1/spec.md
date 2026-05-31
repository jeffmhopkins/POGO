# Block 1: Pre-Gain
Switched 1×/5× gain boost with hard clipping, plus an independent ALT path to the BP block.

DSP source: `plugin/src/dsp/PreGain.hpp`, `plugin/src/Pogo.cpp` (main 341–342; ALT 344–352; ALT→VCA→BP3 routing 439–441)

---

## 1. Intent

Block 1 gives the player a switchable input sensitivity boost before the signal enters
the VCA and filter chain. At 1× it is transparent; at 5× (~14 dB) it drives the
downstream filters harder, pushing them into self-oscillation more easily and generating
audible harmonic content when signals exceed the downstream clipping ceiling. The
clipping at ±10.5 V is not a safety measure — it is a deliberate tonal tool. A second
independent gain switch (GAIN_BP3) applies the same 1×/5× choice to the ALT path, which
injects a separate source (e.g., a raw synth voice) into **BP3 only** — the third bandpass
voice — replacing that voice's normal feed. Per the locked plugin (`Pogo.cpp:440–441`) the
ALT signal still passes **through the VCA** (driven by the same VCA amount/CV as the main
path) before reaching BP3; it bypasses **LP1 only**, not the VCA. BP1 and BP2 are untouched
by the ALT path and always take the main post-VCA/LP1 band. When the ALT jacks are unpatched,
BP3 falls back to the main band, so the ALT path is inaudible until patched.

---

## 2. Theoretical Design and Topology

> ✅ **Re-verified 2026-05-30** against the locked plugin (change 0018, 0017 follow-up).
> The gain-stage math/topology and the ALT-path *gain stage* match the plugin. The ALT
> path's downstream destination description was **corrected**: ALT goes through the VCA
> (shared control) and feeds **BP3 only**, bypassing LP1 (not the VCA). The hardware that
> realizes that downstream path — an ALT VCA cell and the BP3 input selector — is specced
> in **block-4** (2nd THAT2180 on the shared control, G5/G6) and **block-6** (BP3 input
> selector + LP1 normal), and is tracked there, not here. Block 1 builds only the ALT
> *gain stage* and emits `ALT_OUT_L/R`.

### DSP-to-analog mapping

The DSP model is:

```
GAIN=0 (1×):  V_out = V_in
GAIN=1 (5×):  V_out = clamp(5 × V_in, −10.5 V, +10.5 V)
```

The ±10.5 V clamp is the OPA1612 output swing on ±12 V rails. In hardware, the 5× gain
is set by a resistor ratio, and the hard clip is the natural output saturation of the
op-amp — no external clipping diodes needed. The DSP `clamp()` models this faithfully.

### Transfer function

In the linear region (|V_out| < 10.5 V):

```
H = +5    (non-inverting gain-5 configuration)
```

In saturation the output is clamped at ±10.5 V, producing harmonic-rich flat-top
waveforms on loud input signals. The saturation is hard (abrupt, odd-order heavy), not
soft-knee — characteristic of op-amp rail clipping.

### Topology choice and rationale

**Non-inverting amplifier, gain = 1 + R_f/R_g:**

```
Gain = 1 + 18k / 4.7k ≈ 4.83 × ≈ 5×
```

Using R_f = 18 kΩ and R_g = 4.7 kΩ gives gain = 4.83×, within 3.4% of the target 5×, and
minimizes OPA1612 current-noise contribution compared to the 12 kΩ / 47 kΩ values. The gain
error is inaudible and well within the ±5% tolerance a "5×" switch implies. At these lower
impedances, OPA1612 current noise through R_g (i_n = 1.7 pA/√Hz) contributes:
  1.7 pA × 4.7 kΩ = 8.0 nV/√Hz   (vs 20.4 nV/√Hz at 12 kΩ → 61% improvement in RTI noise)
A non-inverting topology is preferred here because:
- Preserves polarity (the DSP model multiplies by +5, not −5).
- High input impedance (suitable for driving from U1 OPA1612 output or an external jack).
- Single-stage — no polarity-restoring second stage required.

The bypass (1×) path routes around the op-amp entirely via the switch, presenting the
input directly to the next stage. This avoids any gain-of-1 op-amp buffer in the
bypass path that could add its own noise floor.

**Gain switch:** A Dailywell DW3 (2M-series DPDT ON-ON) sub-mini toggle implemented as a
**path-select** (the netlist-locked choice): the toggle common picks either the 5× amp
output or the raw input passed through directly. This faithfully matches the plugin's true
bypass at 1× (`PreGain.hpp:10–11` returns `v` unchanged), with the op-amp entirely out of
the 1× path so it adds no noise. The DPDT routes both L and R channels simultaneously with
a single toggle actuator (one pole per channel).

**ALT path (GAIN_BP3):** An identical gain stage (second OPA1612, U3) handles ALT_BP_L and
ALT_BP_R. When neither ALT_BP jack is patched, the ALT gain stage outputs 0 V and BP3 falls
back to the main band (the BP3 input selector, in block-6, holds on the main feed). R
normalling on the ALT path mirrors Block A: if only ALT_BP_L is patched, ALT_BP_R is
normalized to ALT_BP_L. **Asymmetric edge case** (`Pogo.cpp:440–441`): if *only* ALT_BP_R is
patched (L unpatched), BP3's left channel stays on the main band while its right channel
takes the ALT source — so the two BP3 channels can be driven from different sources. The BP3
input selector must therefore be **per-channel**, gated by each channel's ALT-connected
state, not a single stereo switch.

### IC selection: OPA1612 vs. TL072

OPA1612 is specified (not TL072 or NE5532D) because at 5× gain the output-referred noise
floor rises by 14 dB relative to Block A. The OPA1612's 1.1 nV/√Hz is well below the
Johnson noise of R_g (4.7 kΩ → 8.8 nV/√Hz), giving the lowest practical noise floor.
Quiescent current is 5.5 mA per package — lower than NE5532D's 8 mA with better noise,
making OPA1612 strictly superior here. It is already used in blocks 5/6/7/8, consolidating
the BOM by one part number.

### Hardware deviations from DSP model

The DSP model switches instantaneously between 1× and 5×. In hardware, the mechanical
switch produces a transient click (charge redistribution on the feedback network). A
10 nF capacitor across R_f slows the gain edge but this is not modeled in DSP and is a
hardware-only consideration. The clip level varies slightly with temperature and load;
the DSP specifies ±10.5 V as nominal, consistent with OPA1612 datasheet typical figures.

→ References `aux/utility/unity-buffer/spec.md`

---

## 3. Physical Design

> ✅ **Re-verified 2026-05-30** against the locked plugin (change 0018). Gain-stage
> component values, switch (path-select), ALT gain stage, and protection match the §2
> model. ALT downstream routing (VCA + BP3 selector) is realized in block-4 / block-6 and
> tracked there. Documentation-only corrections applied here (ALT destination, aux refs).

### Component values and derivations

**Gain resistors (R3 = R_g, R4 = R_f): 4.7 kΩ, 18 kΩ (each ×2 channels)**

Gain = 1 + R_f / R_g = 1 + 18k / 4.7k = 4.83 ≈ 5×

Standard E24 values. 1% tolerance resistors required: L/R matching within 0.1 dB,
and lower R_g reduces OPA1612 current-noise contribution at the inverting input.

Previous values (12 kΩ / 47 kΩ) gave G = 4.92×; updated for noise — see signal-routing
note below. Both give gain within 5% of 5×.

**Op-amp (U2, U3): OPA1612, SOIC-8**
- U2: main path L+R (two halves of one dual op-amp).
- U3: ALT path L+R (second dual op-amp package).
- Supply decoupling: 100 nF X7R 0603 on each supply pin, placed within 2 mm of IC.
- Iq = 2.75 mA/ch × 2 = 5.5 mA/pkg; P_diss = 24 V × 5.5 mA = 132 mW — safe in SOIC-8.

**Gain switches (SW1 = GAIN_MAIN, SW2 = GAIN_BP3): Dailywell DW3 (2M DPDT ON-ON) toggle**
- One pole per channel (L and R switched simultaneously).
- Switch selects: gain-stage output (5×) vs. direct input bypass (1×).
- PCB-mount sub-mini toggle, 2.54mm pin pitch, 10-48 UNS bushing (Ø6.00mm) through a Ø4.95mm panel hole, 2-position.

### Signal routing

Main path:
```
Block-A outL → R3_L (4.7 kΩ) → U2A (−) input
                               U2A (+) = Block-A outL (non-inv.)
                               U2A output → R4_L (18 kΩ) → U2A (−) [feedback]
SW1 position A: U2A output → pgL
SW1 position B: Block-A outL → pgL (bypass)

Same topology for R channel on U2B.
pgL/pgR → Block VCA
```

ALT path:
```
J_ALT_L → R38 (100 Ω) → D8 clamp → U3A(+) non-inverting amp → SW2 → ALT_OUT_L
J_ALT_R → R39 (100 Ω) → D9 clamp → U3B(+) non-inverting amp → SW2 → ALT_OUT_R
ALT_OUT_L/R → [block-4 ALT VCA cell, shared control] → [block-6 BP3 per-channel
              input selector] → BP3 only.  Bypasses LP1, NOT the VCA.
```

ALT inputs carry the standard POGO jack protection (100 Ω series + BAT54S clamp to
±12 V, per `aux/utility/cv-protection/spec.md` — every jack input). J4 (ALT_BP_R) tip-switch
normalls to the protected ALT_L input node so an unpatched R channel duplicates L
through R's own identical gain stage and the shared toggle (added 2026-05-29).

### Calibration points

No calibration trimmer is required. Resistor tolerances at 1% give < 0.2 dB channel
matching, which is acceptable for an input gain stage. If tighter matching is required,
substitute 0.1% resistors for R3/R4.

### Trim pots

None. The gain ratio is fixed at 5×; the intentional clip is the OPA1612 rail swing.

### Board assignment

Audio board. Place U2 and U3 close to the panel jacks (Block A) to minimize trace
length carrying unshielded pre-gain signals.

### Power Draw Estimate

- 2× OPA1612 (U2, U3, dual SOIC-8): ~5.5 mA each = ~11 mA  (Iq = 2.75 mA/ch × 2)
- **+12V: ~11 mA | −12V: ~11 mA**

→ References `aux/utility/unity-buffer/spec.md` for the op-amp gain-stage ASCII schematic primitive.
(The aux/ library is ASCII-only — there are no SVG schematic files.)

---

## 4. Component Requirements

Component set: see the generated BOM `kicad/pogo-bom.csv` (rows with `Block = block-1`),
sourced from `specs/components.yaml` (the per-ref design manifest) and enriched by the
`components/` registry (MPN, footprint, datasheet). Verification status: `specs/STATUS.md`.
