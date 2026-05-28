# POGO Panel Build Tool — Reference Guide

## Overview

The panel build tool turns `tools/panel-data.yaml` into the VCV Rack SVG (`res/Pogo-source.svg`)
and an interactive design-review HTML file (`design/panel-debug.html`). All positions, colors,
and design rules live in the YAML. Nothing in `res/` is hand-edited after the tool exists.

All commands run from the repo root.

---

## CLI Quick Reference

```
python3 tools/build_panel.py                             # rebuild SVG + debug HTML + editor (default)
python3 tools/build_panel.py --resource                  # SVG only
python3 tools/build_panel.py --design                    # HTML debug viewer only
python3 tools/build_panel.py --editor                    # interactive editor HTML only
python3 tools/build_panel.py --check                     # DRC only; exit 1 on violations
python3 tools/build_panel.py --list                      # table of all resolved positions
python3 tools/build_panel.py --next ZONE_ID              # x_start for the section after ZONE_ID
python3 tools/build_panel.py --dist ID1 ID2              # clearances between two components
python3 tools/build_panel.py --snap-to ID DIR TYPE GAP   # placement calculator
python3 tools/build_panel.py --zone-bbox ZONE_ID         # bounding box of a zone
python3 tools/build_panel.py --select X1 Y1 X2 Y2        # list components in a bounding box
python3 tools/build_panel.py --shift ZONE_ID DX DY       # preview bulk zone shift
python3 tools/build_panel.py --shift ZONE_ID DX DY --apply   # write zone shift to YAML
python3 tools/build_panel.py --shift-select X1 Y1 X2 Y2 DX DY         # preview bbox shift
python3 tools/build_panel.py --shift-select X1 Y1 X2 Y2 DX DY --apply # write bbox shift
```

## Interactive Editor (`design/panel-editor.html`)

`--editor` (included in the default build) generates `design/panel-editor.html` — a
**single static HTML+JS file** for visually editing the panel. It needs no server: open it
directly in a browser. It is built *from* `panel-data.yaml`; you edit visually, then copy the
exported YAML back over `panel-data.yaml`.

The editor embeds the parsed YAML, the original YAML text (for export), the real DRC constants
from `panel_rules.py`, and the real KiCad footprint geometry from `panel_kicad.py` — so its
in-browser DRC and footprint overlays match `build_panel.py` exactly (no drift).

**Layout**

- **Left** — palette of addable component types (click to add) + a zone/component tree (click to
  select).
- **Centre** — the live panel SVG. Drag components to move them; the selected one is highlighted;
  DRC violators are outlined red. Layer-visibility checkboxes (Panel / Keep-Out / Nuts /
  Courtyards / KiCad) and an optional grid snap live in the top bar.
- **Right** — inspector for the selected component: `id`, `type`, resolved `cx`/`cy` (numeric
  entry), `rotate` (cycle button), `label`, `font_size`, `cpp_id`/`cpp_param`, and the read-only
  KiCad footprint name. Includes a delete button.
- **Top bar** — panel **HP** field + **Recenter** (recomputes `x_offset`), **Dividers…** modal
  (add/remove separators), **Export YAML**, and a live DRC pass/fail badge.

**Interactions**

