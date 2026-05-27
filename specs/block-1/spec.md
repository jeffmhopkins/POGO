# Block 1: Pre-Gain
Switched 1×/5× gain boost with hard clipping, plus an independent ALT path to the BP block.

DSP source: `plugin/src/dsp/PreGain.hpp`, `plugin/src/Pogo.cpp` (lines 350–362)

---

## 1. Intent

Block 1 gives the player a switchable input sensitivity boost before the signal enters
the VCA and filter chain. At 1× it is transparent; at 5× (~14 dB) it drives the
downstream filters harder, pushing them into self-oscillation more easily and generating
audible harmonic content when signals exceed the downstream clipping ceiling. The
clipping at ±10.5 V is not a safety measure — it is a deliberate tonal tool. A second
independent gain switch (GAIN_BP3) applies the same 1×/5× choice to the ALT path, which
feeds the Triple Bandpass block directly, bypassing the VCA and LP1 entirely. This lets
the player inject a separate source (e.g., a raw synth voice) into the BP formant section
without touching the main signal path.

---

## 2. Theoretical Design and Topology

### DSP-to-analog mapping

The DSP model is:

```
GAIN=0 (1×):  V_out = V_in
GAIN=1 (5×):  V_out = clamp(5 × V_in, −10.5 V, +10.5 V)
```

The ±10.5 V clamp is the NE5532 output swing on ±12 V rails. In hardware, the 5× gain
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

Using R_f = 18 kΩ and R_g = 4.7 kΩ gives gain = 4.83×, within 3.4% of the target 5×, and halves
the NE5532D current-noise contribution compared to the 12 kΩ / 47 kΩ values. The gain error is
inaudible and well within the ±5% tolerance a "5×" switch implies. At these lower impedances,
NE5532D current noise through R_g (i_n = 0.7 pA/√Hz) contributes:
  0.7 pA × 4.7 kΩ = 3.3 nV/√Hz   (vs 8.4 nV/√Hz at 12 kΩ → 61% improvement in RTI noise)
A non-inverting topology is preferred here because:
- Preserves polarity (the DSP model multiplies by +5, not −5).
- High input impedance (suitable for driving from U1 LM4562 output or an external jack).
- Single-stage — no polarity-restoring second stage required.

The bypass (1×) path routes around the op-amp entirely via the switch, presenting the
input directly to the next stage. This avoids any gain-of-1 op-amp buffer in the
bypass path that could add its own noise floor.

**Gain switch:** A DPDT slide switch shorts R_g to ground (feedback to inverting input)
in the gain position, or opens the feedback network to connect the op-amp output directly
back to the inverting input (unity-gain follower). Alternatively — and simpler for
layout — the switch selects between two signal paths: the gain stage output vs. the
input passed through directly. The DPDT routes both L and R channels simultaneously
with a single switch actuator (one pole per channel).

**ALT path (GAIN_BP3):** An identical stage (second NE5532D) handles ALT_BP_L and
ALT_BP_R. When neither ALT_BP_L nor ALT_BP_R is patched, the alt path outputs 0 V
and the BP block ignores it (falls back to LP1 output). R normalling on the ALT path
mirrors Block A: if only ALT_BP_L is patched, ALT_BP_R is normalized to ALT_BP_L.

### IC selection: NE5532D vs. TL072

NE5532D is specified (not TL072) because at 5× gain the output-referred noise floor
rises by 14 dB relative to Block A. The NE5532 has an equivalent input noise of
~5 nV/√Hz vs. TL072's ~18 nV/√Hz, keeping the accumulated noise contribution
acceptable. Quiescent current is ~8 mA per rail per package — higher than TL072 but
appropriate for an audio-quality gain stage.

### Hardware deviations from DSP model

The DSP model switches instantaneously between 1× and 5×. In hardware, the mechanical
switch produces a transient click (charge redistribution on the feedback network). A
10 nF capacitor across R_f slows the gain edge but this is not modeled in DSP and is a
hardware-only consideration. The clip level varies slightly with temperature and load;
the DSP specifies ±10.5 V as nominal, consistent with NE5532 datasheet typical figures.

→ References `aux/unity-buffer.md`

---

## 3. Physical Design

