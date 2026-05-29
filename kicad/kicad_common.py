#!/usr/bin/env python3
"""
POGO KiCad 7 schematic generation — shared infrastructure.

Usage in each board generator:
    from kicad_common import *

Each generator defines its own emit_lib_symbols() and build_schematic(),
then calls write_schematic("output.kicad_sch") to produce the file.

Pin coordinate convention
─────────────────────────
Every sym_* function returns a lib_symbol string.
Every *_pins(ox, oy) function returns {pin_number_str: (x, y)} at canvas coords,
matching the lib_symbol geometry exactly so connect_pin() lands on the pin stub.
"""

import uuid
import math

OUT = []


def reset():
    """Clear the output buffer. Call before build_schematic() if reusing in one process."""
    global OUT
    OUT.clear()


def uid():
    return str(uuid.uuid4())


def emit(s):
    OUT.append(s)


# ---------------------------------------------------------------------------
# Schematic skeleton
# ---------------------------------------------------------------------------

def begin_schematic(paper="A0"):
    emit(f'(kicad_sch (version 20230121) (generator "eeschema")')
    emit(f'(paper "{paper}")')


def end_schematic():
    emit(')')


def write_schematic(out_path):
    """Join OUT and write to file. Prints a summary."""
    output = "\n".join(OUT)
    with open(out_path, "w") as f:
        f.write(output)
    import re
    from collections import Counter
    labels = re.findall(r'\(global_label "([^"]+)"', output)
    singles = [k for k, v in Counter(labels).items() if v == 1]
    opens, closes = output.count('('), output.count(')')
    print(f"Written: {out_path}")
    print(f"  Parens balanced: {opens == closes}")
    print(f"  Single-occurrence nets: {len(singles)}"
          + (f"  ← check these" if singles else "  ✓"))
    for s in sorted(singles):
        print(f"    {s}")


# ---------------------------------------------------------------------------
# Power rail lib_symbols — used on every board
# ---------------------------------------------------------------------------

def sym_power(name):
    """Power rail lib_symbol: +12V, -12V, or GND."""
    if name == "GND":
        body = (
            '      (polyline (pts (xy 0 0) (xy 0 -1.27)) (stroke (width 0) (type default)) (fill (type none)))\n'
            '      (polyline (pts (xy -1.27 -1.27) (xy 1.27 -1.27)) (stroke (width 0.254) (type default)) (fill (type none)))\n'
            '      (polyline (pts (xy -0.762 -1.778) (xy 0.762 -1.778)) (stroke (width 0.254) (type default)) (fill (type none)))\n'
            '      (polyline (pts (xy -0.254 -2.286) (xy 0.254 -2.286)) (stroke (width 0.254) (type default)) (fill (type none)))'
        )
        pin_y, pin_angle = 0, 270
    elif "12V" in name:
        d = 1 if "+" in name else -1
        body = (
            f'      (polyline (pts (xy 0 0) (xy 0 {d*1.27:.3f})) (stroke (width 0) (type default)) (fill (type none)))\n'
            f'      (polyline (pts (xy -0.635 {d*0.635:.3f}) (xy 0 {d*1.27:.3f}) (xy 0.635 {d*0.635:.3f})) (stroke (width 0) (type default)) (fill (type none)))'
        )
        pin_y, pin_angle = 0, 270
    else:
        body = '      (circle (center 0 0) (radius 0.508) (stroke (width 0) (type default)) (fill (type none)))'
        pin_y, pin_angle = 0, 270
    return f'''  (symbol "power:{name}"
    (power)
    (pin_names (offset 0) hide)
    (pin_numbers hide)
    (property "Reference" "#PWR" (at 0 -3.81 0) (effects (font (size 1.27 1.27)) (hide yes)))
    (property "Value" "{name}" (at 0 3.81 0) (effects (font (size 1.27 1.27))))
    (symbol "{name}_0_1"
{body}
    )
    (symbol "{name}_1_1"
      (pin power_in line (at 0 {pin_y} {pin_angle}) (length 0)
        (name "~" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
    )
  )'''


# ---------------------------------------------------------------------------
# IDC connector lib_symbol — parameterised by row count
# ---------------------------------------------------------------------------

def _connector_sym(name, rows, cols=2):
    """Shared body for IDC and PinHeader lib symbols (same 2.54mm 2-col geometry)."""
    short = name.split(":")[-1]
    lines = [
        f'  (symbol "{name}"',
        '    (pin_names (offset 1.016) hide)',
        '    (pin_numbers hide)',
        f'    (property "Reference" "CN" (at 0 {rows*1.27+2.54:.3f} 0) (effects (font (size 1.27 1.27))))',
        f'    (property "Value" "{name}" (at 0 {-(rows*1.27+2.54):.3f} 0) (effects (font (size 1.27 1.27)) (hide yes)))',
        f'    (symbol "{short}_0_1"',
    ]
    h = rows * 2.54
    lines.append(f'      (rectangle (start -3.81 {h/2:.3f}) (end 3.81 {-h/2:.3f}) (stroke (width 0.254) (type default)) (fill (type background)))')
    lines.append('    )')
    lines.append(f'    (symbol "{short}_1_1"')
    for r in range(rows):
        y = (rows / 2 - 0.5 - r) * 2.54
        odd, even = 2*r+1, 2*r+2
        lines += [
            f'      (pin passive line (at -6.35 {y:.3f} 0) (length 2.54)',
            f'        (name "Pin_{odd}" (effects (font (size 1.016 1.016))))',
            f'        (number "{odd}" (effects (font (size 1.016 1.016)))))',
            f'      (pin passive line (at 6.35 {y:.3f} 180) (length 2.54)',
            f'        (name "Pin_{even}" (effects (font (size 1.016 1.016))))',
            f'        (number "{even}" (effects (font (size 1.016 1.016)))))',
        ]
    lines += ['    )', '  )']
    return '\n'.join(lines)


def sym_idc(rows, cols=2):
    """IDC header lib_symbol. rows=17→34-pin, rows=20→40-pin, rows=12→24-pin."""
    name = f"Connector_IDC:IDC-Header_{cols}x{rows:02d}_P2.54mm_Vertical"
    return _connector_sym(name, rows, cols)


def sym_pin_header(rows, cols=2):
    """PinHeader stacking header lib_symbol. rows=20→40-pin (2×20)."""
    name = f"Connector_PinHeader_2.54mm:PinHeader_{cols}x{rows:02d}_P2.54mm_Vertical"
    return _connector_sym(name, rows, cols)


# ---------------------------------------------------------------------------
# Passive component lib_symbols — resistor, capacitor, pot
# ---------------------------------------------------------------------------

def sym_r():
    """Resistor (Device:R). Pins: 1, 2 (vertical, pin 1 top)."""
    return '''  (symbol "Device:R"
    (pin_names (offset 0) hide)
    (pin_numbers hide)
    (property "Reference" "R" (at 1.778 0 90) (effects (font (size 1.27 1.27))))
    (property "Value" "R" (at -1.778 0 90) (effects (font (size 1.27 1.27))))
    (symbol "R_0_1"
      (rectangle (start -1.016 -2.032) (end 1.016 2.032) (stroke (width 0.254) (type default)) (fill (type none)))
    )
    (symbol "R_1_1"
      (pin passive line (at 0 3.81 270) (length 1.778)
        (name "~" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
      (pin passive line (at 0 -3.81 90) (length 1.778)
        (name "~" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
    )
  )'''


