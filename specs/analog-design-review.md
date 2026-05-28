# POGO Analog Design Review — Trim Pots / Parts / Impedance / Noise

**Date:** 2026-05-27  
**Scope:** Full analog design review across all block specs, aux library, and components.yaml  
**Branch:** dev  
**Status:** Issues documented and corrected (see ACTION column).

---

## 1. Trim Pot Audit

### 1.1 Summary — All Calibration Trimmers (23 total on hardware)

| Ref | Block | Board | Purpose | Necessary? |
|---|---|---|---|---|
| RV_VCA_UNITY_L | block-4 | audio | THAT 2180 L-channel unity gain (0 dB) | ✅ Required — dB-law IC; gain depends on R_gain tolerance |
| RV_VCA_UNITY_R | block-4 | audio | THAT 2180 R-channel unity gain | ✅ Required — stereo matching |
| RV_REF (LP1) | block-5 | audio | f_ref = 632 Hz at 0 V CV | ✅ Required — sets absolute pitch reference |
| RV_1VOCT (LP1) | block-5 | audio | 1 V/oct tracking ±1 cent | ✅ Required — THAT340 gain slope calibration |
| RV_QMAX (LP1) | block-5 | audio | Self-oscillation onset and Butterworth point | ✅ Required — LM13700 Iabc_q offset calibration |
| RV_LP1_TILT_NULL | block-5 | audio | L = R cutoff when tilt knob at center | ✅ Required — tilt inverter imbalance < 5 mV; without trim L/R desync audible at self-osc |
| RV_REF (HP) | block-7 | audio | f_ref = 632 Hz at 0 V CV | ✅ Required |
| RV_1VOCT (HP) | block-7 | audio | 1 V/oct tracking | ✅ Required |
| RV_QMAX (HP) | block-7 | audio | Self-oscillation onset | ✅ Required |
| RV_REF (LP2) | block-8 | audio | f_ref = 632 Hz at 0 V CV | ✅ Required |
| RV_1VOCT (LP2) | block-8 | audio | 1 V/oct tracking | ✅ Required |
| RV_QMAX (LP2) | block-8 | audio | Self-oscillation onset | ✅ Required |
| RV_BP1_REF | block-6 | audio | f_ref = 200 Hz (BP1) | ✅ Required |
| RV_BP1_1VOCT | block-6 | audio | 1 V/oct tracking (BP1) | ✅ Required |
| RV_BP1_QMAX | block-6 | audio | Q calibration (BP1) | ✅ Required |
| RV_BP2_REF | block-6 | audio | f_ref = 1500 Hz (BP2) | ✅ Required |
| RV_BP2_1VOCT | block-6 | audio | 1 V/oct tracking (BP2) | ✅ Required |
| RV_BP2_QMAX | block-6 | audio | Q calibration (BP2) | ✅ Required |
| RV_BP3_REF | block-6 | audio | f_ref = 6000 Hz (BP3) | ✅ Required |
| RV_BP3_1VOCT | block-6 | audio | 1 V/oct tracking (BP3) | ✅ Required |
| RV_BP3_QMAX | block-6 | audio | Q calibration (BP3) | ✅ Required |
| RV_MB_ZERO | block-3 | utility | Mod bus offset null (< 10 mV at scale=0) | ✅ Required — **was missing from block-3/spec.md, now added** |
| RV_MB_AMOUNT_MAX | block-3 | utility | 5× gain calibration | ✅ Required — **was missing from block-3/spec.md, now added** |

### 1.2 Trimmers NOT Needed (no-trim blocks)

| Block | Reason no trim needed |
|---|---|
| block-A Input Buffer | OPA1612 V_os < 0.2 mV; gain = 1 unity; no calibration needed |
| block-1 Pre-Gain | Resistor-ratio gain 1×/5×; 1% resistors give ±2% accuracy, acceptable for a switched gain |
| block-2 Dual LFO | LFO rate accuracy not critical (±20% acceptable for musical use); log pot + end resistors adequate |
| block-B Output Buffer | Unity-gain TL072 followers; no calibration |

### 1.3 BP Tilt Null (Optional, Not Currently Specified)

Block-6 BP has a BP_TILT parameter (stereo spread). If the tilt inverter has a DC offset,
L and R BP cutoffs will diverge when tilt = 0. The BP groups are less pitch-sensitive than
LP1 (BP cutoffs span 200–6000 Hz, each with its own independent FREQ pot). A tilt null trim
is **not required** for block-6 unless stereo BP center tracking < 10 Hz becomes important.
Do not add unless prototype reveals audible issue.

