#!/usr/bin/env python3
"""
POGO control board schematic validator.

Parses pogo-control-board.kicad_sch with kiutils and runs structural +
pin-level checks against the ground-truth pinout in layout-notes.md.

Checks:
  1.  Component counts           J×28, RV×43, SW×4, CN×3
  2.  No duplicate refs          unique reference designators
  3.  Floating nets              single-occurrence global labels (minus known spares)
  4.  Required nets present      all 86 named nets exist
  5.  NET_MODBUS_NORM count      exactly 20 (19 SW lugs + 1 CN2 pin)
  6.  Jack pin assignments       tip / sleeve / SW per jack (all 28)
  7.  Pot pin assignments        CCW / wiper / CW per pot (all 43)
  8.  Switch pin assignments     throws and common per switch (all 4)
  9.  CN1 pinout                 34-pin IDC vs. layout-notes.md §5
  10. CN2 pinout                 40-pin IDC vs. layout-notes.md §5
  11. CN3 pinout                 24-pin IDC vs. layout-notes.md §5

Install: pip3 install kiutils
Run:     python3 validate_schematic.py [schematic.kicad_sch]
Exit:    0 = pass, 1 = failures found
"""

import sys, os, re
from collections import Counter

try:
    from kiutils.schematic import Schematic
except ImportError:
    print("ERROR: kiutils not installed. Run: pip3 install kiutils")
    sys.exit(1)

sys.path.insert(0, os.path.dirname(__file__))
from kicad_common import jack_pins, rpot_pins, spdt_pins, sp3t_pins, idc_pins


# ---------------------------------------------------------------------------
# Ground-truth pinout tables (from layout-notes.md §5 + generator source)
# ---------------------------------------------------------------------------

EXPECTED_COUNTS = {"J": 28, "RV": 43, "SW": 4, "CN": 3}

KNOWN_SPARE_NETS = {"SPARE_CN2_28", "SPARE_CN2_40", "SPARE_CN3_24"}

REQUIRED_NETS = [
    "NET_L_IN", "NET_R_IN",
    "NET_ENV_OUT_L", "NET_ENV_OUT_R",
    "NET_BAND_OUT_L", "NET_BAND_OUT_R",
    "NET_LEFT_OUT", "NET_RIGHT_OUT",
    "NET_MOD_IN", "NET_ENV_NORM", "NET_MODBUS_NORM",
    "NET_WPR_ATTACK", "NET_WPR_RELEASE",
    "NET_WPR_AMOUNT", "NET_WPR_OFFSET_MB",
    "NET_WPR_COMB_BYPASS", "NET_WPR_WIDTH",
    "NET_WPR_MASTER_OFFSET", "NET_WPR_FB_DIST_BLEND",
    "NET_WPR_FREQ1", "NET_WPR_FREQ2", "NET_WPR_FREQ3",
    "NET_WPR_FB1", "NET_WPR_FB2", "NET_WPR_FB3",
    "NET_WPR_DRIVE1", "NET_WPR_DRIVE2", "NET_WPR_DRIVE3",
    "NET_WPR_LP1_CUT", "NET_WPR_LP1_RES", "NET_WPR_LP1_SPREAD",
    "NET_WPR_LP2_CUT", "NET_WPR_LP2_RES",
    "NET_WPR_HP_CUT", "NET_WPR_HP_RES",
    "NET_WPR_ATT_BYPASS", "NET_WPR_ATT_OFFSET", "NET_WPR_ATT_BLEND",
    "NET_WPR_ATT_VCA_AMT",
    "NET_WPR_ATT_FREQ1", "NET_WPR_ATT_FREQ2", "NET_WPR_ATT_FREQ3",
    "NET_WPR_ATT_FB1",   "NET_WPR_ATT_FB2",   "NET_WPR_ATT_FB3",
    "NET_WPR_ATT_DRIVE1","NET_WPR_ATT_DRIVE2","NET_WPR_ATT_DRIVE3",
    "NET_WPR_ATT_LP1_CUT","NET_WPR_ATT_LP1_RES",
    "NET_WPR_ATT_LP2_CUT","NET_WPR_ATT_LP2_RES",
    "NET_WPR_ATT_HP_CUT", "NET_WPR_ATT_HP_RES",
    "NET_CV_BYPASS", "NET_CV_OFFSET", "NET_CV_BLEND", "NET_CV_VCA_AMT",
    "NET_CV_LP1_CUT","NET_CV_LP1_RES",
    "NET_CV_LP2_CUT","NET_CV_LP2_RES",
    "NET_CV_HP_CUT", "NET_CV_HP_RES",
    "NET_CV_FREQ1",  "NET_CV_FREQ2",  "NET_CV_FREQ3",
    "NET_CV_FB1",    "NET_CV_FB2",    "NET_CV_FB3",
    "NET_CV_DRIVE1", "NET_CV_DRIVE2", "NET_CV_DRIVE3",
    "NET_SW_GAIN_COM",
    "NET_SW_MODE_SFT", "NET_SW_MODE_HRD", "NET_SW_MODE_WFD",
    "NET_SW_MODSRC_L", "NET_SW_MODSRC_MAX", "NET_SW_MODSRC_AVG",
    "NET_SW_POL_POS",  "NET_SW_POL_OFF",   "NET_SW_POL_NEG",
    "+12V", "-12V", "GND",
]

