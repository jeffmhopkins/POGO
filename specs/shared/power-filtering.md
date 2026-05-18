# Standard Power Supply Filtering

Applied to every POGO PCB at the power connector and at each IC.

## Power Connector (16-pin IDC, Doepfer A-100 compatible)

```
Pin 1–2   −12 V  ←  RED STRIPE (always orient red stripe toward −12 V label on busboard)
Pin 3–10  GND
Pin 11–12 +5 V   (not used — regulate on-module from +12 V if +5 V is ever needed)
Pin 13–16 +12 V
```

Verify pinout against your busboard before PCB layout — orientation errors destroy ICs.

## Reverse Polarity Protection

Series Schottky diode on each rail at the power header:
- Part: BAT85 (SOD-80, 200 mA) or similar
- Adds ~0.3 V forward drop — choose op-amps that tolerate (11.7 V / −11.7 V rails)
- TL072/TL074: rated ±18 V, tolerates this headroom reduction without issue

Power-on indicator: red LED + 1 kΩ series resistor across the +12 V rail (after the diode).

## Board-Level Filtering at Power Header

```
+12 V rail:  [ferrite bead FB1]──┬── to board +12 V plane
                                  ├── 10 µF electrolytic (≥25 V) to GND
                                  └── 100 nF ceramic to GND

−12 V rail:  [ferrite bead FB2]──┬── to board −12 V plane
                                  ├── 10 µF electrolytic (≥25 V) to GND
                                  └── 100 nF ceramic to GND
```

Ferrite bead: Murata BLM18AG601SN1D (600 Ω at 100 MHz, 500 mA rated, 0603)

## Per-IC Decoupling

At every op-amp supply pin:
- 100 nF ceramic (0603, X7R or X5R) from V+ to GND, placed within 1 mm of pin
- 100 nF ceramic from V− to GND, placed within 1 mm of pin
- Do NOT rely on the board-level bulk caps alone — each IC must have local decoupling

## Ground

- Star ground topology: all ground returns meet at a single point near the power connector
- Panel ground: connect panel to module ground via a single low-impedance path
- Avoid ground loops between PCBs in a multi-board build — use a ribbon cable with a dedicated GND wire