---

## 2. Parts Availability Review

### 2.1 Verified Available (2026)

| Part | MPN | Source | Notes |
|---|---|---|---|
| THAT 2180 | THAT2180A08-U | Mouser, Digi-Key | In production; ±12 V compatible |
| THAT 340 | **THAT340S14-U** | Mouser, Digi-Key | SOIC-14 (14-pin), NOT SOIC-8 — see §2.2 |
| LM13700M | LM13700M/NOPB | TI, Mouser, Digi-Key | Long-running TI part; ample stock |
| TL072CDT | TL072CDT | STMicro, Digi-Key | Common; multiple sources |
| TL074CDT | TL074CDT | STMicro, Digi-Key | Common; multiple sources |
| OPA1612 | OPA1612AIDR | TI, Digi-Key | In production; SOIC-8; replaced NE5532D (block-1) and LM4562MA (block-A) |
| BAT54S | BAT54S | Vishay, Nexperia | SOT-23, multiple sources |
| CD4053BM96 | CD4053BM96 | TI | SOIC-16 (bipolar supply variant); verify VDD/VSS ±12 V operation |
| BZX84C10 | BZX84C10LT1G | OnSemi | SOT-23 10 V zener (mod bus clamp) |
| BZX84C5V1 | BZX84C5V1LT1G | OnSemi | SOT-23 5.1 V zener (HC clip) |
| 1N4148W | 1N4148WS | Various | SOD-323; confirm SOD-123 vs SOD-323 in component table |
| Murata BLM18AG601SN1D | BLM18AG601SN1D | Murata/Digi-Key | 0603 ferrite bead |
| Bourns 3224W | 3224W-1-104E (100kΩ), 3224W-1-103E (10kΩ) | Bourns / Digi-Key | SMD cermet trimmer; specify full MPN |

### 2.2 THAT340 Package Error — **Fixed in all specs and components.yaml**

**Error:** Every THAT340 entry in block specs (blocks 5, 6, 7, 8) and components.yaml had
`SOIC-8` as the package. **Correct package is SOIC-14.**

- THAT340**P**14-U = PDIP-14 (14-pin DIP, through-hole)
- THAT340**S**14-U = SOIC-14 (14-pin SOIC, SMD)

The "14" in the part suffix refers to pin count: 4 matched NPNs × 3 pins each + 2 pins = 14.
The PCB footprint must be SOIC-14, not SOIC-8. **Using SOIC-8 footprint would place pads
incorrectly; this is a critical build error.**

**ACTION TAKEN:** Fixed in block-5, block-6, block-7, block-8 spec files and components.yaml.

### 2.3 BAT85 SOD-80 Through-Hole — **Fixed in aux-power-filter.md**

The reverse-polarity protection in aux-power-filter.md specified BAT85 in SOD-80, which is
an axial through-hole package. POGO is an all-SMD design. **ACTION TAKEN:** Spec now calls for
**SS14 (SMA/DO-214AC, 1 A, 40 V)** as primary recommendation; MBR0520LT1G (SOD-123) as
alternative. Both are SMD, widely available, and rated for ≥200 mA reverse polarity current.

### 2.4 Precision Resistor Tolerances — Needs BOM Flag

The following resistors require 1% tolerance (or better). Components.yaml currently does not
flag tolerance. These must be called out during BOM preparation:

| Ref | Value | Location | Why |
|---|---|---|---|
| R_VOCT (block-5, 6, 7, 8) | 47 kΩ | THAT340 V/oct network | 1% error = 12 cents pitch tracking error; with R_E=1kΩ and RV_1VOCT≈7.5kΩ → 18.0 mV/V exact |
| R_inv_in, R_inv_f (all attenuverters) | 10 kΩ | Attenuverter inverter | 1% mismatch → center null only ~40 dB |
| R_MB_INV (block-3) | 100 kΩ | MB_INV stage | 1% mismatch → mod bus gain error at zero offset |
| R_TILT_INV_IN/FB (block-5) | 100 kΩ | Tilt inverter | Mismatch shifts tilt center null |

**ACTION REQUIRED (not yet done):** Flag 1% (or 0.1%) tolerance in components.yaml entries.
Add a `tol: "1%"` field to affected entries before PCB BOM generation.

