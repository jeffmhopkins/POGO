#!/usr/bin/env python3
"""
POGO KiCad 7 schematic emit primitives — generic, symbol-agnostic.

Symbol definitions (the `(symbol "lib_id" …)` lib_symbols bodies and their
pin connection-point geometry) are NO LONGER here. They are authored data in
`components/symbols.yaml`, loaded and emitted by `tools/symbols.py`. This module
keeps only the board-independent s-expr emitters that `generate_schematic.py`
calls: the schematic skeleton, instance placement, and net labels.

Pin coordinate convention
─────────────────────────
A pin's connection point is its `(at x y)` coordinate (NOT the stub end);
`symbols.pin_points()` returns those rotated into canvas coords so a
`connect_pin()` global label lands exactly on the pin.
"""

import uuid

OUT = []


def reset():
    """Clear the output buffer. Call before build if reusing in one process."""
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