def sym_c():
    """Capacitor (Device:C). Pins: 1=+, 2=~ (vertical, pin 1 top)."""
    return '''  (symbol "Device:C"
    (pin_names (offset 0.254))
    (pin_numbers hide)
    (property "Reference" "C" (at 1.778 0 0) (effects (font (size 1.27 1.27))))
    (property "Value" "C" (at 1.778 -2.54 0) (effects (font (size 1.27 1.27))))
    (symbol "C_0_1"
      (polyline (pts (xy -2.032 -0.762) (xy 2.032 -0.762)) (stroke (width 0.508) (type default)) (fill (type none)))
      (polyline (pts (xy -2.032 0.762) (xy 2.032 0.762)) (stroke (width 0.508) (type default)) (fill (type none)))
    )
    (symbol "C_1_1"
      (pin passive line (at 0 3.81 270) (length 3.048)
        (name "+" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
      (pin passive line (at 0 -3.81 90) (length 3.048)
        (name "~" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
    )
  )'''


def sym_rpot():
    """3-pin pot / slider (Device:R_POT). Pins: 1=CCW, 2=Wiper, 3=CW."""
    return '''  (symbol "Device:R_POT"
    (pin_names (offset 1.016) hide)
    (pin_numbers hide)
    (property "Reference" "RV" (at 2.54 0 0) (effects (font (size 1.27 1.27)) (justify left)))
    (property "Value" "R_POT" (at 2.54 -2.54 0) (effects (font (size 1.27 1.27)) (justify left)))
    (symbol "R_POT_0_1"
      (rectangle (start -1.016 -2.032) (end 1.016 2.032) (stroke (width 0.254) (type default)) (fill (type none)))
      (polyline (pts (xy -1.778 0) (xy -1.016 0)) (stroke (width 0.254) (type default)) (fill (type none)))
      (polyline (pts (xy -1.778 0) (xy -1.27 0.508)) (stroke (width 0.254) (type default)) (fill (type none)))
      (polyline (pts (xy -1.778 0) (xy -1.27 -0.508)) (stroke (width 0.254) (type default)) (fill (type none)))
    )
    (symbol "R_POT_1_1"
      (pin passive line (at 0 -3.81 90) (length 1.778)
        (name "~" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
      (pin passive line (at -3.81 0 0) (length 2.794)
        (name "Wiper" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
      (pin passive line (at 0 3.81 270) (length 1.778)
        (name "~" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
    )
  )'''


# ---------------------------------------------------------------------------
# IC lib_symbols — op-amps, OTAs, VCAs, analog switches
# ---------------------------------------------------------------------------

def _opamp_triangle():
    return '(polyline (pts (xy -5.08 -5.08) (xy -5.08 5.08) (xy 5.08 0) (xy -5.08 -5.08)) (stroke (width 0.254) (type default)) (fill (type background)))'


def sym_tl072():
    """TL072 dual op-amp SOIC-8.
    Unit A: Out=1, In-=2, In+=3. Unit B: Out=7, In-=6, In+=5. V+=8, V-=4.
    Verify against TI SLOS080 datasheet before PCB layout."""
    t = _opamp_triangle()
    return f'''  (symbol "Amplifier_Operational:TL072"
    (pin_names (offset 0.254) hide)
    (pin_numbers hide)
    (property "Reference" "U" (at 5.08 5.08 0) (effects (font (size 1.27 1.27))))
    (property "Value" "TL072" (at 5.08 -5.08 0) (effects (font (size 1.27 1.27))))
    (symbol "TL072_0_1"
      (rectangle (start -1 -1) (end 1 1) (stroke (width 0) (type default)) (fill (type none)))
    )
    (symbol "TL072_1_1"
      {t}
      (pin input line (at -7.62 2.54 0) (length 2.54) (name "In-" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
      (pin input line (at -7.62 -2.54 0) (length 2.54) (name "In+" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
      (pin output line (at 7.62 0 180) (length 2.54) (name "Out" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
    )
    (symbol "TL072_2_1"
      {t}
      (pin input line (at -7.62 2.54 0) (length 2.54) (name "In-" (effects (font (size 1.27 1.27)))) (number "6" (effects (font (size 1.27 1.27)))))
      (pin input line (at -7.62 -2.54 0) (length 2.54) (name "In+" (effects (font (size 1.27 1.27)))) (number "5" (effects (font (size 1.27 1.27)))))
      (pin output line (at 7.62 0 180) (length 2.54) (name "Out" (effects (font (size 1.27 1.27)))) (number "7" (effects (font (size 1.27 1.27)))))
    )
    (symbol "TL072_3_1"
      (pin power_in line (at 0 7.62 270) (length 2.54) (name "V+" (effects (font (size 1.27 1.27)))) (number "8" (effects (font (size 1.27 1.27)))))
      (pin power_in line (at 0 -7.62 90) (length 2.54) (name "V-" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))
    )
  )'''


def sym_lm4562():
    """LM4562 low-noise dual op-amp SOIC-8. Pin-compatible with TL072.
    Unit A: Out=1, In-=2, In+=3. Unit B: Out=7, In-=6, In+=5. V+=8, V-=4.
    Verify against TI datasheet before PCB layout."""
    t = _opamp_triangle()
    return f'''  (symbol "Amplifier_Operational:LM4562"
    (pin_names (offset 0.254) hide)
    (pin_numbers hide)
    (property "Reference" "U" (at 5.08 5.08 0) (effects (font (size 1.27 1.27))))
    (property "Value" "LM4562" (at 5.08 -5.08 0) (effects (font (size 1.27 1.27))))
    (symbol "LM4562_0_1"
      (rectangle (start -1 -1) (end 1 1) (stroke (width 0) (type default)) (fill (type none)))
    )
    (symbol "LM4562_1_1"
      {t}
      (pin input line (at -7.62 2.54 0) (length 2.54) (name "In-" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
      (pin input line (at -7.62 -2.54 0) (length 2.54) (name "In+" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
      (pin output line (at 7.62 0 180) (length 2.54) (name "Out" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
    )
    (symbol "LM4562_2_1"
      {t}
      (pin input line (at -7.62 2.54 0) (length 2.54) (name "In-" (effects (font (size 1.27 1.27)))) (number "6" (effects (font (size 1.27 1.27)))))
      (pin input line (at -7.62 -2.54 0) (length 2.54) (name "In+" (effects (font (size 1.27 1.27)))) (number "5" (effects (font (size 1.27 1.27)))))
      (pin output line (at 7.62 0 180) (length 2.54) (name "Out" (effects (font (size 1.27 1.27)))) (number "7" (effects (font (size 1.27 1.27)))))
    )
    (symbol "LM4562_3_1"
      (pin power_in line (at 0 7.62 270) (length 2.54) (name "V+" (effects (font (size 1.27 1.27)))) (number "8" (effects (font (size 1.27 1.27)))))
      (pin power_in line (at 0 -7.62 90) (length 2.54) (name "V-" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))
    )
  )'''


