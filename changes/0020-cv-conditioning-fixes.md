# 0020 — CV-conditioning & behavioral netlist fixes (adversarial-review findings)

- **Lane:** B (hardware-only). The plugin is ground truth and already LOCKED for these blocks;
  only spec §2–4 / nets / components change. Enter at Step 5, gates G4–G6 + `--check`.
- **Status:** OPEN — G1 confirmed (fix all CRIT+HIGH; full H5/H6/M5 fixes). Working per cluster.
- **Opened:** 2026-05-30
- **Branch:** `change/0020-cv-conditioning-fixes` (stacked on `change/0019-doc-staleness-refresh`;
  rebase onto `dev` once 0019 merges).
- **Stacked-on:** 0019 (inherits the corrected aux-expo / aux-distortion / block-6 docs).

## Intent

A 6-agent adversarial review (plugin→spec→nets→schematic, primary sources) found the **signal
paths sound** but the **CV-conditioning sub-circuits and a few change-0018 behavioral wirings
wrong** vs the locked plugin. Fix the confirmed netlist/topology defects so the hardware spec
faithfully reproduces the plugin. No plugin/panel change (Lane B).

## Findings to address (prioritized; severity from review, ✓ = I independently verified)

### CRITICAL
- **C1 — Expo V/oct has no attenuation divider (blocks 5,7,8 + 6 by inheritance). ✓**
  CV reaches the THAT340 base through series R only (`R_VOCT`+`RV_1VOCT`), no shunt → no ~18 mV/oct
  scaling; converter rails. Needs a base divider (≈1:55) / proper summing node + the 1V/oct trim
  acting within it. (block-5/7/8 nets + aux-expo-converter §Schematic/Transfer.)
- **C2 — Mod-bus delivers ~3% depth at unpatched destinations (block 3). ✓**
  100 kΩ `R_SRC_NORM` into a ~3.3 kΩ destination node (10 kΩ inverter-in ∥ 10 kΩ pot) → ÷31.
  Fix: low-Z/direct normal (tip-switch breaks it) or buffer per destination. Pairs with H-mod below.
- **C3 — LP1 stereo-tilt "summer" injects into the raw expo base, not a summing node (block 5). ✓**
  Same root as C1; tilt scaling unrealizable. Fix together with C1.

