# Enclosure

A two-piece printed case for the 65 × 55 mm SWC board.

- **J1 opening:** only **J1**, the Molex Micro-Fit 2×6 harness connector on the board's top edge, gets an opening.
- **Enclosed:** the XIAO's USB-C port and JP1 stay inside. Programming means pulling JP1 first (see the [main README](../../README.md#safety-notes) and the board silkscreen), so the cover has to come off anyway.
- **Vents:** slots in the cover vent the heat from U1 and R1.

| File | Purpose |
|---|---|
| `swc_case_base.stl` | Tray with four stepped board standoffs. Print floor-down. |
| `swc_case_cover.stl` | Cover with clamp posts, XIAO hold-down pad, vent slots and engraved labels, already flipped to print **top-down**. |
| `swc_case.step` | Both parts in assembly position, for CAD. |
| `swc_board.step` | KiCad 3D export of the board, used for the previews and fit check. It's exported from a temporary copy of the board file, so the KiCad project is never modified. |
| `build_enclosure.py` | Parametric generator. Re-run after changing a dimension (see below). |
| `preview_*.png`, `build_report.txt` | Renders, the vent-over-pad map, and the fit-check result. |

## Size and fit

- **Outside:** 70 × 60 × 27.6 mm. It's a plain box with 3 mm rounded corners and no mounting ears, so nothing snags the wiring bundle.
- **Walls and clearances:**
  - 2 mm wall, floor and top.
  - 0.5 mm clearance from the board to the walls.
  - 4 mm below the board: the socket tails (2.64 mm) clear the floor by 1.4 mm.
  - 18 mm above the board.
- **Tallest part:** JP1 with its handled shunt, at 16.51 mm. It clears the ceiling by 1.5 mm.
- **XIAO hold-down:** the XIAO stack is 14.55 mm tall. A 2 mm pad under the ceiling stops 1.5 mm above it, so the module can move at most 1.5 mm. The sockets engage at least 3.68 mm, so it can't work loose. A module up to 1 mm thicker than Seeed's figure still fits.
- **J1 opening:** 0.5 mm clearance around the header face. It runs 13.8 mm up from the board: the 10.29 mm mated height plus 3 mm for the latch and a fingertip. The header face sits 2.6 mm behind the outside of the wall, so the plug's latch lever stays outside the case.
- **Fit check:** the generator checks both parts against:
  - the KiCad board model and 46 component models;
  - envelopes for the parts KiCad has no model for (J1, the XIAO stack and sockets, the JP1 shunt, F1);
  - the J1 insertion path;
  - label spacing;
  - vent placement.

  The result is **PASS** (`build_report.txt`). Both STLs are watertight, with no non-manifold edges or self-intersections.
- **Orientation:** in `preview_top_view.png`, compare the case and board against the KiCad top view. Facing the J1 end of the case, J1 sits left of centre.

## Ventilation

U1 (LT3012) and R1 (10 Ω, 1 W) were sized for up to about 0.95 W together, a conservative design allocation. At the measured 25 mA they dissipate about 0.3 W at 16 V. Air comes in low through one side wall and goes out the top.

| Group | Where | Count | Open area |
|---|---|---:|---:|
| Top | Regular array centred over R1/U1: 5 identical 16 mm slots along X, forming a 16 × 17 mm block | 5 | 141 mm² |
| Side (inlet) | +X wall next to R1/U1, from 3.7 to 10.7 mm above the board, clear of the J1 end | 9 vertical slots, 7 mm tall | 107 mm² |
| **Total** | | **14** | **248 mm²** |

- **Slot size:** both groups use the same 1.8 mm slot width and 3.8 mm pitch, which leaves 2 mm webs. Each top slot sits in line with a side slot, so the two groups read as one pattern.
- **Clearances:** the generator checks that the array stays at least 2 mm from:
  - the labels;
  - the cover posts;
  - the walls, locating lip and corner radius;
  - the XIAO hold-down pad;
  - J1 and its opening.
- **Pads below the top slots:** a 1.8 mm slot can't pass an M3 screw, so slots aren't trimmed around pads any more. The pads that lie under the array are listed in `build_report.txt` and shown in `preview_vent_pad_map.png`, for information only.
- **Printing:** the top slots print as the first layers. The side slots have semicircular ends, so they print without supports when the cover is printed top-down.

## Dimensions used