def sym_ne5532():
    """NE5532 audio dual op-amp SOIC-8. Pin-compatible with TL072.
    Unit A: Out=1, In-=2, In+=3. Unit B: Out=7, In-=6, In+=5. V+=8, V-=4.
    Verify against TI datasheet before PCB layout."""
    t = _opamp_triangle()
    return f'''  (symbol "Amplifier_Operational:NE5532"
    (pin_names (offset 0.254) hide)
    (pin_numbers hide)
    (property "Reference" "U" (at 5.08 5.08 0) (effects (font (size 1.27 1.27))))
    (property "Value" "NE5532" (at 5.08 -5.08 0) (effects (font (size 1.27 1.27))))
    (symbol "NE5532_0_1"
      (rectangle (start -1 -1) (end 1 1) (stroke (width 0) (type default)) (fill (type none)))
    )
    (symbol "NE5532_1_1"
      {t}
      (pin input line (at -7.62 2.54 0) (length 2.54) (name "In-" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
      (pin input line (at -7.62 -2.54 0) (length 2.54) (name "In+" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
      (pin output line (at 7.62 0 180) (length 2.54) (name "Out" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
    )
    (symbol "NE5532_2_1"
      {t}
      (pin input line (at -7.62 2.54 0) (length 2.54) (name "In-" (effects (font (size 1.27 1.27)))) (number "6" (effects (font (size 1.27 1.27)))))
      (pin input line (at -7.62 -2.54 0) (length 2.54) (name "In+" (effects (font (size 1.27 1.27)))) (number "5" (effects (font (size 1.27 1.27)))))
      (pin output line (at 7.62 0 180) (length 2.54) (name "Out" (effects (font (size 1.27 1.27)))) (number "7" (effects (font (size 1.27 1.27)))))
    )
    (symbol "NE5532_3_1"
      (pin power_in line (at 0 7.62 270) (length 2.54) (name "V+" (effects (font (size 1.27 1.27)))) (number "8" (effects (font (size 1.27 1.27)))))
      (pin power_in line (at 0 -7.62 90) (length 2.54) (name "V-" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))
    )
  )'''


def sym_opa1612():
    """OPA1612 low-noise dual op-amp SOIC-8. Pin-compatible with TL072.
    Unit A: Out=1, In-=2, In+=3. Unit B: Out=7, In-=6, In+=5. V+=8, V-=4.
    Verify against TI SBOS450 datasheet before PCB layout."""
    t = _opamp_triangle()
    return f'''  (symbol "Amplifier_Operational:OPA1612"
    (pin_names (offset 0.254) hide)
    (pin_numbers hide)
    (property "Reference" "U" (at 5.08 5.08 0) (effects (font (size 1.27 1.27))))
    (property "Value" "OPA1612" (at 5.08 -5.08 0) (effects (font (size 1.27 1.27))))
    (symbol "OPA1612_0_1"
      (rectangle (start -1 -1) (end 1 1) (stroke (width 0) (type default)) (fill (type none)))
    )
    (symbol "OPA1612_1_1"
      {t}
      (pin input line (at -7.62 2.54 0) (length 2.54) (name "In-" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
      (pin input line (at -7.62 -2.54 0) (length 2.54) (name "In+" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
      (pin output line (at 7.62 0 180) (length 2.54) (name "Out" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
    )
    (symbol "OPA1612_2_1"
      {t}
      (pin input line (at -7.62 2.54 0) (length 2.54) (name "In-" (effects (font (size 1.27 1.27)))) (number "6" (effects (font (size 1.27 1.27)))))
      (pin input line (at -7.62 -2.54 0) (length 2.54) (name "In+" (effects (font (size 1.27 1.27)))) (number "5" (effects (font (size 1.27 1.27)))))
      (pin output line (at 7.62 0 180) (length 2.54) (name "Out" (effects (font (size 1.27 1.27)))) (number "7" (effects (font (size 1.27 1.27)))))
    )
    (symbol "OPA1612_3_1"
      (pin power_in line (at 0 7.62 270) (length 2.54) (name "V+" (effects (font (size 1.27 1.27)))) (number "8" (effects (font (size 1.27 1.27)))))
      (pin power_in line (at 0 -7.62 90) (length 2.54) (name "V-" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))
    )
  )'''


def sym_bat54s():
    """BAT54S dual series Schottky SOT-23.
    Series config: Pin1=Anode D1, Pin2=Common (cathode D1 + anode D2, signal node),
    Pin3=Cathode D2. Both diodes conduct pin1→pin2→pin3.
    In POGO input clamps: Pin1→-12V, Pin2→signal node, Pin3→+12V
    (see specs/aux/aux-cv-protection.md — pin orientation is CRITICAL).
    Verify against Diodes Inc. DS11005 datasheet before PCB layout."""
    return '''  (symbol "Diode:BAT54S"
    (pin_names (offset 0.254) hide)
    (pin_numbers hide)
    (property "Reference" "D" (at 0 3.81 0) (effects (font (size 1.27 1.27))))
    (property "Value" "BAT54S" (at 0 2.54 0) (effects (font (size 1.27 1.27))))
    (symbol "BAT54S_0_1"
      (polyline (pts (xy -5.08 0) (xy 5.08 0)) (stroke (width 0.254) (type default)) (fill (type none)))
      (polyline (pts (xy 0 0) (xy 0 -2.54)) (stroke (width 0.254) (type default)) (fill (type none)))
      (polyline (pts (xy -3.302 1.016) (xy -1.778 0) (xy -3.302 -1.016) (xy -3.302 1.016)) (stroke (width 0.254) (type default)) (fill (type none)))
      (polyline (pts (xy -1.778 1.016) (xy -1.778 -1.016)) (stroke (width 0.254) (type default)) (fill (type none)))
      (polyline (pts (xy 1.778 1.016) (xy 3.302 0) (xy 1.778 -1.016) (xy 1.778 1.016)) (stroke (width 0.254) (type default)) (fill (type none)))
      (polyline (pts (xy 3.302 1.016) (xy 3.302 -1.016)) (stroke (width 0.254) (type default)) (fill (type none)))
    )
    (symbol "BAT54S_1_1"
      (pin passive line (at -7.62 0 0) (length 2.54) (name "A1" (effects (font (size 1.016 1.016)))) (number "1" (effects (font (size 1.016 1.016)))))
      (pin passive line (at 0 -5.08 90) (length 2.54) (name "COM" (effects (font (size 1.016 1.016)))) (number "2" (effects (font (size 1.016 1.016)))))
      (pin passive line (at 7.62 0 180) (length 2.54) (name "K2" (effects (font (size 1.016 1.016)))) (number "3" (effects (font (size 1.016 1.016)))))
    )
  )'''


def sym_jack():
    """Audio_Jack_3.5mm_SwitchT with tip-switching lug (Thonkiconn PJ301M-12 / PJ398SM).
    Pins: T=Tip(1), S=Sleeve(2), SW=Switch-lug(3, normalled to tip when unpatched)."""
    return '''  (symbol "Device:Audio_Jack_3.5mm_SwitchT"
    (pin_names (offset 1.016) hide)
    (pin_numbers hide)
    (property "Reference" "J" (at 0 5.08 0) (effects (font (size 1.27 1.27))))
    (property "Value" "Audio_Jack_3.5mm_SwitchT" (at 0 -7.62 0) (effects (font (size 1.27 1.27))))
    (symbol "Audio_Jack_3.5mm_SwitchT_0_1"
      (circle (center 0 0) (radius 2.159) (stroke (width 0.254) (type default)) (fill (type none)))
      (polyline (pts (xy -2.159 0) (xy -3.175 0)) (stroke (width 0.254) (type default)) (fill (type none)))
      (polyline (pts (xy 2.159 0) (xy 3.175 0)) (stroke (width 0.254) (type default)) (fill (type none)))
    )
    (symbol "Audio_Jack_3.5mm_SwitchT_1_1"
      (pin passive line (at -5.08 0 0) (length 1.905)
        (name "T" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
      (pin passive line (at 5.08 0 180) (length 1.905)
        (name "S" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
      (pin passive line (at 0 -5.08 90) (length 1.905)
        (name "SW" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
    )
  )'''


