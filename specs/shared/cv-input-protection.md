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
| D_clamp | BAT54S | SOT-23 | — | Dual Schottky, common anode/cathode to rails |
| C_bypass | 100 nF | 0603 | 100 nF | Optional: across input to GND for HF filtering |

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
