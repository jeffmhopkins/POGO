Investigate and fix DRC violations in the POGO panel.
Source of truth: `tools/panel-data.yaml`. All commands from repo root.
Branch: `dev`.

## Run the check first

```
python3 tools/build_panel.py --check
```

## Violation categories and fixes

### [PCB KEEPOUT]
The component's PCB courtyard extends past the rail keepout boundary. This is a real physical
error — the PCB cannot be manufactured this way.

Causes and fixes:
- Jack at cy > 105.52mm → move up, OR add `rotate: 180` to flip body above hole
- Pot at cy > 111.83mm → move up
- Switch body at cy > 115.0mm → move up
- Component near top (cy < ~15mm) → PCB body may extend above y=10mm — move down

Rotation trick for bottom-row jacks:
```yaml
- {type: jack_input, cy: 112.5, rotate: 180}   # body flips up; courtyard bottom = 113.92mm ✓
```

### [PCB OVERLAP]
Two components' PCB courtyards intersect. Both have PCB footprints that physically conflict.

Check with: `python3 tools/build_panel.py --dist ID1 ID2`

Minimum cy gaps required when components share an x column:
| Pair (above → below) | Min gap (mm) |
|---|---|
| pot → jack | 19.65 |
| jack → pot | 8.09 |
| jack → jack | 14.40 |
| pot → pot | 13.34 |

If the gap is insufficient, either:
- Move the lower component down (larger cy)
- Move the upper component up (smaller cy)
- Use `--snap-to UPPER_ID below LOWER_TYPE 0` to get the minimum safe cy for the lower component

### [NUT KEEPOUT]
The panel-face nut or hole circle enters the top (y < 10mm) or bottom (y > 118.5mm) keepout.
Fix by adjusting cy. Rule: `cy - nut_r ≥ 10` and `cy + nut_r ≤ 118.5`.

Nut radii: jack = 5.0mm, pot = 5.5mm, switch = 3.15mm, LED = 1.6mm.

### [MH CLEARANCE]
PCB courtyard is within 3.5mm of a mounting hole center. Move the component away from the
corner mounting holes (at x=7.5mm and x=297.3mm).

## After fixing

Run `--check` after each fix to verify it resolved the violation without introducing new ones.
When clean: `python3 tools/build_panel.py` to rebuild, then commit.
