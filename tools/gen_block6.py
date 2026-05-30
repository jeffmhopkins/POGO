#!/usr/bin/env python3
"""Generate specs/block-6/block-6.nets.yaml — Triple BP + Distortion (the last block).

3-group repetition (like block-3 was generated). This is a netlist-only,
decision-locked transcription per SCHEMATIC-GEN-PLAN.md "block-6 readiness":

  - BP resonator = Option B (DSP-faithful): the plugin BP (BandpassSVF.hpp) is the
    same 2-integrator Simper SVF as LP1/HP/LP2; mirror block-5/8 but tap v1 (BP)
    instead of v2 (LP). Per-group Q-VCA OTAs (U67-69, cell A=L / cell B=R) inject
    damping current at the SUM_AMP virtual ground, exactly like the shared-q sheet.
  - Per-channel expo (true BP_TILT): U28-30 = L expo, U70-72 = R expo; each fed
    BP{g}_VCTRL ± V_tilt (U27-A inverter makes -V_tilt; R127 tilt summers).
  - Distortion mux = stereo 1-of-3 from 2 CD4053/group (U31/U75, U32/U76, U33/U77):
    muxB picks HC-vs-WF -> MID; muxA picks SC-vs-MID -> DIST out, per channel
    (L on the X channel, R on the Y channel; Z channel spare). DW5 (SW4-6) is the
    mode encoder -> 2 control bits via R128 pull-ups to the 5V logic rail.
  - Q control: per-group IRES_AMP (U73-A=BP1, U73-B=BP2, U74-A=BP3; U74-B spare)
    with R117/R118/R119, RV9/12/15 V_bias, D13 V_ires>=0 clamp, R116 -> Q Iabc.
  - Distortion cells (per aux-distortion + spec §2, 6 paths): SC = inv gain amp
    (U34-39 half A) + 1N4148 chain D4 across fb; HC = inv gain amp (half B) +
    BZX84C5V1 back-to-back zeners D5 (±5.8V); WF = pre-gain (U40-45 half A) +
    passive 1N4148 clamp (D6/R24) + folder (half B, R25/R_f_wf): Vo = 2·Vclamp - Vin.

Three controls are under-specified in the STALE specs and flagged Phase-3R; the
signal path is wired faithfully and the control is treated as boundary CV applied
via a Phase-3R element (see the FLAG notes printed into the YAML header).

Run:  python3 tools/gen_block6.py     # writes specs/block-6/block-6.nets.yaml
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import symbols as S
_SYM = S.load()
# Board RAIL POLICY: which committed rail each NAMED supply pin connects to.
# (Pin NUMBERS come from components/symbols.yaml; the rail choice is board policy, not symbol data.)
_RAIL = {
    "ota":    {"V+": "P12", "V-": "N12"},
    "opamp2": {"V+": "P12", "V-": "N12"},
    "expo":   {"SUB": "N12"},                       # THAT340: both SUB pins -> -12V (no Vcc)
    "cd4053": {"VDD": "P12", "VEE": "N12", "VSS": "GND", "INH": "GND"},
}

OUT = Path(__file__).resolve().parent.parent / "specs" / "block-6" / "block-6.nets.yaml"

parts: list[tuple[str, str, str]] = []     # (ref, "{ sym: ... }", comment)
nets:  list[tuple[str, list[str], str]] = []  # (name, [REF.PIN], comment)
ncs:   list[str] = []                       # no_connect pins
bnd:   list[tuple[str, str]] = []           # (boundary net, comment)

# accumulators for the three rails (filled as parts are emitted)
P12: list[str] = []   # +12V
N12: list[str] = []   # -12V
GND: list[str] = []   # GND


def part(ref, spec, comment=""):
    parts.append((ref, spec, comment))


def net(name, pins, comment=""):
    nets.append((name, pins, comment))


def boundary(name, comment=""):
    bnd.append((name, comment))


CH = ("L", "R")


# ── IC inventory + supply pins (also drives decoupling C110, 2 per IC) ────────
# type -> (Vplus_pin, Vminus_pin, gnd_pins, vplus_is_decoupled, vminus_is_decoupled)
def supply(ref, typ):
    """Wire an IC's supply pins to the rails and add its two C110 decoupling caps."""
    if typ not in _RAIL:
        raise ValueError(typ)
    bucket = {"P12": P12, "N12": N12, "GND": GND}
    for name, railkey in _RAIL[typ].items():
        for num in S.pin_number(_SYM[typ], name):
            bucket[railkey].append(f"{ref}.{num}")
    vp, vn = "+12V", "-12V"
    # two decoupling caps per IC (C110, qty 90 = 2 x 45 ICs)
    cp, cn = f"C110_{ref}p", f"C110_{ref}n"
    part(cp, "{ sym: c, value: 100nF }", f"{ref} {vp} decoupling")
    part(cn, "{ sym: c, value: 100nF }", f"{ref} {vn} decoupling")
    P12.append(f"{cp}.1"); GND.append(f"{cp}.2")
    N12.append(f"{cn}.1"); GND.append(f"{cn}.2")


# ── declare the 45 ICs ────────────────────────────────────────────────────────
IC = []
def addic(ref, sym, partstr, value, typ, comment):
    part(ref, f"{{ sym: {sym}, part: {partstr}, value: {value} }}", comment)
    supply(ref, typ)
    IC.append(ref)

for g in (1, 2, 3):
    addic(f"U{15+(g-1)*2}", "ota", "LM13700M", "LM13700", "ota", f"BP{g} integrator OTAs L (cell A=OTA1/HP->v1, cell B=OTA2/v1->v2)")
    addic(f"U{16+(g-1)*2}", "ota", "LM13700M", "LM13700", "ota", f"BP{g} integrator OTAs R")
