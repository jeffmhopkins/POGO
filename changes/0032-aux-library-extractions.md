# 0032 — aux library extractions: new primitives + cells + Composes links

- **Slug:** aux-library-extractions  **Branch:** `change/0032-aux-library-extractions`
- **Lane:** B (tooling + test fixtures / library docs).
- **Status:** OPEN
- **Opened:** 2026-05-31
- **Blocks:** none (aux library; extracted FROM blocks but does not edit them).   **Boards:** n/a

## Intent
Phase 3 (final) of the aux library. Extract the genuinely-reusable sub-circuits identified in the scrub
into NEW typed library entries (`spec.md` + hardcoded `sim/` decks), and wire the **Composes:**
cross-links so composed cells reference their primitives. Each new entry is generalized from its source
block (the proven block decks) and reconciled against the live design.

## The 11 new entries
| Type | Entry | Extracted from | Core sim |
|---|---|---|---|
| filter | **gm-c-integrator** (primitive) | block-5/7/8 OTA loop | corner f=gm/(2πC) |
| filter | **voct-expo-divider** (primitive) | block-7/5/8 expo_voct | V_T·ln2 mV/oct base divider |
| vca | **ref-injection-trim** | block-4 ref_divider + vca_ecplus | ±ref level + injection authority |
| distortion | **soft-clip** | block-6-dist dist_clip (SC) | tanh diode-chain ±1.4V soft knee |
| distortion | **hard-clip** | block-6-dist dist_clip (HC) | back-to-back zener ±5.8V |
| distortion | **wavefolder** | block-6-dist wf_fold | Buchla 2·Vclamp−Vin reflection |
| modulation | **inverting-summer** (primitive) | block-3 mb_* | −Σ(Rf/Rin)·Vin |
| modulation | **schmitt-trigger** (primitive) | block-2 lfo | trip thresholds ±V_sat·R7/(R5+R7) |
| utility | **output-buffer** | block-B out_buffer | unity + 1k series div + ±11V clamp |
| utility | **clip-detector** | block-6-dist clip_threshold | ±4V window comparator + hysteresis |
| led | **led-breathing** | block-2 led_bias/led_slope | NPN level-shift I_LED∝(V_tri+5) |

## Composes wiring (composed cell → primitive)
- filter/ota-c-svf → gm-c-integrator ; filter/expo-converter → voct-expo-divider
- modulation/lfo-core → schmitt-trigger (+ gm-c-integrator) ; mod-bus-core → inverting-summer ;
  attenuverter → inverting-summer
- vca/vca-cell → ref-injection-trim ; distortion/overview → soft-clip + hard-clip + wavefolder

## Pipeline
1. **Write** [4 parallel agents] — author each new entry's spec.md (CLAUDE template + Type/Composes/Used-By)
   + hardcoded `sim/` decks (adapt from the source block deck, generalize), reconcile vs the source block,
   and wire the Composes links into the related composed cells.
2. **Verify** [parallel adversarial] — Q1/Q2 + Q3′ non-vacuous (library form).
3. **Integrate** — fix findings, full gate stack, finalize `_LIBRARY.md` (all entries ✅), mark COMPLETE.

## Decisions log
- 2026-05-31: user chose "Everything reusable" — these 11 include the standalone primitives
  (gm-c-integrator, voct-expo-divider, inverting-summer, schmitt-trigger) that the existing composed
  cells will reference via Composes, plus the high-value extracted cells (wavefolder, clip cells, LED,
  clip-detector, output-buffer, ref-injection-trim). The block-3 spec 10k/50k flag (from 0031) is handled
  as a separate block-side change, not here.

## Stage 1 — write (4 parallel) ✅ — 11 new entries + 16 sim decks + Composes links, all PASS
- **filter primitives:** gm-c-integrator (corner + phase; fixed a radians-units bug), voct-expo-divider
  (V/oct slope + octave ratios). Composes → ota-c-svf, expo-converter.
- **distortion cells:** soft-clip, hard-clip, wavefolder (signature; ×2 emerges from Rg/Rf). Composes → overview.
- **modulation primitives:** inverting-summer, schmitt-trigger (real hysteretic loop). Composes → lfo-core,
  mod-bus-core, attenuverter.
- **utility+vca+led:** output-buffer, clip-detector, ref-injection-trim (self-corrected an injection sign
  to match block-4), led-breathing. Composes → vca-cell.
- All hardcoded library form (NO netlist_bind); each falsifiable quantity emerges from modeled Rs.

## Stage 2 — verify-intent (2 parallel adversarial) ✅ — ALL 28 new-deck assertions SOUND
Library bar (Q1 computes / Q2 spec-derived / Q3′ non-vacuous via deck perturbation). Both reviewers ran
live perturbation probes: every falsifiable quantity moves+fails when its component is perturbed (gm/C
separable — NOT self-fulfilling; wavefolder ×2 from Rg/Rf; schmitt from R_a/R_b on a real bistable loop;
ref-injection collapses to 0.322V on the 45k3 regression; clip thresholds reference live divider nodes;
LED base voltages from the superposition). All [NV] values (clamp ±11V, ±5.8/±1.4 clip, 6.1mV/dB, Vbe)
honestly documentary. All Composes back-links resolve.

### Findings (integrated)
- **expo-converter spec R_VOCT 47k→49.9k** (real staleness vs live nets, change 0020 §A) — FIXED.
- **lfo-core Composes wrongly claimed gm-c-integrator** — the LFO integrator is a TL072 op-amp Miller
  R-C integrator, NOT the OTA gm-C primitive. Corrected to schmitt-trigger only (with a note). 
- Cosmetic: voct_octave description ("I_ref and V_T cancel" → only I_ref); reworded.

## Stage 3 — integrate ✅
- Applied the R_VOCT + lfo-core-Composes + voct_octave fixes. All 7 `--check` gates green; **82 decks total**
  (47 block + 35 aux library). `_LIBRARY.md` status → **✅ COMPLETE**.

## Gate checklist
- [x] Stage 1 write (4 parallel → 11 new entries + sims + Composes links)
- [x] Stage 2 verify-intent (2 adversarial → all SOUND; found the R_VOCT staleness + the bad Composes link)
- [x] Stage 3 integrate (fixes applied; all 7 gates green)
- [x] Update `specs/aux/_LIBRARY.md` (all entries ✅; status COMPLETE)
- [ ] PR `change/0032-aux-library-extractions` → `dev`
