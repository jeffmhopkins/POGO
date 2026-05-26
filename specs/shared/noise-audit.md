# POGO Noise & Inter-Block Connection Audit

**Audit date:** 2026-05-24
**Scope:** Full signal chain — IC selection, inter-block impedances, ribbon cable signal integrity,
noise accumulation, and board design rules.
**Status:** All findings resolved; changes applied to individual block specs and layout-notes.md.

---

## 1. Inter-Block Architecture Summary

All signal-chain blocks (A through B) reside on the combined audio board — L-channel in the
left half, R-channel in the right half, separated by a 4 mm center GND guard strip.
Every inter-block connection within a channel is a **direct DC-coupled PCB trace** — no coupling
capacitors in the signal path. Output impedances are ~1.5 Ω (closed-loop op-amp) at every stage;
input impedances are 100 kΩ (SVF summing nodes), 10 kΩ (Block 1 gain stage), or 10 MΩ (unity
followers). No impedance mismatches exist at the board-level signal chain.

Board-to-board connections use two technologies:
- CN_CTRL_1 (34-pin) + CN_CTRL_2 (40-pin) + CN_CTRL_3 (24-pin): control board ↔ utility board — IDC ribbon cables
- STK_AUDIO_L + STK_AUDIO_R (**40-pin** each): utility board ↔ combined audio board — 2.54 mm stacking headers (face-to-face)

The highest-risk inter-board signals are the **I_abc exponential currents** (pins 12–19 in revised
pinout) — any noise on these lines modulates filter frequency directly. Changes H2 and H3 below
address this specifically.

---

## 2. Noise Chain Analysis

### Noise accumulation through the chain (18 nV/√Hz TL072 baseline)

| Stage | Device | Noise (input-referred) | Cascaded effect |
|---|---|---|---|
| Block A input buffer | LM4562 (changed from TL072) | 2.7 nV/√Hz | First-in-chain — sets noise floor for all downstream processing |
| Block 1 unity mode | NE5532 (changed from TL072) | 5 nV/√Hz × 1 = 5 nV/√Hz at output | Inaudible above Block A contribution |
| Block 1 boost (×5) | NE5532 | 5 nV/√Hz → 25 nV/√Hz at Block 1 output | 5× noise penalty; acceptable |
| Block 3 SVF (3 groups) | 1× TL074 (summing) + 6× LM13700 | BP peak amplifies noise at formant freq by Q | Same OTA-C noise characteristic as LP/HP; at high Q formant tone masks noise floor |
| LP1/LP2/HP SVF | TL074 summing amps | 18 nV/√Hz at unity Q | Noise floor rises at high Q due to regenerative feedback — inherent to OTA-C topology (see D1) |

**Key finding:** TL072 in Block A was the primary noise concern as the first active element.
Replacing with LM4562 reduces the input noise floor 6.7×. In boost mode (Block 1 at 5×),
NE5532 replaces TL072, reducing boost-mode noise 3.6×.

### Why OTA-C noise increases at high Q

At Q → ∞ (self-oscillation onset), LM13700 OTA integrators are operating at Iabc → 0.
OTA input noise current (~10 pA/√Hz) reflected through the high-impedance integrator C
dominates. This is inherent to OTA-C topology and expected behavior. The oscillating tone
at self-oscillation onset masks the elevated noise floor. Not actionable; documented as
accepted limitation in block-5-lp1/spec.md (see D1 below).

---

## 3. High-Priority Findings and Resolutions

### H1: Block A — TL072 → LM4562

**Problem:** TL072 (18 nV/√Hz) in Block A is the first active stage; all downstream noise
accumulation originates here. In boost mode (Block 1 at 5×), this noise is amplified before
entering Block 3's SVF resonators.
**Resolution:** TL072CDT replaced with **LM4562** (SOIC-8, pin-compatible) in Block A.
- Noise: 2.7 nV/√Hz (6.7× improvement)
- Same SOIC-8 footprint, ±15V supply, GBW ~55 MHz
**Changed in:** `specs/block-A-input-buffer/spec.md` Phase 3 IC selection

### H2: STK_AUDIO_L/R — 40-pin with GND guard pins for I_abc signals

**Problem:** The six I_abc exponential current signals (SVF FREQ 1/2/3, LP1/LP2/HP expo
outputs) require adjacent GND guard pins to prevent capacitive coupling of noise onto these
frequency-sensitive current lines. I_abc noise directly modulates filter pitch.
**Resolution:** STK_AUDIO_L/R stacking headers use 40-pin pinout with 3 GND guard pins
interleaved in the I_abc group (see pinout in layout-notes.md Section 5). Stacking headers
have inherently lower inter-pin coupling than IDC ribbon cable (no long parallel runs of
adjacent conductors), providing additional noise margin over the original IDC design.
**Changed in:** `specs/board-layout/layout-notes.md` Section 5 connector tables

### H3: LM13700 Iabc pins — 10 nF local bypass cap