# Jack rules: ref → (tip_net, sleeve_net, sw_net)
JACK_RULES = {
    "J1":  ("NET_L_IN",       "GND", "GND"),
    "J2":  ("NET_R_IN",       "GND", "GND"),
    "J3":  ("NET_ENV_OUT_L",  "GND", "GND"),
    "J4":  ("NET_ENV_OUT_R",  "GND", "GND"),
    "J5":  ("NET_BAND_OUT_L", "GND", "GND"),
    "J6":  ("NET_BAND_OUT_R", "GND", "GND"),
    "J7":  ("NET_LEFT_OUT",   "GND", "GND"),
    "J8":  ("NET_RIGHT_OUT",  "GND", "GND"),
    "J9":  ("NET_MOD_IN",     "GND", "NET_ENV_NORM"),       # normalizes to ENV
    "J10": ("NET_CV_BYPASS",  "GND", "NET_MODBUS_NORM"),
    "J11": ("NET_CV_OFFSET",  "GND", "NET_MODBUS_NORM"),
    "J12": ("NET_CV_BLEND",   "GND", "NET_MODBUS_NORM"),
    "J13": ("NET_CV_FREQ1",   "GND", "NET_MODBUS_NORM"),
    "J14": ("NET_CV_FB1",     "GND", "NET_MODBUS_NORM"),
    "J15": ("NET_CV_DRIVE1",  "GND", "NET_MODBUS_NORM"),
    "J16": ("NET_CV_FREQ2",   "GND", "NET_MODBUS_NORM"),
    "J17": ("NET_CV_FB2",     "GND", "NET_MODBUS_NORM"),
    "J18": ("NET_CV_DRIVE2",  "GND", "NET_MODBUS_NORM"),
    "J19": ("NET_CV_FREQ3",   "GND", "NET_MODBUS_NORM"),
    "J20": ("NET_CV_FB3",     "GND", "NET_MODBUS_NORM"),
    "J21": ("NET_CV_DRIVE3",  "GND", "NET_MODBUS_NORM"),
    "J22": ("NET_CV_VCA_AMT", "GND", "NET_MODBUS_NORM"),
    "J23": ("NET_CV_LP1_CUT", "GND", "NET_MODBUS_NORM"),
    "J24": ("NET_CV_LP1_RES", "GND", "NET_MODBUS_NORM"),
    "J25": ("NET_CV_LP2_CUT", "GND", "NET_MODBUS_NORM"),
    "J26": ("NET_CV_LP2_RES", "GND", "NET_MODBUS_NORM"),
    "J27": ("NET_CV_HP_CUT",  "GND", "NET_MODBUS_NORM"),
    "J28": ("NET_CV_HP_RES",  "GND", "NET_MODBUS_NORM"),
}