def sym_diode():
    """Generic diode (Device:D), e.g. 1N4148W. Pins A (anode, top), K (cathode, bottom).
    Pad names A/K match the SOD-123 footprint."""
    return '''  (symbol "Device:D"
    (pin_names (offset 0) hide)
    (pin_numbers hide)
    (property "Reference" "D" (at 2.032 0 90) (effects (font (size 1.27 1.27))))
    (property "Value" "D" (at -2.032 0 90) (effects (font (size 1.27 1.27))))
    (symbol "D_0_1"
      (polyline (pts (xy -1.27 1.27) (xy 1.27 1.27) (xy 0 -1.016) (xy -1.27 1.27)) (stroke (width 0.254) (type default)) (fill (type none)))
      (polyline (pts (xy -1.27 -1.016) (xy 1.27 -1.016)) (stroke (width 0.254) (type default)) (fill (type none)))
    )
    (symbol "D_1_1"
      (pin passive line (at 0 3.81 270) (length 2.794) (name "A" (effects (font (size 1.27 1.27)))) (number "A" (effects (font (size 1.27 1.27)))))
      (pin passive line (at 0 -3.81 90) (length 2.794) (name "K" (effects (font (size 1.27 1.27)))) (number "K" (effects (font (size 1.27 1.27)))))
    )
  )'''


def sym_led():
    """LED (Device:LED). Pins A (anode, top), K (cathode, bottom). Pad names A/K
    match LED_THT/LED_D3.0mm."""
    return '''  (symbol "Device:LED"
    (pin_names (offset 1.016) hide)
    (pin_numbers hide)
    (property "Reference" "LED" (at 2.54 0 90) (effects (font (size 1.27 1.27))))
    (property "Value" "LED" (at -2.54 0 90) (effects (font (size 1.27 1.27))))
    (symbol "LED_0_1"
      (polyline (pts (xy -1.27 1.27) (xy 1.27 1.27) (xy 0 -1.016) (xy -1.27 1.27)) (stroke (width 0.254) (type default)) (fill (type none)))
      (polyline (pts (xy -1.27 -1.016) (xy 1.27 -1.016)) (stroke (width 0.254) (type default)) (fill (type none)))
      (polyline (pts (xy 1.27 1.778) (xy 2.286 2.794)) (stroke (width 0.254) (type default)) (fill (type none)))
      (polyline (pts (xy 0.254 2.032) (xy 1.27 3.048)) (stroke (width 0.254) (type default)) (fill (type none)))
    )
    (symbol "LED_1_1"
      (pin passive line (at 0 3.81 270) (length 2.794) (name "A" (effects (font (size 1.27 1.27)))) (number "A" (effects (font (size 1.27 1.27)))))
      (pin passive line (at 0 -3.81 90) (length 2.794) (name "K" (effects (font (size 1.27 1.27)))) (number "K" (effects (font (size 1.27 1.27)))))
    )
  )'''


def diode2_pins(ox, oy, angle=0):
    """2-pin diode/LED: A (anode, top), K (cathode, bottom). Matches sym_diode/sym_led."""
    return {
        "A": _rot(ox, oy, angle, 0,  3.81),
        "K": _rot(ox, oy, angle, 0, -3.81),
    }


def _sym_dpdt(lib_id, value):
    """Shared DPDT 6-pin toggle lib_symbol (Dailywell DW3/DW5 2M body).
    Pole A: 1=A1, 2=A_COM, 3=A2.  Pole B: 4=B1, 5=B_COM, 6=B2.
    Commons (2,5) on the left; throws (1,3,4,6) on the right. Matches dpdt6_pins().
    Footprint pad map (2x3 grid) lives in the .kicad_mod; symbol geometry is
    independent — connectivity is by pin number."""
    return f'''  (symbol "{lib_id}"
    (pin_names (offset 0.254) hide)
    (pin_numbers hide)
    (property "Reference" "SW" (at 0 9.144 0) (effects (font (size 1.27 1.27))))
    (property "Value" "{value}" (at 0 -9.144 0) (effects (font (size 1.27 1.27))))
    (symbol "{value}_0_1"
      (rectangle (start -2.54 -7.62) (end 2.54 7.62) (stroke (width 0.254) (type default)) (fill (type background)))
      (polyline (pts (xy -2.54 5.08) (xy 1.27 6.35)) (stroke (width 0.254) (type default)) (fill (type none)))
      (polyline (pts (xy -2.54 -5.08) (xy 1.27 -3.81)) (stroke (width 0.254) (type default)) (fill (type none)))
    )
    (symbol "{value}_1_1"
      (pin passive line (at 5.08 6.35 180) (length 2.54) (name "A1" (effects (font (size 1.016 1.016)))) (number "1" (effects (font (size 1.016 1.016)))))
      (pin passive line (at -5.08 5.08 0) (length 2.54) (name "A_COM" (effects (font (size 1.016 1.016)))) (number "2" (effects (font (size 1.016 1.016)))))
      (pin passive line (at 5.08 3.81 180) (length 2.54) (name "A2" (effects (font (size 1.016 1.016)))) (number "3" (effects (font (size 1.016 1.016)))))
      (pin passive line (at 5.08 -3.81 180) (length 2.54) (name "B1" (effects (font (size 1.016 1.016)))) (number "4" (effects (font (size 1.016 1.016)))))
      (pin passive line (at -5.08 -5.08 0) (length 2.54) (name "B_COM" (effects (font (size 1.016 1.016)))) (number "5" (effects (font (size 1.016 1.016)))))
      (pin passive line (at 5.08 -6.35 180) (length 2.54) (name "B2" (effects (font (size 1.016 1.016)))) (number "6" (effects (font (size 1.016 1.016)))))
    )
  )'''


def sym_dw3():
    """Dailywell DW3 (2M DPDT ON-ON) sub-mini toggle — 2-position. 6-pin DPDT body."""
    return _sym_dpdt("Switch:SW_Dailywell_DW3", "SW_DW3")


def sym_dw5():
    """Dailywell DW5 (2M DPDT ON-ON-ON) sub-mini toggle — 3-position. Same 6-pin body."""
    return _sym_dpdt("Switch:SW_Dailywell_DW5", "SW_DW5")


def sym_tl074():
    """TL074 quad op-amp SOIC-14.
    Unit A: Out=1, In-=2, In+=3. Unit B: Out=7, In-=6, In+=5.
    Unit C: Out=8, In-=9, In+=10. Unit D: Out=14, In-=13, In+=12.
    V+=4, V-=11. Unit 5 = power pins.
    Verify against TI SLOS082 datasheet before PCB layout."""
    t = _opamp_triangle()
    unit_pins = [("1","2","3"), ("7","6","5"), ("8","9","10"), ("14","13","12")]
    units = []
    for i, (out, inn, inp) in enumerate(unit_pins, 1):
        units.append(f'    (symbol "TL074_{i}_1"')
        units.append(f'      {t}')
        units.append(f'      (pin input line (at -7.62 2.54 0) (length 2.54) (name "In-" (effects (font (size 1.27 1.27)))) (number "{inn}" (effects (font (size 1.27 1.27)))))')
        units.append(f'      (pin input line (at -7.62 -2.54 0) (length 2.54) (name "In+" (effects (font (size 1.27 1.27)))) (number "{inp}" (effects (font (size 1.27 1.27)))))')
        units.append(f'      (pin output line (at 7.62 0 180) (length 2.54) (name "Out" (effects (font (size 1.27 1.27)))) (number "{out}" (effects (font (size 1.27 1.27)))))')
        units.append('    )')
    units.append('    (symbol "TL074_5_1"')
    units.append('      (pin power_in line (at 0 3.81 270) (length 1.27) (name "V+" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))')
    units.append('      (pin power_in line (at 0 -3.81 90) (length 1.27) (name "V-" (effects (font (size 1.27 1.27)))) (number "11" (effects (font (size 1.27 1.27)))))')
    units.append('    )')
    return f'''  (symbol "Amplifier_Operational:TL074"
    (pin_names (offset 0.254) hide)
    (pin_numbers hide)
    (property "Reference" "U" (at 5.08 5.08 0) (effects (font (size 1.27 1.27))))
    (property "Value" "TL074" (at 5.08 -5.08 0) (effects (font (size 1.27 1.27))))
    (symbol "TL074_0_1"
      (rectangle (start -1 -1) (end 1 1) (stroke (width 0) (type default)) (fill (type none)))
    )
{chr(10).join(units)}
  )'''


