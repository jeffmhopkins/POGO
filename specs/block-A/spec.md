# Block A: Input Buffers
Unity-gain stereo input stage that clamps, protects, and normalizes R to L when unpatched.

DSP source: `plugin/src/dsp/InputBuffer.hpp`, `plugin/src/Pogo.cpp` (lines 344–348)

---

## 1. Intent

Block A is the first thing the outside world touches. Its job is purely protective and
organizational: accept up to two TS audio jacks, absorb any cable impedance mismatch,
clamp destructively high voltages before they can reach the signal chain, and present a
low-impedance, unity-gain copy of each input to Block 1. When only a mono source is
patched into the L jack, the R channel silently duplicates L so every downstream stereo
block receives a coherent pair without the user needing to manually mult. The user hears
nothing attributable to this block under normal conditions; its audible contribution is the
absence of buzzing, clipping artifacts from external overdrive, and the convenience of
transparent mono-to-stereo normalling.

---

## 2. Theoretical Design and Topology

### DSP-to-analog mapping

The DSP model is a single-line hard clamp:

```
V_out = clamp(V_in, −11.0 V, +11.0 V)
```

The ±11 V limit reflects the OPA1612 output swing on ±12 V rails (typ. ±11 V). In
hardware the clamp is not a software limit but a consequence of op-amp output saturation
combined with upstream Schottky diode protection. The analog realization therefore maps
directly: the clamp is the op-amp's natural output ceiling, and the series resistor plus
BAT54S diodes protect the op-amp input before the rail is ever reached.

### Transfer function

In the linear region (|V_in| < 11 V):

```
H(s) = 1      (ideal voltage follower, unity gain, zero phase shift at audio frequencies)
```

The OPA1612 has a gain-bandwidth product of ~80 MHz; configured as a voltage follower
(100% feedback) the −3 dB corner is well above 1 MHz, invisible to audio.

### Topology choice and rationale

Non-inverting voltage follower (gain = +1). Chosen because:
- Unity gain — no resistor ratio to trim or drift.
- Non-inverting — preserves signal polarity; no phantom inversion to track through the chain.
- Lowest possible output impedance for driving the next stage's 10 kΩ input.
- OPA1612 selected for noise floor: 1.1 nV/√Hz vs. TL072's 18 nV/√Hz and LM4562's 2.7 nV/√Hz.
  Because Block A sits at the head of the entire chain, its noise contribution is amplified by
  every subsequent gain stage. OPA1612 is the superior choice: it has lower noise than LM4562
  and draws half the quiescent current (2.75 mA/ch vs. 5.5 mA/ch), avoiding SOIC-8 thermal
  stress (LM4562 at 11 mA total = 264 mW in SOIC-8 exceeds the ~200 mW conservative limit).

### Input protection network

Each jack feeds:

```
jack tip ─── 100 Ω ─── BAT54S (to +12V and −12V) ─── op-amp (+) input
```

The 100 Ω series resistor limits the peak current through the Schottky clamp diodes
during an extreme overvoltage event (e.g., patching a powered output from a different
module that is at rail). BAT54S forward voltage ≈ 0.3 V at 1 mA; with the 100 Ω
series resistor, an input of +15 V results in only ~28 mA through the diode, safely
within the BAT54S 200 mA continuous rating.

### R normalling

The R jack carries a tip-switching contact. When the R jack is empty, the tip-switch
ring connects the R buffer's (+) input to the output of the L buffer. When a cable is
inserted into R, the tip-switch opens and the R channel becomes independent. This is a
passive mechanical normalling; no additional circuitry is required.

### Hardware deviations from DSP model

The DSP clamp is symmetric at exactly ±11.0 V. In hardware the OPA1612 output swing is
a function of load current and rail accuracy; it typically saturates at ±10.8 V to
±11.2 V. This is consistent with the DSP spec and requires no correction. There is no
intentional nonlinearity in this block.

→ References `aux/unity-buffer.md`, `aux/cv-input-protection.md`

---

## 3. Physical Design

### Component values and derivations

**Series protection resistors (R1, R2): 100 Ω**
- Chosen to limit diode clamp current to < 50 mA at ±17 V worst-case (e.g., +5 V bench
  supply mis-patch): I = (17 − 0.3) / 100 = 167 mA → borderline; use 150 Ω if desired.
  100 Ω is the community standard for Eurorack and keeps insertion loss negligible:
  voltage divider with a 1 MΩ op-amp input = 0.00001 dB attenuation.

**Clamp diodes (D1, D2): BAT54S (dual Schottky, SOT-23)**
- BAT54S contains two matched Schottky diodes in a single SOT-23. Anode of D_upper
  connects to signal node; cathode to +12 V. Cathode of D_lower connects to −12 V;
  anode to signal node. This holds the op-amp (+) input within ±(12 + 0.3) = ±12.3 V.

**Op-amp (U1): OPA1612, SOIC-8**
- Dual: one package serves both L and R channels.
- Configured as voltage followers: (+) = signal input, (−) tied to output, no external
  resistors.
- Supply decoupling: 100 nF X7R 0603 from each supply pin (V+ and V−) to ground,
  placed within 2 mm of IC pins.
- Iq = 2.75 mA/channel × 2 = 5.5 mA total; P_diss = 24 V × 5.5 mA = 132 mW — within
  SOIC-8 practical limit.

### Signal routing

```
J1 (L_IN) → R1 (100 Ω) → D1 clamp → U1A (+) → U1A output → Block 1 inL
J2 (R_IN) → R2 (100 Ω) → D2 clamp → U1B (+) → U1B output → Block 1 inR
J2 (empty) → tip-switch normalling → routes U1A output to U1B (+) input
```

### Calibration points

No calibration is needed for this block. Voltage followers have no adjustable gain.
The ±11 V clamp is set by the OPA1612 rail swing — a property of the IC, not a tunable
parameter.

### Trim pots

None.

### Board assignment

Audio board. Both channels are on a single SOIC-8. Place near the panel edge where the
jacks are located to keep input traces short and shielded from digital noise.

### Power Draw Estimate

- 1× OPA1612 (U1, dual SOIC-8): ~6 mA  (Iq = 2.75 mA/channel × 2 channels = 5.5 mA)
- **+12V: ~6 mA | −12V: ~6 mA**

→ References `aux/unity-buffer.svg` for op-amp follower schematic primitive.

---

## 4. Component Requirements

| Ref | Part | Package | Value | Qty | Board | Block | Function |
|---|---|---|---|---|---|---|---|
| U1 | OPA1612 | SOIC-8 | — | 1 | audio | block-A | Input buffers L+R (dual op-amp); 1.1 nV/√Hz |
| D1 | BAT54S | SOT-23 | — | 1 | audio | block-A | L input protection clamp ±12 V |
| D2 | BAT54S | SOT-23 | — | 1 | audio | block-A | R input protection clamp ±12 V |
| R1 | resistor | 0603 | 100 Ω | 1 | audio | block-A | L series input protection |
| R2 | resistor | 0603 | 100 Ω | 1 | audio | block-A | R series input protection |
| C1 | cap, X7R | 0603 | 100 nF | 2 | audio | block-A | OPA1612 supply decoupling (+12 V and −12 V) |
| J1 | PJ301M-12 | panel | — | 1 | panel | block-A | L_IN jack |
| J2 | PJ301M-12 | panel | — | 1 | panel | block-A | R_IN jack (tip-switching normalling to L) |
