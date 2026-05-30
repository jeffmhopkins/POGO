# Change 0018: hardware spec/netlist alignment to plugin (0017 follow-up)

- **Slug:** hardware-plugin-alignment   **Branch:** `claude/hardware-plugin-alignment-KSBDQ`
- **Lane:** B (hardware-only) — per-block; some blocks reduce to Lane C (doc-only)
- **Status:** OPEN
- **Blocks:** all (A, 1, 2, 3, 4, 5, 6, 7, 8, B)   **Boards:** audio, utility, control, panel
- **Opened:** 2026-05-30       **Closed:** —
- **PR:** —              **CI run:** —

> Lanes & gates are defined in `CLAUDE.md` → "Git Workflow & Change Process".

## Intent  (follow-up context)

This change is the **hardware follow-up to change 0017** (`dist-before-bandpass` +
`MOD_SRC` switch), which was merged into `dev` before its deferred hardware-side gates
(G4 spec / G5 topology / G6 components) were completed. The plugin and front panel are the
locked ground truth; this pass walks the hardware layer (`specs/block-*/spec.md` §2–4,
`specs/*/block-*.nets.yaml`, generated `.kicad_sch`, `components.yaml`/BOM) **block by block**
to bring it into parity with the locked plugin — both the genuine 0017 topology change
(block-6 dist-before-BP, block-2/3 mod source) and the pre-existing §2–4 STALE debt on the
other blocks.

**Per-block method (heavy):** 2 independent comprehension agents (plugin-truth card + spec
card) → adversarial diff/challenge → validated divergence list → user checkpoint → competing
spec authors + group adversarial review → netlist + design-intent review → user checkpoint.

## Scope / Out of scope

- **In:** `specs/block-*/spec.md` (§1–4), `specs/*/block-*.nets.yaml`, generated
  `kicad/pogo-block-*.kicad_sch`, `specs/components.yaml` + registry/BOM (only if a block
  genuinely needs a new/changed part — gated G6), `specs/aux/*` consistency, `specs/STATUS.md`.
- **Out:** No plugin DSP edits (plugin is locked ground truth). No panel geometry changes
  (panel already carries 0017). Plugin source comment fixes are noted in spec, not edited.

## Per-block progress

| Block | Analysis (cp1) | Edits (cp2) | Result | Notes |
|---|---|---|---|---|
| A — Input Buffers | ✅ | ✅ | Lane C (doc-only) | No behavioral divergence; spec/nets match plugin. Fixed: DSP line cite, LM4562→OPA1612 part note, STALE banners lifted, aux cross-refs, 100Ω clamp-current math, aux board-name table. **100Ω kept** (user). |
| 1 — Pre-Gain | ✅ | ✅ | G4 text-only | No B1-local HW change (gain-stage netlist correct). Fixed: ALT destination (through VCA → **BP3 only**, bypasses LP1 not VCA), per-channel selector + asymmetric edge case documented, STALE banners lifted, aux refs, DSP cite, switch=path-select, aux OPA1612 note softened. **Substantive HW deferred → block-4 (ALT VCA cell) + block-6 (BP3 selector, distortion order).** |
| 2 — Dual LFO | ✅ | ✅ | G4+G5+G6a/b | LFO core faithful. Both LFOs tap MOD_SRC switch (LFO1_OUT pos0 + new LFO2_OUT pos1); aux-lfo-core refreshed; topology-doc MOD_SRC + ALT fixed. **LED: full-cycle breathing NPN current-source driver** (MMBT3904 ×2 + base level-shift; D1/D2 removed, R9/R10→R_E) — matches plugin `(V_tri+5)/10`. New part **MMBT3904** registered (npn symbol, SOT-23). Switch wiring deferred to block-3. |
| 3 — Mod Bus | ✅ | ✅ | G4+G5+G6(delete) | **Big block.** Wired MOD_SRC SW7 (DW5) 3-way LFO1/LFO2/EXT (COMs bridged), MOD_IN→EXT-only, accept LFO1+LFO2 boundary inputs. **Removed** 3 MOD LEDs + driver U4 + R56-60 (no plugin/panel backing; 7→6 TL074). **Removed** VCA_AMT attenuverter RV5+inverter (VCA = raw bus normal, depth pot → block-4). Renamed per-band `BP*_FOCUS`→`TILT` (plugin/panel have no FOCUS CV). Refreshed aux-mod-bus-core + aux-attenuverter; dropped phantom distribution buffer (load is light). 18 attenuverters + 1 raw VCA normal. |
| 4 — VCA | 🔲 | 🔲 | — | **DEFERRED-IN (from B1):** add 2nd THAT2180 ALT VCA cell on shared `V_CTRL`. **DEFERRED-IN (from B3):** VCA_INPUT gets RAW V_modbus normal (no attenuverter); add VCA_AMT depth pot here (moved from block-3 RV5). |
| 5 — LP Filter 1 | 🔲 | 🔲 | — | |
| 6 — Triple BP + Dist | 🔲 | 🔲 | — | **0017 core:** netlist still wires **SVF→DIST**; plugin is **DIST→SVF** (`Pogo.cpp:443`) — core reorder UNBUILT. **DEFERRED-IN (from B1):** add per-channel BP3 input selector (ALT-VCA vs main band; main normal when ALT unpatched); resolve `ALT_OUT_L/R`↔`BP3IN_L/R` boundary. CLIP LED on dist output; BP3 tap post-BP pre-mix. |
| 7 — HP Filter | 🔲 | 🔲 | — | |
| 8 — LP Filter 2 | 🔲 | 🔲 | — | |
| B — Output Buffers | 🔲 | 🔲 | — | §2–4 STALE. |