- **Tools** (top bar): Select (drag to move), Pan (drag canvas; or hold **Space** anytime).
- **Arrow keys** nudge the selection (Shift = bigger / 1 HP); **Del** deletes; **Ctrl+Z / Ctrl+Shift+Z** undo/redo; **Esc** cancels a pick / deselects.
- **Snap**: toggle + step in **mm or HP** (e.g. 2.25 HP = the jack pitch). The grid origin can be panel 0,0 or "grid: SEL" (counts from the selected component).
- **Align / place** (component inspector): "Align X/Y to…" then click a reference component; or "Place at offset" from panel 0,0 or a divider, in mm/HP.
- **Sections** (click a zone name in the list): rename `id`/`label`, edit `x_start`, and move the whole section with the dx/dy buttons or arrow keys (mirrors `--shift`: `x_start` moves column-relative parts, explicit-`cx` parts shift with it).
- **Add** drops the new component into the selected component's (or selected zone's) zone.
- **Revert to build spec** resets a component to its original `panel-data.yaml` values (disabled for components added in the editor).
- **Panel…** renames `meta.title` / `meta.brand`. Dailywell toggles (`toggle_dw3`/`toggle_dw5`) render and DRC-check exactly as the build tool does.
- **Add Component / Divider / Zone** (left sidebar): the palette adds components (incl. a **text** annotation with fill/weight/anchor options); **+ Divider ▏/—** adds a vertical/horizontal divider; **+ Zone** adds a new column-relative section. New components drop into the selected component's/zone's zone.
- **Dividers** are shown nested under the zone whose x-span contains them (not a separate category); ones outside every zone fall under "Other dividers". Click one to select it; drag its end handles on the panel to change length, or the middle handle to move it sideways; the inspector edits style/endpoints/label. Editing patches only that separator's line and adding appends one line — surrounding derivation comments are preserved.
- **Vertical dividers are tied to zones**: there's no standalone "add vertical divider" — **+ Zone** creates a section *and* its left-edge vertical boundary, and moving a zone's `x_start` moves that boundary with it. **+ Divider —** adds a horizontal divider spanning the selected zone.
- **Live feedback while dragging**: the dragged component's DRC red highlight updates in real time (alongside the clearance HUD), and the selected component paints on top.
- **Zones**: select a zone to rename `id`/`label`, edit `x_start`, move it, or delete it; export inserts/removes/patches whole zone blocks as needed.
- **Label border**: jacks and `led_labeled` have a "label border" checkbox (+ width) in the inspector that draws the rounded-rect outline (the one output jacks use). It's an explicit `label_border` field rendered identically by the editor and the Python build.
- **DRC panel** rows are clickable (jump-to-component); dragging shows a live clearance HUD (centre-to-centre / nut / courtyard gaps).

**Notes**

- Dragging a component off its column converts it from `col:`-relative to an explicit `cx:` on
  export (the `col:` line is replaced). Vertical moves write a numeric `cy:` (replacing any
  `_cv_jack_cy_` / `_att_cy_` template).
- **Export preserves comments**: it line-patches the original YAML (mirroring
  `_apply_yaml_patches`), only inserting/removing lines for adds, deletes, divider changes,
  zone `x_start`/`label`/`id` renames, and `meta` edits. A no-op export is byte-identical.

**Workflow**

```
1. python3 tools/build_panel.py --editor   # (or default build)
2. open design/panel-editor.html in a browser
3. drag / rotate / add / delete / change HP / add dividers
4. Export YAML → Copy
5. paste over tools/panel-data.yaml
6. python3 tools/build_panel.py --check    # authoritative DRC
7. python3 tools/build_panel.py            # rebuild SVG + HTML when clean
```

### --dist

Shows center-to-center, nut-edge clearance, and PCB courtyard gap between any two components.
Use this before committing a cy value to verify there is no conflict.

```
python3 tools/build_panel.py --dist LFO1_OUT MOD_AMOUNT

  LFO1_OUT    jack_output  cx=22.86  cy=76.00
  MOD_AMOUNT  trimpot      cx=22.86  cy=96.50

  Δcx = +0.00 mm (0.00 HP)  ← aligned on cx
  Δcy = +20.50 mm (4.04 HP)
  Center-to-center:  20.50 mm
  Nut/hole clearance: +10.00 mm  (r=5.0+r=5.5=10.5)  ✓
  PCB courtyard gap:  +0.85 mm  ✓
```

### --snap-to

Given an existing component, computes the cx/cy for a new component placed adjacent to it with
a specified nut-edge gap. Also shows the resulting PCB courtyard gap as a sanity check.

```
python3 tools/build_panel.py --snap-to MOD_IN above trimpot 2.0

  Snap trimpot above of MOD_IN (jack_input  r=5.0mm), 2.0mm nut-edge gap:
  offset = r_existing(5.0) + gap(2.0) + r_new(5.5) = 12.50mm

  new cx = 22.86 mm  (4.50 HP)
  new cy = 92.50 mm
  PCB courtyard gap: +4.41 mm  ✓
```

Direction options: `right`, `left`, `above` (or `up`), `below` (or `down`)

### --next

Returns the right boundary of a column-relative zone, which is the x_start for the next section.

```
python3 tools/build_panel.py --next zone_modbus
→  zone_modbus  next x_start = 45.72 mm  (HP 9.00)
```

### --zone-bbox

Shows the center-point bounding box of all components in a zone plus the zone's x span.