# Pot rules: ref → (ccw_net, wiper_net, cw_net)
# CCW=-12V = bipolar (attenuverter or 1V/oct); CCW=GND = unipolar
POT_RULES = {
    "RV1":  ("GND",  "NET_WPR_ATTACK",          "+12V"),
    "RV2":  ("GND",  "NET_WPR_RELEASE",         "+12V"),
    "RV3":  ("GND",  "NET_WPR_AMOUNT",          "+12V"),
    "RV4":  ("-12V", "NET_WPR_OFFSET_MB",       "+12V"),  # bipolar ±5V offset
    "RV5":  ("GND",  "NET_WPR_COMB_BYPASS",     "+12V"),
    "RV6":  ("-12V", "NET_WPR_WIDTH",           "+12V"),  # bipolar
    "RV7":  ("-12V", "NET_WPR_MASTER_OFFSET",   "+12V"),  # bipolar ±5V
    "RV8":  ("GND",  "NET_WPR_FB_DIST_BLEND",   "+12V"),
    "RV9":  ("-12V", "NET_WPR_ATT_BYPASS",      "+12V"),  # attenuverter
    "RV10": ("-12V", "NET_WPR_ATT_OFFSET",      "+12V"),
    "RV11": ("-12V", "NET_WPR_ATT_BLEND",       "+12V"),
    "RV12": ("-12V", "NET_WPR_FREQ1",           "+12V"),  # 1V/oct, bipolar
    "RV13": ("GND",  "NET_WPR_FB1",             "+12V"),
    "RV14": ("GND",  "NET_WPR_DRIVE1",          "+12V"),
    "RV15": ("-12V", "NET_WPR_ATT_FREQ1",       "+12V"),
    "RV16": ("-12V", "NET_WPR_ATT_FB1",         "+12V"),
    "RV17": ("-12V", "NET_WPR_ATT_DRIVE1",      "+12V"),
    "RV18": ("-12V", "NET_WPR_FREQ2",           "+12V"),
    "RV19": ("GND",  "NET_WPR_FB2",             "+12V"),
    "RV20": ("GND",  "NET_WPR_DRIVE2",          "+12V"),
    "RV21": ("-12V", "NET_WPR_ATT_FREQ2",       "+12V"),
    "RV22": ("-12V", "NET_WPR_ATT_FB2",         "+12V"),
    "RV23": ("-12V", "NET_WPR_ATT_DRIVE2",      "+12V"),
    "RV24": ("-12V", "NET_WPR_FREQ3",           "+12V"),
    "RV25": ("GND",  "NET_WPR_FB3",             "+12V"),
    "RV26": ("GND",  "NET_WPR_DRIVE3",          "+12V"),
    "RV27": ("-12V", "NET_WPR_ATT_FREQ3",       "+12V"),
    "RV28": ("-12V", "NET_WPR_ATT_FB3",         "+12V"),
    "RV29": ("-12V", "NET_WPR_ATT_DRIVE3",      "+12V"),
    "RV30": ("-12V", "NET_WPR_ATT_VCA_AMT",     "+12V"),  # attenuverter
    "RV31": ("-12V", "NET_WPR_LP1_CUT",         "+12V"),  # 1V/oct
    "RV32": ("-12V", "NET_WPR_LP1_SPREAD",      "+12V"),  # bipolar spread
    "RV33": ("GND",  "NET_WPR_LP1_RES",         "+12V"),
    "RV34": ("-12V", "NET_WPR_ATT_LP1_CUT",     "+12V"),
    "RV35": ("-12V", "NET_WPR_ATT_LP1_RES",     "+12V"),
    "RV36": ("GND",  "NET_WPR_LP2_CUT",         "+12V"),  # slider, unipolar
    "RV37": ("GND",  "NET_WPR_LP2_RES",         "+12V"),
    "RV38": ("-12V", "NET_WPR_ATT_LP2_CUT",     "+12V"),
    "RV39": ("-12V", "NET_WPR_ATT_LP2_RES",     "+12V"),
    "RV40": ("GND",  "NET_WPR_HP_CUT",          "+12V"),  # slider
    "RV41": ("GND",  "NET_WPR_HP_RES",          "+12V"),
    "RV42": ("-12V", "NET_WPR_ATT_HP_CUT",      "+12V"),
    "RV43": ("-12V", "NET_WPR_ATT_HP_RES",      "+12V"),
}

