# Block LFO: Dual Triangle-Wave LFO

## Status
- Phase 1R (Extract from code): [ ] complete
- Phase 2R (Analog model): [ ] complete
- Phase 3R (Circuit design): [ ] complete

---

## Phase 1R: Functional Specification (extracted from plugin code)

### Source
`plugin/src/dsp/LFO.hpp`, `plugin/src/Pogo.cpp`

### Overview
Dual independent triangle-wave LFO providing:
- A general-purpose modulation source that normalizes into the mod bus
- A standalone output-only second LFO

Replaces the 40HP envelope follower (Block 2) as the default mod bus source.

### Parameters

| Name | Enum | Range | Default | Taper | Description |
|---|---|---|---|---|---|
| LFO 1 Rate | `LFO1_RATE_PARAM` | 0–1 | 0.3 | Exponential | Frequency of LFO1 |
| LFO 2 Rate | `LFO2_RATE_PARAM` | 0–1 | 0.3 | Exponential | Frequency of LFO2 |

**Rate law:** `f_Hz = 0.05 × 400^param`
- param=0.0 → 0.05 Hz (~20 s period)
- param=0.3 → ~0.7 Hz (~1.4 s period)
- param=0.5 → ~1.0 Hz (1 s period)
- param=1.0 → 20 Hz (audio-rate LFO territory)

### Waveform
Triangle wave computed from a normalized phase accumulator:
```
phase ∈ [0, 1)
phase < 0.5 → output = 4·phase − 1   (rising: −1 at phase=0, +1 at phase=0.5)
phase ≥ 0.5 → output = 3 − 4·phase   (falling: +1 at phase=0.5, −1 at phase=1)
```
Output range: [−1, +1] (normalized). Scaled ×5 for Eurorack output → ±5 V.

### Outputs

| Name | Enum | Description |
|---|---|---|
| LFO 1 Out | `LFO1_OUTPUT` | ±5 V triangle wave |
| LFO 2 Out | `LFO2_OUTPUT` | ±5 V triangle wave |

### Lights

| Name | Enum | Behavior |
|---|---|---|
| LFO 1 | `LFO1_LIGHT` | Brightness = (raw + 1) / 2 → 0 (dark at −5V) to 1 (bright at +5V) |
| LFO 2 | `LFO2_LIGHT` | Same |

### Normalling

**LFO1 → MOD_IN:** When the MOD_IN jack is unpatched, LFO1 output normalizes into the
mod bus source. The mod bus processor (`MOD_SCALE`, `MOD_OFFSET`) applies to it.
When MOD_IN is patched, the external signal overrides LFO1.

LFO2 has no normalling — it is output-only.

### Signal levels at I/O
- Output: ±5 V (Eurorack bipolar CV standard)
- Light input: normalized [−1, +1]

---

## Phase 2R: Analog Behavior Model

### Transfer function
Triangle oscillator. Phase accumulator increments by f_Hz × T_s each sample.
No filtering or waveshaping applied.

**Target behavior for analog implementation:**
- Frequency range: 0.05–20 Hz
- Waveform: triangle (linear rising/falling edges, equal positive/negative excursion)
- Output amplitude: ±5 V (adjustable via trim pot in hardware)
- Frequency law: exponential (1 octave per constant increment of control voltage)
  - Hardware: expo converter on the rate CV or digital-controlled frequency

### Frequency accuracy
±2% across temperature is acceptable (LFO pitch is non-critical).
No V/oct tracking required for LFO rate.

---

## Phase 3R: Circuit Design

### Topology options (TBD)

**Option A: Analog triangle/square oscillator**
- Classic op-amp integrator + comparator feedback (e.g., LM13700 integrator + comparator)
- Rate set by expo converter → VCA driving integrator current
- Advantage: fully analog, inherits all the "feel" of analog LFO drift
- Challenge: expo converter adds thermal complexity; needs temperature compensation

**Option B: Microcontroller-generated triangle wave with DAC output**
- ATtiny or similar generates precise triangle at any rate from a lookup table
- DAC (e.g., MCP4922 SPI 12-bit) → output buffer (LM4562)
- Rate knob → ADC input on MCU
- Advantage: exact frequency law, easy rate LED driving, no expo converter
- Challenge: adds digital circuitry to analog module; needs power isolation

**Option C: Hybrid — digital rate control, analog integrator**
- MCU generates rate CV (via DAC) → analog VCA-integrator triangle core
- Splits concerns: MCU handles expo law, analog core handles wave shaping
- Medium complexity

**Recommended approach:** Defer until Phase 2R complete. Likely Option A or C.

### Known challenges
- Expo converter requires ±60 mV/°C compensation for accurate rate tracking
- LFO amplitude trim needed to hit exactly ±5 V; use trimpot on output gain stage

### Power draw estimate (rough)
- Analog triangle core: +12V ~5 mA, −12V ~5 mA per LFO
- Total both LFOs: ~10 mA / −10 mA (estimate)