for g in (1, 2, 3):
    addic(f"U{21+(g-1)*2}", "opamp2", "OPA1612", "OPA1612", "opamp2", f"BP{g} L: A=SUM_AMP, B=BP(v1) output buffer")
    addic(f"U{22+(g-1)*2}", "opamp2", "OPA1612", "OPA1612", "opamp2", f"BP{g} R: A=SUM_AMP, B=BP(v1) output buffer")
addic("U27", "opamp2", "TL072CDT", "TL072", "opamp2", "A=tilt inverter (-V_tilt for R expos); B=reserved output polarity-restore inverter (Phase-3R)")
for g in (1, 2, 3):
    addic(f"U{28+(g-1)}", "expo", "THAT340S14-U", "THAT340", "expo", f"BP{g} expo converter L")
for g in (1, 2, 3):
    addic(f"U{31+(g-1)}", "cd4053", "CD4053", "CD4053", "cd4053", f"BP{g} dist mux A (SC-vs-MID; X=L, Y=R)")
for g in (1, 2, 3):
    addic(f"U{34+(g-1)*2}", "opamp2", "TL072CDT", "TL072", "opamp2", f"BP{g} L SC/HC amp (A=SC, B=HC)")
    addic(f"U{35+(g-1)*2}", "opamp2", "TL072CDT", "TL072", "opamp2", f"BP{g} R SC/HC amp (A=SC, B=HC)")
for g in (1, 2, 3):
    addic(f"U{40+(g-1)*2}", "opamp2", "TL072CDT", "TL072", "opamp2", f"BP{g} L WF amp (A=pre-gain, B=folder G=+2)")
    addic(f"U{41+(g-1)*2}", "opamp2", "TL072CDT", "TL072", "opamp2", f"BP{g} R WF amp (A=pre-gain, B=folder G=+2)")
addic("U46", "opamp2", "TL072CDT", "TL072", "opamp2", "L: A=wet summer (BP1+BP2+BP3), B=MIX amp")
addic("U47", "opamp2", "TL072CDT", "TL072", "opamp2", "R: A=wet summer, B=MIX amp")
addic("U48", "opamp2", "TL072CDT", "TL072", "opamp2", "wet buffer: A=L (drives MIX pot), B=R")
for g in (1, 2, 3):
    addic(f"U{67+(g-1)}", "ota", "LM13700M", "LM13700", "ota", f"BP{g} Q VCA (cell A=L Q, cell B=R Q)")
for g in (1, 2, 3):
    addic(f"U{70+(g-1)}", "expo", "THAT340S14-U", "THAT340", "expo", f"BP{g} expo converter R (per-channel tilt)")
addic("U73", "opamp2", "TL072CDT", "TL072", "opamp2", "Q IRES_AMP: A=BP1, B=BP2")
addic("U74", "opamp2", "TL072CDT", "TL072", "opamp2", "Q IRES_AMP: A=BP3; B=spare")
for g in (1, 2, 3):
    addic(f"U{75+(g-1)}", "cd4053", "CD4053", "CD4053", "cd4053", f"BP{g} dist mux B (HC-vs-WF; X=L, Y=R)")

assert len(IC) == 45, len(IC)

# per-group ref maps
INT  = {g: (f"U{15+(g-1)*2}", f"U{16+(g-1)*2}") for g in (1, 2, 3)}   # (L,R) integrator OTA
SUM  = {g: (f"U{21+(g-1)*2}", f"U{22+(g-1)*2}") for g in (1, 2, 3)}   # (L,R) SUM_AMP+buf
QVCA = {g: f"U{67+(g-1)}" for g in (1, 2, 3)}                          # Q OTA (A=L,B=R)
EXPO = {g: (f"U{28+(g-1)}", f"U{70+(g-1)}") for g in (1, 2, 3)}        # (L,R) expo
MUXA = {g: f"U{31+(g-1)}" for g in (1, 2, 3)}
MUXB = {g: f"U{75+(g-1)}" for g in (1, 2, 3)}
SCHC = {g: (f"U{34+(g-1)*2}", f"U{35+(g-1)*2}") for g in (1, 2, 3)}    # (L,R) SC/HC amp
WF   = {g: (f"U{40+(g-1)*2}", f"U{41+(g-1)*2}") for g in (1, 2, 3)}    # (L,R) WF amp
# IRES_AMP half: (ref, in-/out/+in pins) — half A=unit1 {2,1,3}, B=unit2 {6,7,5}
IRES = {1: ("U73", "2", "1", "3"), 2: ("U73", "6", "7", "5"), 3: ("U74", "2", "1", "3")}
# integrator-cap values + refs per group
CAPREF = {1: "C15", 2: "C19", 3: "C23"}
CAPVAL = {1: "150nF", 2: "22nF", 3: "4.7nF"}
# expo trims (L: ref + 1V/oct; Q: V_bias)  — R expo trims are RV24/RV25 per group
LREFTR  = {1: "RV7", 2: "RV10", 3: "RV13"}
LVOCTTR = {1: "RV8", 2: "RV11", 3: "RV14"}
QTRIM   = {1: "RV9", 2: "RV12", 3: "RV15"}


# ── passive declarations + per-group / per-channel wiring ─────────────────────
def R(ref, val, comment=""):
    part(ref, f"{{ sym: r, value: {val} }}", comment)

def C(ref, val, comment=""):
    part(ref, f"{{ sym: c, value: {val} }}", comment)

def D1148(ref, comment=""):
    part(ref, "{ sym: diode, part: 1N4148W, value: 1N4148W }", comment)

def DZ(ref, comment=""):
    part(ref, "{ sym: zener, part: BZX84C5V1, value: BZX84C5V1 }", comment)

def TRIM(ref, val, value, comment=""):
    part(ref, f"{{ sym: trimpot, part: \"Bourns 3224W\", value: {value} }}", comment)


