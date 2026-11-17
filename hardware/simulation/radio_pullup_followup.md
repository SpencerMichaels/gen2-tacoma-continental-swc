# Radio pull-up and switching-pulse follow-up — 2026-09-30

Historical A/B study: C11 has since been implemented. See `../simulation_review.md` for the current design and verification.

The earlier project measurements recorded 3.30 V open-circuit and 1.63 V with an approximately 470 ohm load. An ideal divider implies approximately 482 ohms; the original notes reasonably describe this as roughly 470 ohms. This is an inferred DC equivalent, not a complete input model or absolute-maximum specification.

The original transient sweep used 1k and 10k pull-ups and omitted this known estimate. Its 3.446 V worst case should not be presented as the expected peak for this radio.

`check_radio_pullup.py` repeats seven command transitions with the same approximate MOSFET model, a 470 ohm pull-up, 3.3 V source, and assumed 100 pF intrinsic input capacitance. It also evaluates a hypothetical 10 nF capacitor between SWRC+ and SWRC_GND. Results are in `../checks/simulation/radio_470ohm.json`.

| Fixture | Highest modeled peak |
|---|---:|
| Existing output, 470 ohm pull-up | 3.3635 V |
| Same fixture plus 10 nF across SWRC input | 3.3061 V |

All seven settled resistance windows pass in both configurations. These are sensitivity results, not guaranteed real peaks or evidence of the radio's damage threshold. Actual input capacitance, MOSFET nonlinear capacitance, wiring, temperature and radio protection are not characterized. The AO3400A capacitance figures used in the original approximation are typical values at a different bias condition, not worst-case bounds.

A small capacitor is a proportionate mitigation to consider: it reduces feedthrough without changing steady-state command resistances. With a 470 ohm pull-up, 10 nF adds an approximately 4.7 microsecond release time constant, or about 24 microseconds to settle within 1% in an ideal RC model. This is small relative to the proposed 20 millisecond debounce interval. It is not an ACC overvoltage clamp or protection against a direct 12 V bridge.

No schematic, BOM or PCB modification is made by this follow-up. Recommendation: include a modest output capacitor in the next design revision, subject to final component selection and verification. Do not infer that any universal +0.15 V allowance exists; radio absolute limits remain unknown. Conversely, this approximate, low-energy switching pulse alone does not justify concluding that the present circuit will damage the radio or that isolated outputs are necessary.

Measurement source: Continental SWRC measurements, see [docs/interface.md](../../docs/interface.md). Model reference: https://www.aosmd.com/res/data_sheets/AO3400A.pdf.
