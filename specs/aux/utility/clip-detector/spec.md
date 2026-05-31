# aux: Clip Detector (±4 V window comparator + hysteresis + diode-OR LED)

**Type:** `utility` · part of the [aux circuit library](../../_LIBRARY.md)

Design status: [x] draft → [ ] reviewed → [ ] validated on prototype

## Overview

A **±4 V window clip indicator**: a signal that swings outside the ±4 V window lights a LED.
Two open-loop comparators per monitored signal (one for `> +4 V`, one for `< −4 V`) are
diode-OR'd onto a single LED. Light positive feedback gives a small hysteresis band so the
LED does not chatter at the threshold. The ±4 V thresholds are set by two shared passive
dividers from the ±12 V rails (`VREF_P4` / `VREF_N4`).

This is the analog realization of the plugin's per-band CLIP light, which lights when the
post-distortion / pre-SVF signal magnitude exceeds 4.0 V:
`BP{n}_CLIP_LIGHT = (max(|distOutL|, |distOutR|) > 4.0f)`.

In POGO each band monitors a stereo pair (L and R), so a full per-band detector is **four**
comparators (`>+4 L`, `<−4 L`, `>+4 R`, `<−4 R`) diode-OR'd to one LED — the same cell
instanced twice for the two polarities and twice again for the two channels.

## Schematic

```
  ±4 V reference dividers (shared by all 3 bands' detectors):
    +12V ──[ R_top 20k ]──┬── VREF_P4 (+4.0V)        −12V ──[ R_top 20k ]──┬── VREF_N4 (−4.0V)
                          [ R_bot 10k ]                                    [ R_bot 10k ]
                          └── GND                                          └── GND

  One channel/polarity (>+4 detector shown):
                        VREF_P4 ──►(−)┐
    DISTOUT ──[ R_in 100k ]──────►(+) │  comparator  out ──►|──┐   (1N4148 OR steering)
                          ▲           └──────┐                 │
                          └──[ R_hys 2.2M ]──┘ (positive fb)   ├─ CLIP_OR ──[ R_led 1k ]──► LED anode
    (the <−4 detector swaps in±: VREF_N4 on +in, DISTOUT on −in)              LED cathode ──► GND

  out HIGH (≈+11V) when DISTOUT > +4V (or < −4V for the N detector) → steers current into the LED.
```

## Transfer Function

```
Thresholds (passive ±12V dividers):
  VREF_P4 = +12 · R_bot/(R_top+R_bot) = +12 · 10k/30k = +4.0 V
  VREF_N4 = −12 · R_bot/(R_top+R_bot) = −12 · 10k/30k = −4.0 V

Window comparator logic (per channel):
  CLIP =  (DISTOUT > +4 V)  OR  (DISTOUT < −4 V)   →  LED on
       =  |DISTOUT| > 4 V                          (matches plugin `> 4.0f`)

Hysteresis (input-referred, ±10.5 V comparator swing):
  ΔV_hys ≈ (R_in / R_hys) · ΔV_out = (100k / 2.2M) · 21 Vpp ≈ 0.95 V band
```

The ±4 V threshold emerges from the 20k/10k divider ratio against the ±12 V rails — change the
top or bottom R and the threshold moves (the sim proves this is non-vacuous). The hysteresis is
a small input-referred band (~±0.5 V around the knee) that prevents chatter; its absolute width
is a comfort margin, not the load-bearing claim (the threshold is).

## Design Choices & Rationale

- **Window = two comparators, not a rectifier + one comparator:** a true bipolar window with
  independent `>+4` and `<−4` comparisons exactly matches the plugin's `max(|L|,|R|) > 4` and
  avoids a precision-rectifier's diode-drop error near the threshold.
- **Shared ±4 V dividers:** one `VREF_P4` and one `VREF_N4` node feed all three bands' detectors
  (high-Z comparator inputs add no divider loading), saving parts and guaranteeing matched
  thresholds across bands. 1% resistors give ~±40 mV threshold error; trimmed/accepted Phase-3R.
- **Light hysteresis (R_hys ≫ R_in):** R_hys = 2.2 MΩ vs R_in = 100 kΩ → ~0.95 V input-referred
  band, enough to stop LED chatter on a signal grazing 4 V, small enough not to hide real clips.
- **Diode-OR (1N4148):** steering diodes combine the 2 (or 4) comparator outputs onto one LED
  without back-driving an idle comparator; the LED current-limit R sets brightness.

## Component Values (POGO-specific)

| Ref (generic) | Part | Package | Value | Notes |
|---|---|---|---|---|
| U_cmp | TL074CDT (quad) | SOIC-14 | — | 4 open-loop comparators (>+4 L, <−4 L, >+4 R, <−4 R) |
| R_top (×2) | Resistor | 0603 | 20 kΩ | VREF_P4 / VREF_N4 divider top |
| R_bot (×2) | Resistor | 0603 | 10 kΩ | VREF_P4 / VREF_N4 divider bottom → ±4.0 V |
| R_in (×4) | Resistor | 0603 | 100 kΩ | DISTOUT → comparator input; with R_hys sets hysteresis |
| R_hys (×4) | Resistor | 0603 | 2.2 MΩ | Positive-feedback hysteresis (~0.95 V input-referred) |
| R_led | Resistor | 0603 | 1 kΩ | CLIP LED current-limit at the OR node |
| D_OR (×4) | 1N4148W | SOD-123 | — | Diode-OR steering into the LED anode |
| C_ref (×2) | Ceramic | 0603 | 100 nF | VREF_P4 / VREF_N4 bypass (tames comparator-input noise) |

(Generic representative values; live block-6-dist1 refs: R186/R187 + R188/R189 dividers,
R177–R180 inputs, R181–R184 hysteresis, R185 LED limit, R190/R191 N4 series.)

## Performance Characteristics

| Parameter | Value | Condition |
|---|---|---|
| Trip threshold | ±4.0 V | 20k/10k from ±12 V (= plugin 4.0f) |
| Hysteresis (input-referred) | ~0.95 V | R_in/R_hys · 21 Vpp swing |
| Threshold error | ~±40 mV | 1% divider resistors |
| Response | comparator prop. delay | open-loop TL074 |

## Known Gotchas / Assembly Notes

- Comparator inputs are high-Z — the ±4 V references see no DC load from them, so the divider
  ratio (and thus the threshold) is set purely by R_top/R_bot. Do not add a series R into the
  reference input that would shift the trip point.
- For the `<−4` comparator, VREF_N4 feeds the `+in` *through a series R* so the hysteresis
  feedback sums at that node; keep that series R equal to R_in or the hysteresis band skews.
- The LED brightness is binary in the plugin (`1.f`/`0.f`); the analog LED is likewise full-on
  past threshold — do not interpret partial brightness as a soft clip.

## Used By

| Block | Instance | Board | Notes |
|---|---|---|---|
| block-6 (dist1) | BP1 CLIP (U94 + R186–R189) | audio | ±4 V window on BP1 distortion out → BP1_CLIP LED |
| block-6 (dist2) | BP2 CLIP | audio | Shares VREF_P4/N4 via boundary nets |
| block-6 (dist3) | BP3 CLIP | audio | Shares VREF_P4/N4 via boundary nets |

Plugin law: `plugin/src/Pogo.cpp:459` — `BP1_CLIP_LIGHT = (max(|bpInL[0]|,|bpInR[0]|) > 4.0f)`.
