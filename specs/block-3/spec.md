# Block 3: Mod Bus
Centralized modulation processor: selects a source (LFO1 / LFO2 / External) via MOD_SRC, scales/offsets it, and distributes to 18 attenuverter destinations (+ a raw VCA normal).

DSP source: `plugin/src/dsp/ModBus.hpp`, `plugin/src/Pogo.cpp` (MOD_SRC selector 363–366; processor 368–370; distribution 373–379; VCA raw normal 382–386)

---

## 1. Intent

The Mod Bus is the central modulation hub of POGO. The bus source is chosen by the **MOD_SRC**
3-position panel switch — **LFO 1**, **LFO 2**, or **External** (the MOD_IN jack; 0 V if
unpatched) — per the locked plugin (`Pogo.cpp:363–366`). The selected source is conditioned by
two trimpots (SCALE and OFFSET) to produce a single shared bus voltage V_modbus in the range
±10 V. That bus voltage is distributed to **18 modulation destinations** throughout the filter
stack, each with a tip-switching override jack and a bipolar attenuverter trimpot.

A 19th tap — **VCA depth** — is special: per the plugin (`Pogo.cpp:382–386`) the raw V_modbus
normals directly into VCA_INPUT (no attenuverter), and the VCA's own bipolar depth control
(VCA_AMT) lives in block 4. So the VCA is driven by the bus but is **not** one of the 18
block-3 attenuverter destinations.

The bus lets a single source sweep every filter parameter simultaneously, with each destination
scaled and inverted independently. Plugging into any destination override jack breaks the bus
normalling for that destination only (the jack CV replaces the bus, scaled by the attenuverter),
allowing an external per-parameter CV while the rest of the module still follows the shared bus.

*(There are no MOD-bus status LEDs: the plugin drives no MOD_POS/NEG/CLIP lights and the locked
panel has no footprints for them. The earlier 3-LED scheme is removed — change 0018.)*

---

## 2. Theoretical Design and Topology

> ✅ **Re-verified 2026-05-30** against the locked plugin (change 0018, 0017 follow-up).
> Aligned to plugin ground truth: added the MOD_SRC 3-way source select; corrected the
> destination set to **18 attenuverter destinations + 1 raw VCA normal** (per-band BP CV is
> **TILT**, not FOCUS); removed the 3 MOD-bus LEDs + their driver IC (no plugin/panel
> backing). Processor scale/offset/clamp math unchanged (faithful to `ModBus.hpp`).

### Mod Source Select (MOD_SRC)

The bus source is a 3-way analog selector (SW7, Dailywell DW5, DPDT ON-ON-ON) wiring LFO1 /
LFO2 / External(MOD_IN) to the SCALE-pot input (V_SRC). The DPDT's two commons are bridged so
the three positions present one source at a time:

```
A_COM(2) = V_SRC (selected output → SCALE pot)
A1(1) = LFO1   ;   B1(4) = LFO2   ;   B2(6) = EXT (MOD_IN, post-protection)
A2(3) ── bridged ── B_COM(5)
  pos 0 → LFO1 ; pos 1 → LFO2 ; pos 2 → EXT
```

MOD_IN carries the standard 100 Ω + BAT54S input protection and feeds only the EXT throw —
it no longer auto-normals into the bus (that was the pre-0017 behavior). *(Phase-3R: verify
the DW5 ON-ON-ON contact sequence against the datasheet and swap throw assignments if the
physical position↔param order differs.)*

### Mod Bus Processor

The DSP processor applies an exponential gain taper followed by a DC offset and hard clamp:

```
gain   = 0.2 × 25^p          (p = MOD_SCALE_PARAM ∈ [0,1])
offset = MOD_OFFSET_PARAM × 5  (V, param ∈ [–1,+1])
V_bus  = clamp(V_src × gain + offset, –10, +10)
```

Gain table:

| p (SCALE knob) | gain  |
|---|---|
| 0.0 (full CCW) | 0.2×  |
| 0.5 (noon)     | 1.0×  |
| 1.0 (full CW)  | 5.0×  |

This is a 5-octave range in gain (0.2×–5×) on an exponential curve, implemented in hardware
as an exponential-law resistor network or a log-taper pot driving an inverting op-amp with
fixed feedback.

The simplest practical analog implementation is an inverting op-amp summer (U_MB_SUM) whose
input resistor for V_src is set by the SCALE pot (log-taper, 470 kΩ) in series with a fixed
floor resistor (R_MB_SRC = 22 kΩ), plus a second input resistor for the OFFSET pot
(linear-taper, ±5 V supply tap). A second stage inverts to restore correct polarity.
Both stages use one TL074CDT quad op-amp.