### Component values and derivations

**Gain resistors (R3 = R_g, R4 = R_f): 4.7 kΩ, 18 kΩ (each ×2 channels)**

Gain = 1 + R_f / R_g = 1 + 18k / 4.7k = 4.83 ≈ 5×

Standard E24 values. 1% tolerance resistors required: L/R matching within 0.1 dB,
and lower R_g reduces NE5532D current-noise contribution at the inverting input.

Previous values (12 kΩ / 47 kΩ) gave G = 4.92×; updated for noise — see signal-routing
note below. Both give gain within 5% of 5×.

**Op-amp (U2, U3): NE5532D, SOIC-8**
- U2: main path L+R (two halves of one dual op-amp).
- U3: ALT path L+R (second dual op-amp package).
- Supply decoupling: 100 nF X7R 0603 on each supply pin, placed within 2 mm of IC.

**Gain switches (SW1 = GAIN_MAIN, SW2 = GAIN_BP3): 2PDT slide switch**
- One pole per channel (L and R switched simultaneously).
- Switch selects: gain-stage output (5×) vs. direct input bypass (1×).
- Panel-mount, horizontal slide, 2-position.

### Signal routing

Main path:
```
Block-A outL → R3_L (12 kΩ) → U2A (−) input
                               U2A (+) = Block-A outL (non-inv.)
                               U2A output → R4_L (47 kΩ) → U2A (−) [feedback]
SW1 position A: U2A output → pgL
SW1 position B: Block-A outL → pgL (bypass)

Same topology for R channel on U2B.
pgL/pgR → Block VCA
```

ALT path:
```
J_ALT_L → R_ALT_g (12 kΩ) → U3A non-inverting amp → SW2 → altL
J_ALT_R → R_ALT_g (12 kΩ) → U3B non-inverting amp → SW2 → altR
altL/altR → Block BP (direct input, bypassing VCA and LP1)
```

### Calibration points

No calibration trimmer is required. Resistor tolerances at 1% give < 0.2 dB channel
matching, which is acceptable for an input gain stage. If tighter matching is required,
substitute 0.1% resistors for R3/R4.

### Trim pots

None. The gain ratio is fixed at 5×; the intentional clip is the NE5532 rail swing.

### Board assignment

Audio board. Place U2 and U3 close to the panel jacks (Block A) to minimize trace
length carrying unshielded pre-gain signals.

→ References `aux/unity-buffer.svg` for op-amp gain stage schematic primitive.

---

## 4. Component Requirements

| Ref | Part | Package | Value | Qty | Board | Block | Function |
|---|---|---|---|---|---|---|---|
| U2 | NE5532D | SOIC-8 | — | 1 | audio | block-1 | Main gain amp, L+R channels |
| U3 | NE5532D | SOIC-8 | — | 1 | audio | block-1 | ALT BP gain amp, L+R channels |
| R3 | resistor 1% | 0603 | 4.7 kΩ | 2 | audio | block-1 | R_g main gain stage (×2 ch); 1% for L/R match + low i_n×R noise |
| R4 | resistor 1% | 0603 | 18 kΩ | 2 | audio | block-1 | R_f main gain stage (×2 ch); G = 4.83× ≈ 5× |
| R5 | resistor 1% | 0603 | 4.7 kΩ | 2 | audio | block-1 | R_g ALT gain stage (×2 ch) |
| R6 | resistor 1% | 0603 | 18 kΩ | 2 | audio | block-1 | R_f ALT gain stage (×2 ch) |
| SW1 | 2PDT slide switch | panel | — | 1 | panel | block-1 | GAIN_MAIN 1×/5× |
| SW2 | 2PDT slide switch | panel | — | 1 | panel | block-1 | GAIN_BP3 1×/5× (ALT path) |
| C2 | cap, X7R | 0603 | 100 nF | 4 | audio | block-1 | NE5532 supply decoupling (2 ICs × 2 pins) |
| J3 | PJ301M-12 | panel | — | 1 | panel | block-1 | ALT_BP_L input jack |
| J4 | PJ301M-12 | panel | — | 1 | panel | block-1 | ALT_BP_R input jack (normalled to ALT_BP_L) |
