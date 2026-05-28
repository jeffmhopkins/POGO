# aux: Panel Switch Sourcing & Footprint Reference
Design status: [x] draft → [ ] reviewed → [ ] validated on prototype

Sourcing/selection reference for POGO's panel-mount 2-position and 3-position
switches. Compiled from a multi-source web survey of Eurorack DIY practice
(ModWiggler, r/synthdiy, Thonk, Love My Switches, Befaco/Mutable/Music Thing
ecosystems) with adversarial verification against manufacturer datasheets,
Digi-Key product attributes, and the official KiCad footprint library index.

> Stock/price figures are point-in-time (May 2026) and volatile — **re-verify at
> the distributor before locking a BOM.** Core technical facts (pole/throw,
> ON-ON-ON behavior, footprint existence, part existence) were adversarially
> confirmed; quantitative stock/price drifts where noted.

---

## Overview

POGO uses three flavors of panel switch (see signal chain in `CLAUDE.md`):

| Function | Block | Required config | Current spec | Recommended part |
|---|---|---|---|---|
| `GAIN_MAIN` / `GAIN_BP3` (SW1/SW2) — 1×/5×, **stereo L+R on one actuator** | block-1 | **2-position DPDT (2PDT)** | `eg_2pos` (EG1218) | **E-Switch EG2219** |
| `BP_POL` (SW_POL) — +/− polarity | block-6 | 2-position SPDT | 2-pos SPDT slide | **E-Switch EG1218** |
| `BP_DIST` (SW_DIST) — soft/hard/fold mode select → 2 logic lines | block-6 | 3-position (1 pole used) | `eg_3pos` (EG2301) | **E-Switch EG2301** (DP3T) or **C&K OS103011MS8QP1** (true SP3T) |

> ⚠️ **Flagged BOM inconsistency (not yet fixed):** `block-1/spec.md` describes
> SW1/SW2 as a **2PDT** (DPDT) slide that switches both L and R channels with one
> actuator, but the panel/components staple is **EG1218, which is SPDT
> (single-pole)** and cannot route a stereo pair. The correct in-stock DPDT slide
> with an official KiCad footprint is **E-Switch EG2219**. Reconcile
> `block-1/spec.md`, `components.yaml`, and `tools/panel-data.yaml` before fab.

---

## Recommendation summary (best → worst for compact Eurorack)

Selection criteria for a compact system, in priority order:
**(1)** correct pole/throw for the job, **(2)** in stock at a major distributor,
**(3)** ready-to-use KiCad footprint (ideally the official `Button_Switch_THT`
library), **(4)** mechanical robustness on the panel, **(5)** cost.
Behind-panel depth is *not* a differentiator here — every candidate fits POGO's
35 mm depth budget comfortably — so footprint availability and pole count drive
the ranking.

### 2-position

| # | Part | Config | Mount / actuator | Stock (Digi-Key, May'26) | Price q1 / q100 | KiCad footprint |
|---|------|--------|------------------|---------------------------|------------------|-----------------|
| **1** | **E-Switch EG2219** | **DPDT** ON-ON | THT right-angle, 9 mm act., 500 mA/15 VDC | 20,948 ✅ Active | $1.13 / $0.80 | ✅ **Official** `SW_E-Switch_EG2219_DPDT_Angled` (Button_Switch_THT) |
| **2** | **E-Switch EG1218** | SPDT ON-ON | THT vertical, 2 mm act., 200 mA/30 VDC, 11.6×4.0×7.4 mm | 37,212 ✅ Active | $0.72 / $0.51 | ⚠️ Not in std lib — Digi-Key KiCad lib `Switch_Slide_11.6x4mm_EG1218`, SnapEDA, UltraLibrarian |
| **3** | **C&K JS202011CQN / AQN** | DPDT ON-ON | THT straight / right-angle | AQN backorder; verify CQN | ~$0.75 | ✅ **Official** `SW_CuK_JS202011CQN_DPDT_Straight` / `SW_CuK_JS202011AQN_DPDT_Angled` |
| **4** | **E-Switch EG1271** | SPDT ON-ON | THT vertical, 2 mm act., 300 mA/30 VDC | 3,933 ✅ Active | $0.94 / $0.66 | ✅ In std lib but **misnamed** `SW_E-Switch_EG1271_DPDT` (part is SPDT) |
| **5** | **Dailywell SL1** (`5FS1S102M2QES`) / Taiway slide | SPDT ON-ON | THT PCB-pin 2.54 mm, **nuts + washer incl.** | Thonk / Befaco ✅ | ~£1.55 | ❌ No published footprint — roll-your-own generic 3-pin |
| **6** | Generic SS-12D00 / SS12D00G | SPDT | THT, varies per batch | Tayda / AliExpress (commodity) | ~$0.10 | ❌ No authoritative datasheet/footprint — **avoid for documented BOM** |

