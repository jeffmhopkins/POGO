# Standard CV / Audio Input Protection Circuit

**Type:** `utility` · part of the [aux circuit library](../../_LIBRARY.md)

> ✅ **Re-verified 2026-05-30** (change 0018). 100Ω + BAT54S clamp; tip-switch normalling pattern.

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
| D_clamp | BAT54S | SOT-23 | — | Dual Schottky **series** configuration; the **series junction is the signal node**. **Pin orientation (CRITICAL, per Diodes Inc DS11005)**: Pin 1 = A1 (anode D1) → connect to −12 V; Pin 2 = K2 (cathode D2) → connect to +12 V; Pin 3 = K1;A2 (the series junction) → connect to the signal node (after 100 Ω). A pin-labeling error creates silent failure (no/incorrect clamping). Every schematic using BAT54S must show Pin 1, 2, 3 explicitly. |
| C_bypass | 100 nF | 0603 | 100 nF | Optional: across input to GND for HF filtering |

## BAT54S Pinout Reference

```
BAT54S SOT-23 (series dual Schottky — junction at the signal node):

  Pin 1 = A1              Pin 3 = K1;A2 (series junction)          Pin 2 = K2
  ──►|── D1 ──────────────►  = SIGNAL NODE  ──────────── D2 ──►|──
  → −12 V rail            (signal, after 100 Ω series R)          → +12 V rail

  D1: A1(pin1, −12 V) → K1(pin3, signal)    low clamp  (conducts when signal < −12.3 V)
  D2: A2(pin3, signal) → K2(pin2, +12 V)    high clamp (conducts when signal > +12.3 V)
```

Correct: the signal sits on the **series junction (Pin 3)**, clamped to stay between −12 V
and +12 V (Schottky forward drop ≈ 0.3 V). **Pin 3 — not Pin 2 — is the junction.** An earlier
revision of this doc mislabeled the signal node as Pin 2; with a real BAT54S that reverse-biases
D1 and pins the input toward +12 V (silent failure). Every schematic must show this connection
explicitly with pin numbers.

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
- **Block A exception**: uses OPA1612 (SOIC-8, pin-compatible) instead of TL072 because Block A
  is the first active stage — its noise is amplified by all downstream blocks. OPA1612: 1.1 nV/√Hz, 5.5 mA/pkg.

## Normalling

For jacks that normalize to another signal (e.g., the BP3_R output jack normals to BP3_L):
- Use tip-switching (TS) Thonkiconn PJ301M-12 jack socket
- Normalled signal connects to the sleeve switching lug
- When a cable is inserted, the tip disconnects from the sleeve lug, breaking the normalling
