# Change 0017: interactive BOM — hide ref/block/function when collapsed by value
- Lane: C   Status: CLOSED   Blocks: none (docs viewer only)
Intent: when "collapse by value" is on in `docs/bom.html`, hide the Ref, Block, and
Function columns (they aggregate many parts and stop being per-row meaningful in that
view). Add a "sort" dropdown to the toolbar so any column — including the now-hidden
Block — stays sortable; the dropdown stays in sync with header-click sorting. No DSP,
panel geometry, `components.yaml`, or netlist changes. No gates. PR to follow.
