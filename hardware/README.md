# Hardware

The KiCad 10 project for the SWC board: 65 × 55 mm, 2 layers, 1.6 mm FR-4, ENIG, all components on the top side. Most parts are SMT and meant for factory assembly; the XIAO RP2040 plugs into two sockets.

| File | What |
|---|---|
| `tacoma_swc_only.kicad_pro` / `.kicad_sch` / `.kicad_pcb` | The KiCad project, with four schematic sheets: interface, power, inputs, outputs |
| `fab/` | Gerbers, BOM, placement files, assembly drawings, [ordering notes](fab/ORDERING.md) |
| `enclosure/` | 3D-printable case: STL, STEP and the generator; see its [README](enclosure/README.md) |
| `checks/` | Schematic PDF, layout PDF, top/bottom SVGs, ERC/DRC reports, design-check results, netlist, simulation outputs |
| `design_intent.json`, `output_commands.json`, `parts_selection.json` | Machine-readable pin, net, command and part data that the scripts and firmware tests check against |
| `build_schematic.py`, `build_board.py`, `clean_route_stubs.py`, `check_design.py` | Scripts that generate and check the design (see [Rebuilding](#rebuilding)) |
| `simulation/`, [`simulation_review.md`](simulation_review.md) | ngspice checks of the inputs, outputs, command transitions and layout spacing |
| `footprints/`, `Tacoma.kicad_sym` | Project footprint and symbol libraries |
| `3dmodels/` | Simplified Micro-Fit (J1) model and its generator, since KiCad's library has none |

**Status.** This is the board that was built: the PCB file's SHA-256 was `6188309d…cdaf1a` when it was fabricated. Since then only the 3D model references for J1 and A1 have changed, so copper, DRC and Gerbers are the same. It passes ERC (0 violations) and DRC with schematic parity (0 violations, 0 unconnected, 0 parity errors). Two factory-assembled boards were bench-tested with the radio; see the [main README](../README.md#status).

## Circuit

| Block | Parts | What it does |
|---|---|---|
| **Power input** | F1 250 mA fast fuse, D1 STPS1H100A, R1 10 Ω 1 W, D2 SMBJ24A, C1 47 µF/63 V, C2 10 µF/63 V | ACC → fuse → reverse-blocking Schottky → 10 Ω → TVS clamp. R1 limits the current the TVS has to absorb. |
| **Regulator** | U1 LT3012EDE (DFN-12), R2 30.1 k / R3 10.0 k (0.1 %), C3 22 µF polymer | 5 V nominal (4.97 V). The LT3012 tolerates reverse input and up to 80 V. The output goes to the XIAO's 5 V pin through JP1. |
| **JP1** | 2-pin header + shunt | Disconnects the regulator from the XIAO. **Pull it before connecting USB**: the XIAO's 5 V pin is tied directly to USB VBUS. |
| **Wheel inputs** | D5/D6 BAS70, R5/R6 2.2 kΩ, R7/R8 22 kΩ, C5/C6 10 nF, D7/D8 BAS70-04, R4 330 Ω | Each line is pulled up from the XIAO's 3.3 V through a diode and 2.2 kΩ. The 22 kΩ + 10 nF filter and the clamp diodes protect the ADC pin. R4 bleeds 3.3 V so that small clamp currents can't lift the rail. |
| **Outputs** | Q1/Q3/Q5/Q6/Q7 AO3400A, R11 47 Ω, R13 191 Ω, R15 390 Ω, R16 1 kΩ, R17 2 kΩ (1 %), 1 kΩ gate resistors, 100 kΩ gate pull-downs | Five low-side branches from SWRC+ to SWRC GND. The pull-downs keep every branch off while the XIAO is in reset or unplugged. |
| **C11** | 10 nF | Across SWRC+ / SWRC GND. Softens the switching edges. |
| **NT1** | net tie | Bonds SWRC GND to the board ground. |

### XIAO pins

The firmware uses RP2040 GPIO numbers, not the XIAO's D labels.

| Carrier pad | XIAO label | RP2040 | Function |
|---:|---|---|---|
| 1 | D0 | GP26 / ADC0 | SW1 |
| 2 | D1 | GP27 / ADC1 | SW2 |
| 7 | D6 | GP0 | 47 Ω branch (Q1) |
| 8 | D7 | GP1 | 191 Ω branch (Q3) |
| 9 | D8 | GP2 | 390 Ω branch (Q5) |
| 10 | D9 | GP4 | 1 kΩ branch (Q6) |
| 11 | D10 | GP3 | 2 kΩ branch (Q7) |
| 12 | 3V3 | | Pull-up and clamp supply (from the XIAO's own regulator) |
| 13 | GND | | |
| 14 | 5V | | From JP1 |
| 3–6 | D2–D5 | | Not used |

Pads are numbered DIP-style: viewed from above with USB at the top, 1–7 run down the left side and 8–14 run up the right.

### Command masks

| Command | Branches | Ω | GPIO mask |
|---|---|---:|---:|
| Release | none | open | `0x00` |
| Volume Down | Q1 | 47 | `0x01` |
| Volume Up | Q3 + Q5 | 128.2 | `0x06` |
| Source | Q3 | 191 | `0x02` |
| Seek Up | Q5 + Q6 | 280.6 | `0x14` |
| Seek Down | Q5 | 390 | `0x04` |
| Phone | Q6 | 1000 | `0x10` |
| Mic Mute | Q7 | 2000 | `0x08` |

## Power budget

| | |
|---|---|
| Measured, 12 V ACC, XIAO running, no USB | 25 mA total |
| Measured, 12 V ACC, XIAO removed | under 1 mA |
| Design allocation | 60 mA |
| U1 dissipation at 16 V, 25 mA | about 0.3 W (U1 plus R1) |

At the measured current, U1, C3 and R1 aren't noticeably warm. The case has vents over U1 and R1 anyway.

## PCB layout

- **Placement.** J1 is on the top edge, and the XIAO sits on the left with its USB port facing up. The output bank runs along the bottom, and the power section is on the right. There's an M3 mounting hole in each corner, with a 7 × 7 mm copper keep-out around each.
- **Routing.** Freerouting, imported into KiCad and cleaned up. Signals are 0.3 mm; ACC and the SWRC return are 0.6 mm. There are ground pours on both layers. U1's exposed pad has four ground vias.
- **ACC spacing.** `tacoma_swc_only.kicad_dru` keeps at least 2 mm between every ACC net and SWRC+ or the output-branch nets; the layout gives about 2.15 mm. So a stray solder bridge is unlikely to put 12 V on the radio's input.
- **XIAO sockets.** The two Samtec SSW-107-01-G-S sockets are 15.24 mm apart in 1.04 mm finished holes. Nothing on the carrier sits under the module.
- **3D models.**
  - J1 uses `3dmodels/Molex_Micro-Fit_3.0_43045-1210_simplified.step`, generated by `3dmodels/make_microfit_model.py`.
  - A1 uses two of KiCad's `PinSocket_1x07_P2.54mm_Vertical` models. There's no model of the XIAO module itself.

## Simulation

`simulation/run_simulation.py` builds ngspice circuits from the KiCad netlist. Results are in `checks/simulation/`, and the summary is in [`simulation_review.md`](simulation_review.md). The checks cover:

- **Input bands:** every wheel resistance over the tolerance sweep lands in its own band.
- **Outputs:** every command lands inside its Continental window.
- **Transitions:** all 56 command-to-command changes, at two C11 values (`check_command_transitions.py`).
- **Firmware:** 3,024 cases with the real C++ decoder driven by simulated ADC waveforms, including bounce and RC settling (`check_firmware_integration.py`).
- **Faults:** an ACC bridge onto SWRC+, and a drain-source short.

The MCU and radio are modelled as simple stubs, so these results show the design is consistent, not that it survives every fault.

## Rebuilding

Run from the repository root:

```sh
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3

python3 hardware/check_design.py                             # pin/net/part checks → checks/design_checks.json
python3 hardware/simulation/run_simulation.py                # ngspice (needs ngspice on PATH)
python3 hardware/simulation/check_command_transitions.py
python3 hardware/simulation/check_firmware_integration.py
$KPY hardware/simulation/audit_layout.py                     # ACC spacing audit

kicad-cli sch erc --format json -o hardware/checks/erc.json hardware/tacoma_swc_only.kicad_sch
kicad-cli pcb drc --schematic-parity --format json -o hardware/checks/pcb-drc.json hardware/tacoma_swc_only.kicad_pcb
```

`build_schematic.py` and `build_board.py` generated the original schematic and placement. **Re-running them overwrites the KiCad files**, including the routing. Edit the KiCad files directly instead, unless you mean to start over.