def sym_lm13700():
    """LM13700 dual OTA SOIC-16. Pinout per TI SNOSBW2F, page 3 Pin Functions:
    1=Iabc_A, 2=DiodeBias_A, 3=In+_A, 4=In-_A, 5=Out_A, 6=V-, 7=BufIn_A, 8=BufOut_A,
    9=BufOut_B, 10=BufIn_B, 11=V+, 12=Out_B, 13=In-_B, 14=In+_B, 15=DiodeBias_B, 16=Iabc_B.
    (Corrected 2026-05-29 from datasheet — prior map had 13/16 pins wrong incl. V+/V-.)"""
    return '''  (symbol "Amplifier_Operational:LM13700"
    (pin_names (offset 0.254) hide)
    (pin_numbers hide)
    (property "Reference" "U" (at 9.144 9.144 0) (effects (font (size 1.27 1.27))))
    (property "Value" "LM13700" (at 9.144 -9.144 0) (effects (font (size 1.27 1.27))))
    (symbol "LM13700_0_1"
      (rectangle (start -1 -1) (end 1 1) (stroke (width 0) (type default)) (fill (type none)))
    )
    (symbol "LM13700_1_1"
      (rectangle (start -8.89 -10.16) (end 8.89 10.16) (stroke (width 0.254) (type default)) (fill (type background)))
      (pin input line (at -11.43 8.89 0) (length 2.54) (name "Iabc_A" (effects (font (size 1.016 1.016)))) (number "1" (effects (font (size 1.016 1.016)))))
      (pin input line (at -11.43 6.35 0) (length 2.54) (name "DiodeBias_A" (effects (font (size 1.016 1.016)))) (number "2" (effects (font (size 1.016 1.016)))))
      (pin input line (at -11.43 3.81 0) (length 2.54) (name "In+_A" (effects (font (size 1.016 1.016)))) (number "3" (effects (font (size 1.016 1.016)))))
      (pin input line (at -11.43 1.27 0) (length 2.54) (name "In-_A" (effects (font (size 1.016 1.016)))) (number "4" (effects (font (size 1.016 1.016)))))
      (pin output line (at -11.43 -1.27 0) (length 2.54) (name "Out_A" (effects (font (size 1.016 1.016)))) (number "5" (effects (font (size 1.016 1.016)))))
      (pin power_in line (at -11.43 -3.81 0) (length 2.54) (name "V-" (effects (font (size 1.016 1.016)))) (number "6" (effects (font (size 1.016 1.016)))))
      (pin input line (at -11.43 -6.35 0) (length 2.54) (name "BufIn_A" (effects (font (size 1.016 1.016)))) (number "7" (effects (font (size 1.016 1.016)))))
      (pin output line (at -11.43 -8.89 0) (length 2.54) (name "BufOut_A" (effects (font (size 1.016 1.016)))) (number "8" (effects (font (size 1.016 1.016)))))
      (pin output line (at 11.43 -8.89 180) (length 2.54) (name "BufOut_B" (effects (font (size 1.016 1.016)))) (number "9" (effects (font (size 1.016 1.016)))))
      (pin input line (at 11.43 -6.35 180) (length 2.54) (name "BufIn_B" (effects (font (size 1.016 1.016)))) (number "10" (effects (font (size 1.016 1.016)))))
      (pin power_in line (at 11.43 -3.81 180) (length 2.54) (name "V+" (effects (font (size 1.016 1.016)))) (number "11" (effects (font (size 1.016 1.016)))))
      (pin output line (at 11.43 -1.27 180) (length 2.54) (name "Out_B" (effects (font (size 1.016 1.016)))) (number "12" (effects (font (size 1.016 1.016)))))
      (pin input line (at 11.43 1.27 180) (length 2.54) (name "In-_B" (effects (font (size 1.016 1.016)))) (number "13" (effects (font (size 1.016 1.016)))))
      (pin input line (at 11.43 3.81 180) (length 2.54) (name "In+_B" (effects (font (size 1.016 1.016)))) (number "14" (effects (font (size 1.016 1.016)))))
      (pin input line (at 11.43 6.35 180) (length 2.54) (name "DiodeBias_B" (effects (font (size 1.016 1.016)))) (number "15" (effects (font (size 1.016 1.016)))))
      (pin input line (at 11.43 8.89 180) (length 2.54) (name "Iabc_B" (effects (font (size 1.016 1.016)))) (number "16" (effects (font (size 1.016 1.016)))))
    )
  )'''


def sym_that340():
    """THAT340 matched transistor array SO14 (THAT340S14-U): 2 NPN (Q1,Q2) + 2 PNP (Q3,Q4).
    Pinout per THAT 300-Series datasheet Doc 600041 Rev 04, Fig 3:
    1=Q1_C, 2=Q1_B, 3=Q1_E, 4=SUB, 5=Q3_E, 6=Q3_B, 7=Q3_C,
    8=Q4_C, 9=Q4_B, 10=Q4_E, 11=SUB, 12=Q2_E, 13=Q2_B, 14=Q2_C.
    For the V/oct expo converter use the matched NPN pair Q1 (1,2,3) + Q2 (14,13,12).
    (Corrected 2026-05-29 — was wrongly a 16-pin all-NPN map.)"""
    return '''  (symbol "POGO:THAT340"
    (pin_names (offset 0.254) hide)
    (pin_numbers hide)
    (property "Reference" "U" (at 9.144 9.144 0) (effects (font (size 1.27 1.27))))
    (property "Value" "THAT340" (at 9.144 -9.144 0) (effects (font (size 1.27 1.27))))
    (symbol "THAT340_0_1"
      (rectangle (start -8.89 -8.89) (end 8.89 8.89) (stroke (width 0.254) (type default)) (fill (type background)))
    )
    (symbol "THAT340_1_1"
      (pin output line (at -11.43 7.62 0) (length 2.54) (name "Q1_C" (effects (font (size 1.016 1.016)))) (number "1" (effects (font (size 1.016 1.016)))))
      (pin input line (at -11.43 5.08 0) (length 2.54) (name "Q1_B" (effects (font (size 1.016 1.016)))) (number "2" (effects (font (size 1.016 1.016)))))
      (pin passive line (at -11.43 2.54 0) (length 2.54) (name "Q1_E" (effects (font (size 1.016 1.016)))) (number "3" (effects (font (size 1.016 1.016)))))
      (pin power_in line (at -11.43 0 0) (length 2.54) (name "SUB" (effects (font (size 1.016 1.016)))) (number "4" (effects (font (size 1.016 1.016)))))
      (pin passive line (at -11.43 -2.54 0) (length 2.54) (name "Q3_E" (effects (font (size 1.016 1.016)))) (number "5" (effects (font (size 1.016 1.016)))))
      (pin input line (at -11.43 -5.08 0) (length 2.54) (name "Q3_B" (effects (font (size 1.016 1.016)))) (number "6" (effects (font (size 1.016 1.016)))))
      (pin output line (at -11.43 -7.62 0) (length 2.54) (name "Q3_C" (effects (font (size 1.016 1.016)))) (number "7" (effects (font (size 1.016 1.016)))))
      (pin output line (at 11.43 -7.62 180) (length 2.54) (name "Q4_C" (effects (font (size 1.016 1.016)))) (number "8" (effects (font (size 1.016 1.016)))))
      (pin input line (at 11.43 -5.08 180) (length 2.54) (name "Q4_B" (effects (font (size 1.016 1.016)))) (number "9" (effects (font (size 1.016 1.016)))))
      (pin passive line (at 11.43 -2.54 180) (length 2.54) (name "Q4_E" (effects (font (size 1.016 1.016)))) (number "10" (effects (font (size 1.016 1.016)))))
      (pin power_in line (at 11.43 0 180) (length 2.54) (name "SUB" (effects (font (size 1.016 1.016)))) (number "11" (effects (font (size 1.016 1.016)))))
      (pin passive line (at 11.43 2.54 180) (length 2.54) (name "Q2_E" (effects (font (size 1.016 1.016)))) (number "12" (effects (font (size 1.016 1.016)))))
      (pin input line (at 11.43 5.08 180) (length 2.54) (name "Q2_B" (effects (font (size 1.016 1.016)))) (number "13" (effects (font (size 1.016 1.016)))))
      (pin output line (at 11.43 7.62 180) (length 2.54) (name "Q2_C" (effects (font (size 1.016 1.016)))) (number "14" (effects (font (size 1.016 1.016)))))
    )
  )'''


