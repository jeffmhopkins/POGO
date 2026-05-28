You are adding a new section to the POGO Eurorack panel.
Source of truth: `tools/panel-data.yaml`. All commands run from repo root.
Branch: `dev`.

## Before you start

1. Run `python3 tools/build_panel.py --check` — must be DRC PASS before touching anything.
2. Run `python3 tools/build_panel.py --next LAST_ZONE_ID` — get the x_start for the new section.
   If unsure which zone is last: `python3 tools/build_panel.py --list | tail -5`

## Hard PCB constraints (these are physical limits — violations mean the module can't be built)

| Constraint | Value | Why |
|---|---|---|
| Jack max cy (default rotation) | 105.52mm | Thonkiconn body extends 12.98mm below hole; rail at 118.5mm |
| Pot max cy | 111.83mm | Alpha 9mm body extends 6.67mm below shaft |
| Pot above jack (same cx column) | ≥ 19.65mm gap | pot_cy_bottom + jack_cy_top |
| Jack above pot (same cx column) | ≥ 8.09mm gap | jack_cy_bottom + pot_cy_top |
| Top keepout | y < 10mm forbidden | Rail hardware |
| Bottom keepout | y > 118.5mm forbidden | Rail hardware |

To place a jack below cy=105.52mm: add `rotate: 180` to flip the PCB body upward.
  Example: jack at cy=112.5 with rotate:180 → courtyard bottom=113.92mm < 118.5mm ✓

## Column-relative positioning

```yaml
- id: zone_example
  x_start: 45.72    # from --next
  col_pitch: 15.24  # 3 HP per column (standard; or 10.16 for 2 HP)
  cols: 2
  components:
    - {id: MY_JACK, type: jack_input, col: 0, cy: 16, label: "IN", cpp_id: "MY_JACK_INPUT"}
    - {id: MY_POT,  type: trimpot,   col: 1, cy: 30, label: "GAIN", cpp_param: "MY_PARAM"}
```

cx resolves to: `x_start + (col + 0.5) × col_pitch`
Explicit `cx:` overrides column resolution (use for LEDs offset from jack, etc.)

## Workflow

Add components in vertical bands from top to bottom. After each band:
```
python3 tools/build_panel.py --check
```
If violations appear, fix before adding more components.

Use `--dist ID1 ID2` to verify any clearance you're not sure about.
Use `--snap-to ID direction type gap` to compute a safe cy adjacent to an existing component.

When the zone is complete and DRC PASS:
```
python3 tools/build_panel.py    # rebuild SVG + HTML
python3 tools/build_panel.py --list   # review final positions
```

Then commit: `git add tools/panel-data.yaml res/Pogo-source.svg design/panel-debug.html && git commit`

## Report back

After completing the section, show:
- `--list` output for the new zone(s)
- `--next NEW_ZONE_ID` (where the next section starts)
- Confirmation of DRC PASS
- Any tight clearances worth noting for the next section