## Gate checklist (rolling, per block)

- [ ] G4 spec §1 + functional approved (you) — per block
- [ ] G5 topology approved (you) — per block, where topology changes
- [ ] G6a/b components — only blocks needing new parts (expected: block-6 possibly none)
- [ ] CI green (5 `--check` gates) after each block's edits

## Decisions log

- 2026-05-30: Scope = all 10 blocks, signal-chain order; heavy agent fan-out; per-block
  checkpoints (after analysis + after edits). (user)
- 2026-05-30: Run as one umbrella follow-up change on `claude/hardware-plugin-alignment-KSBDQ`
  with a per-block checklist, explicitly framed as completing 0017's deferred hardware gates. (user)
- 2026-05-30: **Block A** — no behavioral divergence; series-protection resistor kept at
  **100 Ω** (the "167 mA borderline" caveat was wrong math; true worst-case ≈ 47 mA). (user)
- 2026-05-30: **Block 1** — local fixes are G4 text-only; the gain-stage netlist is correct.
  ALT path corrected to match plugin: through VCA (shared control) → BP3 only, bypasses LP1
  not VCA; BP3 selector must be per-channel (asymmetric L/R ALT case). **Follow the plugin**
  on ALT-through-VCA → block-4 gains a 2nd THAT2180 cell. (user)
- 2026-05-30: Carried-forward block-6 finding: netlist distortion order (SVF→DIST) is the
  pre-0017 order; plugin is DIST→SVF — the core 0017 reorder is not yet built in hardware.
- 2026-05-30: **Block 3** decisions (user): (a) REMOVE the 3 MOD-bus LEDs + driver — plugin
  drives none, locked panel has no footprints; (b) FOLLOW plugin on VCA — raw bus normal into
  VCA_INPUT, no attenuverter, VCA_AMT depth pot moves to block-4. FOCUS→TILT and MOD_SRC switch
  wiring are settled by the locked panel+plugin (G4/G5, no toss-up). SW7 wired as passive DW5
  3-way (COMs bridged); Phase-3R to verify ON-ON-ON contact sequence vs datasheet.
- 2026-05-30: Also corrected a phantom block-3 "distribution buffer" (halves C+D paralleled):
  the bus actually drives 18×100k R_SRC_NORM (~5.6k, ~1.8mA), so no buffer is needed.
- 2026-05-30: **Block 2 LED** — divergence found: plugin LED breathes full-cycle
  `(raw+1)×0.5`, hardware was half-wave "pulsing" (and the spec falsely claimed a match).
  User chose **match plugin**, then **simpler/cheaper driver**: single-transistor NPN current
  source (MMBT3904) per LED, accepting a small V_be toe near the dark end. G5 topology + G6a
  component approved. New `npn` symbol primitive authored; MMBT3904 SOT-23 footprint exists. (user)

## Component additions

| ref | board | block | part | pkg | val | datasheet? | fn |
|-----|-------|-------|------|-----|-----|-----------|----|
| Q1, Q2 | utility | block-2 | MMBT3904 | SOT-23 | — | onsemi product page (G6b: SOT-23 fp exists; new `npn` symbol) | LFO LED breathing current sources |
| R19–R24 | utility | block-2 | ~ (0603) | 0603 | 51k/68k/10k ×2 | n/a (passives) | LED-driver base level-shift networks |

(R9/R10 repurposed 1.2k→470Ω as emitter R; D1/D2 1N4148 removed.)

## Artifacts  (paths / links, not copies)

- Plugin (locked ground truth): `dev` @ change 0017 (CI run on dev)
- Specs:   `specs/block-*/spec.md`, `specs/aux/*`
- Netlist: `specs/*/block-*.nets.yaml` → `kicad/pogo-block-*.kicad_sch`
- STATUS.md rows updated per block as completed.

## Notes / carried-forward findings

- **block-1 / ALT path:** `docs/plugin-topology.md:224–225` says ALT_BP_L unpatched falls
  back to `pgL`; plugin (`Pogo.cpp:347–349`) falls back to `0.f` (silence). Doc↔plugin bug
  to resolve when Block 1 is processed.
