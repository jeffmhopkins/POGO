# Block 4: VCA
Pre-LP1 voltage-controlled amplifier; accents or ducks the signal entering the filter stack via mod bus or external CV.

DSP source: `plugin/src/dsp/VcaBlock.hpp`, `plugin/src/Pogo.cpp` (control 382–386; main VCA 387–389; ALT VCA → BP3 439–441)

---

## 1. Intent

Block 4 is a stereo VCA inserted between the pre-gain stage (Block 1) and the LP1 filter
(Block 5). Its purpose is dynamic amplitude control of the signal before it enters the filter
stack — accent, ducking, or gating driven by the mod bus or an external envelope.

Two trimpots govern behaviour:

- **VCA_AMT** (bipolar, –1 to +1): determines how much and in which direction the CV affects
  gain. At noon (0), the VCA is transparent — gain is unity regardless of CV. Turned CW
  (positive), the CV accents the signal: CV=0 → muted, CV=5 V → unity. Turned CCW (negative),
  the CV ducks the signal: CV=0 → unity, CV=5 V → muted.

- **VCA_OFS** (unipolar, 0–1): adds a fixed floor to the effective CV before the gain
  calculation. At noon (0.5), a 2.5 V floor is added, so the signal never fully disappears
  even with a zero-volt CV at positive AMT settings. This is a "minimum volume" or
  "always-on" control.

The VCA_INPUT jack normalles to V_modbus, so without any patch cable the mod bus drives the
VCA directly. Plugging into VCA_INPUT overrides this.

Both channels (L, R) are processed identically — the same CV and parameter values are applied
to both, maintaining stereo balance.

**ALT-BP VCA (added 2026-05-30, change 0018):** per the locked plugin (`Pogo.cpp:439–441`),
the ALT-BP signal (block-1 `ALT_OUT_L/R`) passes through a **second** VCA driven by the **same**
control (`V_ctrl`) as the main path, then feeds **BP3 only** (block 6). So the ALT voice is
gated by the VCA exactly like the main voice. This is realized with two more THAT 2180 cells
(ALT-L, ALT-R) sharing `V_ctrl`; their outputs leave as boundary nets to the block-6 BP3 input
selector (which chooses ALT-VCA vs the main band depending on whether the ALT jacks are patched).

---

## 2. Theoretical Design and Topology

> ✅ **CORRECTED 2026-05-29; re-verified + extended 2026-05-30 (change 0018)** — THAT2180
> current-in/current-out topology (datasheet pinout), R_in + I/V op-amp per channel, Ec+ control.
> 0018 additions: (a) the **ALT-BP VCA cell** (2 more THAT2180 on the shared `V_ctrl`, → BP3);
> (b) **VCA_OFS placement corrected** — OFS is now summed into the CV *before* the AMT
> attenuverter (matching the plugin order `vcaCV = clamp(raw+OFS·5)` then the AMT law), so AMT=0
> gives unity regardless of OFS. Exact CV→Ec+ scaling remains Phase-3R bring-up.

### Gain Law (DSP and hardware)

```cpp
float normCV = clamp(cvV / 5.f, 0.f, 1.f);
float control;
if (amtParam >= 0.f)
    control = 1.f - amtParam * (1.f - normCV);   // 1 − AMT×(1−CV)
else
    control = 1.f + amtParam * normCV;            // 1 − |AMT|×CV
control = clamp(control, 0.f, 1.f);
// dB-law: G = 10^(2*(control-1))  →  0 dB at control=1, −40 dB at control=0
float G = (control <= 0.001f) ? 0.f : std::pow(10.f, 2.f * (control - 1.f));
// output = input × G
```

Key operating points:

| AMT  | CV    | control | G (dB-law) | Description |
|------|-------|---------|------------|-------------|
| 0    | any   | 1.0     | 1.00 (0 dB)   | Unity always (AMT at noon) |
| +1   | 0 V   | 0.0     | 0.00 (−∞ dB)  | Muted |
| +1   | 5 V   | 1.0     | 1.00 (0 dB)   | Accent: unity at 5 V |
| +1   | 2.5 V | 0.5     | 0.10 (−20 dB) | Mid-CV accent; perceptually ~half loudness |
| –1   | 0 V   | 1.0     | 1.00 (0 dB)   | Through (duck mode, no CV) |
| –1   | 5 V   | 0.0     | 0.00 (−∞ dB)  | Ducked fully at 5 V |
| –1   | 2.5 V | 0.5     | 0.10 (−20 dB) | Mid-CV duck; perceptually ~half loudness |

The OFS floor is applied before this calculation:

```
eff_CV = clamp(raw_CV + VCA_OFS × 5, 0, 10)
```