```
python3 tools/build_panel.py --zone-bbox zone_lfo

  Zone 'zone_lfo' component bbox (centres):
  cx: 22.86 – 38.10 mm  (span 15.24 mm = 3.00 HP)
  cy: 64.00 – 74.50 mm  (span 10.50 mm)
  zone x: 15.24 – 45.72 mm  (2 cols × 15.24 mm pitch = 30.48 mm)
```

### --select

Returns a table of all components whose resolved panel-hole centres fall within the specified
bounding box (all coordinates in mm, min/max order doesn't matter).

```
python3 tools/build_panel.py --select 15 60 45 90

  Selection bbox: x=[15.00–45.00]  y=[60.00–90.00]  (6 component(s))

  ZONE                 ID                             TYPE                  cx      cy  rot
  -----------------------------------------------------------------------------------------
  zone_lfo             LFO1_SPEED                     trimpot            22.86   64.00
  zone_lfo             LFO2_SPEED                     trimpot            38.10   64.00
  zone_lfo             LFO1_OUT                       jack_output        22.86   74.50
  zone_lfo             LFO2_OUT                       jack_output        38.10   74.50
  zone_lfo             LFO1_LED                       led                22.86   82.00
  zone_lfo             LFO2_LED                       led                38.10   82.00
```

Use `--select` to identify which zone and component IDs to reference before running `--shift`
or `--shift-select`.

### --shift

Previews (or applies) a bulk dx/dy position shift for every component in the named zone.

- **DX** shifts the zone's `x_start` (column-relative components move automatically). Any
  component with an explicit `cx:` field has its value patched individually.
- **DY** patches every component's `cy:` value. Template placeholders (`_cv_jack_cy_`,
  `_att_cy_`) are converted to their resolved numeric values plus the offset.

Without `--apply` the output is a dry-run preview. DRC runs automatically after `--apply`.

```
python3 tools/build_panel.py --shift zone_lfo 0 5

  Shift zone 'zone_lfo'  dx=+0mm  dy=+5mm  (6 change(s)):

  comp  LFO1_SPEED              cy: 64 → 69
  comp  LFO2_SPEED              cy: 64 → 69
  comp  LFO1_OUT                cy: 74.5 → 79.5
  comp  LFO2_OUT                cy: 74.5 → 79.5
  comp  LFO1_LED                cy: 82 → 87
  comp  LFO2_LED                cy: 82 → 87

  (dry-run — add --apply to write changes to panel-data.yaml)


python3 tools/build_panel.py --shift zone_lfo 0 5 --apply
  → patches panel-data.yaml, then prints DRC result
```

Template placeholder example — `_cv_jack_cy_` and `_att_cy_` resolve before shifting:
```
python3 tools/build_panel.py --shift zone_modbus 0 2

  comp  MOD_AMOUNT              cy: _att_cy_ → 96.25
  comp  MOD_OFFSET              cy: _att_cy_ → 96.25
  comp  MOD_IN                  cy: _cv_jack_cy_ → 107
  comp  MOD_LED                 cy: _cv_jack_cy_ → 107
```

**Note:** Band zones (`band1`, `band2`, `band3`) are not supported — edit their
`cx_left`/`cx_center`/`cx_right` directly in the YAML.

### --shift-select

Like `--shift` but operates on components selected by bounding box rather than by zone.
Useful for moving a subset of a zone, or components from multiple adjacent zones.

- For components using `col:` (column-relative x), a warning is printed for each affected zone
  and the suggestion to use `--shift ZONE_ID DX 0` instead of patching cx individually.
- Components with explicit `cx:` values are shifted directly.

```
python3 tools/build_panel.py --shift-select 15 60 45 90 0 5

  Shift-select  bbox=(15.00,60.00)–(45.00,90.00)  dx=+0  dy=+5  (6 patch(es)):

  [zone_lfo] LFO1_SPEED            cy: 64 → 69
  [zone_lfo] LFO2_SPEED            cy: 64 → 69
  [zone_lfo] LFO1_OUT              cy: 74.5 → 79.5
  [zone_lfo] LFO2_OUT              cy: 74.5 → 79.5
  [zone_lfo] LFO1_LED              cy: 82 → 87
  [zone_lfo] LFO2_LED              cy: 82 → 87

  (dry-run — add --apply to write changes to panel-data.yaml)


python3 tools/build_panel.py --shift-select 15 60 45 90 0 5 --apply
  → patches panel-data.yaml, then prints DRC result
```