def sym_that2180():
    """THAT2180 Blackmer current-in/current-out VCA SOIC-8.
    Pinout per THAT 2180-Series datasheet (Doc 600029 Rev 02), Table 1:
    1=Input, 2=Ec+, 3=Ec-, 4=Sym, 5=V-, 6=Gnd, 7=V+, 8=Output.
    Current-in (pin 1) / current-out (pin 8): needs an R_in (V->I) at the input and
    a transimpedance op-amp (I->V) at the output. Gain via Ec+ (pin 2, +6.1 mV/dB)."""
    return '''  (symbol "POGO:THAT2180"
    (pin_names (offset 0.254) hide)
    (pin_numbers hide)
    (property "Reference" "U" (at 5.08 7.62 0) (effects (font (size 1.27 1.27))))
    (property "Value" "THAT2180" (at 5.08 -7.62 0) (effects (font (size 1.27 1.27))))
    (symbol "THAT2180_0_1"
      (rectangle (start -6.35 -6.35) (end 6.35 6.35) (stroke (width 0.254) (type default)) (fill (type background)))
    )
    (symbol "THAT2180_1_1"
      (pin input line (at -8.89 5.08 0) (length 2.54) (name "Input" (effects (font (size 1.016 1.016)))) (number "1" (effects (font (size 1.016 1.016)))))
      (pin input line (at -8.89 2.54 0) (length 2.54) (name "Ec+" (effects (font (size 1.016 1.016)))) (number "2" (effects (font (size 1.016 1.016)))))
      (pin input line (at -8.89 0 0) (length 2.54) (name "Ec-" (effects (font (size 1.016 1.016)))) (number "3" (effects (font (size 1.016 1.016)))))
      (pin input line (at -8.89 -2.54 0) (length 2.54) (name "Sym" (effects (font (size 1.016 1.016)))) (number "4" (effects (font (size 1.016 1.016)))))
      (pin power_in line (at -8.89 -5.08 0) (length 2.54) (name "Gnd" (effects (font (size 1.016 1.016)))) (number "6" (effects (font (size 1.016 1.016)))))
      (pin output line (at 8.89 5.08 180) (length 2.54) (name "Output" (effects (font (size 1.016 1.016)))) (number "8" (effects (font (size 1.016 1.016)))))
      (pin power_in line (at 8.89 2.54 180) (length 2.54) (name "V+" (effects (font (size 1.016 1.016)))) (number "7" (effects (font (size 1.016 1.016)))))
      (pin power_in line (at 8.89 -2.54 180) (length 2.54) (name "V-" (effects (font (size 1.016 1.016)))) (number "5" (effects (font (size 1.016 1.016)))))
    )
  )'''


def sym_cd4053():
    """CD4053 triple 2-channel analog switch SOIC-16.
    Three independent SPDT switches (A, B, C) with shared INH and V_EE.
    Verify against TI CD4053B datasheet before PCB layout."""
    return '''  (symbol "Analog_Switch:CD4053"
    (pin_names (offset 0.254) hide)
    (pin_numbers hide)
    (property "Reference" "U" (at 7.62 7.62 0) (effects (font (size 1.27 1.27))))
    (property "Value" "CD4053" (at 7.62 -7.62 0) (effects (font (size 1.27 1.27))))
    (symbol "CD4053_0_1"
      (rectangle (start -6.35 -7.62) (end 6.35 7.62) (stroke (width 0.254) (type default)) (fill (type background)))
    )
    (symbol "CD4053_1_1"
      (pin input line (at -8.89 6.35 0) (length 2.54) (name "A" (effects (font (size 1.016 1.016)))) (number "11" (effects (font (size 1.016 1.016)))))
      (pin input line (at -8.89 3.81 0) (length 2.54) (name "B" (effects (font (size 1.016 1.016)))) (number "10" (effects (font (size 1.016 1.016)))))
      (pin input line (at -8.89 1.27 0) (length 2.54) (name "C" (effects (font (size 1.016 1.016)))) (number "9" (effects (font (size 1.016 1.016)))))
      (pin input line (at -8.89 -1.27 0) (length 2.54) (name "INH" (effects (font (size 1.016 1.016)))) (number "6" (effects (font (size 1.016 1.016)))))
      (pin power_in line (at -8.89 -3.81 0) (length 2.54) (name "VDD" (effects (font (size 1.016 1.016)))) (number "16" (effects (font (size 1.016 1.016)))))
      (pin power_in line (at -8.89 -6.35 0) (length 2.54) (name "VSS" (effects (font (size 1.016 1.016)))) (number "8" (effects (font (size 1.016 1.016)))))
      (pin power_in line (at 8.89 -6.35 180) (length 2.54) (name "VEE" (effects (font (size 1.016 1.016)))) (number "7" (effects (font (size 1.016 1.016)))))
      (pin bidirectional line (at 8.89 6.35 180) (length 2.54) (name "X_A" (effects (font (size 1.016 1.016)))) (number "14" (effects (font (size 1.016 1.016)))))
      (pin bidirectional line (at 8.89 5.08 180) (length 2.54) (name "X0_A" (effects (font (size 1.016 1.016)))) (number "13" (effects (font (size 1.016 1.016)))))
      (pin bidirectional line (at 8.89 3.81 180) (length 2.54) (name "X1_A" (effects (font (size 1.016 1.016)))) (number "15" (effects (font (size 1.016 1.016)))))
      (pin bidirectional line (at 8.89 1.27 180) (length 2.54) (name "X_B" (effects (font (size 1.016 1.016)))) (number "2" (effects (font (size 1.016 1.016)))))
      (pin bidirectional line (at 8.89 0 180) (length 2.54) (name "X0_B" (effects (font (size 1.016 1.016)))) (number "1" (effects (font (size 1.016 1.016)))))
      (pin bidirectional line (at 8.89 -1.27 180) (length 2.54) (name "X1_B" (effects (font (size 1.016 1.016)))) (number "3" (effects (font (size 1.016 1.016)))))
      (pin bidirectional line (at 8.89 -3.81 180) (length 2.54) (name "X_C" (effects (font (size 1.016 1.016)))) (number "5" (effects (font (size 1.016 1.016)))))
      (pin bidirectional line (at 8.89 -5.08 180) (length 2.54) (name "X0_C" (effects (font (size 1.016 1.016)))) (number "4" (effects (font (size 1.016 1.016)))))
      (pin bidirectional line (at 8.89 -6.35 180) (length 2.54) (name "X1_C" (effects (font (size 1.016 1.016)))) (number "12" (effects (font (size 1.016 1.016)))))
    )
  )'''