# Switch rules: ref → {pin_str: net}
# SPDT pins: "1"=A throw, "2"=B throw, "3"=Common
# SP3T pins: "1"=pos1, "2"=pos2, "3"=pos3, "4"=Common
SWITCH_RULES = {
    "SW1": {  # GAIN SPDT — common reads low (GND) or high (+12V); utility decodes
        "1": "GND",              # 1× position → GND
        "2": "+12V",             # 5× position → +12V
        "3": "NET_SW_GAIN_COM",  # common → CN2 pin 5
    },
    "SW2": {  # MOD SRC SP3T — common tied +12V; active position output goes high
        "1": "NET_SW_MODSRC_L",
        "2": "NET_SW_MODSRC_MAX",
        "3": "NET_SW_MODSRC_AVG",
        "4": "+12V",             # common → +12V power rail on control board
    },
    "SW3": {  # POLARITY SP3T
        "1": "NET_SW_POL_POS",
        "2": "NET_SW_POL_OFF",
        "3": "NET_SW_POL_NEG",
        "4": "+12V",
    },
    "SW4": {  # MODE SP3T (1 shared switch for all 3 comb groups)
        "1": "NET_SW_MODE_SFT",
        "2": "NET_SW_MODE_HRD",
        "3": "NET_SW_MODE_WFD",
        "4": "+12V",
    },
}

# Connector pinouts — directly from layout-notes.md §5
CN1_PINOUT = {
    1:  "+12V",           2:  "+12V",
    3:  "-12V",           4:  "-12V",
    5:  "GND",            6:  "GND",
    7:  "NET_L_IN",       8:  "NET_R_IN",
    9:  "NET_ENV_OUT_L",  10: "NET_ENV_OUT_R",
    11: "NET_BAND_OUT_L", 12: "NET_BAND_OUT_R",
    13: "NET_LEFT_OUT",   14: "NET_RIGHT_OUT",
    15: "NET_CV_BYPASS",  16: "NET_CV_OFFSET",
    17: "NET_CV_BLEND",   18: "NET_CV_VCA_AMT",
    19: "NET_CV_LP1_CUT", 20: "NET_CV_LP1_RES",
    21: "NET_CV_LP2_CUT", 22: "NET_CV_LP2_RES",
    23: "NET_CV_HP_CUT",  24: "NET_CV_HP_RES",
    25: "NET_CV_FREQ1",   26: "NET_CV_FREQ2",
    27: "NET_CV_FREQ3",   28: "NET_CV_FB1",
    29: "NET_CV_FB2",     30: "NET_CV_FB3",
    31: "NET_CV_DRIVE1",  32: "NET_CV_DRIVE2",
    33: "NET_CV_DRIVE3",  34: "NET_MOD_IN",
}