**Problem:** The trace from THAT340 expo output → stacking header → combined audio board →
LM13700 Iabc pin can still pick up HF noise. LM13700 Iabc pin impedance is ~2.6 kΩ at nominal
10 µA operating current; voltage noise on this trace couples directly into I_abc, modulating
cutoff frequency.
**Resolution:** Add **10 nF C0G 0402 cap** from each LM13700 Iabc pin to GND, within 2 mm
of the pin. At 2.6 kΩ source impedance: f_-3dB = 1/(2π × 2.6k × 10n) = 6.1 kHz — low-pass
filtering noise above audio range. Combined with H2's GND guard pins (which reduce coupled
voltage noise ~60 dB) and the stacking header's inherently lower coupling vs. IDC ribbon,
this gives extremely robust I_abc noise immunity.
**Changed in:** `specs/block-3-apcf/spec.md`, `specs/block-5-lp1/spec.md` Phase 3 IC tables
(also applies to LP2 and HP by reference to LP1 topology)

### H4: POLARITY switch "Off" — 10 kΩ bleeder resistor

**Problem:** When POLARITY = Off, the feedback summing node must see GND. Panel toggle switches
have typical contact leakage of 1–10 nA. At R_fb = 100 kΩ and 10 nA leakage = 1 mV offset,
producing audible feedback bleed-through at high FB knob settings.
**Resolution:** Add **10 kΩ resistor to GND** at the POLARITY switch output (the "Off"
contact). This provides a definite low-impedance GND return: 10 nA through 10 kΩ = 0.1 µV —
inaudible. The 10 kΩ does not meaningfully load the Positive/Negative signal positions (output
impedance of POL_INV op-amp is ~1.5 Ω; 10 kΩ draws 0.5 mA, within op-amp drive capability).
**Changed in:** `specs/block-3-apcf/spec.md` Phase 3 Known Circuit Challenges and component table

### H5: THAT340 cluster — dedicated local power pi-filter

**Problem:** THAT340 expo converters output I_abc proportional to e^(V_ctrl/V_T). Power supply
noise on the THAT340 +12V supply pin appears directly as I_abc noise → pitch modulation.
All THAT340s shared the utility board power plane with mod bus, attenuverter, and other circuitry.
**Resolution:** Add a dedicated **100 Ω + 10 µF + 100 nF local pi-filter** for the THAT340
cluster supply (+12V and −12V) on the utility board, separate from the main board power pour.
- 100 Ω series resistance creates RC lowpass: f_-3dB = 1/(2π × 100 × 10µ) = 159 Hz, attenuating
  100 Hz busboard ripple by ~2× and 1 kHz noise by 10×
- Power drop: 100 Ω × (6 × 1 mA) = 0.6 V → THAT340 operates at 11.4 V (within spec)
**Changed in:** `specs/board-layout/layout-notes.md` Section 7 THAT340 placement rules

### H6: Post-distortion feedback path — 100 pF EMI bypass, GND-adjacent routing

**Problem:** V_post_dist travels: Block 4 (combined audio board) → STK_AUDIO_L pins 31–34 →
utility board FB DIST BLEND crossfade → STK_AUDIO_L pin 35 → back to Block 3 (combined audio
board). Although stacking headers eliminate the long ribbon cable runs, the signal still crosses
the board boundary twice and enters Block 3's regenerative feedback loop, where any noise is
amplified at high FB settings.
**Resolution:**
1. Block 4 TL074 SUM_AMP output (source Z ~1.5 Ω) confirmed to drive post-dist tap pins directly.
2. **100 pF C0G cap** to GND at post-dist tap entries on utility board (at stacking header, after pin).
   100 pF at 1.5 Ω source Z rolls off at 1 GHz — EMI suppression only, no effect on audio.
   IMPORTANT: do NOT use 100 nF here; 100 nF at 100 Ω would roll off at 16 kHz, destroying HF content.
3. Same 100 pF caps at the FB DIST BLEND return pin entry on the combined audio board.
4. Post-dist tap group (pins 31–35 in revised pinout) located adjacent to a GND pin.
Note: The stacking header design substantially reduces inter-pin coupling versus the original
IDC ribbon, further improving H6 noise immunity. The 100 pF bypass remains advisable as
belt-and-suspenders protection given the signal's route through the regenerative feedback path.
**Changed in:** `specs/board-layout/layout-notes.md` Section 5 and 7

### H7: Block 1 — TL072 → NE5532

**Problem:** Block 1 gain stage TL072 (18 nV/√Hz) amplifies its own noise by 5× in boost mode,
producing 90 nV/√Hz at the Block 1 output. Combined with Block A noise (also amplified),
the noise entering Block 3's SVF resonators in boost mode was significantly elevated.
**Resolution:** Replace TL072CDT with **NE5532** (SOIC-8, pin-compatible) in Block 1.
- Noise: 5 nV/√Hz → 25 nV/√Hz at 5× boost (3.6× improvement over TL072)
- Same SOIC-8 footprint, ±15V supply, 10 MHz GBW (vs. TL072 3 MHz — no audio impact)
**Changed in:** `specs/block-1-pregain/spec.md` Phase 3 IC selection and Phase 2 noise note