At default OFS = 0.5: eff_CV = raw_CV + 2.5 V (floor 2.5 V; signal never fully silenced
at positive AMT unless raw_CV goes negative, which is clamped away).

### Hardware Analog Model — THAT 2180 (current-in / current-out)

Per the datasheet (Doc 600029 Rev 02, Table 1), the THAT 2180 is a **current-in / current-out**
Blackmer VCA. Pinout: **Input=1, Ec+=2, Ec−=3, Sym=4, V−=5, Gnd=6, V+=7, Output=8**. Gain is
set by a voltage at the **Ec+** control port:

```
G_dB = Ec+ / (6.1 mV/dB)      (Ec+/Gain constant = +6.1 mV/dB; Ec−/Gain = −6.1 mV/dB)
```

Matching the DSP law `G = 10^(2·(control−1))` ⇒ `G_dB = 40·(control−1)` gives the control target:

```
Ec+ = 6.1 mV/dB × 40 × (control−1) = 244 mV × (control−1)
       control = 1 → Ec+ = 0   (0 dB, unity)
       control = 0 → Ec+ = −244 mV   (−40 dB)
```

**Audio path (per channel, single inversion):**
- `AUDIO_IN → R_in (20 kΩ) → Input (pin 1)`. Pin 1 is a current input (≈ virtual ground);
  `I_in = AUDIO_IN / R_in`.
- `Output (pin 8) → transimpedance op-amp (TL072 half, (+)=AGND, R_f feedback) → AUDIO_OUT`.
  `AUDIO_OUT = −I_out·R_f`; with `R_f = R_in (20 kΩ)`, gain = −1 at 0 dB. The single inversion
  is compensated by LP1's inverting SUM_AMP downstream.
- `Ec− (pin 3)`, `Sym (pin 4, factory pre-trimmed)` and `Gnd (pin 6)` → AGND. `V+ (7)=+12 V`,
  `V− (5)=−12 V`.

This requires **one I/V op-amp half per channel** (U6 = dual TL072) — there is no voltage
output pin and no IN−/OUT−/OUT-termination (the earlier differential-VCA model was wrong).

**Unity-gain calibration:** a Bourns 3224W (500 Ω) per channel trims the Ec+ offset so
`Ec+ = 0` ⇒ exactly 0 dB, matching L and R.

**CV conditioning (U63 = dual TL072) — OFS summed BEFORE the AMT attenuverter:**

The plugin adds the OFS floor to the CV *before* the AMT gain law (`vcaCV = clamp(raw + OFS·5,
0, 10)`, then `control = 1 − AMT·(1−normCV)`). The analog chain mirrors that order:

1. Raw CV enters through a 100 Ω series resistor + BAT54S clamp (standard CV protection) → the
   protected node CVP.
2. **CV + OFS summer (U63-A):** an inverting summer combines CVP with the VCA_OFS floor (RV45,
   referenced to set the effCV = 5 V unity pivot) → `−effCV`.
3. **Inverter (U63-B):** inverts `−effCV` → `+effCV`.
4. **AMT attenuverter:** the bipolar VCA_AMT pot (RV44) sits **symmetrically** across `+effCV`
   (CW) and `−effCV` (CCW); the wiper is `V_ctrl = AMT·effCV`. Because the pot is symmetric about
   ±effCV, the **center detent (AMT = 0) gives V_ctrl = 0 → unity regardless of OFS** — exactly
   the plugin behavior, and the fix vs the old "OFS summed after AMT" topology.
5. `V_ctrl` drives all four Ec+ pins (main L/R + ALT L/R) via per-channel unity trims
   (RV1, RV2, RV46, RV47).

The exact summer/Ec scaling (to hit `Ec+ = 244 mV·(control−1)`), the effCV−5 V pivot reference,
and any `V_ctrl` wiper buffer are nominal here and set at **Phase-3R bring-up** — consistent with
the project's intentional DSP↔hardware deviation (linear DSP gain index vs. true dB-law hardware).

### ALT-BP VCA cell

Two additional THAT 2180 cells (U78 = ALT-L, U79 = ALT-R) mirror the main audio path
(R_in → THAT 2180 → I/V op-amp U80), but take their audio from block-1 `ALT_OUT_L/R` and emit
`ALT_VCA_OUT_L/R` to the block-6 BP3 input selector. They share the **same** `V_ctrl` as the
main cells (via trims RV46/RV47), so the ALT voice tracks the main VCA gain identically — as
the plugin does (`VcaBlock::process(altL/R, vcaAmt, vcaCV)`). No separate CV conditioning is
needed; U63B's `V_ctrl` now fans out to four Ec+ trims (light load).