# tilt inverter (U27-A) — global; shared by all 3 R expos
R("R16_in", "100k", "tilt inverter R_in (U27-A)")
R("R16_fb", "100k", "tilt inverter R_fb (U27-A)")
# reserved output polarity-restore inverter (U27-B) — Phase-3R (see FLAG)
R("R17_in", "100k", "reserved output polarity-restore R_in (U27-B); Phase-3R")
R("R17_fb", "100k", "reserved output polarity-restore R_fb (U27-B); Phase-3R")
net("BP_TILT_CV", ["R16_in.1", "R127_1L.1", "R127_2L.1", "R127_3L.1"],
    "<- control/mod: BP tilt CV (boundary); +V_tilt to L expos + tilt-inv input")
net("BP_TILT_INVN", ["U27.2", "R16_in.2", "R16_fb.1"], "tilt inverter virtual ground")
net("BP_NTILT", ["U27.1", "R16_fb.2", "R127_1R.1", "R127_2R.1", "R127_3R.1"],
    "-V_tilt -> R-channel tilt summers")
GND.append("U27.3")    # tilt-inv +in
boundary("BP_TILT_CV", "<- control/mod: BP stereo tilt CV")

# 5V logic rail for the CD4053 mode-select inputs (D7 zener shunt off +12V)
R("R29", "1k", "R_5V_logic: +12V -> D7 zener shunt (5.1V CD4053 logic rail)")
part("D7", "{ sym: zener, part: BZX84C5V1, value: BZX84C5V1 }",
     "5.1V zener shunt -> 5V logic rail for CD4053 selects")
C("C27", "10uF", "5V logic rail bulk bypass")
C("C28", "100nF", "5V logic rail HF bypass")
P12.append("R29.1")   # +12V feed to the 5V-logic series R
net("V5LOGIC", ["R29.2", "D7.3", "C27.1", "C28.1",
                "R128_1sc.1", "R128_1wf.1", "R128_2sc.1", "R128_2wf.1",
                "R128_3sc.1", "R128_3wf.1"],
    "5V logic rail (zener-clamped) -> CD4053 select pull-ups")
GND.append("D7.1"); GND.append("C27.2"); GND.append("C28.2")

# wet summer / MIX / output (per channel)
for ci, c in enumerate(CH):
    R(f"R26_{c}1", "33k", f"wet summer in BP1 ({c})")
    R(f"R26_{c}2", "33k", f"wet summer in BP2 ({c})")
    R(f"R26_{c}3", "33k", f"wet summer in BP3 ({c})")
    R(f"R26_{c}f", "33k", f"wet summer feedback ({c})")
    R(f"R27_{c}", "100k", f"MIX dry input R_dry ({c})")
    R(f"R28_{c}", "100k", f"MIX feedback R_mix_f ({c})")
    sumref = "U46" if c == "L" else "U47"
    # wet summer: half A (unit1) inverting sum of 3 distortion taps
    net(f"BP_WETVG_{c}", [f"{sumref}.2", f"R26_{c}1.2", f"R26_{c}2.2", f"R26_{c}3.2", f"R26_{c}f.1"],
        f"wet summer virtual ground ({c})")
    net(f"BP_WETSUM_{c}", [f"{sumref}.1", f"R26_{c}f.2", "U48.3" if c == "L" else "U48.5"],
        f"wet summer out (-Sigma wet) -> U48 buffer +in ({c})")
    GND.append(f"{sumref}.3")
    # U48 unity buffer drives the off-board MIX pot top
    if c == "L":
        net("BP_WETPOS_L", ["U48.1", "U48.2"], "buffered wet -> MIX pot top L (boundary)")
    else:
        net("BP_WETPOS_R", ["U48.7", "U48.6"], "buffered wet -> MIX pot top R (boundary)")
    boundary(f"BP_WETPOS_{c}", f"-> MIX-level pot top ({c}); Phase-3R blend element")
    # MIX amp: half B (unit2) inverting summer — dry (R27) + wet (off-board pot, BP_MIX_CV)
    net(f"BP_MIX_CV_{c}", [f"{sumref}.6", f"R27_{c}.2", f"R28_{c}.1"],
        f"MIX virtual ground = wet return from MIX-pot wiper ({c}); R_wet is the off-board pot (boundary)")
    boundary(f"BP_MIX_CV_{c}", f"<- MIX-pot wiper (scaled wet) ({c}); Phase-3R blend element")
    GND.append(f"{sumref}.5")
    # MIX amp output IS the block output (inverting; downstream HP SUM_AMP re-inverts).
    out_pins = [f"{sumref}.7", f"R28_{c}.2"]
    if c == "L":
        out_pins.append("R17_in.1")    # also feeds the reserved restore inverter (Phase-3R)
    net(f"BP_OUT_{c}", out_pins, f"BP output ({c}) -> block-7 HP (boundary)")
    boundary(f"BP_OUT_{c}", f"-> block-7 (HP input, {c})")

# reserved output polarity-restore inverter (U27-B) — input from L MIX out
net("BP_POLVG_L", ["U27.6", "R17_in.2", "R17_fb.1"], "reserved restore virtual ground (Phase-3R)")
net("BP_POLRESTORE_L", ["U27.7", "R17_fb.2"],
    "reserved output polarity-restore inverter out (Phase-3R; unused: HP inverts downstream)")
GND.append("U27.5")

