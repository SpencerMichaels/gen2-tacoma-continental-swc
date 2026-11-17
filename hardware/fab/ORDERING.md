# Ordering

The board was built by PCBWay with full assembly. Any turnkey PCB assembly service should work.

## Files to upload

| File | What |
|---|---|
| [`tacoma_swc_gerbers.zip`](tacoma_swc_gerbers.zip) | Gerbers, PTH/NPTH drills, Gerber job file and fabrication notes. The same files are unpacked in [`gerbers/`](gerbers/). |
| [`BOM.csv`](BOM.csv) | One combined BOM. It covers the 46 SMT parts and 4 through-hole parts on each carrier, plus the XIAO module, its headers and the JP1 shunt. The last column is the quantity for two boards. |
| [`assembly/smt-placement.csv`](assembly/smt-placement.csv) | SMT centroid file. Units are mm, origin at the board's top-left corner, +X right, +Y up (so Y values are negative). |
| [`assembly/tht-placement-reference.csv`](assembly/tht-placement-reference.csv) | Through-hole positions: R1, JP1 and the two XIAO sockets |
| [`assembly/top-assembly.svg`](assembly/top-assembly.svg), [`socket-placement.svg`](assembly/socket-placement.svg), [`u1-pin-detail.svg`](assembly/u1-pin-detail.svg) | Assembly drawings: top view, the XIAO socket strips, and U1's pin 1 |

## Board spec

65 × 55 mm, 2 layers, 1.6 mm FR-4, 1 oz copper, ENIG, any mask colour. All components go on the top side.
- **Socket holes:** the 14 XIAO socket holes are 1.04 mm finished. Ask the fab to confirm their tolerance.
- **Mounting holes:** the four 3.2 mm holes are non-plated.

## Notes for the assembler

- **XIAO module.** Ask for the **standard Seeed XIAO RP2040 (102010428), not the Plus**, with its two 1 × 7 male headers (Seeed 102010490) soldered on. Ship it unplugged. Don't solder it to the carrier: it plugs into the two Samtec SSW-107-01-G-S sockets (A1L, A1R).
- **JP1 shunt.** Samtec SNT-100-BK-T-H, the version with a pull handle. Ship it loose.
- **J1.** Molex 43045-1209 is a right-angle SMT Micro-Fit header with solder retention tabs. It may need the assembler's global-sourcing service. 43045-1210 and 43045-1211 share the footprint and differ only in contact plating. The through-hole 43045-1200 does **not** fit this footprint.
- **U1.** Use the automotive-grade LT3012EDE: `#WPBF` (tube) or `#WTRPBF` (reel). The plain `#PBF` and `#TRPBF` versions aren't the automotive grade. Its exposed pad is ground.
- **Polarised parts.** C1 (electrolytic) and C3 (polymer, pad 1 is +) are polarised; both are marked on the silkscreen.

## Cost

For reference, in October 2026: two assembled boards plus three bare boards came to about **$194** before shipping. That was $44 for fabrication, $29 for assembly and $121 for parts (including two XIAOs). Lead time was about four weeks.

## Hand assembly

It's possible, but it isn't what the board was laid out for.
- **U1** is a 3 × 4 mm DFN with a thermal pad: it needs hot air or a hotplate.
- **J1** is SMT with large retention tabs.
- **Everything else** is 0805/1206, SOT-23, SMA/SMB, or through-hole.