# ---------------------------------------------------------------------------
# Pin coordinate helpers — return {pin_str: (x, y)} at canvas coords
# ---------------------------------------------------------------------------

def _rot(ox, oy, angle, dx, dy):
    a = math.radians(angle)
    return (ox + dx*math.cos(a) - dy*math.sin(a),
            oy + dx*math.sin(a) + dy*math.cos(a))


def rpot_pins(ox, oy, angle=0):
    """R_POT: pin1=CCW (bottom), pin2=Wiper (left), pin3=CW (top)."""
    return {
        "1": _rot(ox, oy, angle, 0, -3.81),
        "2": _rot(ox, oy, angle, -3.81, 0),
        "3": _rot(ox, oy, angle, 0, 3.81),
    }


def jack_pins(ox, oy, angle=0):
    """Audio_Jack_3.5mm_SwitchT: pin1=Tip (left), pin2=Sleeve (right), pin3=SW (bottom)."""
    return {
        "1": _rot(ox, oy, angle, -5.08, 0),
        "2": _rot(ox, oy, angle,  5.08, 0),
        "3": _rot(ox, oy, angle,  0, -5.08),
    }


def spdt_pins(ox, oy, angle=0):
    """SW_SPDT: pin1=A (upper-left), pin2=B (lower-left), pin3=C/Common (right)."""
    return {
        "1": _rot(ox, oy, angle, -3.81,  2.032),
        "2": _rot(ox, oy, angle, -3.81, -2.032),
        "3": _rot(ox, oy, angle,  3.81,  0),
    }


def sp3t_pins(ox, oy, angle=0):
    """SW_SP3T: pin1=pos1 (top-left), pin2=pos2 (mid-left), pin3=pos3 (bot-left), pin4=C (right)."""
    return {
        "1": _rot(ox, oy, angle, -3.81,  3.048),
        "2": _rot(ox, oy, angle, -3.81,  0),
        "3": _rot(ox, oy, angle, -3.81, -3.048),
        "4": _rot(ox, oy, angle,  3.81,  0),
    }


def idc_pins(ox, oy, rows, angle=0):
    """IDC header: odd pins left (-6.35), even pins right (+6.35), rows top-to-bottom."""
    pins = {}
    for r in range(rows):
        y = (rows/2 - 0.5 - r) * 2.54
        pins[str(2*r+1)] = _rot(ox, oy, angle, -6.35, y)
        pins[str(2*r+2)] = _rot(ox, oy, angle,  6.35, y)
    return pins


def r_pins(ox, oy, angle=0):
    """Device:R: pin1 top, pin2 bottom."""
    return {
        "1": _rot(ox, oy, angle, 0,  3.81),
        "2": _rot(ox, oy, angle, 0, -3.81),
    }


def c_pins(ox, oy, angle=0):
    """Device:C: pin1 top (+), pin2 bottom."""
    return {
        "1": _rot(ox, oy, angle, 0,  3.81),
        "2": _rot(ox, oy, angle, 0, -3.81),
    }


def opamp_dual_pins(ox, oy, unit, angle=0):
    """Dual op-amp (TL072/LM4562/NE5532) pin coords for unit A (1) or B (2).
    Returns {pin_str: (x,y)} for signal pins of that unit only.
    Power pins (4, 8) are not returned — place power symbols at supply pins separately."""
    if unit == 1:
        return {
            "2": _rot(ox, oy, angle, -7.62,  2.54),  # In-
            "3": _rot(ox, oy, angle, -7.62, -2.54),  # In+
            "1": _rot(ox, oy, angle,  7.62,  0),     # Out
        }
    else:  # unit 2
        return {
            "6": _rot(ox, oy, angle, -7.62,  2.54),  # In-
            "5": _rot(ox, oy, angle, -7.62, -2.54),  # In+
            "7": _rot(ox, oy, angle,  7.62,  0),     # Out
        }


def opamp_dual_all_pins(ox, oy, angle=0):
    """All pins of a dual op-amp (TL072/LM4562/NE5532/OPA1612): both units + power.
    Unit A: 1/2/3, Unit B: 7/6/5, Power: V+=8 (top), V-=4 (bottom)."""
    pins = {}
    pins.update(opamp_dual_pins(ox, oy, 1, angle))
    pins.update(opamp_dual_pins(ox, oy, 2, angle))
    pins["8"] = _rot(ox, oy, angle, 0,  7.62)   # V+
    pins["4"] = _rot(ox, oy, angle, 0, -7.62)   # V-
    return pins


def dpdt6_pins(ox, oy, angle=0):
    """DW3/DW5 DPDT 6-pin toggle: 1=A1, 2=A_COM, 3=A2, 4=B1, 5=B_COM, 6=B2.
    Matches _sym_dpdt() geometry (commons left, throws right)."""
    return {
        "1": _rot(ox, oy, angle,  5.08,  6.35),
        "2": _rot(ox, oy, angle, -5.08,  5.08),
        "3": _rot(ox, oy, angle,  5.08,  3.81),
        "4": _rot(ox, oy, angle,  5.08, -3.81),
        "5": _rot(ox, oy, angle, -5.08, -5.08),
        "6": _rot(ox, oy, angle,  5.08, -6.35),
    }


def bat54s_pins(ox, oy, angle=0):
    """BAT54S: pin1=A1 (left), pin2=COM (bottom, signal node), pin3=K2 (right).
    Matches sym_bat54s() geometry."""
    return {
        "1": _rot(ox, oy, angle, -7.62, 0),
        "2": _rot(ox, oy, angle, 0, -5.08),
        "3": _rot(ox, oy, angle,  7.62, 0),
    }


def that2180_pins(ox, oy, angle=0):
    """THAT2180: 1=Input, 2=Ec+, 3=Ec-, 4=Sym, 6=Gnd (left); 8=Output, 7=V+, 5=V- (right).
    Matches sym_that2180() geometry."""
    return {
        "1": _rot(ox, oy, angle, -8.89,  5.08),
        "2": _rot(ox, oy, angle, -8.89,  2.54),
        "3": _rot(ox, oy, angle, -8.89,  0),
        "4": _rot(ox, oy, angle, -8.89, -2.54),
        "6": _rot(ox, oy, angle, -8.89, -5.08),
        "8": _rot(ox, oy, angle,  8.89,  5.08),
        "7": _rot(ox, oy, angle,  8.89,  2.54),
        "5": _rot(ox, oy, angle,  8.89, -2.54),
    }


def opamp_quad_pins(ox, oy, unit, angle=0):
    """Quad op-amp (TL074) pin coords for unit 1-4. Power unit (5) not included."""
    unit_map = {
        1: {"2": (-7.62, 2.54), "3": (-7.62, -2.54), "1": (7.62, 0)},
        2: {"6": (-7.62, 2.54), "5": (-7.62, -2.54), "7": (7.62, 0)},
        3: {"9": (-7.62, 2.54), "10": (-7.62, -2.54), "8": (7.62, 0)},
        4: {"13": (-7.62, 2.54), "12": (-7.62, -2.54), "14": (7.62, 0)},
    }
    return {p: _rot(ox, oy, angle, dx, dy) for p, (dx, dy) in unit_map[unit].items()}