**Stage boundaries:** Block 1 (OPA1612 output, <50 Ω) drives R_in (20 kΩ) — negligible loss;
VCA I/V outputs (op-amp, <100 Ω) drive LP1 / BP3 input resistors — negligible loss.

---

## 3. Physical Design

> ✅ **CORRECTED 2026-05-29; extended 2026-05-30 (change 0018)** — THAT2180
> current-in/current-out topology (datasheet pinout), R_in + I/V op-amp per channel, Ec+
> control. 0018 added the ALT-BP VCA cell (2 more THAT2180 + I/V) and corrected the VCA_OFS
> placement. Verified in `specs/block-4/block-4.nets.yaml`. CV→Ec+ scaling is Phase-3R bring-up.

> 🔧 **Change 0020 HIGH-3 (Ec+ unity-trim topology fix):** the 4 unity trims (RV1/2/46/47) were wired
> as **series rheostats into the high-Z Ec+ port** — which can't set a DC offset (SPICE `vca_ecplus.cir`:
> ~0.004 dB authority). Replaced with a **voltage-injection trim**: the AMT wiper is now buffered
> (**new U97-A** TL072 unity buffer → `V_CTRL_BUF`, decoupling the 4 cells, which the old unbuffered
> wiper coupled) and drives each Ec+ via `R_ec` (10k, R235–R238); each trim (now **10k**) is a divider
> across a shared **±1.2 V reference** (R233/R234 = **11.3 k**, sized for the 4 parallel trim loads —
> change 0025 fix; 45.3 k was wrong, see below), wiper → `R_inj` (1M, R239–R242) → Ec+. Gives ±~2 dB
> unity authority and nulls the port's bias-current offset (SPICE: `sim/vca_ecplus.cir` authority +
> `sim/vctrl_buffer.cir` g_ctrl≈0.98 + `sim/ref_divider.cir` ±1.195 V ref). The same fix is applied to
> the block-6 per-band DRIVE VCAs (RV51–56; ref R243…R256 = **22.6 k** for their 2-trim loads).
>
> **Change 0025 — ref divider corrected:** R233/R234 were originally 45.3 k, which (with all four
> unity trims loading REF_P↔REF_N in parallel = 2.5 k) set the reference to only ±0.32 V → ~±0.5 dB
> Ec+ authority, not the intended ±2 dB. Resized to 11.3 k (→ ±1.195 V). Found by the SPICE-math gate.

**Board assignment:** Audio board (carries audio-frequency signal; THAT 2180 and CV
conditioning are co-located with the signal path). The VCA_AMT/OFS pots are on the control board.

**Panel controls / jacks:**

| Item | Qty | Type | Notes |
|---|---|---|---|
| VCA_INPUT jack | 1 | PJ301M-12 | Tip-switching; normalles to mod bus V_modbus |
| VCA_AMT trimpot (RV44) | 1 | 9 mm, centre detent | Bipolar –1× to +1× |
| VCA_OFS trimpot (RV45) | 1 | 9 mm | Unipolar 0–1 (CV floor) |

No LEDs for this block; status is not indicated on panel. The ALT-BP VCA reuses block-1's
existing ALT_BP_L/R jacks as its audio source — no new panel controls.

**Stereo / cell implementation:**

**Four THAT 2180 ICs**: U4/U5 (main L/R) and U78/U79 (ALT-BP L/R). All four share one `V_ctrl`
(applied to each Ec+ via a per-channel unity trim RV1/RV2/RV46/RV47), so the main and ALT
voices track identically. Two dual TL072 I/V converters: U6 (main) + U80 (ALT). U63 (dual TL072)
does the CV conditioning (CV+OFS summer + inverter).

**Signal levels:**

- Audio into R_in → Input (pin 1): from pre-gain / ALT block, ±10.5 V max (clipped upstream).
- I/V op-amp output: same range, attenuated by the dB-law gain.
- eff_CV: 0–10 V (clamped).
- Ec+ control: 0 V (unity) down to ≈ −244 mV (−40 dB), per the 6.1 mV/dB constant.

**Power estimate:**

- 4× THAT 2180: ~4 mA each = ~16 mA per rail.  (THAT Corp datasheet: Icc ≈ 4 mA typ)
- 3× TL072CDT (dual, U6/U63/U80): ~2.8 mA each ≈ ~8.5 mA per rail.
- Total: +12 V ~25 mA, −12 V ~25 mA.

---

## 4. Component Requirements

Component set: see the generated BOM `kicad/pogo-bom.csv` (rows with `Block = block-4`),
sourced from `specs/components.yaml` (the per-ref design manifest) and enriched by the
`components/` registry (MPN, footprint, datasheet). Verification status: `specs/STATUS.md`.
