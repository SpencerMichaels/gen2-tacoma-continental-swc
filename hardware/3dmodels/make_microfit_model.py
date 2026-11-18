"""Simplified 3D model of the Molex Micro-Fit 3.0 43045-1209/1210/1211 (12 circuit, dual row, right angle, SMT).

KiCad's library has no Micro-Fit 43045 models, so this script makes a visual stand-in for
renders: the housing is the footprint's F.Fab outline extruded to the 10.3 mm mated height,
with twelve mating cavities, the SMT pin tails and the two retention tabs. It is not a
dimensioned Molex model.

Run:  /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd make_microfit_model.py
Writes Molex_Micro-Fit_3.0_43045-1210_simplified.step next to this file.
Coordinates follow KiCad's model convention: footprint origin, X right, Y = -footprint Y.
"""
import os
import FreeCAD as App
import Part

V = App.Vector
HERE = os.path.dirname(os.path.abspath(__file__))
H = 10.3                     # housing height above the board
BACK, FACE = 2.475, 12.385   # housing back and mating face (footprint Y negated)
ROWS = {3.3: 2.315, 6.3: -2.315}   # cavity height -> pad row Y (pins 1-6 lower, 7-12 upper)
COLS = [-7.5, -4.5, -1.5, 1.5, 4.5, 7.5]
# F.Fab outline from Molex_43045_12_SMT_SeparateRetentionPads (footprint Y negated)
outline = [(-10.825, BACK), (-10.825, 10.385), (-9.825, FACE), (9.825, FACE), (10.825, 10.385), (10.825, BACK)]
wire = Part.makePolygon([V(x, y, 0) for x, y in outline] + [V(*outline[0], 0)])
housing = Part.Face(wire).extrude(V(0, 0, H))
cav, depth = 2.4, 7.0        # mating cavities, open toward the board edge (+Y)
for zc in ROWS:
    for xc in COLS:
        housing = housing.cut(Part.makeBox(cav, depth, cav, V(xc - cav / 2, FACE - depth, zc - cav / 2)))

t, w = 0.3, 0.64             # pin tail thickness and width
parts = []
for zc, yp in ROWS.items():
    y0 = yp - 0.9            # outer end of the solder foot
    for xc in COLS:
        x0 = xc - w / 2
        parts.append(Part.makeBox(w, 1.8, t, V(x0, y0, 0)))                         # foot on the pad
        parts.append(Part.makeBox(w, w, zc + w / 2, V(x0, y0, 0)))                  # riser
        parts.append(Part.makeBox(w, BACK + 0.5 - y0, w, V(x0, y0, zc - w / 2)))    # into the housing
for s in (-1, 1):            # retention tabs over MP1/MP2 (footprint (±11.385, -7.785))
    xin = s * 10.825
    xout = s * 12.9
    parts.append(Part.makeBox(abs(xout - xin), 1.2, t, V(min(xin, xout), 7.785 - 0.6, 0)))
    parts.append(Part.makeBox(t, 1.2, 4.0, V(xin if s > 0 else xin - t, 7.785 - 0.6, 0)))
shape = housing.fuse(parts).removeSplitter()
shape.exportStep(os.path.join(HERE, 'Molex_Micro-Fit_3.0_43045-1210_simplified.step'))
print('ok', shape.isValid(), shape.Volume)
