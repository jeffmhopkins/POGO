# SPICE deck authoring guide (POGO behavioral checks)

How to write `specs/<block>/sim/*.cir` decks + `*.expect.yaml` assertions that the
`tools/build_spice.py --check` gate runs. Read this fully before authoring decks.

## The core idea — what makes a check *meaningful*

A check is only useful if it can **fail when something is wrong**. The design that gives that:

- **The deck (`.cir`) encodes the NETLIST's component values** (R/C values, topology) from
  `specs/<block>/<block>.nets.yaml`.
- **The assertion (`.expect.yaml`) encodes the SPEC's / plugin's intended MATH** (the target law:
  f_ref, gain, threshold, dB, mV/oct …) from `specs/<block>/spec.md` and the cited `plugin/src/dsp/*`.
- The runner computes the deck's result and compares to the assertion. **So a divergence between the
  netlist's values and the spec's math FAILS the gate.** That is the whole point: it proves "the
  circuit math referenced in the schematic is valid", not just self-consistent.

Corollary: **never copy the expected number from the deck's own output.** Derive `expect:` from the
spec formula independently; let the deck's netlist values land on it (within tolerance) or fail.

Each assertion SHOULD cite its `plugin_ref` (the DSP file/line or spec formula it pins).

### `netlist_bind` — REQUIRED for any deck that pins a netlist component value

A deck hand-transcribes netlist values as literals (e.g. `Rfix nfix pinf 100k`). On its own that makes
the gate a *deck-literal-vs-spec* check, NOT *netlist-vs-spec* — if the netlist silently drifts
(R104 100k→1M) the deck literal still passes. **`netlist_bind` closes that gap:** declare which netlist
ref each load-bearing literal must equal, and the runner reads `specs/<block>/<block>.nets.yaml`,
resolves the ref's value, and **FAILS if the deck's value ≠ the netlist's value.**

```yaml
netlist_bind:                 # label: "REF=value"  (value uses netlist notation: 100k, 47nF, 49k9, 1M)
  R_Iabc_L: "R104=100k"
  C_int:    "C29A=47nF"
```

Rule: **any value your deck uses to pin a circuit fact MUST appear in `netlist_bind`** keyed to its
netlist ref. (Value parser handles `100k`, `47nF`, `1M`, `1k`, and R-notation `49k9`/`4k7`.) Decks
whose result is genuinely value-independent (e.g. a *ratio* check where the constant cancels — like
`voct_octave`'s 2^ΔV octave ratios) need no bind, but say so in the description.

## ngspice mechanics (hard-won — follow these or decks silently misbehave)

1. **First line is a TITLE/comment.** ngspice eats line 1. Always start with a `* comment` line so no
   real card is lost.
2. **Node names: start with a letter.** Nodes like `0a`, `5b` (leading digit) misbehave — `v(0a)`
   reads 0. Use `na`, `nmid`, `bf`. Ground is `0`.
3. **Emit measurements with `print <name>` (or `meas`).** The runner parses stdout lines of the form
   `name = value`. `meas ac f0 when vdb(out)=-3.01` also prints `f0 = …` and is parsed.
4. **Names are matched case-insensitively** (ngspice lowercases vector names in output), so
   `print mv_Mid` in the deck matches `name: mv_mid` in the yaml. Keep them obviously corresponding.
5. **DO NOT use `alter`+`op` loops then `let`/`print`.** The `let` result after an `alter`-driven
   re-`op` frequently comes back zero/empty (scope quirk). **Instead instantiate the circuit in
   PARALLEL — one independent copy per test condition** (e.g. RV at 0 / 5k / 10k as three sub-circuits)
   and `print` each named node. This is the single most important rule; every working POGO deck uses it.
6. **`.control` block** wraps the run:
   ```
   .control
     op            ; or: ac dec 50 10 100k
     let x = v(nmid)*1000
     print x
   .endc
   ```
   `let` defined directly from `v(node)` after a single `op`/`ac` (no preceding `alter`) is reliable.
7. **Ideal models are fine and preferred** for behavioral checks — the goal is the *math*, not device
   modelling. Conventions:
   - **Ideal op-amp:** `Eop out 0 in+ in- 1e6` (high-gain VCVS) with the real feedback Rs → gives the
     real closed-loop gain/virtual-ground.
   - **Unity follower:** `Ebuf out 0 in 0 1`.
   - **Behavioral clamp / nonlinearity:** B-source, e.g.
     `Bc out 0 V = (V(in)>Hi)?Hi:((V(in)<Lo)?Lo:V(in))`.
   - **gm-C integrator (OTA):** `Gint 0 out in out {gm}` + `Cint out 0 {C}` → 1st-order LP, corner
     `gm/(2πC)`; read with `meas ac f0 when vdb(out)=-3.01`.
   - **A pin at a fixed potential** (e.g. LM13700 Iabc pin ≈ −10.8 V): a DC source; read current with
     `i(Vsrc)`.
   - State a one-line justification in a comment for each ideal model (what real device it stands in
     for, and why the simplification preserves the law under test).
8. **`.param`** for shared constants; reference as `{gm}`. Keep the netlist's real values visible.
9. Keep decks **self-contained and fast** (`op` or a bounded `ac`/`tran`; < a few seconds). No external
   models, no PDK.

## `.expect.yaml` schema

```yaml
deck: <name>.cir
description: <what this validates, one line>
plugin_ref: "plugin/src/dsp/Foo.hpp:NN  — <the law>"   # or spec.md §/formula
measurements:
  - name: f0_hz            # MUST match a `print f0_hz` (case-insensitive) in the deck
    expect: 632.0          # DERIVED FROM THE SPEC, not copied from deck output
    tol_pct: 2             # |measured-expect| <= 2% of |expect|
  - name: offset_fixed
    expect: 0.0
    tol_abs: 0.01          # absolute tolerance (units of the measurement)
  - name: depth_ok
    expect: true           # boolean: deck prints 1.0 (true) / 0.0 (false)
```

Tolerance policy: use `tol_pct` for ratios/frequencies (component tolerance + ideal-model error);
`tol_abs` for things that should be near-exact (offsets, normalized thresholds). State *why* a loose
tolerance is loose in a yaml comment (e.g. "trim authority absorbs the rest").

## What to check (claim taxonomy)

For each math claim in the spec/netlist, classify and check:
- **Transfer law** — f_ref/f0, cutoff vs CV (V/oct), Q vs control, gain, mV/oct, mV/dB.
- **Threshold/level** — clip/fold/clamp voltages, ±rail clamps, reference divider outputs.
- **Topology correctness** — virtual-ground sums, polarity/sign (does the SVF tap have the right sign
  vs the plugin?), unity pass-through, normalling behavior.
- **Before/after** a 0020-class fix — model the bug AND the fix in one deck (two named measurements)
  so the deck documents *why* the value is what it is and guards the regression.
- **`[NV]` items** — where the absolute depends on an unmeasured device constant (THAT2180 mV/dB,
  LM13700 bias), check the *trim authority / range* (that the design can be calibrated to the target),
  not the absolute. Note `[NV]` in the description.

## Naming
`specs/<block>/sim/<subcircuit>.cir` + `<subcircuit>.expect.yaml`. One deck per coherent sub-circuit
or law; a deck may carry several `measurements`. Keep names matching the spec's vocabulary.
