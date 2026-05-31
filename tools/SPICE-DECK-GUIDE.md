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
10. **Booleans/comparisons inside `.control` `let`: use `gt`/`lt`/`ge`/`le`/`and`/`or`, NOT `>`/`<`/`&&`.**
    A bare `>` in a `let` line is parsed as a SHELL OUTPUT REDIRECT (ngspice's control language is
    csh-like) — it silently aborts the whole `print` line ("ambiguous redirect") and leaves a stray file
    named after the redirect target. Write `let mono = ((a gt b) and (b gt c)) ? 1 : 0`. (A B-source
    `V = (V(a)>V(b))?1:0` is fine — the `>` trap is only in `.control` `let`/`print` lines.)
11. **Inside a `.cir`, ngspice does NOT parse R-notation `2k4`/`4k7`** (it reads `2k4` as `2k`). Write the
    ohmic value as `2.4k` in the SPICE element, but keep the `netlist_bind` declared as the netlist's
    `2k4` (the *runner's* `parse_value` handles R-notation; only the ngspice deck card needs `2.4k`).
12. **`.param` names are NOT in scope as `.control` vectors.** `.param vsat=11` then `let r = vpk/vsat`
    fails (vsat unknown in the control vector namespace) — divide by the literal (`vpk/11`) in `.control`,
    or only use `{vsat}` inside element cards.

### Transient (`.tran`) + oscillator decks (the harness's `.tran` pattern, from block-2 LFO)

For a relaxation oscillator (integrator + hysteretic comparator) or any time-domain rate law:
- **Build a REAL stateful loop** — the cap/integrator state is what sustains oscillation. A memoryless
  B-source comparator cannot oscillate. Working triangle-LFO core (block-2): inverting integrator
  `Eint nvtri 0 0 nsum 1e6` + `Rint` (drive→nsum) + `Cint` (nsum→nvtri feedback); hysteretic Schmitt
  `Bsq vsq 0 V = (V(nplus) > V(nvtri)) ? vsat : -vsat` with the `R_FB`/`R_HYS` divider forming
  `nplus = vsq·R_HYS/(R_FB+R_HYS)`. Get the integrator SIGN right (invert the square into the drive) or
  it latches and runs to the rail instead of oscillating.
- **Kick it off the metastable point:** `.ic v(nvtri)=0.1` + `.tran <step> <stop> uic` (`uic` honours
  `.ic`). Without a kick an ideal sim can sit at 0 forever.
- **Measure the period skipping startup:** `meas tran t1 WHEN v(nvtri)=0 RISE=2` / `t2 ... RISE=3`, then
  `let fhz = 1/(t2-t1)` (use the 2nd→3rd crossing so the first settling ramp doesn't bias it). The
  oscillation frequency must be VALUE-derived — verify it's invariant to the `.ic` value, step, and stop
  time, and that it MOVES when you perturb the R/C (that's the Q3 proof it's not pinned by the sim setup).
- **Bound the run** `< ~1–2 s` of sim time. For a slow endpoint (e.g. 0.05 Hz = 21 s period), DON'T run
  the transient — check the rate-setting **divider ratio** with an `op` deck instead (block-2 `lfo_fmin`).
- **[NV] supply rails cancel:** if a threshold scales with the op-amp saturation `V_sat`, the oscillation
  frequency is `V_sat`-independent — prove it with a two-`V_sat` PARALLEL ratio deck (=1.0) rather than
  asserting an absolute that depends on the unmeasured rail.

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

---

# Multi-agent authoring pipeline (how to build out a block's checks at scale)

Proven on block-7 (change 0024). Use this when authoring a full block's worth of checks. The stages
are **sequential** (each depends on the prior); parallelism lives *within* a stage. The orchestrator
(you) runs the stages, commits per slice, and integrates.

> **Why a verify stage exists:** a passing deck is NOT a good check. On the block-7 pilot the verify
> stage found that the runner didn't actually read `nets.yaml` — the gate was *deck-literal-vs-spec*,
> not *netlist-vs-spec* (a silent R104 1M→100k would have passed green). That finding — not the decks —
> was the pilot's real product, and it produced the `netlist_bind` mechanism. **Do not skip verify, and
> make its hardest question load-bearing.**

## Stage 1 — DERIVE (1 agent; gates everything downstream)

Reads spec + netlist + plugin DSP + aux; emits a **structured manifest** (one row per math claim), not
prose. Required fields per candidate: `id`, `claim` (one sentence), `source` (file:line for the spec
formula AND the netlist refs/values it depends on), `plugin_ref` (DSP line or "analog-only"),
`spice_able` (YES/NO/PARTIAL), `nv` (YES/NO — depends on an unmeasured device constant?),
`proposed_check` (model + named measurements + how `expect` is DERIVED FROM THE SPEC + tolerance),
`already_covered`. End with: a **prioritized shortlist** of the highest-value NEW checks, and an
explicit list of claims that are **NOT spice-able** (pinouts, sourcing, layout, power, fan-out) so
they're acknowledged out of scope.

The deriver MUST read this guide — the manifest is the spec the writers build from.

## Stage 2 — WRITE (N parallel agents; one slice of the shortlist each)

Split the shortlist into balanced slices (group by type: structural/transfer vs ratio-summers vs
expo/bias). Each writer: reads this guide + the relevant spec/netlist/plugin, authors its `.cir` +
`.expect.yaml` per the conventions, adds `netlist_bind` for every value-pinning literal, and **runs
`build_spice.py --run <block>` to confirm its decks PASS before reporting.** Writers touch ONLY their
own new files — no netlist/spec/other-deck edits. They report each deck's content + measured values +
PASS confirmation, and **escalate (not paper over) any case where a netlist-derived value did not land
on the spec-derived expect** — that is a real divergence finding.

Orchestrator: commit each writer's decks as a slice once it reports PASS (verify in isolation first;
in-flight agents may leave half-written files — never commit a failing/partial deck).

## Stage 3 — VERIFY-INTENT (N parallel adversarial agents)

The job is to find checks that are **WRONG, WEAK, or VACUOUS** — not to confirm they pass. Each
reviewer runs ngspice + **perturbation probes** and judges every deck on three killer questions:

- **Q1 — does the deck COMPUTE what its assertion claims?** (recompute the math by hand; check sample
  points, unit conversions, that the printed measurement equals the named quantity)
- **Q2 — is `expect` INDEPENDENTLY spec-derived, not reverse-engineered from deck output?** (derive each
  expect yourself; verify the cited `plugin_ref` actually says what's claimed)
- **Q3 — THE KEY TEST: would the check FAIL if the netlist value were WRONG?** Actually perturb it:
  flip the tap (HP→LP), invert the follower (the bug), set Rf=200k, revert R104→1M — and confirm the
  assertion fails. **The deepest risk: a deck that models the ideal circuit on BOTH sides proves
  nothing.** Confirm each deck is bound to the real netlist values (via `netlist_bind`), not just
  hardcoded literals that happen to match.

Reviewers report a verdict (SOUND / WEAK / BROKEN) per question with line numbers; prioritize Q3.

## Stage 4 — INTEGRATE (orchestrator)

Reconcile verifier findings: fix BROKEN/WEAK decks, add missing `netlist_bind`, close coverage seams,
correct any spec/netlist bug the process surfaced (the gate exists to find these — fix them, don't
suppress them). Run the full gate stack; commit. If a finding is architectural (like the missing
netlist binding), fix the *mechanism*, not just the symptom, and **prove the fix** (e.g. perturb the
netlist and confirm the gate now fails).

## Prompt-writing lessons (what made this work)

- **A shared guide doc every agent reads** (this file) eliminates repeated rediscovery of the ngspice
  traps (parallel-instances, node names, the `print` contract, boolean-via-B-source).
- **Structured manifest, not prose** — makes Stage 2 parallelizable and Stage 3 checkable.
- **Name the priority explicitly.** "Review the decks" finds nothing; "would it fail if the netlist
  were wrong, and is the deck bound to nets.yaml or a textbook circuit?" found the architectural flaw.
- **Give writers the escalation instruction** ("flag any netlist↔spec divergence; don't paper over") —
  this is how the stale spec line surfaced three independent times.
- **Tell agents to touch only their own files** and to **self-verify via the runner** before reporting.
- Frame the pilot's deliverable as **the methodology + findings**, not the artifact count — the verify
  stage earning a real architectural fix is worth more than N green decks.