**Gain range derivation:**  
With R_f = 100 kΩ and R_src = R_MB_SRC + RV_MB_SCALE:  
  R_src_min = 22 kΩ (pot at zero) → G_max = 100/22 = 4.55× ≈ 5× ✓  
  R_src_max = 22 kΩ + 470 kΩ = 492 kΩ (pot fully CW) → G_min = 100/492 = 0.20× ✓  
A 470 kΩ log-taper pot in series with a 22 kΩ fixed floor resistor achieves 0.20×–4.55× range.

**Offset range:**  
With R_off = 100 kΩ feeding a ±5 V rail tap through a linear pot, the offset contribution at
the summing node is ±5 V (before inversion).

**Output clamp:**  
The op-amp supply rails are ±12 V; the DSP clamp of ±10 V is realized in hardware by back-to-
back Schottky diodes (BAT54S) to ±10 V reference rails, or simply by the rail limiting of the
subsequent attenuverter stages. A dedicated ±10 V clamp using two TL431 shunt references is
optional but recommended for accuracy.

### Per-Destination Attenuverter

Each of the 18 attenuverter destinations is identical:

1. Tip-switching Thonkiconn jack (PJ301M-12): tip is normalled to V_modbus via a 100 kΩ
   resistor; when a cable is inserted, the normalling resistor is broken and the external CV
   is presented directly.
2. 100 Ω series protection resistor.
3. BAT54S dual Schottky clamp to ±12 V (or ±5.1 V zeners for tighter protection).
4. Bipolar attenuverter pot (10 kΩ linear, centre-detent): wiper voltage is 0 V at noon,
   +V_src at full CW, –V_src at full CCW.  
   Hardware implementation: the pot is wired as a voltage divider between V_src and –V_src
   (generated by a TL074 inverter). Wiper → destination. This eliminates the need for a
   multiplying element.
5. Output: attenuated/inverted CV routed to the destination block input.

**Bipolar pot topology:**

```
V_src  ──┬── [R_top, upper half of pot] ──┬── [R_bot, lower half] ──┬── –V_src
          │                                 │                          │
        (top lug)                      (wiper = V_att)            (bottom lug)
```

At noon: V_att = (V_src + (–V_src)) / 2 = 0 V.  
Full CW: wiper at top → V_att = V_src.  
Full CCW: wiper at bottom → V_att = –V_src.

The –V_src rail for each group of attenuverters is generated by one TL074 inverter stage.
With 18 attenuverter destinations and 4 op-amp sections per TL074, 5 TL074s provide 20 inverter
stages (18 used, 2 spare). The Mod Bus Processor itself requires 2 op-amp stages (summer +
inverter), using 2 sections of a sixth TL074. Total: **6× TL074CDT**.

**VCA path (not an attenuverter):** the raw V_modbus normals directly into the VCA_INPUT jack's
tip-switch (handled in block 4); there is no block-3 attenuverter or inverter for the VCA. The
VCA_AMT depth control is a block-4 panel pot. (The former block-3 VCA_AMT attenuverter — RV5 +
its inverter — is removed, change 0018.)

**Mod bus output clamp (±10 V):** Back-to-back 10 V zeners (BZX84C10, SOT-23)
in the MB_INV feedback path. When V_modbus_inv exceeds ±10 V, the zeners conduct and
clamp the output. Zener tolerance = ±5 %, so clamp onset is 9.5–10.5 V (vs the DSP's hard
±10 V — an accepted hardware deviation). There is no MOD_CLIP LED.

**Distribution buffer:** V_modbus drives 18 × 10 kΩ attenuverter pots in parallel
(10 kΩ ÷ 18 ≈ 556 Ω total load) plus the raw VCA normal. At V_modbus = ±10 V this is ~18 mA.
To achieve reliable ±10 V swing at this load, MB_PROC_A uses both of its two spare
sections (halves C and D) wired in parallel as a unity-gain buffer — each half drives
~9.5 mA, well within TL074 limits. A 47 Ω series resistor on each output before
the join prevents oscillation from unequal saturation times.

**IC count summary:**

| Function | Op-amp sections used | TL074CDT | Ref |
|---|---|---|---|
| MB summer + polarity inverter | 2 | 1× | MB_PROC_A (halves A+B; C+D spare) |
| Destination inverters (−V_src for bipolar pots) | 18 (+2 spare) | 5× | MB_INV_1–5 |
| **Total** | **20 sections used** | **6× TL074CDT** | |

Note: U4 (the former MB_PROC_B LED-driver IC) is removed with the MOD LEDs (change 0018),
dropping the count from 7× to 6× TL074CDT. MB_PROC_A's two unused sections (C, D) and U9's
two unused sections remain spare.