# dry source = LP1 output (BP1/BP2 input too)
net("LP1_OUT_L", ["R13_1L.1", "R13_2L.1", "R27_L.1"], "<- block-5 LP1 out L (BP1/BP2 input + MIX dry)")
net("LP1_OUT_R", ["R13_1R.1", "R13_2R.1", "R27_R.1"], "<- block-5 LP1 out R (BP1/BP2 input + MIX dry)")
boundary("LP1_OUT_L", "<- block-5 (LP1 out L)")
boundary("LP1_OUT_R", "<- block-5 (LP1 out R)")
# BP3 input = ALT path (post gain+VCA) when patched, else LP1 out; selection upstream
net("BP3IN_L", ["R13_3L.1"], "<- BP3 input L (ALT-or-LP1; selection+ALT-VCA upstream, see block-1 ALT_OUT)")
net("BP3IN_R", ["R13_3R.1"], "<- BP3 input R")
boundary("BP3IN_L", "<- BP3 input L (ALT/LP1; upstream Phase-3R)")
boundary("BP3IN_R", "<- BP3 input R (ALT/LP1; upstream Phase-3R)")
# BP3 distorted tap -> block-B buffers; buffered return -> J27/J28
boundary("BP3_TAP_L", "-> block-B (BP3 group tap L)")
boundary("BP3_TAP_R", "-> block-B (BP3 group tap R)")
# BP3 output jacks (panel) — fed by block-B BP3 buffers (boundary in)
part("J27", "{ sym: jack, part: PJ301M-12, value: BP3_L_OUT }", "BP3 L output jack")
part("J28", "{ sym: jack, part: PJ301M-12, value: BP3_R_OUT }", "BP3 R output jack")
net("BP3_L_OUT", ["J27.1"], "<- block-B (buffered BP3 L) -> J27 tip (boundary)")
net("BP3_R_OUT", ["J28.1"], "<- block-B (buffered BP3 R) -> J28 tip (boundary)")
boundary("BP3_L_OUT", "<- block-B (buffered BP3 L to panel jack J27)")
boundary("BP3_R_OUT", "<- block-B (buffered BP3 R to panel jack J28)")
GND.append("J27.2"); GND.append("J28.2")
ncs.append("J27.3"); ncs.append("J28.3")   # output jacks: switch lug unused