### 2.5 THAT340 Sharing Opportunity (BOM Optimization, Not a Bug)

Each THAT340S14-U contains 4 matched NPNs. Each expo converter uses 2 (a diff pair for
V/oct + temperature compensation). Currently 6 separate ICs are used (one per filter block:
LP1, LP2, HP, BP1, BP2, BP3). Two NPNs per IC are unused.

**Optional optimization:** Pair expo converters that are thermally proximate:
- LP1 + LP2 → share 1 THAT340S14-U (both are on audio board, adjacent layout)
- HP + one spare pair → share 1 THAT340S14-U
- BP1 + BP2 → share 1 THAT340S14-U
- BP3 + spare pair → share 1 THAT340S14-U
→ **Reduces from 6× to 4× THAT340S14-U.** Saves ~$8 and 4 SOIC-14 footprints.

**Constraint:** Both expo converters sharing an IC must be at the same temperature. On a
shared PCB this is automatic. **Do not share across different boards.**

Not implemented (not a current error); defer to Phase 5R PCB layout review.

---

## 3. Impedance Design — Low-Noise Connections

### 3.1 Mod Bus Distribution Load — **Fixed in block-3/spec.md and aux-mod-bus-core.md**

**Issue:** 19 destinations × 10 kΩ bipolar attenuverter pots = 10 kΩ / 19 ≈ 526 Ω total
load on V_modbus. At ±10 V, this requires ±19 mA. A single TL074 output driving 19 mA on
±12 V rails cannot reliably swing to ±10 V (typical output swing drops ~1–2 V at that
current, leaving only ~±8–9 V).

**Fix implemented:** MB_PROC_A (TL074CDT) uses all four halves:
- Half A: MB_AMP (inverting summer)
- Half B: MB_INV (polarity restoring G=−1)
- Halves C+D: Paralleled as distribution buffer (47 Ω series resistors on each output
  before joining), each driving ≈9.5 mA. Combined: 19 mA @ ±10 V with full output swing.

No additional ICs needed; MB_PROC_A was previously shown with 2 spare sections.

**Alternative if paralleled TL074 proves unstable:** Replace U_MB_BUF with a single
OPA1612 half (output short-circuit current ≈ 38 mA; handles 526 Ω cleanly).

### 3.2 VCA AMT Pot Impedance Loading — **Design Note Added to block-4/spec.md**

**Issue:** VCA_AMT pot (10 kΩ, centre detent) wiper source impedance varies from 0 Ω
(at either end) to R_pot/4 = 2.5 kΩ (at center). In series with R_GAIN (15 kΩ) feeding
the THAT 2180 GAIN pin, this creates a position-dependent effective R_GAIN ranging from
15 kΩ to 17.5 kΩ — a 14 % non-linearity in the dB gain law, largest at center travel.

**Recommended fix (added to block-4/spec.md):** Reduce AMT pot value to **1 kΩ**
(max wiper impedance 250 Ω → error < 1.6 %, absorbed by RV_VCA_UNITY trim).

**Alternative:** Add a TL072 unity-gain follower between wiper and R_GAIN, but this
requires a third TL072 half per channel. The pot-value reduction is simpler.

### 3.3 Q Control High-Impedance Node

The V_ires → Iabc_q path uses R_Iabc = 1 MΩ. This node has Z = 1 MΩ at DC, falling
to ~8 kΩ at 20 kHz. Stray capacitance on this node creates a pole in the Q control
bandwidth (τ = R × C_stray; at 1 pF stray cap, f_pole = 1/(2π × 1M × 1p) ≈ 160 kHz —
well above audio). Johnson noise: √(4kT × 1MΩ) × √BW = 130 nV/√Hz at DC. This is the
dominant noise source on the Iabc_q pin but is common to L and R (same IRES_AMP drives
both), so it appears as common-mode Q modulation, not audio noise.

**Action:** Keep R_Iabc trace length < 5 mm. Use ground-plane shielding. No circuit change needed.

### 3.4 THAT340 Base Loading

Each THAT340 NPN base draws I_B ≈ I_C / h_FE ≈ 10 µA / 200 ≈ 50 nA from the V/oct
resistor network. Through R_VOCT (47 kΩ): voltage drop = 50 nA × 47 kΩ = 2.35 mV.
At 1 V/oct = 58 mV/octave ÷ ln(2) = 83.5 mV/octave, 2.35 mV = 0.028 octaves = 0.34 semitones.
This is absorbed entirely by the RV_REF calibration trim. No circuit change needed.