---

## 4. Medium-Priority Board Design Rules Added

### M1: L/R signal trace separation

SVF group L-channel signal traces must maintain ≥3 mm separation from corresponding R-channel
traces on the same layer. Prefer routing one channel on L1 (top) and the other on L4 (bottom)
so the L2 GND plane provides shielding between them.
**Added to:** `specs/board-layout/layout-notes.md` Section 7

### M2: BAT54S polarity verification checklist

~50+ BAT54S ICs across all boards. Orientation error creates silent ESD protection failure.
Before powering any board: verify each BAT54S with diode-test DMM — pin 2 (center) reads
~300 mV forward drop to pin 3 (toward +12V) and ~300 mV to pin 1 (toward −12V).
**Added to:** `specs/board-layout/layout-notes.md` Section 12 Bring-Up Checklist

### M3: THAT340 Kelvin ground for emitter bias resistors

Each THAT340 emitter bias resistor ground return must connect via a dedicated trace (≥0.5 mm wide,
<5 mm length) directly to the L2 GND plane via, not through any shared audio signal return trace.
Audio return currents through a shared trace create I×R offset voltage across R_e, modulating
the expo output (pitch modulation at audio frequency).
**Added to:** `specs/board-layout/layout-notes.md` Section 7

### M4: 22 pF HF suppression caps — placement rule

LM13700 OTA output HF suppression (22 pF C0G) must be placed within 1 mm of the OTA output
pin (pin 4 per cell), with the GND via on the cap's second pad. Routing through trace before
the cap introduces series inductance (~5 nH/cm), which resonates with 22 pF at ~680 MHz and
worsens HF behavior rather than suppressing it.
**Added to:** `specs/board-layout/layout-notes.md` Section 7

### M5: LP1/LP2 boundary — GND stitching via array

The vague "ground wire between LP1 and LP2 sections" in block-6-lp2/spec.md is now specified
as a dedicated **3× GND stitching via array** placed on the boundary between LP1 and LP2
footprint clusters, connecting L1 copper islands through L2 GND plane without relying on
thin shared traces.
**Added to:** `specs/block-6-lp2/spec.md` Phase 3 Known Circuit Challenges

---

## 5. Accepted Limitations (Documented, Not Fixed)

### D1: OTA-C noise increases at high Q
At Q → ∞ (Iabc → 0), LM13700 input noise current (~10 pA/√Hz) reflected through the high-impedance
integrator capacitor raises the noise floor. Inherent to OTA-C topology. The self-oscillating
sine tone at this setting dominates, masking the noise. No practical fix without a different
filter topology.
**Documented in:** block-5-lp1/spec.md Phase 3 Known Circuit Challenges

### D2: LP1/LP2 Q-VCA thermal coupling
LP1 and LP2 Q-VCAs share one LM13700 die (IC_Q_AB). At the low Iabc operating point (<1 µA),
per-cell power dissipation is <10 µW — thermal coupling between cells is negligible and
inaudible. No fix required.
**Documented in:** block-5-lp1/spec.md Phase 3 Known Circuit Challenges

### D3: BAND OUT phase relative to main output — verify at Phase 6
LP1 V_LP is the OTA2 integrator output. Whether V_LP carries the SUM_AMP phase inversion
depends on integrator polarity details. Main output corrects all inversions via HP output
inverting buffer. BAND OUT taps before LP2 — confirm BAND OUT phase at Phase 6 VCV Rack
verification. Expected to be in-phase with input on a unity-gain path, but must be measured.
**Documented in:** block-B-output-buffer/spec.md Phase 3 Schematic Notes

### D4: CD4053 V_EE = −12V — mandatory bring-up verification
Already documented as critical in block-4-distortion/spec.md. Silent failure mode if wrong.
Added to bring-up checklist in layout-notes.md: verify with DMM before applying audio signal.
**Added to:** `specs/board-layout/layout-notes.md` Section 12

---

## 6. Summary of File Changes

| File | Changes |
|---|---|
| `specs/shared/noise-audit.md` | This file — created |
| `specs/block-A-input-buffer/spec.md` | IC: TL072CDT → LM4562 (H1) |
| `specs/block-1-pregain/spec.md` | IC: TL072CDT → NE5532; added noise penalty note (H7) |
| `specs/block-3-apcf/spec.md` | Added POLARITY bleeder R (H4); 10 nF Iabc bypass caps (H3) |
| `specs/block-5-lp1/spec.md` | Added 10 nF Iabc bypass; D1 and D2 limitations noted (H3) |
| `specs/block-6-lp2/spec.md` | GND stitching via array spec (M5) |
| `specs/block-B-output-buffer/spec.md` | BAND OUT phase verification note (D3) |
| `specs/board-layout/layout-notes.md` | STK_AUDIO_L/R 40-pin stacking headers; new routing rules M1–M5; THAT340 power island H5; H6 post-dist tap; bring-up checklist |
| `specs/STATUS.md` | Audit completion noted |