CN2_PINOUT = {
    1:  "GND",              2:  "GND",
    3:  "+12V",             4:  "-12V",
    5:  "NET_SW_GAIN_COM",
    6:  "NET_SW_MODE_SFT",
    7:  "NET_SW_MODE_HRD",
    8:  "NET_SW_MODE_WFD",
    9:  "NET_WPR_ATT_BYPASS",
    10: "NET_WPR_ATT_OFFSET",
    11: "NET_WPR_ATT_BLEND",
    12: "NET_WPR_ATT_VCA_AMT",
    13: "NET_WPR_ATT_LP1_CUT",
    14: "NET_WPR_ATT_LP1_RES",
    15: "NET_WPR_ATT_LP2_CUT",
    16: "NET_WPR_ATT_LP2_RES",
    17: "NET_WPR_ATT_HP_CUT",
    18: "NET_WPR_ATT_HP_RES",
    19: "NET_WPR_ATT_FREQ1",
    20: "NET_WPR_ATT_FREQ2",
    21: "NET_WPR_ATT_FREQ3",
    22: "NET_WPR_ATT_FB1",
    23: "NET_WPR_ATT_FB2",
    24: "NET_WPR_ATT_FB3",
    25: "NET_WPR_ATT_DRIVE1",
    26: "NET_WPR_ATT_DRIVE2",
    27: "NET_WPR_ATT_DRIVE3",
    28: "SPARE_CN2_28",
    29: "NET_WPR_AMOUNT",
    30: "NET_WPR_OFFSET_MB",
    31: "NET_WPR_LP1_SPREAD",
    32: "NET_SW_MODSRC_L",
    33: "NET_SW_MODSRC_MAX",
    34: "NET_SW_MODSRC_AVG",
    35: "NET_SW_POL_POS",
    36: "NET_SW_POL_OFF",
    37: "NET_SW_POL_NEG",
    38: "NET_ENV_NORM",
    39: "NET_MODBUS_NORM",
    40: "SPARE_CN2_40",
}