### HIGH
- **H1 — BP3 input selector ignores ALT_BP_R (block-6-dist3). ✓** `ALT_L_DET` drives both U81
  selects; no `ALT_R_DET`. Plugin gates BP3_R on `altLConn||altRConn` (`Pogo.cpp:441`). Need an
  ALT_R detect + an OR into the Y(R) select; X(L) select stays on ALT_L_DET.
  **CONSTRAINT (found 2026-05-30):** `J4.3` (ALT_R jack's only switch lug) is already the
  normalling contact (`block-1.nets.yaml:76` `ALT_L_IN:[...,J4.3]` realizes the plugin's
  "normalise R to L if only L patched"). PJ301M-12 has one switch contact, so J4 can't both
  normal and cleanly detect — the ALT_R_DET derivation is a **G5 topology decision** (options:
  comparator off the normalling node / a second detect scheme / document as a minor limitation).
- **H2 — Mod-bus distribution buffer specified but absent (block 3).** Spec says U3 C/D parallel
  buffer; nets ground them as spares. Bare `MB_INV` (one TL074 section) drives 18 loads. Fix with C2.
- **H3 — VCA "unity trims" are series rheostats into the high-Z Ec+ port (block-4; copied to
  block-6 DRIVE trims). ✓** Series R can't set a DC offset on a µA control input. And the shared
  unbuffered V_CTRL wiper couples all 4 cells. Needs a real offset-injection (divider→Ec+) + a
  wiper buffer.
- **H4 — Wavefold mode phase-inverted vs Soft/Hard (block-6-dist, all 3 bands).** Net-by-net
  polarity makes WF net-inverting; flips wet contribution at mix + BP3 tap. Add one inversion in WF.
- **H5 — State variable tapped from LM13700 Darlington buffer → ~1.2 V DC into next OTA input
  (blocks 5,7,8).** Saturates the µV-class OTA input. Tap the unbuffered integrator node, or
  offset-correct. (Needs bias analysis to confirm severity/fix.)
- **H6 — Q=2000 self-osc needs ~260 pA Iabc, below LM13700 floor (5,7,8).** Top decade of Q
  uncontrollable. Likely a documented-limit + soft-limit addition rather than a full fix.

### MED (fold in where cheap)
- **M1 — BP3 R→L output normal averages (L+R)/2 through 2×1 kΩ instead of delivering L (block-6-mix). ✓**
- **M2 — Mod OFFSET range ±12 V vs plugin ±5 V (block 3).** Scale R15 or use ±5 V references.
- ~~M3 — BP per-band TILT CV missing the plugin ×0.22.~~ **RESOLVED / NON-ISSUE (verified
  2026-05-30).** block-6-svf1/2/3 already apply it: `R137/R143/R149 = 470k` into the 100k tilt
  summer = ×0.213 ≈ plugin ×0.22 (the net comment even says so). block-3's BP-tilt destinations are
  plain attenuverters feeding `MOD_BP{n}_TILT` into that summer; the scaling is applied once, in
  block-6, matching the plugin's single `×0.22f`. No change needed — dropped from scope.
- **M4 — I/V transimpedance has no feedback comp cap (block-4, 4 channels).** Add small C_f.
- **M5 — Q-cell Iabc bias math ignores the Iabc-pin rail potential (5,7,8).** Recheck arithmetic.

### Decisions made (G1, 2026-05-30)
- **Scope: fix all confirmed CRITICAL + HIGH defects in this one change (0020)**, plus the cheap
  MEDs (M1, M2, M4, M5). M3 dropped (non-issue, verified).
- **H5/H6/M5: full netlist fixes now** (not deferred to Phase-3R), backed by deeper LM13700
  datasheet analysis.
- Mod-bus strategy + expo divider topology will still be presented at **G5** for approval before
  the nets are rewired (the *decision to fix* is made; the *exact topology* is the G5 gate).

## Status
- **Status:** OPEN — G1 confirmed. Working cluster-by-cluster, committing per cluster.

## Scope / blocks
block-3, block-4, block-5, block-7, block-8, block-6-svf{1,2,3}, block-6-dist{1,2,3}, block-6-mix;
aux-expo-converter, aux-q-control, aux-ota-c-svf, aux-vca-cell, aux-mod-bus-core, aux-distortion;
components.yaml (new parts: shunt resistors, comp caps, possible buffer op-amps, ALT_R detect).

## Reconnaissance notes (wiring facts gathered before G5)
- **M1 mechanism (block-6-mix:88-89):** `BP3_L_OUT:[J27.1, J28.3]` + `BP3_R_OUT:[J28.1]`. BP3_L/R_OUT
  are block-B-buffered (U62, 1k series each). J28 unpatched shorts tip↔switch → ties both buffer
  outputs through 2k → tip = (L+R)/2, and back-feeds R into the J27(L) node. Fix: normal the L
  *source* into J28's switch ahead of R's buffer/series-R, not tie two driven outputs. (Wiring-only.)
- **H4 (WF phase, dist3 + dist1/2):** WF folder `BP3_WFOUT = 2·Vclamp − Vfoldin` with the leading
  DRIVE-VCA I/V inversion makes WF net-inverting while SC/HC are net non-inverting. Fix: add one
  unity inversion in the WF path (or swap a summing polarity) so all 3 modes share sign. Need to
  confirm a free op-amp half exists per dist section (U38/39/44/45 usage) — else +1 component.
- **H1 (BP3 selector):** see CONSTRAINT above — J4.3 already normalling; ALT_R_DET source is a G5 call.

---

## G5 TOPOLOGY PROPOSAL (2026-05-30) — awaiting user approval

Datasheet-grounded values from a focused analog-design pass (LM13700 SNOSBW2F, THAT340 Doc 600041).
Confidence tags: **[HC]** high (math/datasheet solid, verified) · **[NV]** needs datasheet re-verify
(PDF text-extraction unavailable in this env — structural argument sound, exact value to confirm).

### A. Expo V/oct divider — fixes C1 (+C3 base) — blocks 5,7,8 + propagate to 6-svf1/2/3 [HC, SPICE-validated]
- **Root cause:** V/oct CV lands on the THAT340 base through series R only (no shunt) → ratio≈1 → rails.
- **Fix:** add a base divider. ΔV_BE/oct = V_T·ln2 = **17.92 mV/oct** → 1 V ÷ ~55.8.
- ⚠️ **SPICE caught a 2.1× error in the first-pass values (2026-05-30).** The analysis gave R_SHUNT
  866Ω *and* a 1k tempco in series → real shunt leg 1866Ω → 37.8 mV/V (2.1× too high). Corrected
  topology (`specs/sim/expo_voct.cir`): **the +4110ppm tempco (Vishay TFPT 1k) IS the shunt leg to GND**
  (whole shunt tracks temp), and the **series leg sets the ratio**.
  - Validated: `R_VOCT ≈ 51.1k (E96)` + `RV_1VOCT 10k` (series wiper) + `R_TEMPCO = TFPT 1k` shunt→GND
    gives **19.19 → 16.10 mV/V across full trim, 17.92 at ~38% rotation** — target centered with
    authority both sides. (Final series R tuned to E96 to center 17.92 at mid-rotation; SPICE picks it.)
  - Shunt (the tempco) to **GND**, not the I_ref node (loading I_ref shifts f_ref). f_ref trim (RV_REF)
    stays — orthogonal. R_E (1k) + I_ref net unchanged.
  - Tempco SLOPE: TFPT +4110 ppm/K vs ideal ~+3413 ppm/K over-compensates ~20% — RV_1VOCT sets the
    room-temp setpoint; residual tempco-slope error is a documented limit (bench-trimmable, not a value bug).
  - **New part = tempco (G6a, Vishay TFPT, decided).** R_VOCT/RV unchanged types. Counts: LP1=2 (L+R),
    HP=1, LP2=1, BP×3=2 each → ~8 tempco + 8 series-R changes.

### B. LP1 tilt summing node — fixes C3 — block-5 (and the BP per-band tilt summers already OK) [HC]
- **Plugin:** `lp1TiltV = LP1_TILT×5` → full tilt **±5 V/oct**; L=base+tilt, R=base−tilt; sums 1:1 with V_freq.
- **Fix:** replace the direct R55/R56→base resistive mixing with a real **inverting summer** (V_freq +
  ±V_tilt, 3× **100k** + op-amp half/channel) whose output feeds the §A divider. The existing tilt
  inverter (U13-A) already makes −V_tilt for R. **+1 op-amp half per channel** (promote a dual→quad or
  add a TL072 — G6 item). RV6 tilt-null stays as a center offset into the summer.

### C. OTA state-variable tap — fixes H5 — blocks 5,7,8 [HC, pure reroute]
- **Root cause:** v1/v2 tapped from LM13700 **Darlington buffer** outputs (pins 8/9), ~1.2–1.4 V
  (2·V_BE, temp-dependent) below the integrator node → injects ~1.3 V DC into the next OTA's ±30mV input.
- **Fix:** tap v1 from **pin 5**, v2 from **pin 12** (the unbuffered OTA outputs = the cap nodes; merge
  `*_V1_*` into `*_V1CAP_*`, `*_V2_*` into `*_V2CAP_*`). Use the Darlington buffer (8/9) **only** for
  output-jack / inter-block low-Z drive, never inside the loop or into an OTA input. **No new parts.**
  47nF C0G caps stay on pins 5/12; f_ref math unchanged (gm/C identical) — removing the buffer *improves*
  DC accuracy.

### D. Q-cell Iabc bias + self-osc — fixes M5 (bias) + H6 (range) — blocks 5,7,8 [NV — re-verify pin V]
- **M5 root cause:** spec assumes Iabc = V_ires/R_Iabc with the bias pin at 0 V. The LM13700 Iabc pin
  actually sits ~2·V_BE above V− (**≈ −10.8 V at −12V rails**), so a 1 MΩ from a ~0 V node delivers
  ~10.8 µA almost regardless of control → Q pinned at min. **(Structurally certain the pin is near V−,
  not GND; the exact 1-vs-2 V_BE figure is the [NV] item.)**
- **Proposed fix:** `R_Iabc` 1MΩ → **100k**; IRES_AMP drives V_ires **negative** in the ~−10.0…−10.8 V
  window (Iabc = (V_ires−V_pin)/R_Iabc); **fix the clamp polarity** (current BAT54 clamps V_ires≥0,
  wrong sign — should prevent going below V_pin).
- **H6 root cause:** Q=2000 needs Iabc≈**260 pA**, far below the LM13700 controllable floor (~10–100 nA).
  Honest controlled Q_max ≈ **10–50**.
  - **Proposed:** clamp the *controlled* Q range to ~≤10 and reach self-oscillation via a **soft-limit:
    2× BAT54S antiparallel across the BP-tap integrator cap** (BAT54 already in BOM — no new part type).
    Alternative (cleaner, bigger blast radius): lower R_in so a comfortable Iabc maps to high Q — but
    R_in is the SVF summing/gm-reference resistor, so it ripples into SUM_AMP gains. **Recommend the
    soft-limit option.**

### E. BP3 input selector ALT_R — fixes H1 — block-6-dist3 + block-1 [topology decision]
- Plugin: `bp3InR = (altLConn || altRConn)`. Hardware gates both channels on ALT_L_DET only; no ALT_R_DET.
- **Constraint:** J4's one switch lug is already the normalling contact. **Options for G5:**
  - **(E1)** Derive ALT_R_DET with a comparator/transistor off J4's tip node (detect a patched plug by
    the tip being driven), OR off the R134-style pulldown pattern — needs +1 small part on block-1.
  - **(E2)** Add an OR (2 diodes + pullup, or a logic gate) of ALT_L_DET and ALT_R_DET → Y(R) select;
    X(L) select stays ALT_L_DET. (Depends on E1 producing ALT_R_DET.)
  - **(E3)** Document as a minor, rarely-hit limitation (only matters when ALT_R is patched but ALT_L is
    not — an unusual mono-into-R patch) and leave the wiring. Cheapest; small fidelity gap.
  - **Recommend E1+E2** for true plugin parity (it's a real, if narrow, behavioral divergence).

### F. WF phase inversion — fixes H4 — block-6-dist1/2/3 [HC, confirm free op-amp]
- WF path is net-inverting vs SC/HC (leading DRIVE-VCA I/V inversion + the folder's `2·Vclamp−Vfoldin`).
- **Fix:** add one unity inversion in each WF path so all 3 modes share sign into the mux. Need a free
  op-amp half in each dist section — **else +1 dual op-amp/section** (G6). Verifying U38/39/44/45 usage.

### G. BP3 R→L output normal — fixes M1 — block-6-mix [HC, wiring]
- Re-route so J28's switch lug taps the **L source ahead of R's buffer/series-R** (true "R normals to L"),
  instead of tying two driven 1k outputs together (which gives (L+R)/2 and back-feeds the L jack).

### H. Mod-bus depth + buffer — fixes C2 + H2 — block-3 [topology decision]
- C2: 100k `R_SRC_NORM` into a ~3.3k destination node → ~3% depth. H2: spec'd distribution buffer is
  absent (U3 C/D grounded as spares); bare MB_INV drives 18 loads.
- **Options for G5:**
  - **(H-a)** Direct/low-Z normal: bus normals onto V_src via the jack tip-switch (override breaks it),
    drop R_SRC_NORM; **re-enable the U3 C/D distribution buffer** (per the spec's own §145) to drive the
    18×~10k loads (~18 mA). Cleanest plugin parity. **Recommend.**
  - **(H-b)** Per-destination buffer (18 unity buffers) — many parts, overkill.
  - **(H-c)** Raise destination input impedance (10k→100k pots+inverters) so 100k norm divides less —
    changes 18 attenuverter scalings + noise. Not recommended.
- Also fold **M2** (mod OFFSET ±12V→±5V: scale R15 or use ±5V refs) and confirm **M4** (block-4 I/V comp
  cap, add small C_f ~few pF across R_f, 4 ch) here.

### New out-of-scope finding (log, separate change)
- **THAT340 has NO internal PTAT/tempco** — aux-expo-converter's "on-chip compensation" is wrong. A real
  V/oct design needs an external **+3300 ppm/°C tempco resistor** in the expo (e.g. series with R_SHUNT).
  This affects ALL expo converters (5,7,8,6×3). Recommend a **separate change 0021** (it's a new
  component type + every expo), not folded into 0020. Flagging now so it isn't lost.

### G5 DECISIONS (user, 2026-05-30) — APPROVED, proceed
1. **Mod-bus (H):** ✅ **H-a** — low-Z normal via jack tip-switch (drop R_SRC_NORM) + re-enable U3 C/D
   distribution buffer to drive the 18 loads.
2. **BP3 selector (E):** ✅ **E1+E2** — add ALT_R detect (+1 part on block-1) + OR with ALT_L_DET into
   the R-channel select. Full plugin parity.
3. **Q-cell (D):** ✅ **Proceed, flag [NV]** — implement R_Iabc 1M→100k, negative V_ires drive, fix
   clamp polarity, soft-limit diodes for self-osc; mark the LM13700 Iabc-pin-voltage-dependent values
   as needing datasheet/bench re-verify at prototype.
4. **THAT340 tempco (out-of-scope finding):** ✅ **Fold into 0020** — add external +3300 ppm/°C tempco
   resistor to every expo converter (blocks 5,7,8 + 6-svf1/2/3). NEW PART TYPE → G6a/G6b required.

## G6 — new components (gate before any net references them)
| Item | Part | New type? | Gate |
|---|---|---|---|
| Expo base shunt (§A) | R_SHUNT 866Ω 0603 | no (generic R, new value) | — |
| Expo tempco (§4 fold-in) | **tempco resistor +3500 ppm/°C** (e.g. Vishay TFPT/PTF series or KRL) | **YES** | **G6a+G6b** |
| Tilt summer op-amp (§B) | TL072/OPA1612 half | no (existing type, new ref) | — |
| WF invert op-amp (§F) | TL072 half | no (existing type, new ref) | — |
| ALT_R detect (§E1) | MMBT3904 + R (existing) or comparator | no (MMBT3904 in BOM) | — |
| E2 OR gate | 2× 1N4148W + pullup (existing) | no | — |
| Q soft-limit (§D/H6) | 2× BAT54S antiparallel (in BOM) | no | — |
| I/V comp cap (§M4) | C_f ~10pF 0603 (existing type) | no | — |
- **Only the tempco resistor needs G6a/G6b.** Candidate to confirm: a discrete PTC/tempco resistor with
  ~+3300–3500 ppm/°C to compensate the expo's −1/T base-emitter tempco. Need a real MPN + footprint +
  datasheet. **G6a STOP: confirm the tempco-resistor MPN before it enters any netlist.**

## Implementation plan (cluster-by-cluster, commit per cluster, gates per CLAUDE.md Step 5-7)
1. **G6a** tempco resistor part selection (STOP for confirm) → registry + datasheet + footprint.
2. **Cluster expo+tilt** (A,B,§4): block-5/7/8 + 6-svf1/2/3 nets + aux-expo-converter §2-3 + aux-ota-c-svf.
3. **Cluster OTA-tap** (C): block-5/7/8 nets (reroute) + aux-ota-c-svf.
4. **Cluster Q-cell** (D): block-5/7/8 nets + aux-q-control.
5. **Cluster block-6** (E,F,G): dist1/2/3 (WF invert), dist3 (ALT_R sel), mix (BP3 normal) + block-1 (ALT_R det).
6. **Cluster mod-bus** (H,M2): block-3 nets + aux-mod-bus-core; **block-4** M4 comp cap + (carry HIGH-3
   VCA Ec+ trim rework — NOTE: not yet in the A-H proposal above; see below).
7. Regenerate schematics + BOM + netlist-viz; all gates; update specs §2-4 + STATUS; PR.

### ⚠️ Gap to close before G6: VCA Ec+ trim (HIGH-3, block-4 + block-6 DRIVE)
The §A-H proposal does NOT yet cover **HIGH-3** (VCA "unity trims" wired as series rheostats into the
high-Z Ec+ port — can't set offset; shared unbuffered V_CTRL couples 4 cells; copied to block-6 DRIVE
RV51-56). This is in scope (a confirmed HIGH). **Mechanism verified 2026-05-30:** `EC_L:[U4.2,RV1.1,RV1.2]`
+ `V_CTRL:[RV44.2,RV1.3,...]` → RV1 wiper+end to Ec+, other end to V_CTRL = series rheostat into the
high-Z Ec+ port; and V_CTRL (RV44 wiper) is unbuffered into 4 cells.
- **Proposed fix [NV — THAT2180 datasheet]:** (a) buffer V_CTRL with a unity op-amp half (TL072,
  existing type) before the 4-way fan-out → `V_CTRL_BUF`; (b) drive each Ec+ from V_CTRL_BUF through a
  fixed series R, and convert each unity trim to a **voltage-injection divider** (trimmer across a small
  ±ref, wiper → series R → Ec+ node) so it adds an adjustable mV offset (the real unity-null), not a
  series resistance. Exact Ec+ R / ref values depend on the THAT2180 +6.1 mV/dB control-port spec →
  flag [NV] like the Q-cell, confirm at prototype. Same fix applies to block-6 DRIVE RV51-56 + their
  shared V_DRIVE_CTRL fan-out.

## Implementation finding (2026-05-30): cluster C is a topology refinement, not a reroute
Tracing block-5/7/8 during implementation, the "tap v1/v2 from pins 5/12" fix splits into:
- **Safe, unambiguous (H5 literal fix):** move the HIGH-Z consumers — OTA2 In+ (`U7.14`/`U8.14`,
  HP `U49.14`/`U50.14`, LP2 `U56.14`/`U57.14`) and Q-cell In+ (`U9.3`/`U10.3`, etc.) — from the
  Darlington buffer outputs (pins 8/9) to the unbuffered cap nodes (pins 5/12). Removes the ~1.2 V
  offset injected into the next OTA. No loading concern (OTA/Q inputs are high-Z). No new/removed parts.
- **Needs design decision + validation:** the **v2/LP path** drives BOTH the output buffer and the
  resistive feedback `R47`/`R48` (and HP/LP2 equivalents) from the Darlington (pin 9). Consequences:
  (i) the LP/LP2 audio OUTPUT inherits the ~1.2 V Darlington DC offset; (ii) `R47` is a resistive load
  that can't move to the unbuffered cap node without loading the integrator. The clean fix is to drive
  the output buffer input + `R47` from the **precision op-amp buffer** (U11/U58/…) tapping the clean
  cap node (pin 12), dropping the Darlington from the v2 signal path and **removing the R68/R69-class
  pulldowns**. That's a real topology refinement (changes feedback source + removes parts) and its
  **loop DC/stability cannot be validated in this env** (no SPICE; datasheet PDFs won't text-extract).

### SPICE validation results (specs/sim/, ngspice-42)
- **expo_voct.cir [DONE]:** caught the 2.1× value error; corrected divider sweeps 19.2→16.1 mV/V with
  17.92 mV/oct (V_T·ln2) centered at ~38% trim. §A values validated.
- **ota_svf_loop.cir [DONE]:** (1) H5 confirmed — Darlington tap injects **1.26 V** into the next OTA
  input vs ±30 mV linear range (**42× over**); unbuffered tap (§C fix) = **0 V**. (2) gm-C integrator
  corner = **634.6 Hz** at Iabc 9.69 µA (target 632, 0.4%) — re-tap doesn't change f_ref.
- **q_cell.cir [DONE]:** M5 confirmed — 1MΩ@0V → Iabc 10.8µA (14× the claimed 0.74µA, Q pinned).
  §D fix R_Iabc=100k, V_ires −10.0→−10.795V maps Q = 0.065→0.74→2.6→10.4. Butterworth (Q≈0.74) at
  V_ires≈−10.73V. **Design consequence:** useful Q lives in a ~0.8V window just above the −10.8V pin
  and is very steep (~10mV ≈ 5× Q) → V_bias trim needs fine/multi-turn resolution near the rail; H6
  self-osc via soft-limit diodes (Iabc can't precisely set Q>~10–50). Sized when wiring §D.
- **vca_ecplus.cir [TODO]**.

### Proposed split (recommended)
- **Do now (no resonant-loop risk, no validation needed):** clusters **E** (BP3 ALT_R selector),
  **F** (WF phase invert), **G** (BP3 output normal), and **H** (mod-bus low-Z normal + U3 buffer +
  M2/M4). These are digital-select / output-jack / summing wiring — well-understood, gate-checkable.
- **Hold for validation:** clusters **A/B** (expo divider+tilt — math solid but tempco blocked on G6a),
  **C** (OTA tap — the v2/loop refinement above), **D** (Q-cell [NV] bias), and **HIGH-3** ([NV]
  THAT2180 Ec+). These touch the OTA-C resonant loop or carry [NV] values needing SPICE/bench/datasheet
  confirmation. Implement them with a validation step (SPICE model or prototype) rather than blind edits.

## G5b DECISIONS round 2 (user, 2026-05-30) — de-risking Tier 2
1. **Trim-pot strategy (user):** "can we do it so that we have trim pots that enable us to do this
   post-build?" → **YES, and adopt it as the design principle for all [NV] nodes.** Rather than
   pre-committing exact unverifiable values, design each uncertain node with **calibration trim
   authority wide enough to span the uncertainty**, dialed in at bench bring-up. Most already have a
   trim (expo RV_REF + RV_1VOCT; VCA Ec+ RV1/2/46/47; Q-cell V_bias RV5/RV9…). Work = ensure the trim
   covers the corrected range + correct wiring, not guess a fixed resistor. This is the standard synth
   bring-up approach and removes the "blind analog surgery" objection for D, HIGH-3, and the Q-cell bias.
2. **ngspice (user: set it up):** ✅ **ngspice-42 installed & verified** (AC analysis runs). Tier-2
   resonant-loop / [NV] fixes will be **validated with small SPICE models** (expo converter, OTA-C SVF
   loop, Q-cell bias, VCA Ec+) BEFORE committing the netlist edits — no longer deferred to prototype-only.
   SPICE decks live in `specs/sim/` (new dir) committed alongside the change for reproducibility.

## Tempco resistor (G6a) — research result (2026-05-30)
Deep-research found **no in-production SMD part exactly at +3300 ppm/°C with 1k**:
- **Panasonic ERA-S33J102V** (0805, 1k, +3300 ppm, the textbook match) — **EOL/obsolete at DigiKey.**
- **Vishay TFPT0805L1001FM** (0805, 1k) — **active + in stock**, but **+4110 ppm/K** (out of the 3000–3600
  band; over-compensates ~25%). KiCad `Resistor_SMD:R_0805_2012Metric`.
- **KRL/Riedon C-2AQ** (1k, +3500 ppm, ±1%) — **in production**, synth-standard, but **through-hole only**;
  clean datasheet not extractable (order-by-description from synth distributors).
**Implication + how the trim strategy helps:** the tempco TCR mismatch (3300 vs 3500 vs 4110 ppm) is
*exactly* what a trimmable V/oct slope (RV_1VOCT, §A) absorbs — a higher-TCR part just shifts the trim
setpoint. So selecting the **active Vishay TFPT (+4110)** is viable IF the expo divider math is re-centered
for 4110 ppm and RV_1VOCT spans it. **G6a decision still needed (see question).** Until an MPN is locked,
§A wires the divider with a placeholder tempco footprint in series with R_SHUNT (expo fix not blocked).

## G6a — tempco resistor (NEW PART TYPE) — STOP, needs MPN confirmation
The expo tempco (fold-in, decision 4) needs a real **+3300–3500 ppm/°C tempco resistor** (one per expo:
blocks 5,7,8 + 6-svf1/2/3 L+R = ~8 parts). This is a new component type → **G6a (registry + datasheet)
+ G6b (footprint)** must close before any net references it. I will not fabricate an MPN. Candidate
families to confirm: Vishay TFPT (PTC thermistor, +3000–6000 ppm/°C, 0603/0805) or a synth-standard
+3300 ppm/°C tempco resistor. **Next action options:** (i) deep-research a real sourceable MPN +
datasheet, or (ii) user specifies a preferred part. Until then the expo-divider fix (§A) can be wired
*without* the tempco (tempco R sits in series with R_SHUNT and can be added when the MPN lands), so §A
is not blocked — but the tempco itself is.

## Gate checklist
- [x] **G1 — intent** confirmed (fix all CRIT+HIGH; full H5/H6/M5). 
- [ ] **G5 — topology proposal** (assemble after analog-values agent returns) ← CURRENT STOP
- [ ] G4 — spec parity vs locked plugin (per block) [folded with G5 per-block]
- [ ] G4 — spec parity vs locked plugin (per block)
- [ ] G5 — topology approval (per block; mod-bus + expo strategy decisions)
- [ ] G6a/b — new components + footprints
- [ ] `--check` gates + parity green
- [ ] PR `change/0020-cv-conditioning-fixes` → `dev`

## Decisions log
- 2026-05-30: opened off the 0019 tip (stacked) to inherit corrected docs and avoid re-touching
  the same stale text; will rebase onto dev after 0019 merges.