# ── per group / per channel: SVF + expo + Q + distortion + mux ────────────────
for g in (1, 2, 3):
    intL, intR = INT[g]
    sumL, sumR = SUM[g]
    q = QVCA[g]
    expoL, expoR = EXPO[g]
    muxA, muxB = MUXA[g], MUXB[g]
    capref, capval = CAPREF[g], CAPVAL[g]

    # --- per-group SVF resistors / caps (per channel) ---
    for ci, c in enumerate(CH):
        intr = (intL, intR)[ci]
        sumr = (sumL, sumR)[ci]
        R(f"R13_{g}{c}", "100k", f"BP{g} SUM_AMP R_in ({c})")
        R(f"R14_{g}{c}", "100k", f"BP{g} SUM_AMP R_FB (v2/LP damping feedback) ({c})")
        R(f"R15_{g}{c}", "100k", f"BP{g} SUM_AMP R_f (self feedback) ({c})")
        R(f"R12_{g}{c}a", "1k", f"BP{g} OTA1 In- linearizing R ({c})")
        R(f"R12_{g}{c}b", "1k", f"BP{g} OTA2 In- linearizing R ({c})")
        R(f"R123_{g}{c}v1", "10k", f"BP{g} v1 buffer emitter pulldown ({c})")
        R(f"R123_{g}{c}v2", "10k", f"BP{g} v2 buffer emitter pulldown ({c})")
        C(f"{capref}_{c}v1", capval, f"BP{g} integrator cap C1 (v1) ({c})")
        C(f"{capref}_{c}v2", capval, f"BP{g} integrator cap C2 (v2) ({c})")
        C(f"C108_{g}{c}", "10nF", f"BP{g} integrator-OTA Iabc bypass ({c})")
        C(f"C107_{g}{c}", "10nF", f"BP{g} Q-cell Iabc bypass ({c})")
        R(f"R116_{g}{c}", "1M", f"BP{g} R_Iabc_Q: V_ires -> Q OTA Iabc ({c})")

        qIn_p, qIn_n, qOut, qIabc = (("3", "4", "5", "1") if c == "L" else ("14", "13", "12", "16"))
        # SUM_AMP virtual ground (+ Q-cell In-/Out inject here, like shared-q)
        net(f"BP{g}_SUMINV_{c}", [f"{sumr}.2", f"R13_{g}{c}.2", f"R14_{g}{c}.2", f"R15_{g}{c}.1",
                                  f"{q}.{qIn_n}", f"{q}.{qOut}"],
            f"BP{g} SUM_AMP virtual ground (Q damping injected) ({c})")
        GND.append(f"{sumr}.3")    # SUM_AMP +in
        # SUM_AMP out = HP node -> OTA1 In+
        net(f"BP{g}_HP_{c}", [f"{sumr}.1", f"R15_{g}{c}.2", f"{intr}.3"],
            f"BP{g} SUM_AMP out (HP) -> OTA1 In+ ({c})")
        # OTA1: out->C1+BufIn (v1 cap node)
        net(f"BP{g}_V1CAP_{c}", [f"{intr}.5", f"{intr}.7", f"{capref}_{c}v1.1"],
            f"BP{g} OTA1 out -> C1 + Darlington BufIn ({c})")
        GND.append(f"{capref}_{c}v1.2")
        # v1 (BP) = BufOut_A -> OTA2 In+ + pulldown + Q In+ + BP output buffer +in
        net(f"BP{g}_V1_{c}", [f"{intr}.8", f"{intr}.14", f"R123_{g}{c}v1.1",
                              f"{q}.{qIn_p}", f"{sumr}.5"],
            f"BP{g} v1 (BP tap) -> OTA2 In+ + Q In+ + output buffer +in ({c})")
        N12.append(f"R123_{g}{c}v1.2")
        # OTA2: out->C2+BufIn (v2 cap node)
        net(f"BP{g}_V2CAP_{c}", [f"{intr}.12", f"{intr}.10", f"{capref}_{c}v2.1"],
            f"BP{g} OTA2 out -> C2 + Darlington BufIn ({c})")
        GND.append(f"{capref}_{c}v2.2")
        # v2 (LP) = BufOut_B -> R_FB (damping back to SUM_AMP) + pulldown
        net(f"BP{g}_V2_{c}", [f"{intr}.9", f"R14_{g}{c}.1", f"R123_{g}{c}v2.1"],
            f"BP{g} v2 (LP state) -> R_FB + pulldown ({c})")
        N12.append(f"R123_{g}{c}v2.2")
        # BP output buffer (SUM_AMP half B): unity follower on v1 (+in B = v1, set above) -> distortion
        # The output node (= distortion input) gets its cell loads + anti-RF caps appended later.
        net(f"BP{g}_BPBUF_{c}", [f"{sumr}.7", f"{sumr}.6"],
            f"BP{g} v1 buffer out (unity) -> distortion input ({c})")
        # OTA linearizing R to GND
        net(f"BP{g}_LINA_{c}", [f"{intr}.4", f"R12_{g}{c}a.1"], f"BP{g} OTA1 In- linearizing ({c})")
        net(f"BP{g}_LINB_{c}", [f"{intr}.13", f"R12_{g}{c}b.1"], f"BP{g} OTA2 In- linearizing ({c})")
        GND.append(f"R12_{g}{c}a.2"); GND.append(f"R12_{g}{c}b.2")
        # Q-cell Iabc + bypass
        net(f"BP{g}_QIABC_{c}", [f"{q}.{qIabc}", f"C107_{g}{c}.1", f"R116_{g}{c}.2"],
            f"BP{g} Q-cell Iabc <- V_ires/R_Iabc + bypass ({c})")
        GND.append(f"C107_{g}{c}.2")

    # Q-VCA OTA unused pins (buffers + diode-bias)
    for p in ("2", "7", "8", "9", "10", "15"):
        ncs.append(f"{q}.{p}")

    # --- expo converters (L = U28-30, R = U70-72) ---
    R(f"R124_{g}", "1M", f"BP{g} L expo R_IREF_A")
    R(f"R125_{g}", "47k", f"BP{g} L expo R_VOCT")
    R(f"R126_{g}", "1k", f"BP{g} L expo R_E")
    R(f"R120_{g}", "1M", f"BP{g} R expo R_IREF_A")
    R(f"R121_{g}", "47k", f"BP{g} R expo R_VOCT")
    R(f"R122_{g}", "1k", f"BP{g} R expo R_E")
    R(f"R127_{g}L", "100k", f"BP{g} +V_tilt summer into L expo base")
    R(f"R127_{g}R", "100k", f"BP{g} -V_tilt summer into R expo base")
    C(f"C109_{g}L", "100nF", f"BP{g} L expo I_ref bypass")
    C(f"C109_{g}R", "100nF", f"BP{g} R expo I_ref bypass")
    TRIM(LREFTR[g], "500k", f"BP{g}_FREF_L", f"BP{g} L expo f_ref trim (rheostat)")
    TRIM(LVOCTTR[g], "20k", f"BP{g}_1VOCT_L", f"BP{g} L expo 1V/oct trim")
    part(f"RV24_{g}", "{ sym: trimpot, part: \"Bourns 3224W\", value: BP%d_FREF_R }" % g,
         f"BP{g} R expo f_ref trim (rheostat)")
    part(f"RV25_{g}", "{ sym: trimpot, part: \"Bourns 3224W\", value: BP%d_1VOCT_R }" % g,
         f"BP{g} R expo 1V/oct trim")

    # V/oct CV in (boundary) to both expos
    net(f"BP{g}_VCTRL", [f"R125_{g}.1", f"R121_{g}.1"], f"<- control/mod: BP{g} V/oct freq CV (boundary)")
    boundary(f"BP{g}_VCTRL", f"<- control/mod: BP{g} V/oct (offset+freq) CV")
    # L expo
    net(f"BP{g}_IREF_TR_L", [f"R124_{g}.2", f"{LREFTR[g]}.1", f"{LREFTR[g]}.2"], f"BP{g} L I_ref rheostat")
    net(f"BP{g}_IREF_L", [f"{expoL}.14", f"{expoL}.13", f"{LREFTR[g]}.3", f"C109_{g}L.1"],
        f"BP{g} L Q2 collector+base (diode-conn ref) + bypass")
    P12.append(f"R124_{g}.1"); GND.append(f"C109_{g}L.2")
    net(f"BP{g}_VOCT_TR_L", [f"R125_{g}.2", f"{LVOCTTR[g]}.1", f"{LVOCTTR[g]}.2"], f"BP{g} L V/oct rheostat")
    net(f"BP{g}_EXPO_BASE_L", [f"{expoL}.2", f"{LVOCTTR[g]}.3", f"R127_{g}L.2"],
        f"BP{g} L Q1 base: V/oct + +V_tilt")
    net(f"BP{g}_IABC_L", [f"{expoL}.1", f"{intL}.1", f"{intL}.16", f"C108_{g}L.1"],
        f"BP{g} L Iabc -> OTA1+OTA2 + bypass")
    GND.append(f"C108_{g}L.2")
    net(f"BP{g}_EXPO_EMIT_L", [f"{expoL}.3", f"{expoL}.12", f"R126_{g}.1"], f"BP{g} L Q1+Q2 emitters -> R_E")
    N12.append(f"R126_{g}.2")
    # R expo
    net(f"BP{g}_IREF_TR_R", [f"R120_{g}.2", f"RV24_{g}.1", f"RV24_{g}.2"], f"BP{g} R I_ref rheostat")
    net(f"BP{g}_IREF_R", [f"{expoR}.14", f"{expoR}.13", f"RV24_{g}.3", f"C109_{g}R.1"],
        f"BP{g} R diode-conn ref + bypass")
    P12.append(f"R120_{g}.1"); GND.append(f"C109_{g}R.2")
    net(f"BP{g}_VOCT_TR_R", [f"R121_{g}.2", f"RV25_{g}.1", f"RV25_{g}.2"], f"BP{g} R V/oct rheostat")
    net(f"BP{g}_EXPO_BASE_R", [f"{expoR}.2", f"RV25_{g}.3", f"R127_{g}R.2"],
        f"BP{g} R Q1 base: V/oct + -V_tilt")
    net(f"BP{g}_IABC_R", [f"{expoR}.1", f"{intR}.1", f"{intR}.16", f"C108_{g}R.1"],
        f"BP{g} R Iabc -> OTA1+OTA2 + bypass")
    GND.append(f"C108_{g}R.2")
    net(f"BP{g}_EXPO_EMIT_R", [f"{expoR}.3", f"{expoR}.12", f"R122_{g}.1"], f"BP{g} R Q1+Q2 emitters -> R_E")
    N12.append(f"R122_{g}.2")

    # --- Q control (IRES_AMP) ---
    R(f"R117_{g}", "100k", f"BP{g} Q IRES_AMP R_QBIAS")
    R(f"R118_{g}", "100k", f"BP{g} Q IRES_AMP R_QINV (FOCUS CV)")
    R(f"R119_{g}", "100k", f"BP{g} Q IRES_AMP R_f")
    TRIM(QTRIM[g], "", f"BP{g}_QMAX", f"BP{g} Q_max V_bias trim")
    D1148(f"D13_{g}", f"BP{g} V_ires>=0 clamp (anode GND, cathode V_ires)")
    iref, in_n, out_p, in_p = IRES[g]
    net(f"BP{g}_VBIAS", [f"{QTRIM[g]}.2", f"R117_{g}.1"], f"BP{g} Q V_bias (trim wiper)")
    P12.append(f"{QTRIM[g]}.3"); GND.append(f"{QTRIM[g]}.1")
    net(f"BP{g}_FOCUS_CV", [f"R118_{g}.1"], f"<- control/mod: BP{g} FOCUS (Q) CV (boundary)")
    boundary(f"BP{g}_FOCUS_CV", f"<- control/mod: BP{g} FOCUS (Q) CV")
    net(f"BP{g}_IRES_SUM", [f"{iref}.{in_n}", f"R117_{g}.2", f"R118_{g}.2", f"R119_{g}.1"],
        f"BP{g} IRES_AMP virtual ground")
    net(f"BP{g}_VIRES", [f"{iref}.{out_p}", f"R119_{g}.2", f"D13_{g}.K", f"R116_{g}L.1", f"R116_{g}R.1"],
        f"BP{g} V_ires (>=0 by D13) -> R_Iabc L+R")
    GND.append(f"D13_{g}.A"); GND.append(f"{iref}.{in_p}")

    # --- distortion cells (per channel) ---
    for ci, c in enumerate(CH):
        schc = SCHC[g][ci]
        wf = WF[g][ci]
        bp = f"BP{g}_BPBUF_{c}"
        R(f"R18_{g}{c}", "10k", f"BP{g} SC R_in ({c})")
        R(f"R19_{g}{c}", "10k", f"BP{g} SC R_fb_fixed ({c})")
        R(f"R20_{g}{c}", "10k", f"BP{g} HC R_in ({c})")
        R(f"R21_{g}{c}", "10k", f"BP{g} HC R_fb_fixed ({c})")
        R(f"R22_{g}{c}", "10k", f"BP{g} WF R_in ({c})")
        R(f"R23_{g}{c}", "10k", f"BP{g} WF R_fb_fixed ({c})")
        R(f"R24_{g}{c}", "10k", f"BP{g} WF R_clamp ({c})")
        R(f"R25_{g}{c}", "10k", f"BP{g} WF folder R_g ({c})")
        R(f"R_f_wf_{g}{c}", "10k", f"BP{g} WF folder R_f ({c})")
        C(f"C_WF_{g}{c}a", "47pF", f"BP{g} anti-RF cap at distortion input ({c}) [Phase-3R: was drive-pot wiper cap]")
        C(f"C_WF_{g}{c}b", "47pF", f"BP{g} anti-RF cap at WF input ({c}) [Phase-3R: was drive-pot wiper cap]")
        for d in ("a", "b", "c", "d"):
            D1148(f"D4_{g}{c}{d}", f"BP{g} SC soft-clip diode ({c})")
            D1148(f"D6_{g}{c}{d}", f"BP{g} WF clamp diode ({c})")
        DZ(f"D5_{g}{c}a", f"BP{g} HC zener clamp ({c})")
        DZ(f"D5_{g}{c}b", f"BP{g} HC zener clamp ({c})")

        # SC cell (half A): inverting gain + antiparallel diode pairs across fb
        net(f"BP{g}_SCVG_{c}", [f"{schc}.2", f"R18_{g}{c}.2", f"R19_{g}{c}.1",
                                f"D4_{g}{c}b.K", f"D4_{g}{c}c.A"], f"BP{g} SC virtual ground ({c})")
        net(f"BP{g}_SCOUT_{c}", [f"{schc}.1", f"R19_{g}{c}.2", f"D4_{g}{c}a.A", f"D4_{g}{c}d.K"],
            f"BP{g} SC out ({c})")
        net(f"BP{g}_SCM1_{c}", [f"D4_{g}{c}a.K", f"D4_{g}{c}b.A"], f"BP{g} SC diode mid (fwd pair) ({c})")
        net(f"BP{g}_SCM2_{c}", [f"D4_{g}{c}c.K", f"D4_{g}{c}d.A"], f"BP{g} SC diode mid (rev pair) ({c})")
        GND.append(f"{schc}.3")   # SC +in
        # HC cell (half B): inverting gain + back-to-back zener clamp to GND
        net(f"BP{g}_HCVG_{c}", [f"{schc}.6", f"R20_{g}{c}.2", f"R21_{g}{c}.1"], f"BP{g} HC virtual ground ({c})")
        net(f"BP{g}_HCOUT_{c}", [f"{schc}.7", f"R21_{g}{c}.2", f"D5_{g}{c}a.3",
                                 f"{muxB}." + ("12" if c == "L" else "2")],
            f"BP{g} HC out -> mux B in0 ({c})")
        net(f"BP{g}_HCZMID_{c}", [f"D5_{g}{c}a.1", f"D5_{g}{c}b.1"], f"BP{g} HC zener mid (anodes) ({c})")
        GND.append(f"D5_{g}{c}b.3"); GND.append(f"{schc}.5")   # zener to GND, HC +in
        # WF pre-gain (half A) + passive clamp + folder (half B)
        net(f"BP{g}_WFVG_{c}", [f"{wf}.2", f"R22_{g}{c}.2", f"R23_{g}{c}.1"], f"BP{g} WF pre-gain virtual ground ({c})")
        net(f"BP{g}_VFOLDIN_{c}", [f"{wf}.1", f"R23_{g}{c}.2", f"R24_{g}{c}.1", f"R25_{g}{c}.1"],
            f"BP{g} WF pre-gain out (V_fold_in) ({c})")
        GND.append(f"{wf}.3")   # WF pre-gain +in
        net(f"BP{g}_WFCLAMP_{c}", [f"R24_{g}{c}.2", f"D6_{g}{c}a.A", f"D6_{g}{c}d.K", f"{wf}.5"],
            f"BP{g} WF V_clamp -> folder +in ({c})")
        net(f"BP{g}_WFCM1_{c}", [f"D6_{g}{c}a.K", f"D6_{g}{c}b.A"], f"BP{g} WF clamp mid (fwd) ({c})")
        GND.append(f"D6_{g}{c}b.K"); GND.append(f"D6_{g}{c}c.A")
        net(f"BP{g}_WFCM2_{c}", [f"D6_{g}{c}c.K", f"D6_{g}{c}d.A"], f"BP{g} WF clamp mid (rev) ({c})")
        net(f"BP{g}_WFFVG_{c}", [f"{wf}.6", f"R25_{g}{c}.2", f"R_f_wf_{g}{c}.1"], f"BP{g} WF folder virtual ground ({c})")
        net(f"BP{g}_WFOUT_{c}", [f"{wf}.7", f"R_f_wf_{g}{c}.2", f"{muxB}." + ("13" if c == "L" else "1")],
            f"BP{g} WF out -> mux B in1 ({c})")
        # distortion input node = the v1 buffer output: feeds SC/HC/WF input Rs + 2 anti-RF caps
        for nm, pl, cm in nets:
            if nm == bp:
                pl.extend([f"R18_{g}{c}.1", f"R20_{g}{c}.1", f"R22_{g}{c}.1",
                           f"C_WF_{g}{c}a.1", f"C_WF_{g}{c}b.1"])
                break
        GND.append(f"C_WF_{g}{c}a.2"); GND.append(f"C_WF_{g}{c}b.2")

    # --- distortion mux (2 CD4053 per group) + mode pull-ups ---
    R(f"R128_{g}sc", "100k", f"BP{g} mode-encoder pull-up (SEL_SC)")
    R(f"R128_{g}wf", "100k", f"BP{g} mode-encoder pull-up (SEL_WF)")
    # muxB: MID = SEL_WF ? WF : HC   (X=L, Y=R)
    net(f"BP{g}_SEL_WF", [f"{muxB}.11", f"{muxB}.10", f"R128_{g}wf.2"],
        f"BP{g} mux-B selects (HC<->WF); A+B tied; pulled to 5V (boundary to DW5 SW{3+g})")
    boundary(f"BP{g}_SEL_WF", f"<- DW5 SW{3+g} mode bit (WF select); Phase-3R encoding")
    net(f"BP{g}_MID_L", [f"{muxB}.14", f"{muxA}.12"], f"BP{g} mux-B X out (MID L) -> mux-A X in0")
    net(f"BP{g}_MID_R", [f"{muxB}.15", f"{muxA}.2"], f"BP{g} mux-B Y out (MID R) -> mux-A Y in0")
    # muxA: DIST = SEL_SC ? SC : MID
    net(f"BP{g}_SEL_SC", [f"{muxA}.11", f"{muxA}.10", f"R128_{g}sc.2"],
        f"BP{g} mux-A selects (SC<->MID); A+B tied; pulled to 5V (boundary to DW5 SW{3+g})")
    boundary(f"BP{g}_SEL_SC", f"<- DW5 SW{3+g} mode bit (SC select); Phase-3R encoding")
    # SC outs into mux-A in1 (X1=13 for L, Y1=1 for R)
    for ci, c in enumerate(CH):
        x1 = "13" if c == "L" else "1"
        for nm, pl, cm in nets:
            if nm == f"BP{g}_SCOUT_{c}":
                pl.append(f"{muxA}.{x1}")
                break
    # DIST out (mux-A common): X=14 (L), Y=15 (R) -> wet summer; group 3 also = BP3 tap
    for ci, c in enumerate(CH):
        com = "14" if c == "L" else "15"
        if g == 3:
            net(f"BP3_TAP_{c}", [f"{muxA}.{com}", f"R26_{c}3.1"],
                f"BP3 distorted tap ({c}) -> wet summer + block-B (boundary)")
        else:
            net(f"BP{g}_DIST_{c}", [f"{muxA}.{com}", f"R26_{c}{g}.1"],
                f"BP{g} distortion out ({c}) -> wet summer")
    # mux unused: channel Z (Z=4, Z0=5, Z1=3) + C select (9); INH(6)=GND (in supply())
    for mux in (muxA, muxB):
        for p in ("3", "4", "5", "9"):
            ncs.append(f"{mux}.{p}")