---

## 3. Physical Design

> ✅ **Re-verified 2026-05-30** against the locked plugin + panel (change 0018). Source select
> (MOD_SRC SW7) added; per-band BP CV corrected FOCUS→TILT; MOD LEDs + driver removed; VCA
> attenuverter removed (raw bus normal handled in block 4). 6× TL074 (was 7×).

**Board assignment:** Utility board (no audio-frequency signal path); MOD_SRC switch + pots on the control board.

**Panel controls / jacks:**

| Item | Count | Type | Notes |
|---|---|---|---|
| MOD_INPUT jack | 1 | PJ301M-12 | External source (MOD_SRC pos 2); no LFO normal |
| MOD_SRC switch | 1 | DW5 3-pos (DPDT ON-ON-ON) | LFO 1 / LFO 2 / External |
| MOD_SCALE trimpot | 1 | 9 mm log | 0.2×–5× exponential taper |
| MOD_OFFSET trimpot | 1 | 9 mm linear | ±5 V |
| Destination attenuverter pots | 18 | 9 mm bipolar | Centre-detent, –1× to +1× |
| Destination override jacks | 18 | PJ301M-12 | Tip-switching; normalled to bus |

**Destination list (18 attenuverter destinations; VCA is a separate raw normal):**

| # | Jack enum | Attenuverter enum | Block | CV scaling at destination |
|---|---|---|---|---|
| 1 | LP1_FREQ_INPUT | LP1_FREQ_ATT_PARAM | 5 (LP1) | — |
| 2 | LP1_TILT_INPUT | LP1_TILT_ATT_PARAM | 5 (LP1) | — |
| 3 | LP1_RES_INPUT | LP1_RES_ATT_PARAM | 5 (LP1) | ÷10 |
| 4 | BP_FREQ_INPUT | BP_FREQ_ATT_PARAM | 6 (BP master) | — |
| 5 | BP_TILT_INPUT | BP_TILT_ATT_PARAM | 6 (BP master) | — |
| 6 | BP1_FREQ_INPUT | BP1_FREQ_ATT_PARAM | 6 (BP1) | — |
| 7 | BP1_TILT_INPUT | BP1_TILT_ATT_PARAM | 6 (BP1) | ×0.22 |
| 8 | BP1_DIST_INPUT | BP1_DIST_ATT_PARAM | 6 (BP1) | — |
| 9 | BP2_FREQ_INPUT | BP2_FREQ_ATT_PARAM | 6 (BP2) | — |
| 10 | BP2_TILT_INPUT | BP2_TILT_ATT_PARAM | 6 (BP2) | ×0.22 |
| 11 | BP2_DIST_INPUT | BP2_DIST_ATT_PARAM | 6 (BP2) | — |
| 12 | BP3_FREQ_INPUT | BP3_FREQ_ATT_PARAM | 6 (BP3) | — |
| 13 | BP3_TILT_INPUT | BP3_TILT_ATT_PARAM | 6 (BP3) | ×0.22 |
| 14 | BP3_DIST_INPUT | BP3_DIST_ATT_PARAM | 6 (BP3) | — |
| 15 | HP_FREQ_INPUT | HP_FREQ_ATT_PARAM | 7 (HP) | — |
| 16 | HP_RES_INPUT | HP_RES_ATT_PARAM | 7 (HP) | ÷10 |
| 17 | LP2_FREQ_INPUT | LP2_FREQ_ATT_PARAM | 8 (LP2) | — |
| 18 | LP2_RES_INPUT | LP2_RES_ATT_PARAM | 8 (LP2) | ÷10 |

Per-band BP CV uses **TILT** (not FOCUS — BP FOCUS/Q has no CV input in the plugin). The
`×0.22` (per-band TILT) and `÷10` (resonance) factors are plugin scaling laws applied at the
**destination block's CV summing node** (blocks 5–8), not in the block-3 attenuverter.

**VCA (raw normal, not an attenuverter):** VCA_INPUT is in the Block 4 panel zone; the raw
V_modbus normals into its tip-switch (no attenuverter). VCA_AMT depth is a block-4 pot.

**Power estimate:**

6× TL074CDT at ≈ 2.6 mA per IC (TI datasheet: 0.65 mA/ch × 4 ch at ±12 V).

- +12 V: ~16 mA
- −12 V: ~16 mA

---

## 4. Component Requirements

Component set: see the generated BOM `kicad/pogo-bom.csv` (rows with `Block = block-3`),
sourced from `specs/components.yaml` (the per-ref design manifest) and enriched by the
`components/` registry (MPN, footprint, datasheet). Verification status: `specs/STATUS.md`.