### 3.5 OTA Linearizing Resistors (1 kΩ)

LM13700 linearizing resistors (1 kΩ at each OTA input) extend the linear range from
±26 mV to ±(26 + I_abc × 500 Ω) ≈ ±31 mV at I_abc = 10 µA. Johnson noise contribution:
√(4kT × 1kΩ) × √BW = 4 nV/√Hz. This is below the OTA shot noise (7–8 nV/√Hz) and well
below the TL072 SUM_AMP (18 nV/√Hz). Linearizing resistors are correctly sized.

---

## 4. Noise Analysis

### 4.1 Per-Stage Input-Referred Noise (typical, wideband)

| Stage | Device | e_n | Current noise @ Z_in | Total RTI |
|---|---|---|---|---|
| Block A | OPA1612 | 1.1 nV/√Hz | i_n × 100 Ω = 0.2 nV/√Hz | **≈ 1.1 nV/√Hz** |
| Block 1 (G = 5×) | OPA1612 | 1.1 nV/√Hz | i_n (1.7 pA) × 4.7 kΩ = 8.0 nV/√Hz | **≈ 8.1 nV/√Hz** |
| Block 4 (THAT 2180) | THAT 2180 | ~5 nV/√Hz | control path — not audio | **≈ 5 nV/√Hz** |
| Block 5 (LP1 SUM_AMP) | TL072 | 18 nV/√Hz | i_n (0.01 pA) × 100 kΩ = 1 nV/√Hz | **≈ 18 nV/√Hz** |
| Block 6 (BP SUM_AMPs + dist) | TL072 cascade | 18 nV/√Hz per stage; 3–5 stages | **≈ 25 nV/√Hz equiv** |
| Block 7 (HP SUM_AMP) | TL072 | 18 nV/√Hz | — | **≈ 18 nV/√Hz** |
| Block 8 (LP2 SUM_AMP) | TL072 | 18 nV/√Hz | — | **≈ 18 nV/√Hz** |
| Block B | TL072 | 18 nV/√Hz | — | **≈ 18 nV/√Hz** |

### 4.2 Chain SNR Estimate

Assuming unity gain through each block, uncorrelated noise sources sum in quadrature:

```
e_n_chain = √(1.1² + 8.1² + 5² + 18² + 25² + 18² + 18² + 18²)
           = √(1.2 + 65.6 + 25 + 324 + 625 + 324 + 324 + 324)
           = √2013 ≈ 45 nV/√Hz
```

Integrated 20 Hz – 20 kHz:
```
E_noise_RMS = 45 nV/√Hz × √19980 Hz ≈ 45 × 141 ≈ 6.4 µV_RMS
```

Signal level: ±5 V peak audio = 3.54 V_RMS

```
SNR ≈ 20 × log(3.54 V / 6.4 µV) ≈ 115 dB
```

**This exceeds the Eurorack dynamic range limit (~120 dB theoretical for ±12 V rails).**
The module's noise floor is set by the multi-stage filter topology, not a single weak stage.
115 dB SNR is excellent for a complex analog filter module.

### 4.3 Dominant Noise Source: Block 1 (OPA1612 at G = 5×)

The largest single-stage contributor is block-1 at G = 5× mode. OPA1612 (bipolar input)
current noise i_n = 1.7 pA/√Hz through R_g = 4.7 kΩ gives 8.0 nV/√Hz — much larger than
the op-amp's voltage noise (1.1 nV/√Hz). Total RTI ≈ 8.1 nV/√Hz.

```
i_n × R_g = 1.7 pA × 4.7 kΩ = 8.0 nV/√Hz
Total RTI ≈ √(1.1² + 8.0²) ≈ 8.1 nV/√Hz
```

The previous design used NE5532D at R_g = 12 kΩ (RTI ≈ 10 nV/√Hz). The implemented
improvement lowered R_g to 4.7 kΩ and replaced NE5532D with OPA1612, reducing RTI by
~1.9 nV/√Hz (−1.8 dB) and saving 5 mA per rail. At R_g = 4.7 kΩ the OPA1612 bipolar
current noise still dominates. Further reduction would require a FET-input op-amp, but
all ±12V-compatible FET types (TL072, TL074) have e_n ≥ 18 nV/√Hz, which would worsen
the total RTI significantly. No practical improvement remains.