**Typical workflow:**
```
1. --select X1 Y1 X2 Y2            # identify what's in the area
2. --shift-select X1 Y1 X2 Y2 DX DY   # preview the change
3. --shift-select X1 Y1 X2 Y2 DX DY --apply  # apply if DRC passes
4. python3 tools/build_panel.py    # rebuild SVG + HTML
```

---

## panel-data.yaml Structure

### Top-level keys

```yaml
meta:          # HP width, panel dimensions, title
colors:        # all SVG color tokens
design_rules:  # keepout bounds, jack/att positions, label offsets
footprints:    # nut radii (used by DRC)
mounting_holes: # M3 hole positions
separators:    # horizontal / vertical divider lines
zone_labels:   # floating text labels (section titles)
zones:         # component zones (the meat of the file)
```

### Zone structure (column-relative, preferred)

```yaml
- id: zone_example
  label: "Human-readable description"
  x_start: 45.72      # left edge of section (mm)
  col_pitch: 15.24    # 3 HP per column
  cols: 2             # total columns (defines right edge = x_start + cols×col_pitch)
  components:
    - id: MY_JACK
      type: jack_input
      col: 0           # cx = x_start + (col+0.5)×col_pitch = 53.34mm
      cy: 16           # explicit mm from top of panel
      label: "IN"
      font_size: 1.8
      cpp_id: "MY_JACK_INPUT"
```

cx can also be set explicitly when a component doesn't fall on a column grid:
```yaml
    - id: MY_LED
      type: led
      cx: 58.84        # explicit — not column-relative
      cy: 76
      cpp_light: "MY_LIGHT"
```

### Component types and their panel-face radii

| Type | Panel r (mm) | Notes |
|------|-------------|-------|
| `jack_input`, `jack_output` | 5.0 (nut) | Thonkiconn PJ301M-12 |
| `trimpot` | 5.5 (nut) | Alpha 9mm, small knob cap |
| `knob_medium` | 5.5 (nut) | Alpha 9mm, 4.5mm cap radius |
| `knob_large` | 5.5 (nut) | Alpha 9mm, 7.0mm cap radius |
| `knob_xl` | 5.5 (nut) | Alpha 9mm, 9.0mm cap radius |
| `toggle_dw3` | 3.8 (washer) | Dailywell DW3 2-pos toggle (ON-ON) |
| `toggle_dw5` | 3.8 (washer) | Dailywell DW5 3-pos toggle (ON-ON-ON) |
| `led` | 1.6 (hole) | 3mm LED, unlabeled |
| `led_labeled` | 1.6 (hole) | 3mm LED with label below |

### Component rotation

Add `rotate: 180` (or 90/270) to rotate the PCB courtyard only. Panel appearance is unchanged
(circular holes and nuts look the same at any rotation).

The key use case is inverting a bottom-row jack so its PCB body extends UP instead of DOWN:

```yaml
- id: FREQ_CV_1
  type: jack_input
  col: 2
  cy: 112.5     # would normally fail PCB keepout (bottom=125.48mm)
  rotate: 180   # flips body: courtyard bottom = 113.92mm < 118.5mm ✓
  cpp_id: "FREQ_CV_1_INPUT"
```

### Template placeholders in cy

Components with `cy: _cv_jack_cy_` or `cy: _att_cy_` resolve to the design_rules values:
- `_cv_jack_cy_` → 105.0mm (bottom CV jack row)
- `_att_cy_` → 96.5mm (attenuverter row, paired with CV row)

### Separator styles

```yaml
separators:
  - {type: v, x: 45.72, y1: 4.5, y2: 124.0, style: main_cyan}   # bright cyan vertical
  - {type: v, x: 60.96, y1: 4.5, y2: 124.0, style: subdiv_gray} # dim gray vertical
  - {type: h, x1: 45.72, x2: 91.44, y: 52.0, style: zone_div}   # horizontal divider
```

---

## PCB Constraint Quick Reference

All distances in mm, measured from component panel-hole center.

### Thonkiconn PJ301M-12 (jack)
- PCB courtyard: x ∈ [−5.0, +5.0], y ∈ [−1.42, +12.98] (origin = panel hole)
- y extends **12.98mm below** hole by default (rotate: 180 flips to 12.98mm above)
- Nut radius: 5.0mm

### Alpha RD901F 9mm (pot / trimpot / knobs)
- PCB courtyard: x ∈ [−8.65, +5.1], y ∈ [−6.67, +6.67] (origin = shaft centre)
- Nut radius: 5.5mm