### 3-position

| # | Part | Config | Mount / actuator | Stock | Price q1 | KiCad footprint |
|---|------|--------|------------------|-------|----------|-----------------|
| **1** | **E-Switch EG2301** (A/B/C = longer act.) | **DP3T** ON-ON-ON | THT vertical, ~11 mm, 200 mA/30 VDC | ~3,300 ✅ Active | ~$0.84 | ⚠️ SnapEDA (AI-generated — **verify vs datasheet**) |
| **2** | **C&K OS103011MS8QP1** | **true SP3T** ON-ON-ON | THT vertical, 12.6×4.3×4.0 mm, 100 mA/12 VDC | stocked (multi-distributor) | ~$0.80–1.20 | ⚠️ SnapEDA (AI-generated — verify) |
| **3** | **Dailywell DW2 / DW5** or **Taiway 100-SP3** toggle | SPDT ON-OFF-ON / DPDT ON-ON-ON | PCB-pin toggle, **nuts+washer incl.**, round hole | Thonk / LMS ✅ | $1.90–2.42 | ❌ Roll-your-own generic toggle footprint |
| **4** | Generic SK-23D07 / SS-23D07 | DP3T | THT horizontal side-knob, ~0.5 A/50 V | Tayda / AliExpress | ~$0.20 | ❌ No verified footprint |
| **5** | **E-Switch EG1315AA** | SP3T | **SMT, side-actuated, 1.4 mm** | stocked | — | unconfirmed — **not a panel switch; avoid for front panel** |

> **Non-existent parts** (verified absent from the E-Switch catalog — guard against
> typos): **EG2218** and **EG2401**. The real DP3T through-hole family is **EG23xx**
> (EG2301, EG2305, EG2308A, EG2310, …).

---

## Toggle switches (alternative to slides)

The Eurorack-DIY de-facto PCB-mount toggle is the **Taiway 100-series**
(Love My Switches, US) and its functional twin **Dailywell** (Thonk, UK):
PCB-pin on a 2.54 mm grid, ~$1.50–2.20, supplied with two nuts + locking washer,
round panel hole. Full configuration range:

| Dailywell | Config |
|---|---|
| DW1 | SPDT ON-ON |
| DW2 | SPDT ON-OFF-ON |
| DW3 | DPDT ON-ON |
| DW4 | DPDT ON-OFF-ON |
| DW5 | DPDT ON-ON-ON |
| DW9 | SPDT ON-OFF-(ON) momentary |
| DWLP1 / DWLP2 | **Low-profile** SPDT ON-ON / ON-OFF-ON (depth mitigation) |

Trade-off: **no official KiCad footprint** — builders use a generic 3/6-pin
2.54 mm toggle footprint and rely on the round cutout for mechanical fit.

Premium industrial bat toggles — **C&K 7000** (7101 SPDT ON-ON, 7103 SPDT
ON-OFF-ON, 7201 DPDT, 7203 DPDT ON-OFF-ON), **NKK M-series**, **E-Switch 100**,
**APEM 5000** — are mostly **solder-lug**, 1/4-40 threaded bushing, ~$3–11+ qty1,
with SnapEDA-only footprints. Robust but overkill and pricey for compact DIY.
(C&K 7101 qty1 ≈ $6.70–10 depending on variant; cap/ON-OFF-ON DPDT 7203 stock
runs thin — only ~41 units seen at Digi-Key.)

