#!/usr/bin/env python3
"""
POGO Control Board — KiCad 7 schematic generator.

Produces: pogo-control-board.kicad_sch

See specs/kicad-process.md for methodology, net naming, and known gaps.

Run from the kicad/ directory:
    python3 generate_control_board.py
"""

import uuid
import math

OUT = []

def uid():
    return str(uuid.uuid4())

def emit(s):
    OUT.append(s)

# ---------------------------------------------------------------------------
# KiCad 7 lib_symbol geometry helpers
# ---------------------------------------------------------------------------

def sym_jack():
    """AudioJack3 with tip-switching lug (Thonkiconn PJ301M-12).
    Pins: T=Tip, S=Sleeve, SW=Switch-lug"""
    return '''  (symbol "Device:Audio_Jack_3.5mm_SwitchT"
    (pin_names (offset 1.016) hide)
    (pin_numbers hide)
    (property "Reference" "J" (at 0 5.08 0) (effects (font (size 1.27 1.27))))
    (property "Value" "Audio_Jack_3.5mm_SwitchT" (at 0 -5.08 0) (effects (font (size 1.27 1.27))))
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

def sym_rpot():
    """3-pin potentiometer / slider. Pins: 1=CCW, 2=Wiper, 3=CW"""
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

def sym_spdt():
    """SPDT toggle switch. Pins: C=Common, A=throw-A, B=throw-B"""
    return '''  (symbol "Switch:SW_SPDT"
    (pin_names (offset 1.016))
    (pin_numbers hide)
    (property "Reference" "SW" (at 0 3.81 0) (effects (font (size 1.27 1.27))))
    (property "Value" "SW_SPDT" (at 0 -3.81 0) (effects (font (size 1.27 1.27))))
    (symbol "SW_SPDT_0_1"
      (circle (center -1.016 2.032) (radius 0.508) (stroke (width 0) (type default)) (fill (type none)))
      (circle (center -1.016 -2.032) (radius 0.508) (stroke (width 0) (type default)) (fill (type none)))
      (circle (center 1.524 0) (radius 0.508) (stroke (width 0) (type default)) (fill (type none)))
      (polyline (pts (xy -0.508 2.032) (xy 1.016 0.508)) (stroke (width 0) (type default)) (fill (type none)))
    )
    (symbol "SW_SPDT_1_1"
      (pin passive line (at -3.81 2.032 0) (length 2.794)
        (name "A" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
      (pin passive line (at -3.81 -2.032 0) (length 2.794)
        (name "B" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
      (pin passive line (at 3.81 0 180) (length 2.286)
        (name "C" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
    )
  )'''

def sym_sp3t():
    """SP3T toggle switch. Pins: C=Common, 1/2/3=positions"""
    return '''  (symbol "Switch:SW_SP3T"
    (pin_names (offset 1.016))
    (pin_numbers hide)
    (property "Reference" "SW" (at 0 5.08 0) (effects (font (size 1.27 1.27))))
    (property "Value" "SW_SP3T" (at 0 -5.08 0) (effects (font (size 1.27 1.27))))
    (symbol "SW_SP3T_0_1"
      (circle (center -1.016 3.048) (radius 0.508) (stroke (width 0) (type default)) (fill (type none)))
      (circle (center -1.016 0) (radius 0.508) (stroke (width 0) (type default)) (fill (type none)))
      (circle (center -1.016 -3.048) (radius 0.508) (stroke (width 0) (type default)) (fill (type none)))
      (circle (center 1.524 0) (radius 0.508) (stroke (width 0) (type default)) (fill (type none)))
      (polyline (pts (xy -0.508 3.048) (xy 1.016 0.508)) (stroke (width 0) (type default)) (fill (type none)))
    )
    (symbol "SW_SP3T_1_1"
      (pin passive line (at -3.81 3.048 0) (length 2.794)
        (name "1" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
      (pin passive line (at -3.81 0 0) (length 2.794)
        (name "2" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
      (pin passive line (at -3.81 -3.048 0) (length 2.794)
        (name "3" (effects (font (size 1.27 1.27)))) (number "3" (effects (font (size 1.27 1.27)))))
      (pin passive line (at 3.81 0 180) (length 2.286)
        (name "C" (effects (font (size 1.27 1.27)))) (number "4" (effects (font (size 1.27 1.27)))))
    )
  )'''

def sym_idc(rows, cols=2):
    """IDC header symbol with rows×cols pins. rows=17 → 34-pin, rows=10 → 20-pin."""
    total = rows * cols
    name = f"Connector_IDC:IDC-Header_{cols}x{rows:02d}_P2.54mm_Vertical"
    lines = [f'  (symbol "{name}"']
    lines.append('    (pin_names (offset 1.016) hide)')
    lines.append('    (pin_numbers hide)')
    lines.append(f'    (property "Reference" "CN" (at 0 {rows*1.27+2.54:.3f} 0) (effects (font (size 1.27 1.27))))')
    lines.append(f'    (property "Value" "{name}" (at 0 {-(rows*1.27+2.54):.3f} 0) (effects (font (size 1.27 1.27)) (hide yes)))')
    lines.append(f'    (symbol "{name.split(":")[-1]}_0_1"')
    h = rows * 2.54
    lines.append(f'      (rectangle (start -3.81 {h/2:.3f}) (end 3.81 {-h/2:.3f}) (stroke (width 0.254) (type default)) (fill (type background)))')
    lines.append('    )')
    lines.append(f'    (symbol "{name.split(":")[-1]}_1_1"')
    # Odd pins on left (col 1), even pins on right (col 2)
    for r in range(rows):
        y = (rows/2 - 0.5 - r) * 2.54
        pin_odd = 2*r + 1
        pin_even = 2*r + 2
        lines.append(f'      (pin passive line (at -6.35 {y:.3f} 0) (length 2.54)')
        lines.append(f'        (name "Pin_{pin_odd}" (effects (font (size 1.016 1.016))))')
        lines.append(f'        (number "{pin_odd}" (effects (font (size 1.016 1.016)))))')
        lines.append(f'      (pin passive line (at 6.35 {y:.3f} 180) (length 2.54)')
        lines.append(f'        (name "Pin_{pin_even}" (effects (font (size 1.016 1.016))))')
        lines.append(f'        (number "{pin_even}" (effects (font (size 1.016 1.016)))))')
    lines.append('    )')
    lines.append('  )')
    return '\n'.join(lines)

def sym_power(name, pwr_type="pwr"):
    """Power symbol (+12V, -12V, GND)."""
    if name == "GND":
        body = '''      (polyline (pts (xy 0 0) (xy 0 -1.27)) (stroke (width 0) (type default)) (fill (type none)))
      (polyline (pts (xy -1.27 -1.27) (xy 1.27 -1.27)) (stroke (width 0.254) (type default)) (fill (type none)))
      (polyline (pts (xy -0.762 -1.778) (xy 0.762 -1.778)) (stroke (width 0.254) (type default)) (fill (type none)))
      (polyline (pts (xy -0.254 -2.286) (xy 0.254 -2.286)) (stroke (width 0.254) (type default)) (fill (type none)))'''
        pin_y = 0
        pin_angle = 270
    elif "12V" in name:
        arrow_dir = 1 if "+" in name else -1
        body = f'''      (polyline (pts (xy 0 0) (xy 0 {arrow_dir*1.27:.3f})) (stroke (width 0) (type default)) (fill (type none)))
      (polyline (pts (xy -0.635 {arrow_dir*0.635:.3f}) (xy 0 {arrow_dir*1.27:.3f}) (xy 0.635 {arrow_dir*0.635:.3f})) (stroke (width 0) (type default)) (fill (type none)))'''
        pin_y = 0
        pin_angle = 270
    else:
        body = '      (circle (center 0 0) (radius 0.508) (stroke (width 0) (type default)) (fill (type none)))'
        pin_y = 0
        pin_angle = 270

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
# Pin offsets for each symbol (relative to symbol origin, at angle=0)
# ---------------------------------------------------------------------------
# R_POT: pin1 at (0, -3.81), pin2 at (-3.81, 0), pin3 at (0, 3.81)
# AudioJack: pin1/T at (-5.08, 0), pin2/S at (5.08, 0), pin3/SW at (0, -5.08)
# SW_SPDT: pin1/A at (-3.81, 2.032), pin2/B at (-3.81,-2.032), pin3/C at (3.81, 0)
# SW_SP3T: pin1 at (-3.81,3.048), pin2 at (-3.81,0), pin3 at(-3.81,-3.048), pin4/C at(3.81,0)
# IDC 2x17: odd pins at x=-6.35, even at x=6.35, y per row
# power: pin at (0,0)

def rpot_pins(ox, oy, angle=0):
    """Return {pin_num: (x,y)} for R_POT placed at (ox,oy) with angle degrees."""
    a = math.radians(angle)
    def rot(dx, dy):
        return (ox + dx*math.cos(a) - dy*math.sin(a),
                oy + dx*math.sin(a) + dy*math.cos(a))
    return {
        "1": rot(0, -3.81),    # CCW end
        "2": rot(-3.81, 0),    # Wiper
        "3": rot(0, 3.81),     # CW end
    }

def jack_pins(ox, oy, angle=0):
    a = math.radians(angle)
    def rot(dx, dy):
        return (ox + dx*math.cos(a) - dy*math.sin(a),
                oy + dx*math.sin(a) + dy*math.cos(a))
    return {
        "1": rot(-5.08, 0),   # Tip
        "2": rot(5.08, 0),    # Sleeve
        "3": rot(0, -5.08),   # Switch lug
    }

def spdt_pins(ox, oy, angle=0):
    a = math.radians(angle)
    def rot(dx, dy):
        return (ox + dx*math.cos(a) - dy*math.sin(a),
                oy + dx*math.sin(a) + dy*math.cos(a))
    return {
        "1": rot(-3.81, 2.032),   # A
        "2": rot(-3.81, -2.032),  # B
        "3": rot(3.81, 0),        # C (common)
    }

def sp3t_pins(ox, oy, angle=0):
    a = math.radians(angle)
    def rot(dx, dy):
        return (ox + dx*math.cos(a) - dy*math.sin(a),
                oy + dx*math.sin(a) + dy*math.cos(a))
    return {
        "1": rot(-3.81, 3.048),
        "2": rot(-3.81, 0),
        "3": rot(-3.81, -3.048),
        "4": rot(3.81, 0),        # Common
    }

def idc_pins(ox, oy, rows, angle=0):
    """Return pin endpoints for IDC header placed at (ox,oy)."""
    a = math.radians(angle)
    def rot(dx, dy):
        return (ox + dx*math.cos(a) - dy*math.sin(a),
                oy + dx*math.sin(a) + dy*math.cos(a))
    pins = {}
    for r in range(rows):
        y = (rows/2 - 0.5 - r) * 2.54
        pins[str(2*r+1)] = rot(-6.35, y)
        pins[str(2*r+2)] = rot(6.35, y)
    return pins

# ---------------------------------------------------------------------------
# Schematic emitters
# ---------------------------------------------------------------------------

def emit_lib_symbols():
    emit('(lib_symbols')
    emit(sym_jack())
    emit(sym_rpot())
    emit(sym_spdt())
    emit(sym_sp3t())
    emit(sym_idc(17, 2))   # 34-pin (CN_CTRL_1)
    emit(sym_idc(20, 2))   # 40-pin (CN_CTRL_2 — expanded to carry all switch positions)
    emit(sym_idc(12, 2))   # 24-pin (CN_CTRL_3 — 23 parameter wipers + 1 spare)
    emit(sym_power("+12V"))
    emit(sym_power("-12V"))
    emit(sym_power("GND"))
    emit(')')

def place_symbol(lib_id, ref, value, ox, oy, angle=0, mirror=""):
    mirror_str = f'\n    (mirror {mirror})' if mirror else ""
    emit(f'''(symbol
  (lib_id "{lib_id}")
  (at {ox:.3f} {oy:.3f} {angle}){mirror_str}
  (unit 1)
  (in_bom yes)
  (on_board yes)
  (uuid "{uid()}")
  (property "Reference" "{ref}" (at {ox+3:.3f} {oy+3:.3f} 0)
    (effects (font (size 1.27 1.27)) (justify left)))
  (property "Value" "{value}" (at {ox+3:.3f} {oy-0.5:.3f} 0)
    (effects (font (size 1.016 1.016)) (justify left) (hide yes)))
)''')

def global_label(net, x, y, shape="input", angle=0):
    emit(f'''(global_label "{net}"
  (shape {shape})
  (at {x:.3f} {y:.3f} {angle})
  (effects (font (size 1.016 1.016)) (justify left))
  (uuid "{uid()}")
)''')

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

def connect_pin(net, px, py, shape="passive"):
    """Place a global label directly at a pin endpoint."""
    global_label(net, px, py, shape=shape)

def wire(x1, y1, x2, y2):
    emit(f'(wire (pts (xy {x1:.3f} {y1:.3f}) (xy {x2:.3f} {y2:.3f})) (uuid "{uid()}"))')

# ---------------------------------------------------------------------------
# Component placement: zone grid
# Each zone occupies a row of components stacked vertically.
# Grid: X increments by 20mm per component column; Y rows at 30, 60, 90, 120mm etc.
# ---------------------------------------------------------------------------

# We use a simple sequential column layout per zone.
# Components are placed at (col*20, zone_base_y), global labels at pin positions.

def place_jack(ref, value, tip_net, sleeve_net, sw_net, col, row_y):
    ox = col * 20.0
    oy = row_y
    place_symbol("Device:Audio_Jack_3.5mm_SwitchT", ref, value, ox, oy)
    pins = jack_pins(ox, oy)
    connect_pin(tip_net,    *pins["1"], shape="passive")
    connect_pin(sleeve_net, *pins["2"], shape="passive")
    connect_pin(sw_net,     *pins["3"], shape="passive")

def place_pot(ref, value, ccw_net, wpr_net, cw_net, col, row_y):
    ox = col * 20.0
    oy = row_y
    place_symbol("Device:R_POT", ref, value, ox, oy)
    pins = rpot_pins(ox, oy)
    connect_pin(ccw_net, *pins["1"], shape="passive")
    connect_pin(wpr_net, *pins["2"], shape="passive")
    connect_pin(cw_net,  *pins["3"], shape="passive")

def place_spdt(ref, value, a_net, b_net, c_net, col, row_y):
    ox = col * 20.0
    oy = row_y
    place_symbol("Switch:SW_SPDT", ref, value, ox, oy)
    pins = spdt_pins(ox, oy)
    if a_net: connect_pin(a_net, *pins["1"], shape="passive")
    if b_net: connect_pin(b_net, *pins["2"], shape="passive")
    if c_net: connect_pin(c_net, *pins["3"], shape="passive")
    return pins

def place_sp3t(ref, value, p1_net, p2_net, p3_net, c_net, col, row_y):
    ox = col * 20.0
    oy = row_y
    place_symbol("Switch:SW_SP3T", ref, value, ox, oy)
    pins = sp3t_pins(ox, oy)
    if p1_net: connect_pin(p1_net, *pins["1"], shape="passive")
    if p2_net: connect_pin(p2_net, *pins["2"], shape="passive")
    if p3_net: connect_pin(p3_net, *pins["3"], shape="passive")
    if c_net:  connect_pin(c_net,  *pins["4"], shape="passive")
    return pins

def place_idc34(ref, value, net_map, col, row_y):
    """net_map: dict {pin_str: net_name}"""
    ox = col * 20.0
    oy = row_y
    place_symbol("Connector_IDC:IDC-Header_2x17_P2.54mm_Vertical", ref, value, ox, oy)
    pins = idc_pins(ox, oy, 17)
    for pin, net in net_map.items():
        if net:
            connect_pin(net, *pins[str(pin)], shape="passive")

def place_idc20(ref, value, net_map, col, row_y):
    ox = col * 20.0
    oy = row_y
    place_symbol("Connector_IDC:IDC-Header_2x10_P2.54mm_Vertical", ref, value, ox, oy)
    pins = idc_pins(ox, oy, 10)
    for pin, net in net_map.items():
        if net:
            connect_pin(net, *pins[str(pin)], shape="passive")

def place_idc24(ref, value, net_map, col, row_y):
    ox = col * 20.0
    oy = row_y
    place_symbol("Connector_IDC:IDC-Header_2x12_P2.54mm_Vertical", ref, value, ox, oy)
    pins = idc_pins(ox, oy, 12)
    for pin, net in net_map.items():
        if net:
            connect_pin(net, *pins[str(pin)], shape="passive")

def place_idc40(ref, value, net_map, col, row_y):
    ox = col * 20.0
    oy = row_y
    place_symbol("Connector_IDC:IDC-Header_2x20_P2.54mm_Vertical", ref, value, ox, oy)
    pins = idc_pins(ox, oy, 20)
    for pin, net in net_map.items():
        if net:
            connect_pin(net, *pins[str(pin)], shape="passive")

# ---------------------------------------------------------------------------
# Main: define all components and their net assignments
# ---------------------------------------------------------------------------

def build_schematic():
    emit('(kicad_sch (version 20230121) (generator "eeschema")')
    emit('(paper "A0")')

    emit_lib_symbols()

    col = 1   # global column counter (increments for each component)
    BASE = 50  # base Y; components at BASE, BASE+50, BASE+100 within zone

    # -----------------------------------------------------------------------
    # Zone 0a: INPUT jacks + GAIN switch
    # -----------------------------------------------------------------------
    ZY = 50
    place_jack("J1",  "L IN",    "NET_L_IN",       "GND", "GND", col, ZY); col+=1
    place_jack("J2",  "R IN",    "NET_R_IN",        "GND", "GND", col, ZY); col+=1

    # GAIN switch (SPDT): 1× throw → GND, 5× throw → +12V, common → CN2 pin 5.
    # Common reads GND when 1× selected, +12V when 5× selected; utility board decodes.
    pins = place_spdt("SW1", "GAIN 1x/5x",
                      None, None, "NET_SW_GAIN_COM",
                      col, ZY)
    power_sym("GND",  *pins["1"])   # 1× throw → GND
    power_sym("+12V", *pins["2"])   # 5× throw → +12V
    col += 1

    # -----------------------------------------------------------------------
    # Zone 0b: ENVELOPE section
    # -----------------------------------------------------------------------
    ZY = 50  # same row, continue columns

    # MOD SRC select switch: SW2 — 3-pos: L / MAX / AVG; common → +12V on board.
    pins = place_sp3t("SW2", "MOD SRC SEL",
                      "NET_SW_MODSRC_L", "NET_SW_MODSRC_MAX", "NET_SW_MODSRC_AVG",
                      None,
                      col, ZY)
    power_sym("+12V", *pins["4"])   # MOD SRC common → +12V
    col += 1

    # ATTACK pot
    place_pot("RV1", "ATTACK",
              "GND", "NET_WPR_ATTACK", "+12V",
              col, ZY); col+=1

    # RELEASE pot
    place_pot("RV2", "RELEASE",
              "GND", "NET_WPR_RELEASE", "+12V",
              col, ZY); col+=1

    # ENV OUT L jack
    place_jack("J3",  "ENV L",    "NET_ENV_OUT_L",   "GND", "GND", col, ZY); col+=1
    # ENV OUT R jack
    place_jack("J4",  "ENV R",    "NET_ENV_OUT_R",   "GND", "GND", col, ZY); col+=1

    # -----------------------------------------------------------------------
    # Zone 0c: MOD BUS section
    # -----------------------------------------------------------------------
    # AMOUNT pot
    place_pot("RV3", "AMOUNT",
              "GND", "NET_WPR_AMOUNT", "+12V",
              col, ZY); col+=1

    # OFFSET pot
    place_pot("RV4", "OFFSET",
              "-12V", "NET_WPR_OFFSET_MB", "+12V",
              col, ZY); col+=1

    # MOD IN jack (primary mod source; normalizes to ENV when unplugged)
    place_jack("J9",  "MOD IN",   "NET_MOD_IN",      "GND", "NET_ENV_NORM", col, ZY); col+=1

    # -----------------------------------------------------------------------
    # Zone 1 COMB section: COMB BYPASS, WIDTH, POLARITY, MASTER OFFSET
    # -----------------------------------------------------------------------
    ZY = 50
    place_pot("RV5", "COMB BYPASS",
              "GND", "NET_WPR_COMB_BYPASS", "+12V",
              col, ZY); col+=1

    place_pot("RV6", "WIDTH",
              "-12V", "NET_WPR_WIDTH", "+12V",
              col, ZY); col+=1

    # POLARITY switch: SW3 — 3-pos: POS / OFF / NEG; common → +12V on board.
    pins = place_sp3t("SW3", "POLARITY",
                      "NET_SW_POL_POS", "NET_SW_POL_OFF", "NET_SW_POL_NEG",
                      None,
                      col, ZY)
    power_sym("+12V", *pins["4"])   # POLARITY common → +12V
    col += 1

    place_pot("RV7", "MASTER OFFSET",
              "-12V", "NET_WPR_MASTER_OFFSET", "+12V",
              col, ZY); col+=1

    # -----------------------------------------------------------------------
    # Zone 1 DIST section: MODE switch (shared), FB DIST BLEND
    # -----------------------------------------------------------------------
    # MODE switch (SW4): 1 shared switch for all 3 comb groups (per panel.svg).
    # Common → +12V on control board; position outputs → CN2 pins 6–8.
    pins = place_sp3t("SW4", "MODE",
                      "NET_SW_MODE_SFT", "NET_SW_MODE_HRD", "NET_SW_MODE_WFD",
                      None,
                      col, ZY)
    power_sym("+12V", *pins["4"])   # MODE common → +12V
    col += 1

    place_pot("RV8", "FB DIST BLEND",
              "GND", "NET_WPR_FB_DIST_BLEND", "+12V",
              col, ZY); col+=1

    # Zone 1 CV jacks: BYPASS, OFFSET (MASTER), BLEND
    place_jack("J10", "BYPASS CV",  "NET_CV_BYPASS",       "GND", "NET_MODBUS_NORM",  col, ZY); col+=1
    place_jack("J11", "OFFSET CV",  "NET_CV_OFFSET",       "GND", "NET_MODBUS_NORM",  col, ZY); col+=1
    place_jack("J12", "BLEND CV",   "NET_CV_BLEND",        "GND", "NET_MODBUS_NORM",   col, ZY); col+=1

    # Zone 1 attenuverter pots: BYPASS ATT, OFFSET ATT, BLEND ATT
    place_pot("RV9",  "BYPASS ATT",  "-12V", "NET_WPR_ATT_BYPASS",  "+12V", col, ZY); col+=1
    place_pot("RV10", "OFFSET ATT",  "-12V", "NET_WPR_ATT_OFFSET",  "+12V", col, ZY); col+=1
    place_pot("RV11", "BLEND ATT",   "-12V", "NET_WPR_ATT_BLEND",   "+12V", col, ZY); col+=1

    # -----------------------------------------------------------------------
    # Zone 2a: COMB 1 — FREQ1, FB1, DRIVE1, attenuverters, CV jacks
    # -----------------------------------------------------------------------
    place_pot("RV12", "FREQ 1",   "-12V", "NET_WPR_FREQ1",  "+12V", col, ZY); col+=1
    place_pot("RV13", "FB 1",     "GND",  "NET_WPR_FB1",    "+12V", col, ZY); col+=1
    place_pot("RV14", "DRIVE 1",  "GND",  "NET_WPR_DRIVE1", "+12V", col, ZY); col+=1
    place_pot("RV15", "FREQ ATT1","-12V", "NET_WPR_ATT_FREQ1",  "+12V", col, ZY); col+=1
    place_pot("RV16", "FB ATT1",  "-12V", "NET_WPR_ATT_FB1",    "+12V", col, ZY); col+=1
    place_pot("RV17", "DRIVE ATT1","-12V","NET_WPR_ATT_DRIVE1", "+12V", col, ZY); col+=1
    place_jack("J13", "FREQ CV1", "NET_CV_FREQ1",  "GND", "NET_MODBUS_NORM",  col, ZY); col+=1
    place_jack("J14", "FB CV1",   "NET_CV_FB1",    "GND", "NET_MODBUS_NORM",    col, ZY); col+=1
    place_jack("J15", "DRIVE CV1","NET_CV_DRIVE1", "GND", "NET_MODBUS_NORM", col, ZY); col+=1

    # -----------------------------------------------------------------------
    # Zone 2b: COMB 2
    # -----------------------------------------------------------------------
    place_pot("RV18", "FREQ 2",   "-12V", "NET_WPR_FREQ2",  "+12V", col, ZY); col+=1
    place_pot("RV19", "FB 2",     "GND",  "NET_WPR_FB2",    "+12V", col, ZY); col+=1
    place_pot("RV20", "DRIVE 2",  "GND",  "NET_WPR_DRIVE2", "+12V", col, ZY); col+=1
    place_pot("RV21", "FREQ ATT2","-12V", "NET_WPR_ATT_FREQ2",  "+12V", col, ZY); col+=1
    place_pot("RV22", "FB ATT2",  "-12V", "NET_WPR_ATT_FB2",    "+12V", col, ZY); col+=1
    place_pot("RV23", "DRIVE ATT2","-12V","NET_WPR_ATT_DRIVE2", "+12V", col, ZY); col+=1
    place_jack("J16", "FREQ CV2", "NET_CV_FREQ2",  "GND", "NET_MODBUS_NORM",  col, ZY); col+=1
    place_jack("J17", "FB CV2",   "NET_CV_FB2",    "GND", "NET_MODBUS_NORM",    col, ZY); col+=1
    place_jack("J18", "DRIVE CV2","NET_CV_DRIVE2", "GND", "NET_MODBUS_NORM", col, ZY); col+=1

    # -----------------------------------------------------------------------
    # Zone 2c: COMB 3
    # -----------------------------------------------------------------------
    place_pot("RV24", "FREQ 3",   "-12V", "NET_WPR_FREQ3",  "+12V", col, ZY); col+=1
    place_pot("RV25", "FB 3",     "GND",  "NET_WPR_FB3",    "+12V", col, ZY); col+=1
    place_pot("RV26", "DRIVE 3",  "GND",  "NET_WPR_DRIVE3", "+12V", col, ZY); col+=1
    place_pot("RV27", "FREQ ATT3","-12V", "NET_WPR_ATT_FREQ3",  "+12V", col, ZY); col+=1
    place_pot("RV28", "FB ATT3",  "-12V", "NET_WPR_ATT_FB3",    "+12V", col, ZY); col+=1
    place_pot("RV29", "DRIVE ATT3","-12V","NET_WPR_ATT_DRIVE3", "+12V", col, ZY); col+=1
    place_jack("J19", "FREQ CV3", "NET_CV_FREQ3",  "GND", "NET_MODBUS_NORM",  col, ZY); col+=1
    place_jack("J20", "FB CV3",   "NET_CV_FB3",    "GND", "NET_MODBUS_NORM",    col, ZY); col+=1
    place_jack("J21", "DRIVE CV3","NET_CV_DRIVE3", "GND", "NET_MODBUS_NORM", col, ZY); col+=1

    # -----------------------------------------------------------------------
    # Zone 3: VCA + LP1
    # -----------------------------------------------------------------------
    # VCA: AMT attenuverter + CV IN jack
    place_pot("RV30", "VCA AMT",   "-12V", "NET_WPR_ATT_VCA_AMT",  "+12V", col, ZY); col+=1
    place_jack("J22", "VCA CV IN", "NET_CV_VCA_AMT", "GND", "NET_MODBUS_NORM", col, ZY); col+=1

    # LP1: CUTOFF knob, STEREO SPREAD OFFSET, RESONANCE, attenuverters, CV jacks
    place_pot("RV31", "LP1 CUTOFF",    "-12V", "NET_WPR_LP1_CUT",    "+12V", col, ZY); col+=1
    place_pot("RV32", "LP1 SPREAD",    "-12V", "NET_WPR_LP1_SPREAD", "+12V", col, ZY); col+=1
    place_pot("RV33", "LP1 RES",       "GND",  "NET_WPR_LP1_RES",    "+12V", col, ZY); col+=1
    place_pot("RV34", "LP1 CUT ATT",   "-12V", "NET_WPR_ATT_LP1_CUT","+12V", col, ZY); col+=1
    place_pot("RV35", "LP1 RES ATT",   "-12V", "NET_WPR_ATT_LP1_RES","+12V", col, ZY); col+=1
    place_jack("J23", "LP1 CUT CV",  "NET_CV_LP1_CUT", "GND", "NET_MODBUS_NORM", col, ZY); col+=1
    place_jack("J24", "LP1 RES CV",  "NET_CV_LP1_RES", "GND", "NET_MODBUS_NORM", col, ZY); col+=1

    # -----------------------------------------------------------------------
    # Zone 4: BAND OUT + LP2
    # -----------------------------------------------------------------------
    place_jack("J5",  "BAND OUT L", "NET_BAND_OUT_L", "GND", "GND", col, ZY); col+=1
    place_jack("J6",  "BAND OUT R", "NET_BAND_OUT_R", "GND", "GND", col, ZY); col+=1

    # LP2: CUTOFF slider, RESONANCE, attenuverters, CV jacks
    place_pot("RV36", "LP2 CUTOFF SL", "GND",  "NET_WPR_LP2_CUT",    "+12V", col, ZY); col+=1
    place_pot("RV37", "LP2 RES",       "GND",  "NET_WPR_LP2_RES",    "+12V", col, ZY); col+=1
    place_pot("RV38", "LP2 CUT ATT",   "-12V", "NET_WPR_ATT_LP2_CUT","+12V", col, ZY); col+=1
    place_pot("RV39", "LP2 RES ATT",   "-12V", "NET_WPR_ATT_LP2_RES","+12V", col, ZY); col+=1
    place_jack("J25", "LP2 CUT CV",  "NET_CV_LP2_CUT", "GND", "NET_MODBUS_NORM", col, ZY); col+=1
    place_jack("J26", "LP2 RES CV",  "NET_CV_LP2_RES", "GND", "NET_MODBUS_NORM", col, ZY); col+=1

    # -----------------------------------------------------------------------
    # Zone 5: OUT + HP
    # -----------------------------------------------------------------------
    place_jack("J7",  "LEFT OUT",  "NET_LEFT_OUT",  "GND", "GND", col, ZY); col+=1
    place_jack("J8",  "RIGHT OUT", "NET_RIGHT_OUT", "GND", "GND", col, ZY); col+=1

    # HP: CUTOFF slider, RESONANCE, attenuverters, CV jacks
    place_pot("RV40", "HP CUTOFF SL",  "GND",  "NET_WPR_HP_CUT",    "+12V", col, ZY); col+=1
    place_pot("RV41", "HP RES",        "GND",  "NET_WPR_HP_RES",    "+12V", col, ZY); col+=1
    place_pot("RV42", "HP CUT ATT",    "-12V", "NET_WPR_ATT_HP_CUT","+12V", col, ZY); col+=1
    place_pot("RV43", "HP RES ATT",    "-12V", "NET_WPR_ATT_HP_RES","+12V", col, ZY); col+=1
    place_jack("J27", "HP CUT CV",  "NET_CV_HP_CUT", "GND", "NET_MODBUS_NORM", col, ZY); col+=1
    place_jack("J28", "HP RES CV",  "NET_CV_HP_RES", "GND", "NET_MODBUS_NORM", col, ZY); col+=1

    # -----------------------------------------------------------------------
    # CN_CTRL_1 (34-pin): Power + Audio I/O + CV override jack tips
    # Per layout-notes.md §5 CN_CTRL_1 pinout
    # -----------------------------------------------------------------------
    cn1_col = col; col += 1
    cn1_nets = {
        1:  "+12V",           2:  "+12V",
        3:  "-12V",           4:  "-12V",
        5:  "GND",            6:  "GND",
        7:  "NET_L_IN",       8:  "NET_R_IN",
        9:  "NET_ENV_OUT_L",  10: "NET_ENV_OUT_R",
        11: "NET_BAND_OUT_L", 12: "NET_BAND_OUT_R",
        13: "NET_LEFT_OUT",   14: "NET_RIGHT_OUT",
        # Override CV jack tips (15–27: BYPASS, OFFSET, BLEND, VCA_AMT, LP1_CUT, LP1_RES,
        #                         LP2_CUT, LP2_RES, HP_CUT, HP_RES, FREQ1, FREQ2, FREQ3)
        15: "NET_CV_BYPASS",  16: "NET_CV_OFFSET",
        17: "NET_CV_BLEND",   18: "NET_CV_VCA_AMT",
        19: "NET_CV_LP1_CUT", 20: "NET_CV_LP1_RES",
        21: "NET_CV_LP2_CUT", 22: "NET_CV_LP2_RES",
        23: "NET_CV_HP_CUT",  24: "NET_CV_HP_RES",
        25: "NET_CV_FREQ1",   26: "NET_CV_FREQ2",
        27: "NET_CV_FREQ3",
        # 28–34: FB1, FB2, FB3, DRIVE1, DRIVE2, DRIVE3, MOD IN
        28: "NET_CV_FB1",     29: "NET_CV_FB2",
        30: "NET_CV_FB3",     31: "NET_CV_DRIVE1",
        32: "NET_CV_DRIVE2",  33: "NET_CV_DRIVE3",
        34: "NET_MOD_IN",     # MOD IN jack tip → utility board mod bus processor input
    }
    place_idc34("CN1", "CN_CTRL_1", cn1_nets, cn1_col, ZY)

    # -----------------------------------------------------------------------
    # CN_CTRL_2 (40-pin, 2×20): Pot wipers + switch position outputs
    # Per layout-notes.md §5 CN_CTRL_2 pinout
    # -----------------------------------------------------------------------
    cn2_col = col; col += 1
    # 19 attenuverter wipers (one per mod destination, same order as mod-architecture.md).
    # VCA AMT is destination #4, included in the 19. Pins 9–27; pin 28 = SPARE.
    att_wipers = [
        "NET_WPR_ATT_BYPASS",   "NET_WPR_ATT_OFFSET",   "NET_WPR_ATT_BLEND",
        "NET_WPR_ATT_VCA_AMT",                                                  # dest #4
        "NET_WPR_ATT_LP1_CUT",  "NET_WPR_ATT_LP1_RES",
        "NET_WPR_ATT_LP2_CUT",  "NET_WPR_ATT_LP2_RES",
        "NET_WPR_ATT_HP_CUT",   "NET_WPR_ATT_HP_RES",
        "NET_WPR_ATT_FREQ1",    "NET_WPR_ATT_FREQ2",    "NET_WPR_ATT_FREQ3",
        "NET_WPR_ATT_FB1",      "NET_WPR_ATT_FB2",      "NET_WPR_ATT_FB3",
        "NET_WPR_ATT_DRIVE1",   "NET_WPR_ATT_DRIVE2",   "NET_WPR_ATT_DRIVE3",  # dest #19
    ]
    assert len(att_wipers) == 19, f"Expected 19 att wipers, got {len(att_wipers)}"

    cn2_nets = {
        1:  "GND",              2:  "GND",
        3:  "+12V",             4:  "-12V",
        5:  "NET_SW_GAIN_COM",
        6:  "NET_SW_MODE_SFT",  # MODE pos 1 (Soft Clip) → utility board
        7:  "NET_SW_MODE_HRD",  # MODE pos 2 (Hard Clip) → utility board
        8:  "NET_SW_MODE_WFD",  # MODE pos 3 (Wavefold) → utility board
    }
    for i, wpr in enumerate(att_wipers):
        cn2_nets[9 + i] = wpr   # pins 9–27 (19 wipers)
    cn2_nets[28] = "SPARE_CN2_28"
    cn2_nets[29] = "NET_WPR_AMOUNT"
    cn2_nets[30] = "NET_WPR_OFFSET_MB"
    cn2_nets[31] = "NET_WPR_LP1_SPREAD"
    # MOD SRC position outputs (SW2): L / MAX / AVG — utility board selects ENV routing
    cn2_nets[32] = "NET_SW_MODSRC_L"
    cn2_nets[33] = "NET_SW_MODSRC_MAX"
    cn2_nets[34] = "NET_SW_MODSRC_AVG"
    # POLARITY position outputs (SW3): POS / OFF / NEG — utility board APF feedback sign
    cn2_nets[35] = "NET_SW_POL_POS"
    cn2_nets[36] = "NET_SW_POL_OFF"
    cn2_nets[37] = "NET_SW_POL_NEG"
    cn2_nets[38] = "NET_ENV_NORM"   # ENV normalling return: utility board drives J9 SW lug
    cn2_nets[39] = "NET_MODBUS_NORM" # Mod Bus output return: drives all 19 CV jack SW lugs (wired together on ctrl board PCB)
    cn2_nets[40] = "SPARE_CN2_40"
    place_idc40("CN2", "CN_CTRL_2", cn2_nets, cn2_col, ZY)

    # -----------------------------------------------------------------------
    # CN_CTRL_3 (24-pin, 2×12): Main parameter wipers not in CN_CTRL_1/2.
    # 23 signals needed (2 GND + 21 wipers) → 24-pin gives 1 spare.
    # FLAGGED: exact pinout TBD — must be finalized in layout-notes.md before PCB layout.
    # -----------------------------------------------------------------------
    cn3_col = col; col += 1
    cn3_nets = {
        1:  "GND",                   2:  "GND",
        3:  "NET_WPR_ATTACK",        4:  "NET_WPR_RELEASE",
        5:  "NET_WPR_COMB_BYPASS",   6:  "NET_WPR_WIDTH",
        7:  "NET_WPR_MASTER_OFFSET", 8:  "NET_WPR_FB_DIST_BLEND",
        9:  "NET_WPR_FREQ1",         10: "NET_WPR_FREQ2",
        11: "NET_WPR_FREQ3",         12: "NET_WPR_FB1",
        13: "NET_WPR_FB2",           14: "NET_WPR_FB3",
        15: "NET_WPR_DRIVE1",        16: "NET_WPR_DRIVE2",
        17: "NET_WPR_DRIVE3",        18: "NET_WPR_LP1_CUT",
        19: "NET_WPR_LP1_RES",       20: "NET_WPR_LP2_CUT",
        21: "NET_WPR_LP2_RES",       22: "NET_WPR_HP_CUT",   # these 3 overflowed 20-pin
        23: "NET_WPR_HP_RES",        24: "SPARE_CN3_24",
    }
    place_idc24("CN3", "CN_CTRL_3_PLACEHOLDER_TBD", cn3_nets, cn3_col, ZY)

    # -----------------------------------------------------------------------
    # Close schematic
    # -----------------------------------------------------------------------
    emit(')')

# ---------------------------------------------------------------------------
# Write output
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    build_schematic()
    output = "\n".join(OUT)
    out_path = "pogo-control-board.kicad_sch"
    with open(out_path, "w") as f:
        f.write(output)
    print(f"Written: {out_path}")
    # Component count summary
    refs = [line.split('"')[1] for line in OUT if '"Reference"' in line and '#PWR' not in line.split('"')[1] if line.strip().startswith('(property "Reference"')]
    print(f"Components placed: {len(refs)}")
    print(f"Total lines: {len(OUT)}")
