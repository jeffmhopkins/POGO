# Standard CV / Audio Input Protection Circuit

Applied to **every** jack input on POGO (audio in, CV in, override jacks, mod source jack).

## Schematic

```
Jack tip
  │
  ├──[100 Ω]──────────────────────────────────┬── to unity-gain buffer input
  │                                            │
  │                                     BAT54 (SOT-23 dual Schottky)
  │                                      ┌────┴────┐
  │                                      │         │
  │                                    +12V       −12V
  │                                   (clamp)    (clamp)
  │
Jack sleeve → GND
```

## Component Values

| Reference | Part | Package | Value | Notes |
|---|---|---|---|---|
| R_in | 100 Ω | 0603 | 100 Ω | Series current-limit resistor |
| D_clamp | BAT54S | SOT-23 | — | Dual Schottky **series** configuration. **Pin orientation (CRITICAL)**: Pin 1 = Anode of D1 → connect to −12 V; Pin 2 = Common (signal node) → connect to signal after 100 Ω; Pin 3 = Cathode of D2 → connect to +12 V. A labeling error creates silent failure (no clamping). Every schematic using BAT54S must show Pin 1, 2, 3 explicitly. |
| C_bypass | 100 nF | 0603 | 100 nF | Optional: across input to GND for HF filtering |

## BAT54S Pinout Reference

```
BAT54S SOT-23 (series configuration):

Pin 1 (left) = Anode D1  ──►──── Pin 2 (center) = Common ──────►── Pin 3 (right) = Cathode D2
connect to −12 V rail              connect to signal node              connect to +12 V rail
```

Correct: signal at Pin 2 is clamped to stay between −12 V (forward drop ≈ 0.3 V) and +12 V.
Wrong (Pin 2 → GND instead of signal): clamps to GND, not ±12 V — circuit still functions but
clamps at the wrong levels. Every schematic must show this connection explicitly with pin numbers.

## Unity-Gain Input Buffer

After the protection network, drive a non-inverting op-amp buffer:

```
IN ──┬──(+)──[TL072 half]──(out)──── to internal signal node
     └────────────────────(−)
     (feedback: output tied directly to inverting input)
```

- Input impedance: ~1 MΩ (op-amp input impedance)
- Output impedance: ~75 Ω (open-loop output resistance of TL072)
- Use one half of TL072 (SOIC-8) per channel; quad TL074 (SOIC-14) for 4 inputs per IC

## Normalling

For jacks that normalize to another signal (e.g., mod source jack normalizes to ENV OUT):
- Use tip-switching (TS) Thonkiconn PJ301M-12 jack socket
- Normalled signal connects to the sleeve switching lug
- When a cable is inserted, the tip disconnects from the sleeve lug, breaking the normalling
