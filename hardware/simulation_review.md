# SWC simulation and output-protection revision — 2026-09-30

## Result and changes

Added **C11: 10 nF, 50 V, X7R, 0805** between SWRC+ and SWRC_GND, using KEMET C0805C103K5RACTU (also used for C5/C6). Updated native schematic, board, engineering BOM, and authoring/verification scripts. Board outline remains 65×55 mm; connector and module locations are unchanged.

Rerouted the radio-output trunk away from ACC circuitry. The custom KiCad rule requires **2 mm minimum same-layer clearance** from ACC/ACC_FUSED/ACC_DIODE/ACC_CLAMP to SWRC+ and all five branch-drain nets. Current native-shape audit measures **2.148 mm** minimum (ACC_CLAMP / SWRC_PLUS, F.Cu, raw feature R1.2). The audit examined 4,419 feature pairs. Newly added vias are tented on both sides. Copper pours remain GND.

This reduces accidental bridging risk. It is **not** a rated isolation barrier or a guarantee against arbitrary faults. C11 suppresses brief switching feedthrough; it does not clamp a sustained 12 V connection.

## Checks

- KiCad ERC: 0 reported violations.
- KiCad PCB DRC: 0 violations; 0 unconnected items; 0 schematic-parity mismatches.
- Independent net/pin checks include C11 polarity-free connection to SWRC+ / SWRC_GND and its required 10 nF value.
- ngspice result: **PASS_WITH_MODEL_LIMITATIONS**, 0 normal-function assertion failures.
- 3,249 input operating points and 29,241 decoder checks: published resistance endpoints/midpoints, supply and pull-up tolerances, ADC offsets, released/open wires, invalid examples, and combinations across both lines.
- 3,249 end-to-end input → stub MCU → settled output checks.
- 2,304 output DC cases: all 32 masks, radio supplies 0/3.3/5 V, pull-ups 470 Ω/1 kΩ/2.2 kΩ/10 kΩ, ±1% command resistors and assumed switch-resistance corners.
- 63 switching cases: seven commands, three pull-ups, three assumed intrinsic radio capacitances; physical C11 is included separately from intrinsic capacitance.
- 7 bounced-button sequences and 6 reset/high-impedance/power-off DC cases.

| Command | Effective resistance across modeled DC corners, Ω |
|---|---:|
| volume_down | 46.54–47.57 |
| volume_up | 126.93–129.55 |
| source | 189.10–193.01 |
| seek_up | 277.78–283.44 |
| seek_down | 386.11–394.00 |
| phone | 990.01–1010.10 |
| mute | 1980.01–2020.10 |

Every command remains inside the measured Continental acceptance window. Invalid/both-active inputs release under the modeled contract. Same-line button combinations or a short mimicking a valid resistance cannot necessarily be distinguished.

With the radio pull-up modeled as 470 Ω, the largest switching peak is **3.3061 V** for an assumed 3.3 V radio supply. This is an approximate model result, not a measured or guaranteed peak. The earlier inferred 470 Ω comes from 3.30 V unloaded and 1.63 V with an approximately 470 Ω load. The inference is a DC equivalent, not a complete radio model or an absolute-maximum specification. Historical capacitor A/B results are in `simulation/radio_pullup_followup.md`.

## What is and is not protected

There is no intentional DC supply connection to SWRC+. Its exact net inventory is J1 pin 9, TP3, C11 pin 1 and the five command-resistor ends. Each resistor connects to a MOSFET drain; sources connect to SWRC_GND. NT1 bonds that return to vehicle ground. All 32 static MCU masks select passive loads, not a vehicle-power source.

A simulated 0.1 Ω ACC-to-SWRC+ bridge still drives SWRC+ to approximately 12 V. The fact that the model completes is not a safety pass. A bridge to an upstream ACC point bypasses the board fuse; a downstream fault can also damage a signal input without drawing enough current to clear that fuse. The ACC TVS is not a radio-input clamp. A capacitor cannot stop a DC fault. This remains true after the spacing improvement.

MOSFET gate insulation is not certified galvanic isolation. Regulator/MCU/output-transistor failure cascades are not guaranteed contained. Isolated contacts could separate control electronics from the resistor network, but would not prevent a bridge that bypasses them at the output or shared connector. Loss of the main ground can also cause unintended return current through the radio-ground lead.

Reasonable MVP precautions are explicit spacing rules, solder mask and tented signal vias, supplier bare-board electrical testing and assembly inspection, radio-disconnected bench checks using a dummy input, and the planned insulating enclosure/strain relief. See the README for the practical checklist. No additional shunt clamp or active fault disconnect has been fitted.

## Model boundaries

The test engine is ngspice 45.2 bundled with KiCad. R/C/diode/switch connections are taken from the exported KiCad netlist. The MCU is a Python decoding/debounce stub, not compiled firmware. No physical board has been tested.

The output switches use a smooth behavioral conductance approximation, with assumed on-resistance and fixed gate/drain/source capacitances. Diodes are approximate models. AO3400A datasheet capacitances are typical values at a different bias condition, not worst-case bounds. Actual radio impedance, capacitance and protection thresholds remain unknown. C11 is ideal in this simulation; capacitor tolerance, voltage/temperature dependence and PCB parasitics are not fully characterized. The input and command-resistor sweeps are also bounded examples, not exhaustive physical failure coverage.

Regulators/ACC protection are not simulated; the logic supply is ideal. Automotive surge survival, temperature rise, ESD, device failure, firmware timing and true brownout behavior still require appropriate validation. Simulation supports normal behavior under assumptions and cannot prove “never under any fault.”

## Artifacts and reproduction

Current native files: `tacoma_swc_only.kicad_sch`, four child sheets, `tacoma_swc_only.kicad_pcb`, `tacoma_swc_only.kicad_dru`, `fab/BOM.csv`, `parts_selection.json`.

From the project root:

```sh
python3 hardware/simulation/run_simulation.py
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 hardware/simulation/audit_layout.py
python3 hardware/simulation/write_report.py
```

Re-export the KiCad XML netlist and rerun ERC, DRC with schematic parity, and `check_design.py` after any design edit. Saved reports and example SPICE decks are in `checks/simulation/`; JSON records the input netlist/board hashes. `NGSPICE_LIBRARY` can override the bundled library path. Historical pre-change findings are preserved in [the earlier audit](simulation_review_before_c11.md); they describe the older PCB, not the current one.

References: [AO3400A datasheet](https://www.aosmd.com/res/data_sheets/AO3400A.pdf), [ngspice manual](https://ngspice.sourceforge.io/docs/ngspice-manual.pdf), [KiCad custom-rule documentation](https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html), and the Continental measurements in [docs/interface.md](../docs/interface.md).

## Additional command-transition coverage

112 directed transition/capacitance cases: PASS_WITH_MODEL_LIMITATIONS. All 56 changes between seven commands plus release are tested at C11 = 7 and 13 nF, with a proposed 20 microsecond all-off interval. Destination checks pass by 178 microseconds after the new mask finishes switching. These capacitor values are a sensitivity screen, not manufacturer worst-case limits. Intermediate voltages can resemble other commands; actual receiver debounce is unknown. Real firmware and power sequencing still need prototype tests. See the README remaining-verification checklist.