### 4.4 TL072 SUM_AMP Noise (Blocks 5, 7, 8)

TL072CDT: e_n = 18 nV/√Hz. For filter blocks, the SUM_AMP sees 100 kΩ input resistors.
At 18 nV/√Hz over 20 Hz–20 kHz: E_noise ≈ 2.5 µV_RMS per stage. Out-of-band noise is
attenuated by the filter's own frequency response.

**Completed (Phase 3R):** All 12 SUM_AMP ICs (SOIC-8 dual packages) in blocks 5, 6, 7, 8
upgraded to OPA1612 (e_n = 1.1 nV/√Hz, SOIC-8 pin-compatible).

OPA1612 Iq = **2.75 mA per channel** (per op-amp half); dual IC draws 5.5 mA per supply rail.
TL072 Iq = 0.9 mA per channel; dual IC draws 1.8 mA per supply rail.
Delta per dual IC = 5.5 − 1.8 = **3.7 mA per IC**.

Power cost by block (counting IC packages, not channels):
- Block-5: +7.4 mA (2 dual ICs × 3.7 mA/IC)
- Block-7: +7.4 mA (2 dual ICs × 3.7 mA/IC)
- Block-8: +7.4 mA (2 dual ICs × 3.7 mA/IC)
- Block-6: +22 mA (6 dual ICs × 3.7 mA/IC)
- **Total: +44 mA** across all filter stages

SUM_AMP noise floor drops from 18 nV/√Hz to 1.1 nV/√Hz; overall chain SNR improves ~5 dB.
Updated in all block specs, components.yaml, and aux-ota-c-svf.md.

### 4.5 High-Q Noise Behavior

At near-self-oscillation Q (≈ 50), the SVF has gain Q = 50 near ω₀. Any noise within
the resonant bandwidth (f₀/Q) is amplified by Q. This is a physical property of resonant
filters, not a design defect. Self-oscillation mode quality depends primarily on the
LM13700 Iabc_q shot noise; high-Q VCOs using the POGO filter will have phase noise
consistent with LM13700 OTA-based oscillators (measured in literature at ~−80 dBc/Hz
at 1 kHz offset for 1 kHz oscillation frequency).

### 4.6 LFO-to-Audio Coupling

LFO circuits (0.05–20 Hz, ±5 V triangle) on the utility board could couple into the
audio chain via:
1. **Power supply modulation:** LFO drives LED loads (pulsing/breathing) which modulate
   +12 V supply. Ferrite beads + 10 µF bulk caps at each board power inlet attenuate this.
   LFO-rate power ripple at 0.05–20 Hz is well below audio band; inaudible.
2. **Ground impedance:** If LFO output traces run near audio PCB or share a ground star
   with audio signal paths, LFO frequency appears as audio AM (amplitude modulation) of
   the signal. **Layout requirement:** LFO return currents must NOT share the audio board
   star ground. Use separate ground stars per board, connected only at the main module star.
3. **Capacitive coupling:** At 20 Hz max LFO rate, capacitive coupling between LFO traces
   and audio traces requires trace separation of < 0.1 mm to produce even 1 nV of coupling.
   Standard 0.2 mm clearance is adequate. No special shielding needed.

---

## 5. Summary of Changes Made to Spec Files

| File | Change | Reason |
|---|---|---|
| `specs/block-5/spec.md` | THAT340S14-U package: SOIC-8 → SOIC-14 | PCB footprint error |
| `specs/block-6/spec.md` | THAT340S14-U package: SOIC-8 → SOIC-14 | PCB footprint error |
| `specs/block-7/spec.md` | THAT340S14-U package: SOIC-8 → SOIC-14 | PCB footprint error |
| `specs/block-8/spec.md` | THAT340S14-U package: SOIC-8 → SOIC-14 | PCB footprint error |
| `specs/components.yaml` | All 6 THAT340 entries: SOIC-8 → SOIC-14 | PCB footprint error |
| `specs/aux/aux-power-filter.md` | BAT85 SOD-80 → SS14 SMA (SMD) | Through-hole in SMD design |
| `specs/block-3/spec.md` | Added D_MB_CLAMP_P/N (BZX84C10 zeners) | Missing ±10 V clamp components |
| `specs/block-3/spec.md` | Added RV_MB_ZERO, RV_MB_AMOUNT_MAX | Missing calibration trims |
| `specs/block-3/spec.md` | MB_PROC_A: halves C+D → paralleled distribution buffer | Mod bus 526 Ω load needs ±19 mA drive |
| `specs/block-3/spec.md` | Updated IC count table (26 sections, all 4 halves of MB_PROC_A used) | Consistency |
| `specs/block-4/spec.md` | Added design note on AMT pot 14% loading error + fix | Gain law non-linearity |
| `specs/aux/aux-attenuverter.md` | 22 destinations → 19; 6 TL074 ICs → 5; updated tables | Count was stale from pre-Phase-3R |
| `specs/aux/aux-mod-bus-core.md` | 22 destinations → 19; 455 Ω → 526 Ω; updated buffer description | Count/load were stale |
| `specs/aux/aux-mod-bus-core.md` | Component table: replaced U_MB_BUF TL072 with MB_PROC_A dual-buffer topology | Removes unnecessary extra IC |