### Dailywell 2M sub-mini toggle (`toggle_dw3` / `toggle_dw5`)
- PCB courtyard: x ∈ [−4.32, +4.32], y ∈ [−4.82, +4.82] (body 8.13 × 9.14mm + 0.25mm)
- Panel hole: Ø4.95mm; 10-48 UNS bushing (Ø6.00mm). Washer-clearance radius: 3.8mm
- DW3 = DPDT ON-ON (2-position); DW5 = DPDT ON-ON-ON (3-position); shared land pattern

### 3mm LED
- PCB courtyard: x ∈ [−2.0, +2.0], y ∈ [−1.5, +4.0]
- Panel hole radius: 1.6mm

### Rail keepout
- Top: y < 10.0mm — no panel holes, no PCB courtyard
- Bottom: y > 118.5mm — no panel holes, no PCB courtyard

### Minimum cy values (default rotation)
| Component | Max cy for PCB clearance | Formula |
|-----------|------------------------|---------|
| `jack_*` | 105.52mm | 118.5 − 12.98 |
| `trimpot` | 111.83mm | 118.5 − 6.67 |
| `switch_*` | 115.0mm | 118.5 − 3.5 (CY bottom offset) |

### Minimum gap between stacked components (same cx column)
| Above ↕ Below | Min cy gap | Formula |
|---------------|-----------|---------|
| jack above pot | 8.09mm | 1.42 + 6.67 (touching courtyards) |
| pot above jack | 19.65mm | 6.67 + 12.98 (touching courtyards) |
| jack above jack | 14.40mm | 1.42 + 12.98 |
| pot above pot | 13.34mm | 6.67 + 6.67 |

The `pot above jack` gap (19.65mm) is the critical one — it forced the LFO_OUT / MOD_AMOUNT
layout to use cy=76 and cy=96.5 respectively.

---

## Section Addition Workflow

```
1.  python3 tools/build_panel.py --check              # confirm clean baseline
2.  python3 tools/build_panel.py --next LAST_ZONE_ID  # get x_start
3.  Choose HP width, col_pitch, number of columns
4.  Add zone skeleton to panel-data.yaml
5.  Add one row of components at a time
6.  python3 tools/build_panel.py --check              # after each row
7.  Use --dist to verify any tight clearances
8.  Use --snap-to to position a component relative to an existing one
9.  python3 tools/build_panel.py                      # rebuild SVG + HTML when clean
10. Confirm section before moving to the next
```

---

## Pre-Engineered Sub-Agent Prompts

These are self-contained prompts. Copy the relevant one as the `prompt:` field when spawning
an agent, filling in the `[PLACEHOLDER]` values.

---

### Add a new 6HP section (generic)

```
You are adding a new section to the POGO Eurorack panel build tool.
The tool lives in tools/ and the source of truth is tools/panel-data.yaml.
Run all commands from the repo root.

Branch: dev

TASK: Add a [SECTION_NAME] section at x_start=[X_START]mm ([HP_N] HP wide).

Section layout:
  [DESCRIBE COMPONENTS: types, rough vertical positions, labels, cpp_ids]

Hard PCB constraints (MUST satisfy -- these are physical rail limits):
  - jack cy_max = 105.52mm (courtyard bottom ≤ 118.5mm)
  - pot cy_max = 111.83mm
  - Stacked in same cx column: pot-above-jack needs ≥ 19.65mm gap
  - Use rotate: 180 on a jack if you need cy > 105.52mm (body flips up)

Workflow:
  1. Run `python3 tools/build_panel.py --check` to confirm clean baseline
  2. Add zone to panel-data.yaml with column-relative positioning
     (x_start, col_pitch, cols; components use col: N, not explicit cx)
  3. Run --check after every group of components added
  4. Use --dist ID1 ID2 to verify tight vertical clearances before committing
  5. Use --snap-to ID direction type gap to calculate positions relative to existing components
  6. When --check passes: run python3 tools/build_panel.py to rebuild SVG + HTML
  7. Run --list for the new zone and report the results
  8. Commit and push to branch dev

Do NOT create a pull request.
```

---

### Fix DRC violations

