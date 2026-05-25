#!/usr/bin/env python3
"""
POGO Control Board — KiCad 7 schematic generator.

Produces: pogo-control-board.kicad_sch

See specs/kicad-process.md for methodology, net naming, and known gaps.

Run from the kicad/ directory:
    python3 generate_control_board.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from kicad_common import *

# ---------------------------------------------------------------------------
# Control-board-specific lib_symbols (not in kicad_common)
# ---------------------------------------------------------------------------

def sym_jack():
    """AudioJack3 with tip-switching lug (Thonkiconn PJ301M-12).
    Pins: T=Tip(1), S=Sleeve(2), SW=Switch-lug(3)"""
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


def sym_spdt():
    """SPDT toggle switch. Pins: A(1), B(2), C=Common(3)"""
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
    """SP3T toggle switch. Pins: pos1(1), pos2(2), pos3(3), C=Common(4)"""
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


# ---------------------------------------------------------------------------
# Board-specific component placement helpers
# ---------------------------------------------------------------------------

def place_jack(ref, value, tip_net, sleeve_net, sw_net, col, row_y):
    ox, oy = col * 20.0, row_y
    place_symbol("Device:Audio_Jack_3.5mm_SwitchT", ref, value, ox, oy)
    pins = jack_pins(ox, oy)
    connect_pin(tip_net,    *pins["1"], shape="passive")
    connect_pin(sleeve_net, *pins["2"], shape="passive")
    connect_pin(sw_net,     *pins["3"], shape="passive")


def place_pot(ref, value, ccw_net, wpr_net, cw_net, col, row_y):
    ox, oy = col * 20.0, row_y
    place_symbol("Device:R_POT", ref, value, ox, oy)
    pins = rpot_pins(ox, oy)
    connect_pin(ccw_net, *pins["1"], shape="passive")
    connect_pin(wpr_net, *pins["2"], shape="passive")
    connect_pin(cw_net,  *pins["3"], shape="passive")


def place_spdt(ref, value, a_net, b_net, c_net, col, row_y):
    """Returns pins dict. Pass None for any net that gets a power symbol instead."""
    ox, oy = col * 20.0, row_y
    place_symbol("Switch:SW_SPDT", ref, value, ox, oy)
    pins = spdt_pins(ox, oy)
    if a_net: connect_pin(a_net, *pins["1"], shape="passive")
    if b_net: connect_pin(b_net, *pins["2"], shape="passive")
    if c_net: connect_pin(c_net, *pins["3"], shape="passive")
    return pins


def place_sp3t(ref, value, p1_net, p2_net, p3_net, c_net, col, row_y):
    """Returns pins dict. Pass None for any net that gets a power symbol instead."""
    ox, oy = col * 20.0, row_y
    place_symbol("Switch:SW_SP3T", ref, value, ox, oy)
    pins = sp3t_pins(ox, oy)
    if p1_net: connect_pin(p1_net, *pins["1"], shape="passive")
    if p2_net: connect_pin(p2_net, *pins["2"], shape="passive")
    if p3_net: connect_pin(p3_net, *pins["3"], shape="passive")
    if c_net:  connect_pin(c_net,  *pins["4"], shape="passive")
    return pins


# ---------------------------------------------------------------------------
# Lib symbols section
# ---------------------------------------------------------------------------

def emit_lib_symbols():
    emit('(lib_symbols')
    emit(sym_jack())
    emit(sym_rpot())
    emit(sym_spdt())
    emit(sym_sp3t())
    emit(sym_idc(17, 2))   # 34-pin (CN_CTRL_1)
    emit(sym_idc(20, 2))   # 40-pin (CN_CTRL_2)
    emit(sym_idc(12, 2))   # 24-pin (CN_CTRL_3)
    emit(sym_power("+12V"))
    emit(sym_power("-12V"))
    emit(sym_power("GND"))
    emit(')')


# ---------------------------------------------------------------------------
# Main schematic build
# ---------------------------------------------------------------------------

def build_schematic():
    reset()
    begin_schematic("A0")
    emit_lib_symbols()

    col = 1
    ZY = 50

    # --- Zone 0a: Input jacks + GAIN switch ---
    place_jack("J1",  "L IN",  "NET_L_IN",  "GND", "GND", col, ZY); col += 1
    place_jack("J2",  "R IN",  "NET_R_IN",  "GND", "GND", col, ZY); col += 1

    # GAIN switch: 1× throw → GND, 5× throw → +12V, common → CN2 pin 5
    pins = place_spdt("SW1", "GAIN 1x/5x",
                      None, None, "NET_SW_GAIN_COM",
                      col, ZY)
    power_sym("GND",  *pins["1"])
    power_sym("+12V", *pins["2"])
    col += 1

    # --- Zone 0b: Envelope section ---
    # MOD SRC: L / MAX / AVG; common → +12V on board
    pins = place_sp3t("SW2", "MOD SRC SEL",
                      "NET_SW_MODSRC_L", "NET_SW_MODSRC_MAX", "NET_SW_MODSRC_AVG",
                      None, col, ZY)
    power_sym("+12V", *pins["4"])
    col += 1

    place_pot("RV1", "ATTACK",  "GND",  "NET_WPR_ATTACK",  "+12V", col, ZY); col += 1
    place_pot("RV2", "RELEASE", "GND",  "NET_WPR_RELEASE", "+12V", col, ZY); col += 1
    place_jack("J3", "ENV L",   "NET_ENV_OUT_L", "GND", "GND", col, ZY); col += 1
    place_jack("J4", "ENV R",   "NET_ENV_OUT_R", "GND", "GND", col, ZY); col += 1

    # --- Zone 0c: Mod bus section ---
    place_pot("RV3", "AMOUNT", "GND",  "NET_WPR_AMOUNT",    "+12V", col, ZY); col += 1
    place_pot("RV4", "OFFSET", "-12V", "NET_WPR_OFFSET_MB", "+12V", col, ZY); col += 1

    # MOD IN jack: tip → mod bus processor input; SW lug normalizes to ENV return from utility
    place_jack("J9", "MOD IN", "NET_MOD_IN", "GND", "NET_ENV_NORM", col, ZY); col += 1

    # --- Zone 1: COMB section ---
    place_pot("RV5", "COMB BYPASS",   "GND",  "NET_WPR_COMB_BYPASS",   "+12V", col, ZY); col += 1
    place_pot("RV6", "WIDTH",         "-12V", "NET_WPR_WIDTH",          "+12V", col, ZY); col += 1

    # POLARITY: POS / OFF / NEG; common → +12V on board
    pins = place_sp3t("SW3", "POLARITY",
                      "NET_SW_POL_POS", "NET_SW_POL_OFF", "NET_SW_POL_NEG",
                      None, col, ZY)
    power_sym("+12V", *pins["4"])
    col += 1

    place_pot("RV7", "MASTER OFFSET", "-12V", "NET_WPR_MASTER_OFFSET", "+12V", col, ZY); col += 1

    # MODE switch (1 shared, per panel.svg): SFT/HRD/WFD; common → +12V on board
    pins = place_sp3t("SW4", "MODE",
                      "NET_SW_MODE_SFT", "NET_SW_MODE_HRD", "NET_SW_MODE_WFD",
                      None, col, ZY)
    power_sym("+12V", *pins["4"])
    col += 1

    place_pot("RV8", "FB DIST BLEND", "GND", "NET_WPR_FB_DIST_BLEND", "+12V", col, ZY); col += 1

    # Zone 1 CV jacks + attenuverters
    place_jack("J10", "BYPASS CV", "NET_CV_BYPASS", "GND", "NET_MODBUS_NORM", col, ZY); col += 1
    place_jack("J11", "OFFSET CV", "NET_CV_OFFSET", "GND", "NET_MODBUS_NORM", col, ZY); col += 1
    place_jack("J12", "BLEND CV",  "NET_CV_BLEND",  "GND", "NET_MODBUS_NORM", col, ZY); col += 1
    place_pot("RV9",  "BYPASS ATT", "-12V", "NET_WPR_ATT_BYPASS", "+12V", col, ZY); col += 1
    place_pot("RV10", "OFFSET ATT", "-12V", "NET_WPR_ATT_OFFSET", "+12V", col, ZY); col += 1
    place_pot("RV11", "BLEND ATT",  "-12V", "NET_WPR_ATT_BLEND",  "+12V", col, ZY); col += 1

    # --- Zone 2a: COMB 1 ---
    place_pot("RV12", "FREQ 1",    "-12V", "NET_WPR_FREQ1",       "+12V", col, ZY); col += 1
    place_pot("RV13", "FB 1",      "GND",  "NET_WPR_FB1",         "+12V", col, ZY); col += 1
    place_pot("RV14", "DRIVE 1",   "GND",  "NET_WPR_DRIVE1",      "+12V", col, ZY); col += 1
    place_pot("RV15", "FREQ ATT1", "-12V", "NET_WPR_ATT_FREQ1",   "+12V", col, ZY); col += 1
    place_pot("RV16", "FB ATT1",   "-12V", "NET_WPR_ATT_FB1",     "+12V", col, ZY); col += 1
    place_pot("RV17", "DRIVE ATT1","-12V", "NET_WPR_ATT_DRIVE1",  "+12V", col, ZY); col += 1
    place_jack("J13", "FREQ CV1",  "NET_CV_FREQ1",  "GND", "NET_MODBUS_NORM", col, ZY); col += 1
    place_jack("J14", "FB CV1",    "NET_CV_FB1",    "GND", "NET_MODBUS_NORM", col, ZY); col += 1
    place_jack("J15", "DRIVE CV1", "NET_CV_DRIVE1", "GND", "NET_MODBUS_NORM", col, ZY); col += 1

    # --- Zone 2b: COMB 2 ---
    place_pot("RV18", "FREQ 2",    "-12V", "NET_WPR_FREQ2",       "+12V", col, ZY); col += 1
    place_pot("RV19", "FB 2",      "GND",  "NET_WPR_FB2",         "+12V", col, ZY); col += 1
    place_pot("RV20", "DRIVE 2",   "GND",  "NET_WPR_DRIVE2",      "+12V", col, ZY); col += 1
    place_pot("RV21", "FREQ ATT2", "-12V", "NET_WPR_ATT_FREQ2",   "+12V", col, ZY); col += 1
    place_pot("RV22", "FB ATT2",   "-12V", "NET_WPR_ATT_FB2",     "+12V", col, ZY); col += 1
    place_pot("RV23", "DRIVE ATT2","-12V", "NET_WPR_ATT_DRIVE2",  "+12V", col, ZY); col += 1
    place_jack("J16", "FREQ CV2",  "NET_CV_FREQ2",  "GND", "NET_MODBUS_NORM", col, ZY); col += 1
    place_jack("J17", "FB CV2",    "NET_CV_FB2",    "GND", "NET_MODBUS_NORM", col, ZY); col += 1
    place_jack("J18", "DRIVE CV2", "NET_CV_DRIVE2", "GND", "NET_MODBUS_NORM", col, ZY); col += 1

    # --- Zone 2c: COMB 3 ---
    place_pot("RV24", "FREQ 3",    "-12V", "NET_WPR_FREQ3",       "+12V", col, ZY); col += 1
    place_pot("RV25", "FB 3",      "GND",  "NET_WPR_FB3",         "+12V", col, ZY); col += 1
    place_pot("RV26", "DRIVE 3",   "GND",  "NET_WPR_DRIVE3",      "+12V", col, ZY); col += 1
    place_pot("RV27", "FREQ ATT3", "-12V", "NET_WPR_ATT_FREQ3",   "+12V", col, ZY); col += 1
    place_pot("RV28", "FB ATT3",   "-12V", "NET_WPR_ATT_FB3",     "+12V", col, ZY); col += 1
    place_pot("RV29", "DRIVE ATT3","-12V", "NET_WPR_ATT_DRIVE3",  "+12V", col, ZY); col += 1
    place_jack("J19", "FREQ CV3",  "NET_CV_FREQ3",  "GND", "NET_MODBUS_NORM", col, ZY); col += 1
    place_jack("J20", "FB CV3",    "NET_CV_FB3",    "GND", "NET_MODBUS_NORM", col, ZY); col += 1
    place_jack("J21", "DRIVE CV3", "NET_CV_DRIVE3", "GND", "NET_MODBUS_NORM", col, ZY); col += 1

    # --- Zone 3: VCA + LP1 ---
    place_pot("RV30", "VCA AMT",     "-12V", "NET_WPR_ATT_VCA_AMT", "+12V", col, ZY); col += 1
    place_jack("J22", "VCA CV IN",   "NET_CV_VCA_AMT",  "GND", "NET_MODBUS_NORM", col, ZY); col += 1
    place_pot("RV31", "LP1 CUTOFF",  "-12V", "NET_WPR_LP1_CUT",    "+12V", col, ZY); col += 1
    place_pot("RV32", "LP1 SPREAD",  "-12V", "NET_WPR_LP1_SPREAD", "+12V", col, ZY); col += 1
    place_pot("RV33", "LP1 RES",     "GND",  "NET_WPR_LP1_RES",    "+12V", col, ZY); col += 1
    place_pot("RV34", "LP1 CUT ATT", "-12V", "NET_WPR_ATT_LP1_CUT","+12V", col, ZY); col += 1
    place_pot("RV35", "LP1 RES ATT", "-12V", "NET_WPR_ATT_LP1_RES","+12V", col, ZY); col += 1
    place_jack("J23", "LP1 CUT CV",  "NET_CV_LP1_CUT",  "GND", "NET_MODBUS_NORM", col, ZY); col += 1
    place_jack("J24", "LP1 RES CV",  "NET_CV_LP1_RES",  "GND", "NET_MODBUS_NORM", col, ZY); col += 1

    # --- Zone 4: BAND OUT + LP2 ---
    place_jack("J5",  "BAND OUT L", "NET_BAND_OUT_L", "GND", "GND", col, ZY); col += 1
    place_jack("J6",  "BAND OUT R", "NET_BAND_OUT_R", "GND", "GND", col, ZY); col += 1
    place_pot("RV36", "LP2 CUTOFF SL", "GND",  "NET_WPR_LP2_CUT",    "+12V", col, ZY); col += 1
    place_pot("RV37", "LP2 RES",       "GND",  "NET_WPR_LP2_RES",    "+12V", col, ZY); col += 1
    place_pot("RV38", "LP2 CUT ATT",   "-12V", "NET_WPR_ATT_LP2_CUT","+12V", col, ZY); col += 1
    place_pot("RV39", "LP2 RES ATT",   "-12V", "NET_WPR_ATT_LP2_RES","+12V", col, ZY); col += 1
    place_jack("J25", "LP2 CUT CV",    "NET_CV_LP2_CUT", "GND", "NET_MODBUS_NORM", col, ZY); col += 1
    place_jack("J26", "LP2 RES CV",    "NET_CV_LP2_RES", "GND", "NET_MODBUS_NORM", col, ZY); col += 1

    # --- Zone 5: Main OUT + HP ---
    place_jack("J7",  "LEFT OUT",  "NET_LEFT_OUT",  "GND", "GND", col, ZY); col += 1
    place_jack("J8",  "RIGHT OUT", "NET_RIGHT_OUT", "GND", "GND", col, ZY); col += 1
    place_pot("RV40", "HP CUTOFF SL", "GND",  "NET_WPR_HP_CUT",    "+12V", col, ZY); col += 1
    place_pot("RV41", "HP RES",       "GND",  "NET_WPR_HP_RES",    "+12V", col, ZY); col += 1
    place_pot("RV42", "HP CUT ATT",   "-12V", "NET_WPR_ATT_HP_CUT","+12V", col, ZY); col += 1
    place_pot("RV43", "HP RES ATT",   "-12V", "NET_WPR_ATT_HP_RES","+12V", col, ZY); col += 1
    place_jack("J27", "HP CUT CV",    "NET_CV_HP_CUT", "GND", "NET_MODBUS_NORM", col, ZY); col += 1
    place_jack("J28", "HP RES CV",    "NET_CV_HP_RES", "GND", "NET_MODBUS_NORM", col, ZY); col += 1

    # --- CN_CTRL_1 (34-pin): Power + Audio I/O + CV override jack tips ---
    cn1_col = col; col += 1
    cn1_nets = {
        1: "+12V",           2: "+12V",
        3: "-12V",           4: "-12V",
        5: "GND",            6: "GND",
        7: "NET_L_IN",       8: "NET_R_IN",
        9: "NET_ENV_OUT_L",  10: "NET_ENV_OUT_R",
        11: "NET_BAND_OUT_L",12: "NET_BAND_OUT_R",
        13: "NET_LEFT_OUT",  14: "NET_RIGHT_OUT",
        15: "NET_CV_BYPASS", 16: "NET_CV_OFFSET",
        17: "NET_CV_BLEND",  18: "NET_CV_VCA_AMT",
        19: "NET_CV_LP1_CUT",20: "NET_CV_LP1_RES",
        21: "NET_CV_LP2_CUT",22: "NET_CV_LP2_RES",
        23: "NET_CV_HP_CUT", 24: "NET_CV_HP_RES",
        25: "NET_CV_FREQ1",  26: "NET_CV_FREQ2",
        27: "NET_CV_FREQ3",  28: "NET_CV_FB1",
        29: "NET_CV_FB2",    30: "NET_CV_FB3",
        31: "NET_CV_DRIVE1", 32: "NET_CV_DRIVE2",
        33: "NET_CV_DRIVE3", 34: "NET_MOD_IN",
    }
    place_idc34("CN1", "CN_CTRL_1", cn1_nets, cn1_col, ZY)

    # --- CN_CTRL_2 (40-pin): Pot wipers + switch position outputs ---
    cn2_col = col; col += 1
    att_wipers = [
        "NET_WPR_ATT_BYPASS",   "NET_WPR_ATT_OFFSET",   "NET_WPR_ATT_BLEND",
        "NET_WPR_ATT_VCA_AMT",
        "NET_WPR_ATT_LP1_CUT",  "NET_WPR_ATT_LP1_RES",
        "NET_WPR_ATT_LP2_CUT",  "NET_WPR_ATT_LP2_RES",
        "NET_WPR_ATT_HP_CUT",   "NET_WPR_ATT_HP_RES",
        "NET_WPR_ATT_FREQ1",    "NET_WPR_ATT_FREQ2",    "NET_WPR_ATT_FREQ3",
        "NET_WPR_ATT_FB1",      "NET_WPR_ATT_FB2",      "NET_WPR_ATT_FB3",
        "NET_WPR_ATT_DRIVE1",   "NET_WPR_ATT_DRIVE2",   "NET_WPR_ATT_DRIVE3",
    ]
    assert len(att_wipers) == 19
    cn2_nets = {
        1: "GND",              2: "GND",
        3: "+12V",             4: "-12V",
        5: "NET_SW_GAIN_COM",
        6: "NET_SW_MODE_SFT",
        7: "NET_SW_MODE_HRD",
        8: "NET_SW_MODE_WFD",
    }
    for i, wpr in enumerate(att_wipers):
        cn2_nets[9 + i] = wpr       # pins 9–27
    cn2_nets[28] = "SPARE_CN2_28"
    cn2_nets[29] = "NET_WPR_AMOUNT"
    cn2_nets[30] = "NET_WPR_OFFSET_MB"
    cn2_nets[31] = "NET_WPR_LP1_SPREAD"
    cn2_nets[32] = "NET_SW_MODSRC_L"
    cn2_nets[33] = "NET_SW_MODSRC_MAX"
    cn2_nets[34] = "NET_SW_MODSRC_AVG"
    cn2_nets[35] = "NET_SW_POL_POS"
    cn2_nets[36] = "NET_SW_POL_OFF"
    cn2_nets[37] = "NET_SW_POL_NEG"
    cn2_nets[38] = "NET_ENV_NORM"       # utility board drives J9 SW lug (ENV normalling)
    cn2_nets[39] = "NET_MODBUS_NORM"    # utility board drives all 19 CV jack SW lugs
    cn2_nets[40] = "SPARE_CN2_40"
    place_idc40("CN2", "CN_CTRL_2", cn2_nets, cn2_col, ZY)

    # --- CN_CTRL_3 (24-pin): Main parameter wipers (21 signals + 2 GND + 1 spare) ---
    cn3_col = col; col += 1
    cn3_nets = {
        1:  "GND",                    2:  "GND",
        3:  "NET_WPR_ATTACK",         4:  "NET_WPR_RELEASE",
        5:  "NET_WPR_COMB_BYPASS",    6:  "NET_WPR_WIDTH",
        7:  "NET_WPR_MASTER_OFFSET",  8:  "NET_WPR_FB_DIST_BLEND",
        9:  "NET_WPR_FREQ1",          10: "NET_WPR_FREQ2",
        11: "NET_WPR_FREQ3",          12: "NET_WPR_FB1",
        13: "NET_WPR_FB2",            14: "NET_WPR_FB3",
        15: "NET_WPR_DRIVE1",         16: "NET_WPR_DRIVE2",
        17: "NET_WPR_DRIVE3",         18: "NET_WPR_LP1_CUT",
        19: "NET_WPR_LP1_RES",        20: "NET_WPR_LP2_CUT",
        21: "NET_WPR_LP2_RES",        22: "NET_WPR_HP_CUT",
        23: "NET_WPR_HP_RES",         24: "SPARE_CN3_24",
    }
    place_idc24("CN3", "CN_CTRL_3_PLACEHOLDER_TBD", cn3_nets, cn3_col, ZY)

    end_schematic()


if __name__ == "__main__":
    build_schematic()
    write_schematic("pogo-control-board.kicad_sch")
    try:
        import validate_schematic
        validate_schematic.validate("pogo-control-board.kicad_sch")
    except ImportError:
        print("(kiutils not installed — skipping structural validation)")
