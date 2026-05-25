#!/usr/bin/env python3
"""POGO KiCad 7 schematic generator — Utility Board.

Utility board contents (from specs/board-layout/layout-notes.md §3.2):
  - Eurorack power header (CN6, 16-pin IDC)
  - CN_CTRL_1 (34-pin), CN_CTRL_2 (40-pin), CN_CTRL_3 (24-pin) from control board
  - STK_AUDIO_L + STK_AUDIO_R (40-pin stacking headers) to combined audio board
  - Audio input buffers: U1 TL074 (L IN + R IN + ENV normalling)
  - Mod bus processor: U2 TL072 (AMOUNT scaler + OFFSET adder)
  - COMB BYPASS buffer + MODBUS_NORM drive: U3 TL072
  - FB DIST BLEND crossfade: U4 TL072
  - WIDTH + POLARITY processing: U5 TL074
  - Mod destination attenuverters: U6–U10 TL074 (19 destinations, 4 per IC)
  - FB + DRIVE summing: U21 TL074, U22 TL072 (main wiper + att → final CV)
  - Filter CV summing (LP1/LP2/HP cutoff + res): U11 TL072, U12 TL074
  - APF expo converters: U13–U15 THAT340 + U16 TL072 (Vbe refs)
  - Filter expo converters: U17–U19 THAT340 + U20 TL072 (Vbe refs)

Net names match the STK_AUDIO_L/R pinouts in layout-notes.md §5 and the CN_CTRL_*
pinouts used by generate_control_board.py (same global net names on both connector sides).

Attenuverter signal flow:
  Override jack tip (NET_CV_*) → BAT54 clamp (on PCB) → TL074 In+
  Attenuverter pot wiper (NET_WPR_ATT_*) → TL074 gain-control In- node
  TL074 Out → NET_*_ATT (attenuated mod bus contribution)
  Main parameter wiper (NET_WPR_*) + att output → TL072/TL074 summing → STK CV pin

THAT340 emitter notes:
  Each THAT340 NPN emitter connects through R_e (~51 Ω) to GND for bias.
  Emitters are labelled GND in the schematic (R_e is a PCB placement detail).
  See noise-audit.md M3 for Kelvin ground return rule on R_e.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from kicad_common import (
    begin_schematic, end_schematic, write_schematic,
    sym_power, sym_idc, sym_pin_header,
    sym_tl072, sym_tl074, sym_that340, sym_r, sym_c,
    place_idc34, place_idc40, place_idc24, place_idc16,
    place_pin_header40,
    that340_pins, idc_pins,
    place_symbol, connect_pin, power_sym, global_label,
    opamp_dual_pins, opamp_quad_pins,
    emit, uid,
)

ZY = 120.0   # baseline Y for main component row (mm)
ZY2 = 55.0   # upper row for expo converters
STEP = 20.0  # column step (mm)


# ---------------------------------------------------------------------------
# Lib symbol registry
# ---------------------------------------------------------------------------

def emit_lib_symbols():
    emit("(lib_symbols")
    emit(sym_power("GND"))
    emit(sym_power("+12V"))
    emit(sym_power("-12V"))
    emit(sym_idc(8))          # 16-pin: Eurorack power header
    emit(sym_idc(17))         # 34-pin: CN_CTRL_1
    emit(sym_idc(20))         # 40-pin: CN_CTRL_2
    emit(sym_idc(12))         # 24-pin: CN_CTRL_3
    emit(sym_pin_header(20))  # 40-pin: STK_AUDIO_L/R stacking headers
    emit(sym_tl072())
    emit(sym_tl074())
    emit(sym_that340())
    emit(sym_r())
    emit(sym_c())
    emit(")")


# ---------------------------------------------------------------------------
# IC placement helpers
# ---------------------------------------------------------------------------

def _place_tl072_unit(ref, value, unit, ox, oy, nets):
    """Place TL072 unit (A=1, B=2, PWR=3) and label signal pins."""
    place_symbol("Amplifier_Operational:TL072", ref, value, ox, oy, unit=unit)
    if unit in (1, 2):
        pins = opamp_dual_pins(ox, oy, unit)
        im, ip, out = ("2", "3", "1") if unit == 1 else ("6", "5", "7")
        if nets.get("in-"):
            connect_pin(nets["in-"], *pins[im])
        if nets.get("in+"):
            connect_pin(nets["in+"], *pins[ip])
        if nets.get("out"):
            connect_pin(nets["out"], *pins[out])
    elif unit == 3:
        place_symbol("Amplifier_Operational:TL072", ref, value, ox, oy, unit=3)
        power_sym("+12V", ox, oy - 7.62)
        power_sym("-12V", ox, oy + 7.62)


def _place_tl074_unit(ref, value, unit, ox, oy, nets):
    """Place TL074 unit (A=1..D=4, PWR=5) and label signal pins."""
    place_symbol("Amplifier_Operational:TL074", ref, value, ox, oy, unit=unit)
    pin_map = {
        1: ("2", "3", "1"), 2: ("6", "5", "7"),
        3: ("9", "10", "8"), 4: ("13", "12", "14"),
    }
    if unit in pin_map:
        pins = opamp_quad_pins(ox, oy, unit)
        im, ip, out = pin_map[unit]
        if nets.get("in-"):
            connect_pin(nets["in-"], *pins[im])
        if nets.get("in+"):
            connect_pin(nets["in+"], *pins[ip])
        if nets.get("out"):
            connect_pin(nets["out"], *pins[out])
    elif unit == 5:
        power_sym("+12V", ox, oy - 7.62)
        power_sym("-12V", ox, oy + 7.62)


def _place_that340(ref, ox, oy, nets):
    """Place THAT340 and label key pins.
    nets keys: B1,C1,B2,C2,B3,C3,B4,C4,E4,SUB.
    Emitter pins E1/E2/E3 default to GND (R_e bias resistor is a PCB detail).
    """
    place_symbol("POGO:THAT340", ref, "THAT340", ox, oy)
    p = that340_pins(ox, oy)
    mapping = {
        "B1": "1",  "C1": "2",  "E1": "3",
        "B3": "5",  "C3": "6",  "E3": "7",
        "E4": "10", "C4": "11", "B4": "12",
        "E2": "14", "C2": "15", "B2": "16",
    }
    for key, pin in mapping.items():
        net = nets.get(key)
        if net is None and key.startswith("E"):
            net = "GND"  # emitter → R_e → GND (Kelvin ground, see noise-audit M3)
        if net:
            connect_pin(net, *p[pin])
    sub_net = nets.get("SUB", "GND")
    for sub_pin in ("4", "8", "9", "13"):
        connect_pin(sub_net, *p[sub_pin])


# ---------------------------------------------------------------------------
# Main schematic builder
# ---------------------------------------------------------------------------

def build_schematic():
    begin_schematic("A0")
    emit_lib_symbols()

    col = 0   # running column counter

    # =========================================================
    # Zone 0 — Eurorack power header CN6 (16-pin IDC)
    # Standard Eurorack: pins 1-2=-12V, 3-10=GND, 11-12=+5V_BUS, 13-16=+12V
    # =========================================================
    ebus_nets = {
        1: "-12V",       2: "-12V",
        3: "GND",        4: "GND",
        5: "GND",        6: "GND",
        7: "GND",        8: "GND",
        9: "GND",        10: "GND",
        11: "NET_5V_BUS", 12: "NET_5V_BUS",
        13: "+12V",      14: "+12V",
        15: "+12V",      16: "+12V",
    }
    place_idc16("CN6", "J_EBUS", ebus_nets, col, ZY)
    col += 1

    # =========================================================
    # Zone 1 — CN_CTRL_1 (34-pin, from control board)
    # Same net names as generate_control_board.py cn1_nets
    # =========================================================
    cn1_nets = {
        1: "+12V",           2: "+12V",
        3: "-12V",           4: "-12V",
        5: "GND",            6: "GND",
        7: "NET_L_IN",       8: "NET_R_IN",
        9: "NET_ENV_OUT_L",  10: "NET_ENV_OUT_R",
        11: "NET_BAND_OUT_L", 12: "NET_BAND_OUT_R",
        13: "NET_LEFT_OUT",  14: "NET_RIGHT_OUT",
        15: "NET_CV_BYPASS", 16: "NET_CV_OFFSET",
        17: "NET_CV_BLEND",  18: "NET_CV_VCA_AMT",
        19: "NET_CV_LP1_CUT", 20: "NET_CV_LP1_RES",
        21: "NET_CV_LP2_CUT", 22: "NET_CV_LP2_RES",
        23: "NET_CV_HP_CUT",  24: "NET_CV_HP_RES",
        25: "NET_CV_FREQ1",   26: "NET_CV_FREQ2",
        27: "NET_CV_FREQ3",   28: "NET_CV_FB1",
        29: "NET_CV_FB2",     30: "NET_CV_FB3",
        31: "NET_CV_DRIVE1",  32: "NET_CV_DRIVE2",
        33: "NET_CV_DRIVE3",  34: "NET_MOD_IN",
    }
    place_idc34("CN1", "CN_CTRL_1", cn1_nets, col, ZY)
    col += 1

    # =========================================================
    # Zone 2 — CN_CTRL_2 (40-pin, from control board)
    # =========================================================
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
    cn2_nets[38] = "NET_ENV_NORM"
    cn2_nets[39] = "NET_MODBUS_NORM"
    cn2_nets[40] = "SPARE_CN2_40"
    place_idc40("CN2", "CN_CTRL_2", cn2_nets, col, ZY)
    col += 1

    # =========================================================
    # Zone 3 — CN_CTRL_3 (24-pin, from control board)
    # =========================================================
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
    place_idc24("CN3", "CN_CTRL_3", cn3_nets, col, ZY)
    col += 1

    # =========================================================
    # Zone 4 — Audio input buffers: U1 TL074
    # A: L IN unity-gain buffer (BAT54 clamp on PCB between NET_L_IN and In+)
    # B: R IN buffer
    # C: ENV source selector → NET_ENV_NORM (driven to CN2 pin 38)
    #    In+ = NET_ENV_SEL (selected from ENV_OUT_L, ENV_OUT_R, or processed avg/max)
    #    MOD SRC switch (SW2) outputs NET_SW_MODSRC_L/MAX/AVG control the selector mux
    # D: spare
    # =========================================================
    u1x = col * STEP;  col += 1

    _place_tl074_unit("U1", "TL074", 1, u1x, ZY - 15,
                       {"in+": "NET_L_IN",      "in-": "NET_L_IN_BUF",  "out": "NET_L_IN_BUF"})
    _place_tl074_unit("U1", "TL074", 2, u1x, ZY + 5,
                       {"in+": "NET_R_IN",      "in-": "NET_R_IN_BUF",  "out": "NET_R_IN_BUF"})
    _place_tl074_unit("U1", "TL074", 3, u1x, ZY + 25,
                       {"in+": "NET_ENV_SEL",   "in-": "NET_ENV_NORM",  "out": "NET_ENV_NORM"})
    _place_tl074_unit("U1", "TL074", 4, u1x, ZY + 45,
                       {"in+": "GND",           "in-": "NET_U1D_SPARE", "out": "NET_U1D_SPARE"})
    _place_tl074_unit("U1", "TL074", 5, u1x, ZY - 35, {})

    # ENV source selector: SW_MODSRC_L/MAX/AVG pick among ENV_OUT_L, ENV_OUT_R, max, avg
    # The MOD SRC switch drives 3-position logic; selector output = NET_ENV_SEL
    connect_pin("NET_ENV_OUT_L",    u1x - 6, ZY + 28)   # selector input: L channel ENV
    connect_pin("NET_ENV_OUT_R",    u1x - 6, ZY + 22)   # selector input: R channel ENV
    connect_pin("NET_ENV_SEL",      u1x - 6, ZY + 25)   # 2nd label: selector output → U1C
    connect_pin("NET_SW_MODSRC_L",   u1x - 4, ZY + 18)  # SW2 position outputs control selector
    connect_pin("NET_SW_MODSRC_MAX", u1x - 4, ZY + 20)
    connect_pin("NET_SW_MODSRC_AVG", u1x - 4, ZY + 23)

    # =========================================================
    # Zone 5 — Mod bus processor: U2 TL072
    # A: AMOUNT scaler  (In+ = NET_MOD_IN,      gain = NET_WPR_AMOUNT → NET_MOD_SCALED)
    # B: OFFSET adder   (In+ = NET_MOD_SCALED,  offset = NET_WPR_OFFSET_MB → NET_MODBUS)
    # =========================================================
    u2x = col * STEP;  col += 1

    _place_tl072_unit("U2", "TL072", 1, u2x, ZY - 10,
                       {"in+": "NET_MOD_IN",       "in-": "NET_WPR_AMOUNT",
                        "out": "NET_MOD_SCALED"})
    _place_tl072_unit("U2", "TL072", 2, u2x, ZY + 10,
                       {"in+": "NET_MOD_SCALED",   "in-": "NET_WPR_OFFSET_MB",
                        "out": "NET_MODBUS"})
    _place_tl072_unit("U2", "TL072", 3, u2x, ZY + 30, {})

    # =========================================================
    # Zone 6 — COMB BYPASS summing amp + MODBUS_NORM drive: U3 TL072
    # A: sums WPR_COMB_BYPASS (main knob) + ATT_BYPASS_CV (mod att) → NET_COMB_BYPASS_CV
    #    Inverting summer: In+ = WPR_COMB_BYPASS, In- = NET_ATT_BYPASS_CV, Out = COMB_BYPASS_CV
    # B: drives NET_MODBUS → NET_MODBUS_NORM (to all 19 CV jack SW lugs via CN2 pin 39)
    # =========================================================
    u3x = col * STEP;  col += 1

    _place_tl072_unit("U3", "TL072", 1, u3x, ZY - 10,
                       {"in+": "NET_WPR_COMB_BYPASS",  "in-": "NET_ATT_BYPASS_CV",
                        "out": "NET_COMB_BYPASS_CV"})
    _place_tl072_unit("U3", "TL072", 2, u3x, ZY + 10,
                       {"in+": "NET_MODBUS",           "in-": "NET_MODBUS_NORM",
                        "out": "NET_MODBUS_NORM"})
    _place_tl072_unit("U3", "TL072", 3, u3x, ZY + 30, {})

    # =========================================================
    # Zone 7 — FB DIST BLEND crossfade: U4 TL072
    # A: L-channel blend (post-dist taps L1/L2/L3 → NET_FB_BLEND_OUT_L)
    # B: R-channel blend (post-dist taps R1/R2/R3 → NET_FB_BLEND_OUT_R)
    # Blend control: WPR_FB_DIST_BLEND (main knob) + NET_FB_BLEND_ATT (mod att)
    #   both sum into the control input (In- of the crossfade summing stage)
    # =========================================================
    u4x = col * STEP;  col += 1

    _place_tl072_unit("U4", "TL072", 1, u4x, ZY - 10,
                       {"in+": "NET_POST_DIST_L1",  "in-": "NET_FB_BLEND_ATT",
                        "out": "NET_FB_BLEND_OUT_L"})
    _place_tl072_unit("U4", "TL072", 2, u4x, ZY + 10,
                       {"in+": "NET_POST_DIST_R1",  "in-": "NET_FB_BLEND_ATT",
                        "out": "NET_FB_BLEND_OUT_R"})
    _place_tl072_unit("U4", "TL072", 3, u4x, ZY + 30, {})
    # Post-dist chains 2 and 3 also feed the blend summing node (via resistors on PCB)
    connect_pin("NET_POST_DIST_L2", u4x - 8, ZY - 8)
    connect_pin("NET_POST_DIST_L3", u4x - 8, ZY - 12)
    connect_pin("NET_POST_DIST_R2", u4x - 8, ZY + 12)
    connect_pin("NET_POST_DIST_R3", u4x - 8, ZY + 8)
    # Blend main knob also feeds the control summing node (with ATT)
    connect_pin("NET_WPR_FB_DIST_BLEND", u4x - 8, ZY - 14)

    # =========================================================
    # Zone 8 — WIDTH + POLARITY: U5 TL074
    # A: WIDTH wiper buffer → NET_WIDTH_CV (to audio board R-channel APF freq offset)
    # B: POLARITY POS path
    # C: POLARITY NEG path
    # D: POLARITY output buffer → NET_POL_OUT
    # =========================================================
    u5x = col * STEP;  col += 1

    _place_tl074_unit("U5", "TL074", 1, u5x, ZY - 25,
                       {"in+": "NET_WPR_WIDTH",     "in-": "NET_WIDTH_CV",   "out": "NET_WIDTH_CV"})
    _place_tl074_unit("U5", "TL074", 2, u5x, ZY - 5,
                       {"in+": "NET_SW_POL_POS",    "in-": "NET_POL_POS_BUF", "out": "NET_POL_POS_BUF"})
    _place_tl074_unit("U5", "TL074", 3, u5x, ZY + 15,
                       {"in+": "NET_SW_POL_NEG",    "in-": "NET_POL_NEG_BUF", "out": "NET_POL_NEG_BUF"})
    _place_tl074_unit("U5", "TL074", 4, u5x, ZY + 35,
                       {"in+": "NET_POL_POS_BUF",   "in-": "NET_POL_OUT",     "out": "NET_POL_OUT"})
    _place_tl074_unit("U5", "TL074", 5, u5x, ZY - 45, {})
    # SW_POL_OFF (center position) ties to GND on this side → polarity = 0V
    connect_pin("NET_SW_POL_OFF", u5x + 8, ZY + 15)

    # =========================================================
    # Zones 9–13 — Mod destination attenuverters: U6–U10 TL074
    # 19 destinations, 4 per TL074. Each unit:
    #   In+: NET_CV_* (override jack signal, from CN1, after BAT54 clamp on PCB)
    #   In-: NET_WPR_ATT_* (attenuverter pot wiper, from CN2 — gain control)
    #   Out: NET_*_ATT (attenuated mod contribution)
    #
    # Filter cutoff/resonance att outputs (_ATT) are summed with main wipers by
    # U11/U12 (existing) and U21/U22 (FB/DRIVE) to produce the final _CV signals.
    # COMB BYPASS att is summed by U3A.
    # VCA level att goes directly to STK (no separate main wiper for VCA AMT).
    # =========================================================

    # (cv_override_net, wiper_net, att_output_net)
    att_dests = [
        # U6 — destinations 1-4
        ("NET_CV_BYPASS",   "NET_WPR_ATT_BYPASS",   "NET_ATT_BYPASS_CV"),
        ("NET_CV_OFFSET",   "NET_WPR_ATT_OFFSET",   "NET_APF_OFFSET_ATT"),
        ("NET_CV_BLEND",    "NET_WPR_ATT_BLEND",     "NET_FB_BLEND_ATT"),
        ("NET_CV_VCA_AMT",  "NET_WPR_ATT_VCA_AMT",  "NET_VCA_LEVEL_CV"),
        # U7 — destinations 5-8
        ("NET_CV_LP1_CUT",  "NET_WPR_ATT_LP1_CUT",  "NET_LP1_CUT_ATT"),
        ("NET_CV_LP1_RES",  "NET_WPR_ATT_LP1_RES",  "NET_LP1_RES_ATT"),
        ("NET_CV_LP2_CUT",  "NET_WPR_ATT_LP2_CUT",  "NET_LP2_CUT_ATT"),
        ("NET_CV_LP2_RES",  "NET_WPR_ATT_LP2_RES",  "NET_LP2_RES_ATT"),
        # U8 — destinations 9-12
        ("NET_CV_HP_CUT",   "NET_WPR_ATT_HP_CUT",   "NET_HP_CUT_ATT"),
        ("NET_CV_HP_RES",   "NET_WPR_ATT_HP_RES",   "NET_HP_RES_ATT"),
        ("NET_CV_FREQ1",    "NET_WPR_ATT_FREQ1",    "NET_FREQ1_ATT"),
        ("NET_CV_FREQ2",    "NET_WPR_ATT_FREQ2",    "NET_FREQ2_ATT"),
        # U9 — destinations 13-16
        ("NET_CV_FREQ3",    "NET_WPR_ATT_FREQ3",    "NET_FREQ3_ATT"),
        ("NET_CV_FB1",      "NET_WPR_ATT_FB1",      "NET_APF_FB1_ATT"),
        ("NET_CV_FB2",      "NET_WPR_ATT_FB2",      "NET_APF_FB2_ATT"),
        ("NET_CV_FB3",      "NET_WPR_ATT_FB3",      "NET_APF_FB3_ATT"),
        # U10 — destinations 17-19 + spare unit D
        ("NET_CV_DRIVE1",   "NET_WPR_ATT_DRIVE1",   "NET_DRIVE1_ATT"),
        ("NET_CV_DRIVE2",   "NET_WPR_ATT_DRIVE2",   "NET_DRIVE2_ATT"),
        ("NET_CV_DRIVE3",   "NET_WPR_ATT_DRIVE3",   "NET_DRIVE3_ATT"),
    ]
    assert len(att_dests) == 19

    att_ics = ["U6", "U7", "U8", "U9", "U10"]
    for ic_idx, ic_ref in enumerate(att_ics):
        ux = col * STEP;  col += 1
        for unit_idx in range(4):
            dest_idx = ic_idx * 4 + unit_idx
            unit = unit_idx + 1
            uy = ZY + (unit_idx - 2) * 18
            if dest_idx >= 19:
                _place_tl074_unit(ic_ref, "TL074", unit, ux, uy,
                                   {"in+": "GND", "in-": "NET_SPARE_ATT", "out": "NET_SPARE_ATT"})
            else:
                cv_net, wpr_net, out_net = att_dests[dest_idx]
                _place_tl074_unit(ic_ref, "TL074", unit, ux, uy,
                                   {"in+": cv_net, "in-": wpr_net, "out": out_net})
        _place_tl074_unit(ic_ref, "TL074", 5, ux, ZY - 55, {})

    # APF_OFFSET_ATT: apply to all three APF FREQ summing nodes (done later near THAT340s)

    # =========================================================
    # Zone 13b — FB + DRIVE summing: U21 TL074
    # Same architecture as U11/U12 (LP/HP cutoff/res):
    # main wiper (from CN3) + att output (from U9/U10) → final CV → STK
    # A: FB1  CV = WPR_FB1  + APF_FB1_ATT → NET_APF_FB1_CV
    # B: FB2  CV = WPR_FB2  + APF_FB2_ATT → NET_APF_FB2_CV
    # C: FB3  CV = WPR_FB3  + APF_FB3_ATT → NET_APF_FB3_CV
    # D: DRIVE1 CV = WPR_DRIVE1 + DRIVE1_ATT → NET_DRIVE1_CV
    # =========================================================
    u21x = col * STEP;  col += 1

    _place_tl074_unit("U21", "TL074", 1, u21x, ZY - 30,
                       {"in+": "NET_WPR_FB1",     "in-": "NET_APF_FB1_ATT",
                        "out": "NET_APF_FB1_CV"})
    _place_tl074_unit("U21", "TL074", 2, u21x, ZY - 10,
                       {"in+": "NET_WPR_FB2",     "in-": "NET_APF_FB2_ATT",
                        "out": "NET_APF_FB2_CV"})
    _place_tl074_unit("U21", "TL074", 3, u21x, ZY + 10,
                       {"in+": "NET_WPR_FB3",     "in-": "NET_APF_FB3_ATT",
                        "out": "NET_APF_FB3_CV"})
    _place_tl074_unit("U21", "TL074", 4, u21x, ZY + 30,
                       {"in+": "NET_WPR_DRIVE1",  "in-": "NET_DRIVE1_ATT",
                        "out": "NET_DRIVE1_CV"})
    _place_tl074_unit("U21", "TL074", 5, u21x, ZY - 50, {})

    # Zone 13c — DRIVE 2+3 summing: U22 TL072
    u22x = col * STEP;  col += 1

    _place_tl072_unit("U22", "TL072", 1, u22x, ZY - 10,
                       {"in+": "NET_WPR_DRIVE2",  "in-": "NET_DRIVE2_ATT",
                        "out": "NET_DRIVE2_CV"})
    _place_tl072_unit("U22", "TL072", 2, u22x, ZY + 10,
                       {"in+": "NET_WPR_DRIVE3",  "in-": "NET_DRIVE3_ATT",
                        "out": "NET_DRIVE3_CV"})
    _place_tl072_unit("U22", "TL072", 3, u22x, ZY + 30, {})

    # =========================================================
    # Zone 14 — Filter CV summing: U11 TL072
    # Combines main wiper + attenuverter output for cutoff CVs
    # A: LP1 CUTOFF CV  = WPR_LP1_CUT  + LP1_CUT_ATT  → NET_LP1_CUT_CV
    # B: LP2 CUTOFF CV  = WPR_LP2_CUT  + LP2_CUT_ATT  → NET_LP2_CUT_CV
    # =========================================================
    u11x = col * STEP;  col += 1

    _place_tl072_unit("U11", "TL072", 1, u11x, ZY - 10,
                       {"in+": "NET_WPR_LP1_CUT",   "in-": "NET_LP1_CUT_ATT",
                        "out": "NET_LP1_CUT_CV"})
    _place_tl072_unit("U11", "TL072", 2, u11x, ZY + 10,
                       {"in+": "NET_WPR_LP2_CUT",   "in-": "NET_LP2_CUT_ATT",
                        "out": "NET_LP2_CUT_CV"})
    _place_tl072_unit("U11", "TL072", 3, u11x, ZY + 30, {})

    # Zone 14b — Filter CV summing: U12 TL074
    # A: LP1 RES CV = WPR_LP1_RES + LP1_RES_ATT → NET_LP1_RES_CV
    # B: LP2 RES CV = WPR_LP2_RES + LP2_RES_ATT → NET_LP2_RES_CV
    # C: HP CUT CV  = WPR_HP_CUT  + HP_CUT_ATT  → NET_HP_CUT_CV
    # D: HP RES CV  = WPR_HP_RES  + HP_RES_ATT  → NET_HP_RES_CV
    u12x = col * STEP;  col += 1

    _place_tl074_unit("U12", "TL074", 1, u12x, ZY - 30,
                       {"in+": "NET_WPR_LP1_RES",   "in-": "NET_LP1_RES_ATT",
                        "out": "NET_LP1_RES_CV"})
    _place_tl074_unit("U12", "TL074", 2, u12x, ZY - 10,
                       {"in+": "NET_WPR_LP2_RES",   "in-": "NET_LP2_RES_ATT",
                        "out": "NET_LP2_RES_CV"})
    _place_tl074_unit("U12", "TL074", 3, u12x, ZY + 10,
                       {"in+": "NET_WPR_HP_CUT",    "in-": "NET_HP_CUT_ATT",
                        "out": "NET_HP_CUT_CV"})
    _place_tl074_unit("U12", "TL074", 4, u12x, ZY + 30,
                       {"in+": "NET_WPR_HP_RES",    "in-": "NET_HP_RES_ATT",
                        "out": "NET_HP_RES_CV"})
    _place_tl074_unit("U12", "TL074", 5, u12x, ZY - 50, {})

    # =========================================================
    # Zones 15–17 — APF expo converters (THAT340 ×3)
    # Each THAT340 drives both L and R for one APF group:
    #   Q1 (B1/C1): L expo — I_abc_APF*_L  (collector current out)
    #   Q2 (B2/C2): R expo — I_abc_APF*_R
    #   Q3 (B3/C3): Vbe temperature reference (diode-connected; C3=B3)
    #   Q4: spare / not used
    #   Emitters E1/E2/E3: default to GND via R_e bias resistors (see M3)
    #
    # Control voltage at B1/B2 = WPR_FREQ* + WPR_MASTER_OFFSET + APF_OFFSET_ATT + FREQ*_ATT
    #   (resistor summing network on PCB; shown here as global labels on B1/B2)
    # VREF_APF12/3 from U16 also feeds back into the summing node for temperature correction.
    # =========================================================

    # APF group 1: U13 THAT340
    u13x = col * STEP;  col += 1
    _place_that340("U13", u13x, ZY2, {
        "B1": "NET_APF1_CTRL_L",
        "C1": "NET_IABC_APF1_L",    # → STK_AUDIO_L pin 12
        "B2": "NET_APF1_CTRL_R",
        "C2": "NET_IABC_APF1_R",    # → STK_AUDIO_R pin 12
        "B3": "NET_APF1_VREF",
        "C3": "NET_APF1_VREF",      # diode-connected Vbe reference
        "SUB": "GND",
    })
    # APF1 L base summing node: FREQ1 wiper + MASTER OFFSET + APF offset att + FREQ1 att + VREF
    connect_pin("NET_WPR_FREQ1",      u13x - 15, ZY2 + 8.89)
    connect_pin("NET_WPR_MASTER_OFFSET", u13x - 15, ZY2 + 11.43)
    connect_pin("NET_APF_OFFSET_ATT", u13x - 15, ZY2 + 6.35)
    connect_pin("NET_FREQ1_ATT",      u13x - 15, ZY2 + 4.0)
    connect_pin("NET_VREF_APF12",     u13x - 15, ZY2 + 2.0)
    connect_pin("NET_APF1_CTRL_L",    u13x - 15, ZY2 + 0.5)   # 2nd label for summing node
    # APF1 R base summing node (same structure, WIDTH adds stereo spread on audio board)
    connect_pin("NET_APF1_CTRL_R",    u13x - 15, ZY2 - 8.89)

    # APF group 2: U14 THAT340
    u14x = col * STEP;  col += 1
    _place_that340("U14", u14x, ZY2, {
        "B1": "NET_APF2_CTRL_L",
        "C1": "NET_IABC_APF2_L",    # → STK_AUDIO_L pin 13
        "B2": "NET_APF2_CTRL_R",
        "C2": "NET_IABC_APF2_R",    # → STK_AUDIO_R pin 13
        "B3": "NET_APF2_VREF",
        "C3": "NET_APF2_VREF",
        "SUB": "GND",
    })
    connect_pin("NET_WPR_FREQ2",      u14x - 15, ZY2 + 8.89)
    connect_pin("NET_WPR_MASTER_OFFSET", u14x - 15, ZY2 + 11.43)
    connect_pin("NET_APF_OFFSET_ATT", u14x - 15, ZY2 + 6.35)
    connect_pin("NET_FREQ2_ATT",      u14x - 15, ZY2 + 4.0)
    connect_pin("NET_VREF_APF12",     u14x - 15, ZY2 + 2.0)
    connect_pin("NET_APF2_CTRL_L",    u14x - 15, ZY2 + 0.5)
    connect_pin("NET_APF2_CTRL_R",    u14x - 15, ZY2 - 8.89)
    # APF2 Vbe also uses VREF_APF12 (parallel diode-connect Q2 of APF2 THAT340)
    connect_pin("NET_APF2_VREF",      u14x - 8, ZY2 - 9)

    # APF group 3: U15 THAT340
    u15x = col * STEP;  col += 1
    _place_that340("U15", u15x, ZY2, {
        "B1": "NET_APF3_CTRL_L",
        "C1": "NET_IABC_APF3_L",    # → STK_AUDIO_L pin 15
        "B2": "NET_APF3_CTRL_R",
        "C2": "NET_IABC_APF3_R",    # → STK_AUDIO_R pin 15
        "B3": "NET_APF3_VREF",
        "C3": "NET_APF3_VREF",
        "SUB": "GND",
    })
    connect_pin("NET_WPR_FREQ3",      u15x - 15, ZY2 + 8.89)
    connect_pin("NET_WPR_MASTER_OFFSET", u15x - 15, ZY2 + 11.43)
    connect_pin("NET_APF_OFFSET_ATT", u15x - 15, ZY2 + 6.35)
    connect_pin("NET_FREQ3_ATT",      u15x - 15, ZY2 + 4.0)
    connect_pin("NET_VREF_APF3",      u15x - 15, ZY2 + 2.0)
    connect_pin("NET_APF3_CTRL_L",    u15x - 15, ZY2 + 0.5)
    connect_pin("NET_APF3_CTRL_R",    u15x - 15, ZY2 - 8.89)

    # APF Vbe reference TL072: U16
    # A: temp-comp ref for APF1 and APF2 (both share NET_VREF_APF12)
    # B: temp-comp ref for APF3
    u16x = col * STEP;  col += 1
    _place_tl072_unit("U16", "TL072", 1, u16x, ZY2 - 10,
                       {"in+": "GND",  "in-": "NET_APF1_VREF",  "out": "NET_VREF_APF12"})
    _place_tl072_unit("U16", "TL072", 2, u16x, ZY2 + 10,
                       {"in+": "GND",  "in-": "NET_APF3_VREF",  "out": "NET_VREF_APF3"})
    _place_tl072_unit("U16", "TL072", 3, u16x, ZY2 + 30, {})

    # =========================================================
    # Zones 18–20 — Filter expo converters (LP1, LP2, HP)
    # LP1: Q1=LP1_L, Q2=LP1_R; WPR_LP1_SPREAD adds stereo offset to Q2 base
    # LP2: Q1=LP2_L, Q2=LP2_R; B1=B2=NET_LP2_CTRL (no stereo spread)
    # HP:  Q1=HP_L,  Q2=HP_R;  B1=B2=NET_HP_CTRL (no stereo spread)
    # Emitters all default to GND via R_e (bias resistors, see noise-audit M3)
    # =========================================================

    # LP1 expo: U17 THAT340
    u17x = col * STEP;  col += 1
    _place_that340("U17", u17x, ZY2, {
        "B1": "NET_LP1_CTRL_L",     # WPR_LP1_CUT + LP1_CUT_CV (attenuverter contribution)
        "C1": "NET_IABC_LP1_L",     # → STK_AUDIO_L pin 16
        "B2": "NET_LP1_CTRL_R",     # = NET_LP1_CTRL_L + WPR_LP1_SPREAD (stereo spread)
        "C2": "NET_IABC_LP1_R",     # → STK_AUDIO_R pin 16
        "B3": "NET_LP1_VREF",
        "C3": "NET_LP1_VREF",
        "SUB": "GND",
    })
    connect_pin("NET_WPR_LP1_CUT",    u17x - 15, ZY2 + 8.89)
    connect_pin("NET_LP1_CUT_CV",     u17x - 15, ZY2 + 6.35)
    connect_pin("NET_VREF_LP12",      u17x - 15, ZY2 + 2.0)
    connect_pin("NET_LP1_CTRL_L",     u17x - 15, ZY2 + 0.5)
    connect_pin("NET_WPR_LP1_SPREAD", u17x - 15, ZY2 - 8.89)  # spread into R base summing node
    connect_pin("NET_LP1_CTRL_R",     u17x - 15, ZY2 - 11.43)

    # LP2 expo: U18 THAT340
    u18x = col * STEP;  col += 1
    _place_that340("U18", u18x, ZY2, {
        "B1": "NET_LP2_CTRL",
        "C1": "NET_IABC_LP2_L",     # → STK_AUDIO_L pin 18
        "B2": "NET_LP2_CTRL",       # same ctrl, no stereo spread
        "C2": "NET_IABC_LP2_R",     # → STK_AUDIO_R pin 18
        "B3": "NET_LP2_VREF",
        "C3": "NET_LP2_VREF",
        "SUB": "GND",
    })
    connect_pin("NET_WPR_LP2_CUT",  u18x - 15, ZY2 + 8.89)
    connect_pin("NET_LP2_CUT_CV",   u18x - 15, ZY2 + 6.35)
    connect_pin("NET_VREF_LP12",    u18x - 15, ZY2 + 2.0)
    connect_pin("NET_LP2_CTRL",     u18x - 15, ZY2 + 0.5)

    # HP expo: U19 THAT340
    u19x = col * STEP;  col += 1
    _place_that340("U19", u19x, ZY2, {
        "B1": "NET_HP_CTRL",
        "C1": "NET_IABC_HP_L",      # → STK_AUDIO_L pin 19
        "B2": "NET_HP_CTRL",        # same ctrl
        "C2": "NET_IABC_HP_R",      # → STK_AUDIO_R pin 19
        "B3": "NET_HP_VREF",
        "C3": "NET_HP_VREF",
        "SUB": "GND",
    })
    connect_pin("NET_WPR_HP_CUT",   u19x - 15, ZY2 + 8.89)
    connect_pin("NET_HP_CUT_CV",    u19x - 15, ZY2 + 6.35)
    connect_pin("NET_VREF_HP",      u19x - 15, ZY2 + 2.0)
    connect_pin("NET_HP_CTRL",      u19x - 15, ZY2 + 0.5)

    # Filter Vbe reference TL072: U20
    # A: LP1+LP2 Vbe ref (NET_VREF_LP12 feeds both LP1 U17 and LP2 U18 summing nodes)
    # B: HP Vbe ref
    u20x = col * STEP;  col += 1
    _place_tl072_unit("U20", "TL072", 1, u20x, ZY2 - 10,
                       {"in+": "GND",  "in-": "NET_LP1_VREF",  "out": "NET_VREF_LP12"})
    _place_tl072_unit("U20", "TL072", 2, u20x, ZY2 + 10,
                       {"in+": "GND",  "in-": "NET_HP_VREF",   "out": "NET_VREF_HP"})
    _place_tl072_unit("U20", "TL072", 3, u20x, ZY2 + 30, {})
    # LP2 Vbe also uses this ref (LP2 Q3 emitter-connected to same virtual ground as LP1)
    connect_pin("NET_LP2_VREF",  u20x - 8, ZY2 - 9)

    # =========================================================
    # Zones 21–22 — STK_AUDIO_L and STK_AUDIO_R
    # 40-pin stacking headers (2×20) to combined audio board
    # Pinout from layout-notes.md §5
    # Spare pins 39-40 carry switch/wiper signals that need to reach audio board
    # =========================================================

    # STK_AUDIO_L — L-channel zone (left ~100 mm of audio board)
    stk_l_nets = {
        1:  "+12V",    2:  "+12V",
        3:  "-12V",    4:  "-12V",
        5:  "GND",     6:  "GND",
        7:  "NET_L_IN_BUF",
        8:  "NET_ENV_OUT_L",
        9:  "NET_BAND_OUT_L",
        10: "NET_LEFT_OUT",
        11: "GND",                    # GND guard (noise-audit H2)
        12: "NET_IABC_APF1_L",
        13: "NET_IABC_APF2_L",
        14: "GND",                    # GND guard
        15: "NET_IABC_APF3_L",
        16: "NET_IABC_LP1_L",
        17: "GND",                    # GND guard
        18: "NET_IABC_LP2_L",
        19: "NET_IABC_HP_L",
        20: "NET_LP1_CUT_CV",
        21: "NET_LP1_RES_CV",
        22: "NET_LP2_CUT_CV",
        23: "NET_LP2_RES_CV",
        24: "NET_HP_CUT_CV",
        25: "NET_HP_RES_CV",
        26: "NET_VCA_LEVEL_CV",
        27: "NET_COMB_BYPASS_CV",
        28: "NET_APF_FB1_CV",
        29: "NET_APF_FB2_CV",
        30: "NET_APF_FB3_CV",
        31: "NET_DRIVE1_CV",
        32: "NET_DRIVE2_CV",
        33: "NET_DRIVE3_CV",
        34: "GND",
        35: "NET_POST_DIST_L1",
        36: "NET_POST_DIST_L2",
        37: "NET_POST_DIST_L3",
        38: "NET_FB_BLEND_OUT_L",
        39: "NET_SW_GAIN_COM",        # GAIN switch → Block 1 on audio board
        40: "NET_WPR_ATTACK",         # ATTACK wiper → Block 2 on audio board
    }
    place_pin_header40("STK_L", "STK_AUDIO_L", stk_l_nets, col, ZY)
    col += 1

    # STK_AUDIO_R — R-channel zone (right ~100 mm of audio board)
    # Identical signal structure to L; shared CVs use the same net names.
    # Spare pins carry additional wiper/switch signals for R-channel or shared use.
    stk_r_nets = {
        1:  "+12V",    2:  "+12V",
        3:  "-12V",    4:  "-12V",
        5:  "GND",     6:  "GND",
        7:  "NET_R_IN_BUF",
        8:  "NET_ENV_OUT_R",
        9:  "NET_BAND_OUT_R",
        10: "NET_RIGHT_OUT",
        11: "GND",                    # GND guard
        12: "NET_IABC_APF1_R",
        13: "NET_IABC_APF2_R",
        14: "GND",                    # GND guard
        15: "NET_IABC_APF3_R",
        16: "NET_IABC_LP1_R",
        17: "GND",                    # GND guard
        18: "NET_IABC_LP2_R",
        19: "NET_IABC_HP_R",
        20: "NET_LP1_CUT_CV",         # shared — same source drives both L and R
        21: "NET_LP1_RES_CV",
        22: "NET_LP2_CUT_CV",
        23: "NET_LP2_RES_CV",
        24: "NET_HP_CUT_CV",
        25: "NET_HP_RES_CV",
        26: "NET_VCA_LEVEL_CV",       # stereo-linked VCA
        27: "NET_COMB_BYPASS_CV",
        28: "NET_APF_FB1_CV",
        29: "NET_APF_FB2_CV",
        30: "NET_APF_FB3_CV",
        31: "NET_DRIVE1_CV",
        32: "NET_DRIVE2_CV",
        33: "NET_DRIVE3_CV",
        34: "GND",
        35: "NET_POST_DIST_R1",
        36: "NET_POST_DIST_R2",
        37: "NET_POST_DIST_R3",
        38: "NET_FB_BLEND_OUT_R",
        39: "NET_WPR_RELEASE",        # RELEASE wiper → Block 2 on audio board
        40: "NET_SW_MODE_SFT",        # MODE switch pos-1 → Block 4 on audio board
        # NOTE: NET_SW_MODE_HRD and NET_SW_MODE_WFD decoded on utility board (planned)
        # or assigned to a future expanded connector. Currently architectural gap.
    }
    place_pin_header40("STK_R", "STK_AUDIO_R", stk_r_nets, col, ZY)
    col += 1

    end_schematic()


if __name__ == "__main__":
    os.chdir(os.path.dirname(__file__))
    build_schematic()
    write_schematic("pogo-utility-board.kicad_sch")