# U74-B spare half (unit2): grounded unity buffer
net("U74_SPARE", ["U74.7", "U74.6"], "U74-B spare half tied as unity follower")
GND.append("U74.5")

# THAT340 unused PNP pins (5,6,7,8,9,10) for all 6 expos
for g in (1, 2, 3):
    for ex in EXPO[g]:
        for p in ("5", "6", "7", "8", "9", "10"):
            ncs.append(f"{ex}.{p}")
# LM13700 integrator diode-bias pins (2,15) unused
for g in (1, 2, 3):
    for it in INT[g]:
        ncs.append(f"{it}.2"); ncs.append(f"{it}.15")

# rails
net("+12V", P12, "op-amp/OTA V+, CD4053 VDD, expo +12 bypass, I_ref/Q_max tops")
net("-12V", N12, "op-amp/OTA V-, CD4053 VEE, THAT340 SUB, R_E/pulldown returns")
net("GND", GND, "virtual-ground +ins, cap returns, OTA linearizing R, clamp anodes")


# ── emit YAML ─────────────────────────────────────────────────────────────────
HEADER = '''# POGO Block 6 — Triple Bandpass + Distortion (3x 2-pole OTA-C SVF + SC/HC/WF) — the last block
#
# GENERATED by tools/gen_block6.py (3-group repetition, like block-3).
# Source of truth, transcribed from:
#   specs/components.yaml  (block-6 rows, 119; refs authoritative; grouped qty -> suffix instances)
#   plugin/src/dsp/BandpassSVF.hpp + Distortion.hpp + Pogo.cpp lines 401-490 (GROUND TRUTH signal flow)
#   specs/block-6/spec.md (STALE §2/§3/§4), specs/aux/aux-ota-c-svf / aux-q-control / aux-expo / aux-distortion
#   datasheet-cited pinouts: components/symbols.yaml archetypes ota / expo / cd4053 (loaded via tools/symbols.py)
#
# Locked decisions (Option B DSP-faithful Q-VCAs, per-channel expo, +3 CD4053 stereo mux, Q control)
# per SCHEMATIC-GEN-PLAN.md "block-6 readiness". Refdes suffixes: L/R for stereo pairs,
# group digit for per-group parts, letters for series diode/cap repeats.
#
# SIGNAL FLOW (from the plugin, ground truth):
#   LP1_OUT -> BP1,BP2 ;  BP3IN (ALT-or-LP1) -> BP3.  Each group: 2-pole Simper SVF, v1 (BP) tap.
#   v1 -> distortion (SC/HC/WF, one selected by the per-group CD4053 pair) -> distTap[g].
#   wet = sum(distTap) ;  BP_OUT = dry(LP1)*BYPASS + wet*WET  (two scalers, additive — NOT a crossfade).
#   BP3 tap = distTap[2] (post-distortion, pre-mix) -> block-B BP3 buffers -> J27/J28.
#
# PROTOTYPE / Phase-3R FLAGS (under-specified in the STALE specs; wired faithfully, control = boundary CV):
#  1. DRIVE -> variable gain (one per-group knob -> stereo gain): no in-block variable-gain element
#     exists (RV33/36/39 are control-board knobs; no VCA/JFET in the block-6 BOM). The 6 distortion
#     cells are therefore wired at their FIXED minimum gain (R_fb fixed; ~-1x). SC/WF still clip above
#     their ±1.4V diode threshold and HC above ±5.8V at unity, so the cells are functional; the
#     per-band DRIVE depth is a Phase-3R variable-gain element fed by BP{g}_DIST CV (not wired here).
#     The C_WF (47pF) caps — spec'd as drive-pot-wiper bypass — are relocated to the distortion input
#     nodes as anti-RF caps (their pole/intent is preserved); revisit when the drive element is designed.
#  2. DW5 ON-ON-ON -> 2-bit make pattern: SW4-6 (control board) encode mode into 2 bits per group.
#     The two select lines BP{g}_SEL_SC / BP{g}_SEL_WF are pulled to the 5V logic rail (R128) and tie
#     each CD4053's A+B selects together; they leave as boundary nets to the DW5. The exact lug->bit
#     make pattern (which position grounds which bit) is Phase-3R. NOTE: 5V logic high vs VDD=+12V is
#     marginal per the CD4053B datasheet (VIH ~ 0.7*VDD); a level shift or VDD=+5V may be needed —
#     prototype-verify. CD4053 analog rails kept at ±12V here for full ±5V audio headroom.
#  3. BP_MIX blend element: the plugin uses TWO independent scalers (BYPASS, WET); the BOM/spec model it
#     as one MIX pot (dry unity + wet*mix). Wired faithfully as: wet summer (U46/47-A) -> U48 buffer ->
#     off-board MIX pot (BP_WETPOS out) -> wiper returns as BP_MIX_CV into the MIX amp (U46/47-B) virtual
#     ground (the pot IS R_wet) + dry via R27. Whether the element is a crossfade or a 2-scaler network,
#     and a separate BYPASS path, are Phase-3R. The MIX amps invert; BP_OUT is taken directly from them
#     (L/R symmetric; downstream HP SUM_AMP re-inverts). U27-B + R17 (the BOM's single "output
#     polarity-restore inverter") is therefore redundant in this path and is wired as a RESERVED Phase-3R
#     inverter off the L MIX output (a matching R twin + an explicit non-inverting output stage are a
#     Phase-3R add if a non-inverted block-6 output is ever required).

block: block-6
board: audio
title: POGO Block 6 - Triple Bandpass + Distortion
'''


def fmt_pinlist(pins):
    s = "[" + ", ".join(pins) + "]"
    return s


def main():
    lines = [HEADER, "", "parts:"]
    for ref, spec, cm in parts:
        line = f"  {ref}: {spec}"
        if cm:
            line += f"   # {cm}"
        lines.append(line)
    lines.append("")
    lines.append("nets:")
    for name, pins, cm in nets:
        key = f'"{name}"' if name in ("+12V", "-12V") else name
        line = f"  {key}: {fmt_pinlist(pins)}"
        if cm:
            line += f"   # {cm}"
        lines.append(line)
    lines.append("")
    lines.append("no_connect:")
    for pt in ncs:
        lines.append(f"  - {pt}")
    lines.append("")
    lines.append("boundary:")
    seen = set()
    for name, cm in bnd:
        if name in seen:
            continue
        seen.add(name)
        line = f"  - {name}"
        if cm:
            line += f"   # {cm}"
        lines.append(line)
    OUT.write_text("\n".join(lines) + "\n")
    print(f"Wrote {OUT}  [{len(parts)} parts, {len(nets)} nets, "
          f"{len(ncs)} no_connect, {len(seen)} boundary]")


if __name__ == "__main__":
    main()