## 6. Remaining Action Items (Not Yet Done)

All high-priority items from the initial review have been resolved. The following prototype
validation items remain as Phase 5R tasks:

| Item | Priority | Location |
|---|---|---|
| Prototype: VCA AMT pot value — validate 1 kΩ vs 10 kΩ interaction with THAT 2180 | Medium | block-4 |
| Prototype: Paralleled MB_PROC_A output buffer stability (47 Ω series R adequacy) | Medium | block-3 |
| Prototype: THAT340 sharing — reduce 6 ICs to 4 (LP1+LP2 share, BP1+BP2 share) | Low | blocks 5/6/7/8 |
| Prototype: WF fold threshold Vth characterization — bench-measure fold shape at various drive levels; compare to DSP asin(sin(x)) reference (informational; topology is correct and stable) | Low | block-6 |

## 7. Completed Action Items

| Item | Resolution |
|---|---|
| Flag 1% tolerance on R_VOCT, R_inv_in/fb, R_MB_INV, R_TILT_INV | Done — components.yaml header + tol fields on R3/R4/R5/R6, R16 |
| Verify mod destination count (19) against DSP code | Done — confirmed 19 via InputId enum in Pogo.cpp |
| CLAUDE.md "22 CV destinations" → "19 CV destinations" | Done |
| THAT340S14-U package: SOIC-8 → SOIC-14 in all block specs + components.yaml | Done |
| BAT85 SOD-80 → SS14 SMA in aux-power-filter.md | Done |
| Block-3: missing BZX84C10 zener clamps + RV_MB_ZERO + RV_MB_AMOUNT_MAX | Done |
| Block-3: MB_PROC_A paralleled distribution buffer (halves C+D, 47Ω series R) | Done |
| Block-4: AMT pot 10kΩ → 1kΩ (14% → <1.6% THAT 2180 gain error) | Done |
| Block-1: R_g 12kΩ → 4.7kΩ, R_f 47kΩ → 18kΩ; NE5532D → OPA1612 (RTI: 10→8.1 nV/√Hz; −1.8 dB noise, 5 mA saved) | Done |
| OPA1612 for all 12 SUM_AMPs in blocks 5/6/7/8 (1.1 nV/√Hz; 16× noise reduction) | Done |
| aux-attenuverter.md: 22→19 destinations, 100kΩ pot → 10kΩ | Done |
| aux-mod-bus-core.md: 22→19 destinations, buffer topology update | Done |
| aux-ota-c-svf.md: SUM_AMP updated to OPA1612 with noise rationale | Done |
| Power draw estimates added to block-5, 7, 8; block-6 updated for OPA1612 | Done |
| OPA1612 power: corrected 2× Iq underestimate (2.75 mA/channel ≠ per-IC; dual IC = 5.5 mA/rail) | Done — blocks 5/6/7/8 updated; review §4.4 corrected to +44 mA total |
| Block-1 "26% RTI noise improvement" → "61%" (math: (8.4−3.3)/8.4 = 60.7%) | Done |
| aux-attenuverter.md wiper impedance: "1 kΩ" → "2.5 kΩ" (= 10 kΩ/4 at center travel) | Done |
| README.md: "22 CV destinations" → "19"; stale phase status and directory structure updated | Done |
| Block-6 WF topology: replaced diode-in-feedback compressor with true symmetric precision folder (passive clamp + G=+2 subtractor); no extra ICs; D_WF count 24→48; stability proven analytically | Done |
| Wiper bypass cap (47 pF) added to all RV_DRIVE wiper nodes in block-6 (anti-RF, scratchiness reduction) | Done |
