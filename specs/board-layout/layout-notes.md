# POGO Board Layout Notes — 48HP

## Status: Architecture Under Review 🔄

The 40HP 3-board split layout has been archived. The 48HP topology has a significantly
different control count and panel dimensions. Board architecture is being reconsidered.

---

## 48HP Module Dimensions

| Property | Value |
|---|---|
| Panel width | 48HP = 243.84mm |
| Panel height | 3U = 128.5mm usable |
| Max PCB depth from panel | 35mm (Doepfer A-100); up to 60mm in deep cabinets |

---

## Control Count (48HP topology)

From `docs/plugin-topology.md`:

| Type | Count |
|---|---|
| Params (knobs, sliders, switches, trimpots) | 46 |
| Inputs (CV + audio jacks) | 24 |
| Outputs (CV + audio jacks) | 6 |
| LEDs | 5 |
| **Total panel elements** | **81** |

Breakdown by type (from `tools/panel-data.yaml`):
- XL knobs: 5 (LP1_FREQ, BP_OFFSET, BP1_FREQ, BP2_FREQ, BP3_FREQ)
- Large knobs: ~12
- Sliders (V45°): 2 (HP_FREQ, LP2_FREQ)
- Trimpots: ~10
- DW3 toggles (2-pos): 2 (GAIN_MAIN, GAIN_BP3)
- DW5 toggles (3-pos): 3 active (BP1/2/3_DIST_MODE) + MOD_SRC (planned, not yet in plugin)

> **Panel hardware — toggles vs pots.** All toggles are Thonk-sourced Dailywell 2M
> sub-mini units (DW3/DW5) with a **10-48 UNS bushing (Ø6.00mm) through a Ø4.95mm
> panel hole**, secured with their own 10-48 nuts + locking washer. This differs
> from the 9mm Alpha pots' **M7×0.75 bushings** (Ø5.5mm nut). The two thread families
> are independent — each part ships with its own nuts — so they coexist on the same
> panel without conflict; only the panel cutout diameters differ (Ø4.95mm vs the pot
> bushing hole). Panel DRC models the toggle washer at r=3.8mm, the pot nut at r=5.5mm.
- Jacks total: 30 (24 inputs + 6 outputs)

---

## Architecture Options Being Evaluated

### Option A: 3-Board Split (wider boards, same topology)
Same concept as 40HP design but boards are wider.

```
Control board: ~244mm × 80mm (full 48HP width)
  - All Thonkiconn jacks, all pots/knobs, all switches
  - PCB-mount; jack nuts and pot hardware mount direct to panel
  - Connects to utility board via IDC ribbon cables

Utility board: ~244mm × 80mm
  - Mod bus processor, 22 attenuverter circuits, expo converters
  - Receives control voltages from control board via IDC ribbon
  - Connects to audio board via stacking headers

Combined audio board: ~244mm × 100mm
  - L+R audio path (Blocks A/1/VCA/LP1/BP/HP/LP2/B)
  - 4mm center GND guard strip between L and R
  - Stacks behind utility board on M3 standoffs
```

**Pros**: Proven topology; clean separation of concerns.
**Cons**: 48HP width makes control board very long (harder to flex without stress on ribbon connectors). Component density is lower than 40HP — may have more empty real estate.

### Option B: 2-Board Split (combined utility+audio)
Combine utility functions onto the audio board, reducing board count.

```
Control board: ~244mm × 80mm (same as Option A)
  - All panel controls (same)
  - Connects to main board via single wide IDC ribbon or flexible PCB

Main board: ~244mm × 140mm
  - Utility (mod bus, attenuverters) + audio (all blocks)
  - L and R channels side-by-side with center GND strip
```

**Pros**: Fewer connectors = fewer failure points; simpler assembly; more routing space.
**Cons**: Single large board harder to debug; L/R cross-talk risk if layout is poor;
thermal coupling between high-gain and low-noise sections.

### Option C: 4-Board Split (add dedicated LFO/mod board)
Break out the mod system and LFOs onto their own dedicated board.

```
Control board: ~244mm × 70mm
Mod/LFO board: ~120mm × 80mm (half-width)
Audio board L: ~120mm × 100mm
Audio board R: ~120mm × 100mm (mirror of L)
```

**Pros**: Each board has a clear, single purpose; L and R completely isolated.
**Cons**: More connectors; complex assembly; likely the most expensive option.

---

## Decision Factors

The architecture decision should be driven by:

1. **Thermal isolation**: High-gain stages (BP section, distortion) generate heat.
   Keeping them away from expo converters reduces calibration drift.

2. **Connector complexity at 48HP**: At 244mm, the control-board IDC ribbon must carry
   46 pots + 30 jacks = 76 signals. A single 80-pin ribbon is feasible but requires careful
   layout on both boards.

3. **Manufacturability**: 2-board is simpler to assemble; 3-board is easier to debug.

4. **Cost**: Fewer boards = lower PCB cost; more boards = easier rework.

**Preliminary recommendation**: **Option A (3-board)** until audio prototype proves layout.
The 3-board split gives the cleanest separation for bring-up and debugging. Consolidate
to 2-board in a future revision if assembly complexity is a concern.

---

## Next Steps

- [ ] Decide board architecture (see options above)
- [ ] Define control board connector pinout (all 76 control signals)
- [ ] Define utility ↔ audio board stacking header pinout
- [ ] Confirm component placement rules for 48HP dimensions
- [ ] Begin KiCad schematic for control board (many reference values in kicad/ already)

---

## 40HP Archive

Old layout-notes.md (40HP 3-board split, full connector pinouts) is at:
`specs/archive/40hp-era-2026-05/layout-notes.md`