| Item | Value | Source |
|---|---|---|
| Board outline, holes, part positions | 65 × 55 × 1.6 mm, M3 at (4.5, 4.5) … (60.5, 50.5) | `tacoma_swc_only.kicad_pcb`, read with pcbnew (read-only) |
| XIAO sockets, Samtec SSW-107-01-G-S | 8.51 mm body, 2.64 mm tail, 3.68–6.35 mm insertion depth | Datasheet: [Samtec SSW catalog page](https://suddendocs.samtec.com/catalog_english/ssw_th.pdf) |
| XIAO RP2040 module, including USB-C | 3.5 mm thick (20 × 17.5 × 3.5 mm) | Seeed listing: [The Pi Hut / Seeed spec](https://thepihut.com/products/seeed-xiao-rp2040) |
| Male header body under the XIAO, Seeed 102010490 | 2.54 mm | **Estimate.** Seeed doesn't publish it ([product page](https://www.seeedstudio.com/XIAO-Series-7-Pin-Male-Header-5-pcs-p-5460.html)). 2.54 mm is the standard .100" body, the same as Samtec TSW. |
| USB-C overhang past the module outline | 1 mm | **Estimate**, from the Seeed board images |
| JP1 header, Samtec TSW-102-07-G-S | 2.54 mm insulator, 5.84 mm post | Datasheet: [Samtec TSW catalog page](https://suddendocs.samtec.com/catalog_english/tsw_th.pdf). The KiCad model agrees. |
| JP1 shunt, Samtec SNT-100-BK-T-H | 13.97 mm overall with handle, 5.08 × 2.54 mm body | Datasheet: [Samtec SNT-100 print](https://suddendocs.samtec.com/prints/snt-100-xx-x-x-mkt.pdf), -H option |
| J1, Molex 43045-1209 | 10.29 mm mated height | Molex part pages for the same-housing 12-circuit right-angle headers: [43045-1200](https://www.molex.com/en-us/products/part-detail/430451200) gives 10.29 mm and [43045-1222](https://www.molex.com/en-us/products/part-detail/430451222) gives 10.06 mm. No figure is published for -1209 itself, and the Molex drawing site timed out. |
| F1, Littelfuse 451 NANO2 | 6.10 × 2.69 × 2.69 mm | Distributor data: [RS listing](https://benl.rs-online.com/web/p/non-resettable-fuses/7693725) |
| C1, R1, SMT parts | — | KiCad 3D models |

### Values that remain estimates

These come from the case's own geometry; no datasheet was found for them. Check them on the real parts if you can:

| Parameter | Value | Note |
|---|---|---|
| `HDR_SPACER` | 2.54 mm | The XIAO's male-header body. If it's taller, the hold-down pad needs `HOLD_GAP` reduced, or the stack raised. |
| `MICROFIT_H` | 10.29 mm | J1, from the same-housing sibling parts. The opening has 3 mm of spare height above it. |
| `XIAO_H` | 3.5 mm | Seeed's own figure. A community measurement of another XIAO found 4.5 mm over the USB-C, and the hold-down pad still clears that by 0.5 mm. |

After changing a value, re-run:

```sh
/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd build_enclosure.py
```

## Printing (PrusaSlicer)

- **Material:** **PETG or ASA**, not PLA. Behind the dash the case gets hot enough for PLA to creep. Use unfilled filament, not metal- or carbon-filled.
- **Orientation:** the files are already oriented this way.
  - Base: floor on the bed.
  - Cover: top on the bed, so the labels and top vents print as the first layers.
- **Supports:** none needed. The J1 opening is open toward the split line, and the side slots have rounded tops.
- **Settings:** 0.2 mm layers, 3 perimeters, 20–30 % infill. A 0.4 mm nozzle resolves the 3 mm labels and the 1.8 mm slots.
- **Test print first:** do a test fit with the populated board, XIAO and JP1 shunt before installing.

## Hardware and assembly

- **Screws:** 4 × M3 × 12 mm, pan head (ISO 7045) or socket head (ISO 4762).
  - They go in from underneath, through the base standoffs and the board's mounting holes, and thread into 2.6 mm pilot holes in the cover posts.
  - That gives about 7.6 mm of thread engagement. The tip stops 4.4 mm short of the bottom of the pilot hole.
  - Heads sit flush in 6.0 × 3.2 mm recesses, so nothing protrudes below the base.
  - Ordinary machine screws cut their own thread in PETG or ASA. Thread-forming screws for plastic also work. No nuts are needed.
- **Assembly:**
  1. Fit the XIAO and the JP1 shunt.
  2. Set the board on the base standoffs, with J1 at the notched end of the base.
  3. Lower the cover. The lip around the base locates it.
  4. Screw from below. The cover posts clamp the board onto the standoffs.
- **Programming:** unscrew, lift the cover, and remove JP1 before plugging in USB.
- **Mounting:** none needed; it sits in the wiring bundle.
  - Keep the vented +X side and the top uncovered. Don't wrap the whole case in harness tape. A band around the J1 end, or foam tape or Velcro on the flat base, works.
  - Support the harness so the case doesn't hang from J1.
- **Not sealed:** the vents let dust in. U1's heat in a hot dash is was measured at 25 mA on the bench, with no noticeable heating.