# ---------------------------------------------------------------------------
# Generic schematic emitters
# ---------------------------------------------------------------------------

def place_symbol(lib_id, ref, value, ox, oy, angle=0, mirror="", unit=1, footprint=""):
    mirror_str = f'\n    (mirror {mirror})' if mirror else ""
    fp_str = (f'\n  (property "Footprint" "{footprint}" (at {ox:.3f} {oy:.3f} 0)\n'
              f'    (effects (font (size 1.016 1.016)) (hide yes)))') if footprint else ""
    emit(f'''(symbol
  (lib_id "{lib_id}")
  (at {ox:.3f} {oy:.3f} {angle}){mirror_str}
  (unit {unit})
  (in_bom yes)
  (on_board yes)
  (uuid "{uid()}")
  (property "Reference" "{ref}" (at {ox+3:.3f} {oy+3:.3f} 0)
    (effects (font (size 1.27 1.27)) (justify left)))
  (property "Value" "{value}" (at {ox+3:.3f} {oy-0.5:.3f} 0)
    (effects (font (size 1.016 1.016)) (justify left) (hide yes))){fp_str}
)''')


def global_label(net, x, y, shape="input", angle=0):
    emit(f'''(global_label "{net}"
  (shape {shape})
  (at {x:.3f} {y:.3f} {angle})
  (effects (font (size 1.016 1.016)) (justify left))
  (uuid "{uid()}")
)''')


def connect_pin(net, px, py, shape="passive"):
    """Place a global label at a pin endpoint to assign its net."""
    global_label(net, px, py, shape=shape)


def power_sym(name, x, y):
    emit(f'''(symbol
  (lib_id "power:{name}")
  (at {x:.3f} {y:.3f} 0)
  (unit 1) (in_bom yes) (on_board yes)
  (uuid "{uid()}")
  (property "Reference" "#PWR" (at {x:.3f} {y-2:.3f} 0)
    (effects (font (size 1.016 1.016)) (hide yes)))
  (property "Value" "{name}" (at {x:.3f} {y+2:.3f} 0)
    (effects (font (size 1.016 1.016))))
)''')


def wire(x1, y1, x2, y2):
    emit(f'(wire (pts (xy {x1:.3f} {y1:.3f}) (xy {x2:.3f} {y2:.3f})) (uuid "{uid()}"))')


# ---------------------------------------------------------------------------
# IDC connector placement helpers (cover all sizes used in POGO)
# ---------------------------------------------------------------------------

def _place_idc(rows, ref, value, net_map, col, row_y):
    ox, oy = col * 20.0, row_y
    cols = 2
    lib_id = f"Connector_IDC:IDC-Header_{cols}x{rows:02d}_P2.54mm_Vertical"
    place_symbol(lib_id, ref, value, ox, oy)
    pins = idc_pins(ox, oy, rows)
    for pin, net in net_map.items():
        if net:
            connect_pin(net, *pins[str(pin)], shape="passive")


def place_idc34(ref, value, net_map, col, row_y):
    _place_idc(17, ref, value, net_map, col, row_y)


def place_idc40(ref, value, net_map, col, row_y):
    _place_idc(20, ref, value, net_map, col, row_y)


def place_idc24(ref, value, net_map, col, row_y):
    _place_idc(12, ref, value, net_map, col, row_y)


def place_idc16(ref, value, net_map, col, row_y):
    """16-pin IDC (Eurorack power header)."""
    _place_idc(8, ref, value, net_map, col, row_y)


# ---------------------------------------------------------------------------
# PinHeader stacking header placement (Utility ↔ Audio board)
# ---------------------------------------------------------------------------

def _place_pin_header(rows, ref, value, net_map, col, row_y):
    ox, oy = col * 20.0, row_y
    cols = 2
    lib_id = f"Connector_PinHeader_2.54mm:PinHeader_{cols}x{rows:02d}_P2.54mm_Vertical"
    place_symbol(lib_id, ref, value, ox, oy)
    pins = idc_pins(ox, oy, rows)   # same geometry as IDC
    for pin, net in net_map.items():
        if net:
            connect_pin(net, *pins[str(pin)], shape="passive")


def place_pin_header40(ref, value, net_map, col, row_y):
    """40-pin stacking header (2×20) — STK_AUDIO_L / STK_AUDIO_R."""
    _place_pin_header(20, ref, value, net_map, col, row_y)


# ---------------------------------------------------------------------------
# THAT340 and CD4053 pin coordinate helpers
# ---------------------------------------------------------------------------

def lm13700_pins(ox, oy, angle=0):
    """LM13700 SOIC-16 connection-point coords. Matches sym_lm13700() geometry.
    1=Iabc_A,2=DiodeBias_A,3=In+_A,4=In-_A,5=Out_A,6=V-,7=BufIn_A,8=BufOut_A,
    9=BufOut_B,10=BufIn_B,11=V+,12=Out_B,13=In-_B,14=In+_B,15=DiodeBias_B,16=Iabc_B."""
    left = {"1": 8.89, "2": 6.35, "3": 3.81, "4": 1.27,
            "5": -1.27, "6": -3.81, "7": -6.35, "8": -8.89}
    right = {"9": -8.89, "10": -6.35, "11": -3.81, "12": -1.27,
             "13": 1.27, "14": 3.81, "15": 6.35, "16": 8.89}
    pins = {p: _rot(ox, oy, angle, -11.43, y) for p, y in left.items()}
    pins.update({p: _rot(ox, oy, angle, 11.43, y) for p, y in right.items()})
    return pins


def that340_pins(ox, oy, angle=0):
    """THAT340 SO14 connection-point coords. Matches sym_that340() geometry.
    1=Q1_C,2=Q1_B,3=Q1_E,4=SUB,5=Q3_E,6=Q3_B,7=Q3_C,
    8=Q4_C,9=Q4_B,10=Q4_E,11=SUB,12=Q2_E,13=Q2_B,14=Q2_C."""
    left = {"1": 7.62, "2": 5.08, "3": 2.54, "4": 0.0,
            "5": -2.54, "6": -5.08, "7": -7.62}
    right = {"8": -7.62, "9": -5.08, "10": -2.54, "11": 0.0,
             "12": 2.54, "13": 5.08, "14": 7.62}
    pins = {p: _rot(ox, oy, angle, -11.43, y) for p, y in left.items()}
    pins.update({p: _rot(ox, oy, angle, 11.43, y) for p, y in right.items()})
    return pins


def cd4053_pins(ox, oy):
    """CD4053 SOIC-16 connection-point coords. Matches sym_cd4053() geometry."""
    return {
        "11": (ox - 8.89, oy + 6.35),   # A
        "10": (ox - 8.89, oy + 3.81),   # B
        "9":  (ox - 8.89, oy + 1.27),   # C
        "6":  (ox - 8.89, oy - 1.27),   # INH
        "16": (ox - 8.89, oy - 3.81),   # VDD
        "8":  (ox - 8.89, oy - 6.35),   # VSS
        "7":  (ox + 8.89, oy - 6.35),   # VEE
        "14": (ox + 8.89, oy + 6.35),   # X_A
        "13": (ox + 8.89, oy + 5.08),   # X0_A
        "15": (ox + 8.89, oy + 3.81),   # X1_A
        "2":  (ox + 8.89, oy + 1.27),   # X_B
        "1":  (ox + 8.89, oy + 0.00),   # X0_B
        "3":  (ox + 8.89, oy - 1.27),   # X1_B
        "5":  (ox + 8.89, oy - 3.81),   # X_C
        "4":  (ox + 8.89, oy - 5.08),   # X0_C
        "12": (ox + 8.89, oy - 6.35),   # X1_C
    }