```
The POGO panel build tool has DRC violations that need to be resolved.
The tool lives in tools/ and source of truth is tools/panel-data.yaml.
Run all commands from the repo root. Branch: dev.

TASK: Fix all DRC violations.

  1. Run `python3 tools/build_panel.py --check` and read the violation list
  2. For each [PCB OVERLAP] violation: the two components' PCB courtyards intersect.
     Fix by increasing the cy gap between them. Required gaps:
       - pot above jack (same cx): ≥ 19.65mm center-to-center
       - jack above pot: ≥ 8.09mm
       - jack above jack: ≥ 14.40mm
       - pot above pot: ≥ 13.34mm
     Use `--dist ID1 ID2` to see current gap and how much to move.
  3. For each [PCB KEEPOUT] violation: component courtyard exceeds y > 118.5mm.
     Fix by moving component up (lower cy) OR adding rotate: 180 to flip body above hole.
     Max safe cy (default rotation): jack ≤ 105.52mm, pot ≤ 111.83mm.
  4. For each [NUT KEEPOUT] violation: nut circle enters y < 10mm or y > 118.5mm.
     Fix by adjusting cy.
  5. After each fix, run --check to confirm the violation is resolved.
  6. When all violations are cleared: run python3 tools/build_panel.py and commit.

IMPORTANT: [PCB KEEPOUT] is a real blocking error — the PCB cannot extend into the rail zone.
```

---

### Add a CV jack + attenuverter pair

```
Add a CV jack with attenuverter to an existing zone in tools/panel-data.yaml.
Run all commands from the repo root. Branch: dev.

TASK: Add CV jack '[CV_JACK_ID]' and attenuverter '[ATT_ID]' to zone '[ZONE_ID]'.
  - CV jack at col [COL], cy = _cv_jack_cy_ (resolves to 105.0mm)
  - Attenuverter (trimpot) at col [COL], cy = _att_cy_ (resolves to 96.5mm)
  - cpp_id for jack: '[CPP_ID]'
  - cpp_param for att: '[CPP_PARAM]'
  - Label: '[LABEL]'

The _cv_jack_cy_ and _att_cy_ templates auto-resolve from design_rules.
Gap between att pot (cy=96.5) and CV jack (cy=105.0) = 8.5mm > 8.09mm minimum ✓

Steps:
  1. Run --check to confirm clean baseline
  2. Add the two components to the zone
  3. Run --check and --dist ATT_ID CV_JACK_ID to verify
  4. Run build to rebuild SVG + HTML
  5. Commit and push
```

---

### Verify clearance before adding a component

```
Before adding a component to the POGO panel, verify it clears existing components.
Run all commands from the repo root.

TASK: Check whether [NEW_TYPE] at cx=[CX]mm, cy=[CY]mm clears all neighbors.

  1. Run `python3 tools/build_panel.py --list` to find components near cx=[CX], cy=[CY]
  2. For each nearby component, run:
       python3 tools/build_panel.py --dist [NEARBY_ID] [NEW_TYPE]
     (use a placeholder ID for the new component if it doesn't exist yet)
  3. Apply the PCB gap rules:
       - pot above jack: need ≥ 19.65mm
       - jack above pot: need ≥ 8.09mm
       - same-type: use 14.4mm (jack/jack) or 13.34mm (pot/pot)
  4. To find a safe cy, use:
       python3 tools/build_panel.py --snap-to [NEAREST_ID] [direction] [NEW_TYPE] [gap]
  5. Report: proposed position, clearances to all neighbors, DRC status
```

---

## Design Rules Summary (from panel-data.yaml)

```yaml
design_rules:
  top_keepout:       10.0    # no hardware above this y
  bot_keepout_start: 118.5   # no hardware below this y (PCB rail limit)
  cv_jack_cy:        105.0   # bottom CV jack row (_cv_jack_cy_ template)
  att_offset:        -10.75  # att_cy = cv_jack_cy + att_offset = 94.25
  jack_label_dy:     7.0     # label baseline = cy + 7.0
  output_rect_dy:    -1.76   # output jack border rect top offset from label
  output_rect_h:     2.26
  jack_pitch:        15.24   # 1 jack per 3 HP (default col_pitch)
  indicator_length:  2.5     # trimpot indicator line length
```

## Current Panel State (Section 0)

```
HP 1–2:   (empty)
HP 3–9:   Section 0 — INPUT / LFO / MOD BUS  (x=15.24–45.72mm)
HP 10–60: (to be designed)
```

Next section starts at x=45.72mm (HP 9).
