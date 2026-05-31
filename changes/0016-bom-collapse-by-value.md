# Change 0016: interactive BOM — collapse-by-value toggle
- Lane: C   Status: CLOSED   Blocks: none (docs viewer only)
Intent: add an optional "collapse by value" checkbox to `docs/bom.html` so identical parts
(same board/type/value/package/MPN/footprint/datasheet) fold onto one line — refs listed,
Qty summed, Block/Function unioned. Independent of the existing "group by block" toggle
(when both on, collapse happens within each block group). Total pcs is preserved
(476 raw refs → 59 distinct values; 905 pcs unchanged). No DSP, panel geometry,
`components.yaml`, or netlist changes. No gates. PR to follow.