CN3_PINOUT = {
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_prop(sym, key):
    return next(p.value for p in sym.properties if p.key == key)


def ref_prefix(ref):
    return re.match(r"[A-Za-z]+", ref).group(0)


def build_lookups(sch):
    """
    Returns:
      label_at  : {(x, y) → net_str}  global labels (incl. power-named ones)
      power_at  : {(x, y) → net_str}  power symbol instances
      sym_by_ref: {ref → SchematicSymbol}  first instance per ref
    """
    label_at = {}
    for gl in sch.globalLabels:
        k = (round(gl.position.X, 2), round(gl.position.Y, 2))
        label_at[k] = gl.text

    power_at = {}
    for sym in sch.schematicSymbols:
        if sym.libId.startswith("power:"):
            net = sym.libId.split(":", 1)[1]
            k = (round(sym.position.X, 2), round(sym.position.Y, 2))
            power_at[k] = net

    sym_by_ref = {}
    for sym in sch.schematicSymbols:
        ref = get_prop(sym, "Reference")
        if not ref.startswith("#") and ref not in sym_by_ref:
            sym_by_ref[ref] = sym

    return label_at, power_at, sym_by_ref


def net_at(x, y, label_at, power_at):
    """Return net name at canvas position (x, y), or None if nothing found."""
    k = (round(x, 2), round(y, 2))
    return label_at.get(k) or power_at.get(k)


def idc_rows_from_libid(lib_id):
    m = re.search(r"IDC-Header_2x(\d+)_", lib_id)
    return int(m.group(1)) if m else None


# ---------------------------------------------------------------------------
# Check 1: component counts
# ---------------------------------------------------------------------------

def check_counts(sch):
    errors = []
    refs = set(
        get_prop(sym, "Reference")
        for sym in sch.schematicSymbols
        if not get_prop(sym, "Reference").startswith("#")
    )
    counts = Counter(ref_prefix(r) for r in refs)
    for prefix, expected in EXPECTED_COUNTS.items():
        actual = counts.get(prefix, 0)
        if actual != expected:
            errors.append(f"{prefix}: got {actual}, expected {expected}")
    total = len(refs)
    exp_total = sum(EXPECTED_COUNTS.values())
    if total != exp_total:
        errors.append(f"Total components: got {total}, expected {exp_total}")
    return errors


# ---------------------------------------------------------------------------
# Check 2: no duplicate reference designators
# ---------------------------------------------------------------------------

def check_no_duplicates(sch):
    errors = []
    seen = {}
    for sym in sch.schematicSymbols:
        ref = get_prop(sym, "Reference")
        if ref.startswith("#"):
            continue
        lib_id = sym.libId
        if ref in seen and seen[ref] != lib_id:
            errors.append(f"Duplicate ref {ref}: libs {seen[ref]} vs {lib_id}")
        seen[ref] = lib_id
    return errors


# ---------------------------------------------------------------------------
# Check 3: floating (single-occurrence) nets
# ---------------------------------------------------------------------------

def check_floating_nets(sch):
    errors = []
    net_counts = Counter(gl.text for gl in sch.globalLabels)
    singles = {n for n, c in net_counts.items() if c == 1}
    unexpected = singles - KNOWN_SPARE_NETS
    for n in sorted(unexpected):
        errors.append(f"Floating net (single occurrence): {n}")
    for n in sorted(KNOWN_SPARE_NETS - singles):
        errors.append(f"Expected spare net missing entirely: {n}")
    return errors


# ---------------------------------------------------------------------------
# Check 4: required nets present
# ---------------------------------------------------------------------------

def check_required_nets(sch):
    all_nets = {gl.text for gl in sch.globalLabels}
    return [f"Required net missing: {n}" for n in REQUIRED_NETS if n not in all_nets]


# ---------------------------------------------------------------------------
# Check 5: NET_MODBUS_NORM count
# ---------------------------------------------------------------------------

def check_modbus_norm(sch):
    count = sum(1 for gl in sch.globalLabels if gl.text == "NET_MODBUS_NORM")
    if count != 20:
        return [f"NET_MODBUS_NORM appears {count}× (expected 20: 19 SW lugs + 1 CN2 pin)"]
    return []


# ---------------------------------------------------------------------------
# Check 6: jack pin assignments
# ---------------------------------------------------------------------------

def check_jack_pins(sch, label_at, power_at, sym_by_ref):
    errors = []
    pin_names = {"1": "tip", "2": "sleeve", "3": "SW"}
    for ref, (tip, sleeve, sw) in JACK_RULES.items():
        if ref not in sym_by_ref:
            errors.append(f"{ref}: not found in schematic")
            continue
        sym = sym_by_ref[ref]
        ox, oy = sym.position.X, sym.position.Y
        pins = jack_pins(ox, oy)
        expected = {"1": tip, "2": sleeve, "3": sw}
        for pn, exp_net in expected.items():
            actual = net_at(*pins[pn], label_at, power_at)
            if actual != exp_net:
                errors.append(
                    f"{ref} pin {pn} ({pin_names[pn]}): "
                    f"got {actual!r}, expected {exp_net!r}"
                )
    return errors


# ---------------------------------------------------------------------------
# Check 7: pot pin assignments
# ---------------------------------------------------------------------------

def check_pot_pins(sch, label_at, power_at, sym_by_ref):
    errors = []
    pin_names = {"1": "CCW", "2": "wiper", "3": "CW"}
    for ref, (ccw, wiper, cw) in POT_RULES.items():
        if ref not in sym_by_ref:
            errors.append(f"{ref}: not found in schematic")
            continue
        sym = sym_by_ref[ref]
        ox, oy = sym.position.X, sym.position.Y
        pins = rpot_pins(ox, oy)
        expected = {"1": ccw, "2": wiper, "3": cw}
        for pn, exp_net in expected.items():
            actual = net_at(*pins[pn], label_at, power_at)
            if actual != exp_net:
                errors.append(
                    f"{ref} pin {pn} ({pin_names[pn]}): "
                    f"got {actual!r}, expected {exp_net!r}"
                )
    return errors


# ---------------------------------------------------------------------------
# Check 8: switch pin assignments
# ---------------------------------------------------------------------------

def check_switch_pins(sch, label_at, power_at, sym_by_ref):
    errors = []
    for ref, pin_map in SWITCH_RULES.items():
        if ref not in sym_by_ref:
            errors.append(f"{ref}: not found in schematic")
            continue
        sym = sym_by_ref[ref]
        ox, oy = sym.position.X, sym.position.Y
        is_sp3t = len(pin_map) == 4
        pins = sp3t_pins(ox, oy) if is_sp3t else spdt_pins(ox, oy)
        for pn, exp_net in pin_map.items():
            actual = net_at(*pins[pn], label_at, power_at)
            if actual != exp_net:
                errors.append(
                    f"{ref} pin {pn}: got {actual!r}, expected {exp_net!r}"
                )
    return errors


# ---------------------------------------------------------------------------
# Check 9–11: connector pinouts vs. layout-notes.md
# ---------------------------------------------------------------------------

def check_connector(ref, expected_pinout, rows, sym_by_ref, label_at, power_at):
    errors = []
    if ref not in sym_by_ref:
        errors.append(f"{ref}: not found in schematic")
        return errors
    sym = sym_by_ref[ref]
    # Verify the lib_id row count matches
    actual_rows = idc_rows_from_libid(sym.libId)
    if actual_rows != rows:
        errors.append(
            f"{ref}: lib_id has {actual_rows} rows, expected {rows} "
            f"({rows*2}-pin IDC)"
        )
        return errors
    ox, oy = sym.position.X, sym.position.Y
    pins = idc_pins(ox, oy, rows)
    for pin_num, exp_net in expected_pinout.items():
        actual = net_at(*pins[str(pin_num)], label_at, power_at)
        if actual != exp_net:
            errors.append(
                f"{ref} pin {pin_num}: got {actual!r}, expected {exp_net!r}"
            )
    return errors


def check_connectors(sch, label_at, power_at, sym_by_ref):
    errors = []
    errors += check_connector("CN1", CN1_PINOUT, 17, sym_by_ref, label_at, power_at)
    errors += check_connector("CN2", CN2_PINOUT, 20, sym_by_ref, label_at, power_at)
    errors += check_connector("CN3", CN3_PINOUT, 12, sym_by_ref, label_at, power_at)
    return errors


# ---------------------------------------------------------------------------
# Main validation runner
# ---------------------------------------------------------------------------

CHECKS = [
    ("Component counts",          lambda sch, *_: check_counts(sch)),
    ("Duplicate references",      lambda sch, *_: check_no_duplicates(sch)),
    ("Floating nets",             lambda sch, *_: check_floating_nets(sch)),
    ("Required nets present",     lambda sch, *_: check_required_nets(sch)),
    ("NET_MODBUS_NORM count",     lambda sch, *_: check_modbus_norm(sch)),
    ("Jack pin assignments",      lambda sch, la, pa, sr: check_jack_pins(sch, la, pa, sr)),
    ("Pot pin assignments",       lambda sch, la, pa, sr: check_pot_pins(sch, la, pa, sr)),
    ("Switch pin assignments",    lambda sch, la, pa, sr: check_switch_pins(sch, la, pa, sr)),
    ("Connector pinouts (CN1/2/3)",lambda sch, la, pa, sr: check_connectors(sch, la, pa, sr)),
]


def validate(path):
    print(f"Validating: {path}\n")
    sch = Schematic().from_file(path)
    label_at, power_at, sym_by_ref = build_lookups(sch)

    total_errors = 0
    total_checks = 0

    for name, fn in CHECKS:
        errors = fn(sch, label_at, power_at, sym_by_ref)
        total_checks += 1
        if errors:
            print(f"  FAIL  {name} ({len(errors)} error(s)):")
            for e in errors:
                print(f"          • {e}")
            total_errors += len(errors)
        else:
            print(f"  pass  {name}")

    print(f"\n{'PASSED' if total_errors == 0 else 'FAILED'} "
          f"— {total_checks} checks, {total_errors} error(s)")

    # Print pin-check totals as a sanity reference
    n_pins = (len(JACK_RULES)*3 + len(POT_RULES)*3
              + sum(len(v) for v in SWITCH_RULES.values())
              + len(CN1_PINOUT) + len(CN2_PINOUT) + len(CN3_PINOUT))
    print(f"  ({n_pins} individual pin assignments verified)")

    return total_errors == 0


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "pogo-control-board.kicad_sch"
    ok = validate(path)
    sys.exit(0 if ok else 1)