---

## Gotchas / assembly notes (community-verified)

- **Short slide actuators (~2 mm):** the #1 reported slide complaint. Verify the
  actuator clears your actual panel thickness with usable travel before
  committing — tall-actuator stock variants are scarce.
- **PCB-pin slides have no panel nut:** held only by solder joints + the panel
  cutout, so they **wobble** under finger pressure. Toggles with a threaded
  bushing/nut are mechanically anchored. A below-panel nut can stabilize some
  builds.
- **Rectangular cutout vs round hole:** slide cutouts can warp thin panels;
  builders generally prefer round holes (toggles). Not a depth issue — both
  styles fit POGO's 35 mm budget.
- **Toggle pin spacing is family-specific:** Dailywell sub-mini = **2.54 mm**,
  mini = **4.7 mm** — footprints are **not** interchangeable.
- **SnapEDA footprints for EG2301 / OS103011MS8QP1 are AI-generated**
  ("not created by SnapMagic") — dimensionally check against the manufacturer
  datasheet before fabrication.
- **KiCad C&K prefix is `SW_CuK_`**, not `SW_CK_`/`SW_C&K_` — tooling that
  searches by a "C&K" prefix will miss the JS202011 footprints.
- **Official `Button_Switch_THT` library coverage is thin:** only **EG2219**,
  **EG1271**, and the C&K **JS/OS *slide*** parts ship in it. EG1218, EG2301, and
  all C&K *toggles* must come from the Digi-Key KiCad library, SnapEDA, or
  UltraLibrarian.

---

## Used By

| Block | Instance | Recommended part | Notes |
|---|---|---|---|
| block-1 | SW1 `GAIN_MAIN`, SW2 `GAIN_BP3` | E-Switch EG2219 (DPDT) | One pole per channel; switches stereo L+R together. **Supersedes the SPDT EG1218 currently implied — see flagged inconsistency above.** |
| block-6 | SW_POL `BP_POL` | E-Switch EG1218 (SPDT) | DIY staple; correct 2-pos single-pole config. |
| block-6 | SW_DIST `BP_DIST` | E-Switch EG2301 (DP3T) or C&K OS103011MS8QP1 (SP3T) | Common pole + 3 throws → decode to 2 select lines for the CD4053 mux (`aux-distortion.md`). EG2301 = in deep stock, one pole unused; OS103011 = cleaner single-pole part, SnapEDA footprint must be verified. |

---

## Sources (representative; all retrieved during the survey)

- E-Switch EG2219 — Digi-Key product page; KiCad `SW_E-Switch_EG2219_DPDT_Angled` (Button_Switch_THT)
- E-Switch EG1218 — Digi-Key; SnapEDA; Digi-Key KiCad library `Switch_Slide_11.6x4mm_EG1218`
- E-Switch EG1271 — Digi-Key (SPDT, 300 mA); KiCad `SW_E-Switch_EG1271_DPDT` (misnamed)
- E-Switch EG2301 — Digi-Key; SnapEDA (DP3T ON-ON-ON); LCSC datasheet
- C&K OS103011MS8QP1 — Newark; C&K OS-series datasheet; SnapEDA (AI-generated)
- C&K JS202011AQN/CQN — Digi-Key; KiCad `SW_CuK_JS202011*` (Button_Switch_THT)
- C&K 7000-series — C&K datasheet; Digi-Key (7101SYZQE et al.); SnapEDA
- Taiway 100-series — Love My Switches product pages
- Dailywell DW/SL1/DWLP — Thonk shop pages
- Befaco switch range — shop.befaco.org
- Community consensus/gotchas — ModWiggler threads, sdiy.info wiki, Thonk/LMS catalog notes
- KiCad library index — kicad.github.io/footprints/Button_Switch_THT.html
