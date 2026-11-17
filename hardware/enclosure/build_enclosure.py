"""Tacoma SWC (XIAO RP2040 carrier) enclosure v2: base tray + cover, generated with FreeCAD.

Run:  /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd build_enclosure.py
Writes swc_case_base.stl, swc_case_cover.stl, swc_case.step, preview_*.png and build_report.txt
next to this file. (print() is not captured by freecadcmd, so results go to build_report.txt.)

Board facts come from the frozen, read-only design hardware/swc_only/tacoma_swc_only.kicad_pcb
(read with pcbnew; nothing in that folder is ever written):
  * 65 x 55 x 1.6 mm rectangle, origin at the upper-left corner in the KiCad top view.
  * 4 x M3 NPTH holes (3.2 mm) at (4.5, 4.5), (60.5, 4.5), (60.5, 50.5), (4.5, 50.5), 7x7 mm keepouts.
  * J1 Molex 43045-1209 (Micro-Fit 3.0, 2x6, right-angle SMT) on the top edge (board y = 0),
    F.Fab x 31.12..52.88, mating face at y = 0.14; the harness plug goes in from outside that edge.
  * A1 XIAO RP2040 on two Samtec SSW-107 sockets (USB toward the top edge, inset ~9 mm),
    JP1 run/USB jumper, C1 8x10.5 electrolytic, R1 1 W axial. All SMT parts on the front.

Coordinates: X = board x, Y = -board y (board top edge at Y = 0, board runs to Y = -55),
Z up with the base floor underside at Z = 0. This is also KiCad's STEP export frame
(apart from the Z offset), so the exported board model drops straight in.
"""
import os, sys, subprocess
import FreeCAD as App
import Part, Mesh

_report = []
def log(*a):
    _report.append(' '.join(str(x) for x in a))

HERE = os.path.dirname(os.path.abspath(__file__))
V = App.Vector

# ---------------------------------------------------------------- parameters
BW, BD, PCB = 65.0, 55.0, 1.6
HOLES = [(4.5, 4.5), (60.5, 4.5), (60.5, 50.5), (4.5, 50.5)]   # board coords (KiCad, y down)
GAP = 0.5            # board edge to inner wall
WALL = 2.0
FLOOR = 2.0
STANDOFF = 4.0       # under-board clearance: socket tails 2.64 mm, R1/JP1 leads ~1.4 mm
TOP = 2.0
CORNER_R = 3.0       # outer vertical corner radius
TONGUE_W, TONGUE_H, FIT = 1.0, 1.5, 0.2    # base-to-cover locating lip and clearance
WIN_CLR = 0.5        # clearance around each connector face

# Heights above the board top (mm), from datasheets unless marked "est" (sources in README.md).
SSW_H = 8.51         # Samtec SSW-107-01-G-S socket insulator height (SSW catalog page F-226)
SSW_TAIL = 2.64      # SSW -01 tail length below the board (same page)
HDR_SPACER = 2.54    # est: male-header insulator under the XIAO. Seeed 102010490 is unspecified; 2.54 mm
                     #      is the standard .100" body (= Samtec TSW). The pins bottom at 6.35 mm max depth.
XIAO_H = 3.5         # XIAO RP2040 overall thickness incl. USB-C (Seeed listing: 20 x 17.5 x 3.5 mm)
XIAO_STACK_H = SSW_H + HDR_SPACER + XIAO_H      # 14.55 mm
TSW_INSUL = 2.54     # Samtec TSW-102-07-G-S insulator height (TSW catalog page; -07 post 5.84 mm)
SHUNT_H = 13.97      # Samtec SNT-100-BK-T-H overall height with handle (SNT-100 print, -H option)
JP1_SHUNT_H = TSW_INSUL + SHUNT_H               # 16.51 mm: the tallest part on the board
MICROFIT_H = 10.29   # Molex mated height for the Micro-Fit 3.0 dual-row right-angle 12-circuit header
                     # (43045-1200 part page; -1222 lists 10.06). No published value for -1209 itself.
F1_H = 2.69          # Littelfuse 451 NANO2 6.10 x 2.69 x 2.69 mm
HEADROOM = 18.0      # board top to ceiling: JP1 handled shunt + ~1.5 mm
HOLD_GAP = 1.5       # hold-down pad over the XIAO: stops 1.5 mm above its datasheet top, so the module
                     # can't back out of its sockets (travel 1.5 mm vs >= 3.68 mm engagement) and a
                     # module up to 1 mm thicker than the datasheet still fits.

# Ventilation (U1 LT3012 + R1 10R/1W dissipate up to ~0.95 W). Air in through the low slots in the
# +X side wall next to R1/U1, out through the slots in the top above them.
VENT_W = 1.8         # slot width (keeps fingers and debris out; side slots bridge <= 1.8 mm when printed)
VENT_WEB = 2.0       # solid material between slots
# Top array: VENT_TOP_N identical slots running along X (the same direction the side slots face),
# on the side slots' Y grid so each top slot lines up with a side slot. Centred over R1/U1.
VENT_TOP_N = 5
VENT_TOP_LEN = 16.0  # overall slot length incl. rounded ends
VENT_TOP_XC = 51.0   # board x of the array centre (R1 body centre 50.8, U1 51.0)
VENT_TOP_YC = 33.8   # board y of the array centre (snapped to the side-slot grid)
PAD_MARGIN = 0.5     # informational only: pads within this distance of a top slot are listed
VENT_SIDE_Y = (11.0, 44.0)      # board y range for the side-wall slots (+X wall)
VENT_SIDE_H = 7.0    # side slot height

# Screws: M3 from below, through the base standoff and board hole, into the cover post.
SCREW_L = 12.0
CBORE_D, CBORE_DEPTH = 6.0, 3.2   # head recess: fits ISO 7045 pan (5.6 x 2.4) or ISO 4762 socket (5.5 x 3.0)
CLEAR_D, PILOT_D, PILOT_DEPTH = 3.4, 2.6, 12.0
STANDOFF_D, STANDOFF_FOOT_D, FOOT_TOP = 7.0, 9.0, 4.4   # stepped standoff keeps >= 1.5 mm around the recess
POST_D = 6.0

# Exposed connectors on the top board edge: (label, x_left, x_right, face height, extra height
# above the body for the plug's latch lever and a fingertip). Only J1 is used in the vehicle.
CONNECTORS = [
    ('SWC HARNESS', 31.12, 52.88, MICROFIT_H, 3.0),
]
J1_FACE_Y = 0.14     # board y of the J1 mating face (F.Fab)

# Envelopes for parts with no KiCad 3D model, or whose fitted height exceeds the model:
# (name, x0, x1, y0, y1, z0, z1) in board coords, z relative to the board top (negative = below).
ENVELOPES = [
    ('J1 Micro-Fit header + plug', 31.12, 52.88, 0.14, 10.15, 0.0, MICROFIT_H),
    ('A1 socket strip L', 5.2, 7.8, 11.7, 29.5, 0.0, SSW_H),
    ('A1 socket strip R', 20.44, 23.04, 11.7, 29.5, 0.0, SSW_H),
    ('A1 XIAO + headers + USB-C', 5.05, 23.19, 7.9, 31.05, SSW_H, XIAO_STACK_H),  # y0: USB-C overhang (est 1 mm)
    ('A1 socket tails L', 6.0, 7.0, 12.5, 28.7, -PCB - SSW_TAIL, -PCB),
    ('A1 socket tails R', 21.24, 22.24, 12.5, 28.7, -PCB - SSW_TAIL, -PCB),
    ('JP1 handled shunt', 27.73, 32.81, 32.73, 35.27, TSW_INSUL, JP1_SHUNT_H),  # 5.08 x 2.54 body
    ('F1 Littelfuse 451', 53.9, 60.1, 17.11, 19.89, 0.0, F1_H),
]

BOARD_PCB = os.path.join(os.path.dirname(HERE), 'tacoma_swc_only.kicad_pcb')  # read only
BOARD_STEP = os.path.join(HERE, 'swc_board.step')     # exported here, never into the KiCad project
KICAD_CLI = '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'

FONT = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'
BOARD_NAME = 'TACOMA SWC'
KICAD_PY = '/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3'

# Derived heights
Z_BOARD = FLOOR + STANDOFF           # board underside
Z_SPLIT = Z_BOARD + PCB              # board top = base/cover split
Z_CEIL = Z_SPLIT + HEADROOM
Z_TOP = Z_CEIL + TOP

X0, X1 = -GAP, BW + GAP              # cavity
Y0, Y1 = -(BD + GAP), GAP
OX0, OX1, OY0, OY1 = X0 - WALL, X1 + WALL, Y0 - WALL, Y1 + WALL


def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def rbox(x0, x1, y0, y1, z0, z1, r):
    """Box with rounded vertical edges."""
    b = box(x0, x1, y0, y1, z0, z1)
    if r <= 0.05:
        return b
    vert = [e for e in b.Edges if abs(e.Vertexes[0].Point.z - e.Vertexes[1].Point.z) > 1e-6]
    return b.makeFillet(r, vert)


def outer(z0, z1, inset=0.0):
    """Outer shell outline, inset from the outside surface, with matching corner radius."""
    return rbox(OX0 + inset, OX1 - inset, OY0 + inset, OY1 - inset, z0, z1, CORNER_R - inset)


def cyl(x, y, d, z0, z1):
    return Part.makeCylinder(d / 2, z1 - z0, V(x, y, z0))


def ring(z0, z1, inset0, inset1):
    """Band of the outer wall between insets inset0..inset1 measured from the outside."""
    return outer(z0, z1, inset0).cut(outer(z0 - 1, z1 + 1, inset1))


def windows(z0, z1):
    """U-shaped connector openings through the front (Y = 0) wall, from z0 up."""
    s = None
    for _, xl, xr, h, extra in CONNECTORS:
        w = box(xl - WIN_CLR, xr + WIN_CLR, -J1_FACE_Y - 1, OY1 + 1, z0,
                min(z1, Z_SPLIT + h + extra + WIN_CLR))
        s = w if s is None else s.fuse(w)
    return s


def env_box(x0, x1, y0, y1, z0, z1):
    """Envelope in board coords (z relative to board top) -> case coords."""
    return box(x0, x1, -y1, -y0, Z_SPLIT + z0, Z_SPLIT + z1)


# ---------------------------------------------------------------- board data (read-only source)
_PAD_DUMP = r"""
import sys, json, pcbnew
b = pcbnew.LoadBoard(sys.argv[1]); mm = pcbnew.ToMM; out = []
for f in b.GetFootprints():
    for p in f.Pads():
        if not (p.IsOnLayer(pcbnew.F_Cu) or p.IsOnLayer(pcbnew.B_Cu)):
            continue
        bb = p.GetBoundingBox()
        out.append([f.GetReference(), p.GetNumber(), p.GetNetname(),
                    mm(bb.GetX()), mm(bb.GetY()), mm(bb.GetRight()), mm(bb.GetBottom())])
print('PADS' + json.dumps(out))
"""

def board_copy():
    """Copy the frozen board to a temp dir: KiCad tools drop lock files next to what they open."""
    import shutil, tempfile
    tmp = tempfile.mkdtemp(prefix='swc_board_')
    src = os.path.join(tmp, os.path.basename(BOARD_PCB))
    shutil.copy2(BOARD_PCB, src)
    pro = BOARD_PCB.replace('.kicad_pcb', '.kicad_pro')
    if os.path.exists(pro):
        shutil.copy2(pro, os.path.join(tmp, os.path.basename(pro)))
    return src

BOARD_COPY = board_copy()

def load_pads():
    """Exposed copper pads (ref, pad, net, x0, y0, x1, y1 in board coords) via KiCad's pcbnew."""
    try:
        r = subprocess.run([KICAD_PY, '-I', '-c', _PAD_DUMP, BOARD_COPY], capture_output=True,
                           text=True, timeout=120)
        import json
        line = [l for l in r.stdout.splitlines() if l.startswith('PADS')][0]
        return json.loads(line[4:])
    except Exception as e:
        log('pad list unavailable, vent-over-pad check skipped:', e)
        return []

PADS = load_pads()

# ---------------------------------------------------------------- base
base = outer(0, Z_SPLIT).cut(box(X0, X1, Y0, Y1, FLOOR, Z_SPLIT + 1))
base = base.fuse(ring(Z_SPLIT, Z_SPLIT + TONGUE_H, 0, TONGUE_W))     # locating lip, outer edge
base = base.cut(windows(Z_SPLIT - 0.01, Z_SPLIT + TONGUE_H + 1))     # lip must not block the plug
for hx, hy in HOLES:
    x, y = hx, -hy
    base = base.fuse(cyl(x, y, STANDOFF_FOOT_D, FLOOR - 0.01, FOOT_TOP))
    base = base.fuse(cyl(x, y, STANDOFF_D, FLOOR - 0.01, Z_BOARD))
    base = base.cut(cyl(x, y, CLEAR_D, -1, Z_BOARD + 1))             # M3 clearance
    base = base.cut(cyl(x, y, CBORE_D, -1, CBORE_DEPTH))             # head recess from below
base = base.removeSplitter()

# ---------------------------------------------------------------- cover
cover = outer(Z_SPLIT, Z_TOP).cut(box(X0, X1, Y0, Y1, Z_SPLIT - 1, Z_CEIL))
cover = cover.cut(ring(Z_SPLIT - 1, Z_SPLIT + TONGUE_H + FIT, -1, TONGUE_W + FIT))   # seat over the lip
cover = cover.cut(windows(Z_SPLIT - 1, Z_CEIL))
for hx, hy in HOLES:
    x, y = hx, -hy
    cover = cover.fuse(cyl(x, y, POST_D, Z_SPLIT, Z_CEIL + 0.01))    # posts clamp the board
    cover = cover.cut(cyl(x, y, PILOT_D, Z_SPLIT - 1, Z_SPLIT + PILOT_DEPTH))
# Hold-down pad over the XIAO (module outline), HOLD_GAP above its datasheet top.
HOLD = (5.05, 23.19, 8.95, 31.05)    # A1 F.Fab outline, board coords
Z_HOLD = Z_SPLIT + XIAO_STACK_H + HOLD_GAP
if Z_HOLD < Z_CEIL - 0.3:
    cover = cover.fuse(box(HOLD[0], HOLD[1], -HOLD[3], -HOLD[2], Z_HOLD, Z_CEIL + 0.01))

# Engraved labels on the top. Rotated 180 deg so they read for someone facing the J1 edge.
label_boxes = []
def engrave(shape, text, xc, yc, size, depth=0.6):
    try:
        chars = Part.makeWireString(text, os.path.dirname(FONT) + '/', os.path.basename(FONT), size, 0)
    except Exception as e:
        log('label skipped:', text, e)
        return shape
    faces = []
    for ch in chars:
        if ch:
            faces.append(Part.makeFace(ch, 'Part::FaceMakerBullseye'))
    if not faces:
        return shape
    comp = Part.Compound(faces)
    bb = comp.BoundBox
    comp.translate(V(xc - (bb.XMin + bb.XMax) / 2, yc - (bb.YMin + bb.YMax) / 2, Z_TOP - depth))
    comp.rotate(V(xc, yc, Z_TOP), V(0, 0, 1), 180)
    b = comp.BoundBox
    label_boxes.append((text, b.XMin, b.XMax, b.YMin, b.YMax))
    return shape.cut(comp.extrude(V(0, 0, depth + 1)))

for name, xl, xr, _, _ in CONNECTORS:
    cover = engrave(cover, name, (xl + xr) / 2, -5.5, 3.0)
cover = engrave(cover, 'J1', (CONNECTORS[0][1] + CONNECTORS[0][2]) / 2, -10.5, 2.6)
cover = engrave(cover, BOARD_NAME, BW / 2, -BD + 6.5, 5.0)   # back edge, clear of the vents

# ---- vent slots
def stadium_xy(x0, x1, yc, w, z0, z1):
    """Slot along X from x0 to x1 (overall extent), width w, rounded ends; case coords."""
    r = w / 2
    s = box(x0 + r, x1 - r, yc - r, yc + r, z0, z1)
    return s.fuse(cyl(x0 + r, yc, w, z0, z1)).fuse(cyl(x1 - r, yc, w, z0, z1))

def stadium_yz(xa, xb, yc, w, z0, z1):
    """Vertical slot through a wall normal to X (xa..xb), width w along Y, rounded top and bottom."""
    r = w / 2
    s = Part.makeBox(xb - xa, w, z1 - z0 - w, V(xa, yc - r, z0 + r))
    for zc in (z0 + r, z1 - r):
        s = s.fuse(Part.makeCylinder(r, xb - xa, V(xa, yc, zc), V(1, 0, 0)))
    return s

top_slots = []      # (x0, x1, yc) in board coords (y down)
pitch = VENT_W + VENT_WEB
for k in range(VENT_TOP_N):
    yc = round(VENT_TOP_YC + (k - (VENT_TOP_N - 1) / 2) * pitch, 3)
    top_slots.append((VENT_TOP_XC - VENT_TOP_LEN / 2, VENT_TOP_XC + VENT_TOP_LEN / 2, yc))

side_slots = []     # board y centres on the +X wall
y = VENT_SIDE_Y[0]
while y <= VENT_SIDE_Y[1] + 1e-6:
    side_slots.append(y); y += pitch
Z_SIDE0 = Z_SPLIT + TONGUE_H + FIT + 2.0         # 2 mm above the rabbet
Z_SIDE1 = Z_SIDE0 + VENT_SIDE_H

vent_cut = None
for x0, x1, yc in top_slots:
    v = stadium_xy(x0, x1, -yc, VENT_W, Z_CEIL - 1, Z_TOP + 1)
    vent_cut = v if vent_cut is None else vent_cut.fuse(v)
for yc in side_slots:
    v = stadium_yz(X1 - 1, OX1 + 1, -yc, VENT_W, Z_SIDE0, Z_SIDE1)
    vent_cut = v if vent_cut is None else vent_cut.fuse(v)
vol0 = cover.Volume
if vent_cut is not None:
    cover = cover.cut(vent_cut)
cover = cover.removeSplitter()
top_area = sum((x1 - x0 - VENT_W) * VENT_W + 3.14159265 * (VENT_W / 2) ** 2 for x0, x1, _ in top_slots)
side_area = len(side_slots) * ((VENT_SIDE_H - VENT_W) * VENT_W + 3.14159265 * (VENT_W / 2) ** 2)

# ---------------------------------------------------------------- board model
def load_board():
    """Board + component solids from KiCad's STEP export (generated outside swc_only)."""
    if not os.path.exists(BOARD_STEP):
        try:   # export from the temp copy, never from swc_only itself
            subprocess.run([KICAD_CLI, 'pcb', 'export', 'step', '--subst-models', '-f',
                            '-o', BOARD_STEP, BOARD_COPY], check=True, capture_output=True, timeout=300)
        except Exception as e:
            log('board STEP export failed, using envelopes only:', e)
            return None, []
    s = Part.Shape()
    s.read(BOARD_STEP)
    pcb, comps = None, []
    for so in s.Solids:
        b = so.BoundBox
        if b.XLength > BW - 1 and b.YLength > BD - 1 and b.ZLength < PCB + 0.2:
            pcb = so
        else:
            comps.append(so)
    mat = App.Matrix(); mat.move(V(0, 0, Z_BOARD - s.BoundBox.ZMin if pcb is None else Z_BOARD - pcb.BoundBox.ZMin))
    pcb = pcb.transformGeometry(mat) if pcb is not None else None
    comps = [c.transformGeometry(mat) for c in comps]
    return pcb, comps

pcb_model, comp_models = load_board()
log(f'board model: {"KiCad STEP" if pcb_model else "box"}; {len(comp_models)} component solids from KiCad models, '
    f'{len(ENVELOPES)} envelopes (J1, A1, JP1 shunt, F1 have no usable model)')

board = box(0, BW, -BD, 0, Z_BOARD, Z_SPLIT)
for hx, hy in HOLES:
    board = board.cut(cyl(hx, -hy, 3.2, Z_BOARD - 1, Z_SPLIT + 1))
if pcb_model is not None:
    board = pcb_model

envs = [(n, env_box(*a)) for n, *a in ENVELOPES]

# ---------------------------------------------------------------- checks
fails = []
def interferes(name, shape):
    for pname, part in (('cover', cover), ('base', base)):
        v = shape.common(part).Volume
        if v > 1e-3:
            fails.append(f'{name} intersects {pname} ({v:.2f} mm3)')

interferes('board outline', board)                                   # (a)
for i, c in enumerate(comp_models):                                  # (b) modelled parts
    bb = c.BoundBox
    interferes(f'component model #{i} at X{bb.Center.x:.1f} Y{bb.Center.y:.1f}', c)
for n, e in envs:                                                    # (b) envelopes
    interferes(n, e)
# (c) each connector face must be fully open through the wall (plug insertion path)
for name, xl, xr, h, _ in CONNECTORS:
    face = box(xl, xr, -J1_FACE_Y, OY1 + 2, Z_SPLIT + 0.01, Z_SPLIT + h)
    for pname, part in (('cover', cover), ('base', base)):
        v = face.common(part).Volume
        if v > 1e-3:
            fails.append(f'{name} opening blocked by {pname} ({v:.2f} mm3)')
if base.common(cover).Volume > 1e-3:
    fails.append('base and cover overlap')
# labels must sit on the top face and not touch each other
for i, (t, x0, x1, y0, y1) in enumerate(label_boxes):
    if x0 < OX0 + 2 or x1 > OX1 - 2 or y0 < OY0 + 2 or y1 > OY1 - 2:
        fails.append(f'label "{t}" too close to the edge')
    for t2, a0, a1, b0, b1 in label_boxes[i + 1:]:
        if x0 < a1 + 1 and a0 < x1 + 1 and y0 < b1 + 1 and b0 < y1 + 1:
            fails.append(f'labels "{t}" and "{t2}" closer than 1 mm')
# vents: clear of pads (plan view), labels, posts, walls/lip/corners
def rect_gap(a0, a1, b0, b1, c0, c1, d0, d1):
    """Gap between rectangles [a0,a1]x[b0,b1] and [c0,c1]x[d0,d1] (0 if overlapping)."""
    dx = max(c0 - a1, a0 - c1, 0); dy = max(d0 - b1, b0 - d1, 0)
    return (dx * dx + dy * dy) ** 0.5
pads_under = set()
for x0, x1, yc in top_slots:
    sy0, sy1 = -yc - VENT_W / 2, -yc + VENT_W / 2           # case coords
    for ref, num, net, px0, py0, px1, py1 in PADS:   # informational: 1.8 mm slots can't pass an M3 screw
        if rect_gap(x0, x1, yc - VENT_W / 2, yc + VENT_W / 2, px0, px1, py0, py1) < PAD_MARGIN - 1e-6:
            pads_under.add(f'{ref}.{num}')
    # keep the array clear of J1 and its opening
    if rect_gap(x0, x1, yc - VENT_W / 2, yc + VENT_W / 2, CONNECTORS[0][1] - 2, CONNECTORS[0][2] + 2, -5, 10.15) < 2.0:
        fails.append(f'top slot y={yc:.1f} within 2 mm of J1')
    for t, lx0, lx1, ly0, ly1 in label_boxes:
        if rect_gap(x0, x1, sy0, sy1, lx0, lx1, ly0, ly1) < 2.0:
            fails.append(f'top slot y={yc:.1f} within 2 mm of label "{t}"')
    for hx, hy in HOLES:
        if rect_gap(x0, x1, sy0, sy1, hx, hx, -hy, -hy) < POST_D / 2 + 2.0:
            fails.append(f'top slot y={yc:.1f} within 2 mm of a cover post')
    if x0 < X0 + 2 or x1 > X1 - 2 or sy0 < Y0 + 2 or sy1 > Y1 - 2:
        fails.append(f'top slot y={yc:.1f} within 2 mm of the wall')
    if rect_gap(x0, x1, sy0, sy1, HOLD[0], HOLD[1], -HOLD[3], -HOLD[2]) < 2.0:
        fails.append(f'top slot y={yc:.1f} over the XIAO hold-down')
if any(abs(yc - min(side_slots, key=lambda v: abs(v - yc))) > 1e-6 for _, _, yc in top_slots):
    fails.append('top slots not aligned with the side-slot grid')
for yc in side_slots:
    if -yc - VENT_W / 2 < OY0 + CORNER_R + 2 or -yc + VENT_W / 2 > OY1 - CORNER_R - 2:
        fails.append(f'side slot y={yc:.1f} too close to a corner')
    for hx, hy in HOLES:
        if abs(yc - hy) < POST_D / 2 + 2 + VENT_W / 2:
            fails.append(f'side slot y={yc:.1f} too close to a cover post')
if Z_SIDE1 > Z_CEIL - 2:
    fails.append('side slots too close to the ceiling')
log('checks:', 'PASS' if not fails else 'FAIL')
log(f'  checked: board outline, {len(comp_models)} modelled components, {len(envs)} envelopes, '
    f'{len(CONNECTORS)} connector face(s), base/cover overlap, {len(label_boxes)} labels, '
    f'{len(top_slots) + len(side_slots)} vent slots vs {len(PADS)} pads/labels/posts/walls')
for f in fails:
    log('  ', f)

# clearances worth knowing
tall = max(comp_models + [e for _, e in envs], key=lambda s: s.BoundBox.ZMax)
log(f'tallest part top Z={tall.BoundBox.ZMax:.2f} ({tall.BoundBox.ZMax - Z_SPLIT:.1f} above board), '
    f'ceiling Z={Z_CEIL:.1f}, gap {Z_CEIL - tall.BoundBox.ZMax:.2f} mm')
low = min(comp_models + [e for _, e in envs], key=lambda s: s.BoundBox.ZMin)
log(f'lowest under-board item Z={low.BoundBox.ZMin:.2f}, floor top Z={FLOOR:.1f}, gap {low.BoundBox.ZMin - FLOOR:.2f} mm')
for t, x0, x1, y0, y1 in label_boxes:
    log(f'label "{t}": {x1 - x0:.1f} x {y1 - y0:.1f} mm at X{(x0 + x1) / 2:.1f} Y{(y0 + y1) / 2:.1f}')

# ---------------------------------------------------------------- export
def stl(shape, name):
    import MeshPart
    m = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.02, AngularDeflection=0.25, Relative=False)
    if m.hasSelfIntersections():
        m.fixSelfIntersections()
    m.write(os.path.join(HERE, name))
    ok = m.isSolid() and not m.hasNonManifolds() and not m.hasSelfIntersections()
    if not ok:
        fails.append(f'{name} mesh not clean')
    log(f'{name}: {m.CountFacets} facets, watertight={m.isSolid()}, '
        f'non-manifold={m.hasNonManifolds()}, self-intersecting={m.hasSelfIntersections()}')

log(f'solids valid: base={base.isValid()} ({len(base.Solids)} solid), cover={cover.isValid()} ({len(cover.Solids)} solid)')
stl(base, 'swc_case_base.stl')
cover_print = cover.copy()
cover_print.rotate(V(0, 0, Z_TOP / 2), V(1, 0, 0), 180)   # print top-down: flat top on the bed
cover_print.translate(V(0, 0, -cover_print.BoundBox.ZMin))
stl(cover_print, 'swc_case_cover.stl')
Part.Compound([base, cover]).exportStep(os.path.join(HERE, 'swc_case.step'))

bb = base.fuse(cover).BoundBox
log(f'vents: {len(top_slots)} top slots ({top_area:.0f} mm2) over R1/U1 + {len(side_slots)} side slots '
    f'({side_area:.0f} mm2) low in the +X wall; total open area {top_area + side_area:.0f} mm2; '
    f'{VENT_W} mm wide, {pitch:.1f} mm pitch (>= {VENT_WEB} mm webs) on both groups')
log(f'  top array: {VENT_TOP_N} x {VENT_TOP_LEN:.1f} mm slots along X, centred on board ({VENT_TOP_XC}, {VENT_TOP_YC}), '
    f'{VENT_TOP_LEN:.1f} x {(VENT_TOP_N - 1) * pitch + VENT_W:.1f} mm block, each in line with a side slot; '
    f'pads within {PAD_MARGIN} mm in plan (informational): {", ".join(sorted(pads_under)) or "none"}')
for x0, x1, yc in top_slots:
    log(f'  top slot: board x {x0:.1f}..{x1:.1f}, y {yc:.1f} ({x1 - x0:.1f} mm long)')
log(f'  side slots: board y {", ".join(f"{v:.1f}" for v in side_slots)}; Z {Z_SIDE0:.1f}..{Z_SIDE1:.1f} '
    f'({Z_SIDE0 - Z_SPLIT:.1f}..{Z_SIDE1 - Z_SPLIT:.1f} above board), rounded ends (self-supporting top-down)')
log(f'XIAO hold-down pad at {Z_HOLD - Z_SPLIT:.2f} above board ({HOLD_GAP} mm over the {XIAO_STACK_H:.2f} mm stack)')
log(f'outer size: {bb.XLength:.1f} x {bb.YLength:.1f} x {bb.ZLength:.1f} mm (no ears, 3 mm corner radius)')
log(f'board underside Z={Z_BOARD:.1f}, board top/split Z={Z_SPLIT:.1f}, ceiling Z={Z_CEIL:.1f}, top Z={Z_TOP:.1f}')
log(f'screw: 4 x M3 x {SCREW_L:.0f} from below (pan or socket head, {CBORE_D} x {CBORE_DEPTH} mm recess); '
    f'thread engagement in cover post = {SCREW_L - (Z_SPLIT - CBORE_DEPTH):.1f} mm; '
    f'pilot {PILOT_D} mm x {PILOT_DEPTH:.0f} deep; tip {Z_SPLIT + PILOT_DEPTH - (CBORE_DEPTH + SCREW_L):.1f} mm short of pilot bottom')
o = CONNECTORS[0]
log(f'J1 opening: X {o[1] - WIN_CLR:.2f}..{o[2] + WIN_CLR:.2f} (board x), Z {Z_SPLIT:.1f}..'
    f'{Z_SPLIT + o[3] + o[4] + WIN_CLR:.1f} ({o[3] + o[4] + WIN_CLR:.1f} above board); face '
    f'{J1_FACE_Y + GAP + WALL:.2f} mm behind the outside of the wall')

# ---------------------------------------------------------------- previews
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def render(items, fname, elev, azim, title, px=900):
    """Orthographic z-buffer render with simple shading (no GUI needed)."""
    e, a = np.radians(elev), np.radians(azim)
    d = -np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])
    r = np.cross(d, [0, 0, 1.0]); r /= np.linalg.norm(r)
    u = np.cross(r, d)
    light = -d + 0.6 * u + 0.3 * r; light /= np.linalg.norm(light)
    tris_all, cols = [], []
    for shape, color in items:
        if shape is None or shape.isNull():
            continue
        pts, tris = shape.tessellate(0.1)
        if not tris:
            continue
        P = np.array([[p.x, p.y, p.z] for p in pts])
        T = P[np.array(tris)]
        tris_all.append(T); cols.append(np.tile(matplotlib.colors.to_rgb(color), (len(T), 1)))
    T = np.concatenate(tris_all); C = np.concatenate(cols)
    S = np.stack([T @ r, T @ u, T @ d], axis=-1)
    lo, hi = S[..., :2].reshape(-1, 2).min(0), S[..., :2].reshape(-1, 2).max(0)
    scale = (px - 40) / (hi - lo).max()
    W = int((hi[0] - lo[0]) * scale) + 40; H = int((hi[1] - lo[1]) * scale) + 40
    zbuf = np.full((H, W), np.inf); img = np.ones((H, W, 3))
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    shade = 0.35 + 0.65 * np.abs(n @ light)
    for k in range(len(S)):
        x = (S[k, :, 0] - lo[0]) * scale + 20; y = H - ((S[k, :, 1] - lo[1]) * scale + 20); z = S[k, :, 2]
        x0, x1 = int(max(np.floor(x.min()), 0)), int(min(np.ceil(x.max()), W - 1))
        y0, y1 = int(max(np.floor(y.min()), 0)), int(min(np.ceil(y.max()), H - 1))
        if x1 < x0 or y1 < y0: continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        den = (y[1] - y[2]) * (x[0] - x[2]) + (x[2] - x[1]) * (y[0] - y[2])
        if abs(den) < 1e-9: continue
        w0 = ((y[1] - y[2]) * (gx - x[2]) + (x[2] - x[1]) * (gy - y[2])) / den
        w1 = ((y[2] - y[0]) * (gx - x[2]) + (x[0] - x[2]) * (gy - y[2])) / den
        w2 = 1 - w0 - w1
        m = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
        if not m.any(): continue
        zz = w0 * z[0] + w1 * z[1] + w2 * z[2]
        sub = zbuf[y0:y1 + 1, x0:x1 + 1]
        upd = m & (zz < sub)
        sub[upd] = zz[upd]
        img[y0:y1 + 1, x0:x1 + 1][upd] = C[k] * shade[k]
    fig = plt.figure(figsize=(W / 110, H / 110 + 0.4), dpi=110)
    plt.imshow(img); plt.axis('off'); plt.title(title, fontsize=10)
    fig.savefig(os.path.join(HERE, fname), bbox_inches='tight'); plt.close(fig)

BASE_C, COVER_C, PCB_C, COMP_C, ENV_C = '#5b8def', '#c8c8c8', '#2e8b57', '#505050', '#d9a441'
comps_shape = Part.Compound(comp_models) if comp_models else None
env_shape = Part.Compound([e for _, e in envs])
board_items = [(board, PCB_C), (comps_shape, COMP_C), (env_shape, ENV_C)]

render([(base, BASE_C)] + board_items, 'preview_base_with_board.png', 40, 60,
       'Base with SWC board (KiCad models grey, estimated envelopes gold); J1 edge at right-front')
render([(base, BASE_C)] + board_items, 'preview_top_view.png', 89, -90,
       'Top view, cover off (same orientation as the KiCad top view: J1 edge at top)')
render([(base, BASE_C), (cover, COVER_C)] + board_items, 'preview_assembled_front.png', 15, 70,
       'Assembled, from the J1 side: SWC HARNESS opening (J1 appears left of centre from here)')
render([(cover, COVER_C)], 'preview_cover_top.png', 75, 90, 'Cover top: engraved labels (read from the J1 side)')
render([(base, BASE_C)], 'preview_base_bottom.png', -50, 60, 'Base underside: screw head recesses')
# Cutaway through the J1 centre line: everything at X < cut, viewed from +X.
XC = (CONNECTORS[0][1] + CONNECTORS[0][2]) / 2
half = box(OX0 - 5, XC, OY0 - 5, OY1 + 5, -5, Z_TOP + 5)
def clip(s):
    return None if s is None else s.common(half)
render([(clip(base), BASE_C), (clip(cover), COVER_C), (clip(board), PCB_C),
        (clip(comps_shape), COMP_C), (clip(env_shape), ENV_C)],
       'preview_cutaway.png', 10, 25, f'Cutaway at X={XC:.1f} through J1 (J1 edge at right): board in the base, J1 face behind its opening')

render([(base, BASE_C), (cover, COVER_C)], 'preview_vents.png', 32, -35,
       'Vent slots: top slots over R1/U1, low slots in the +X side wall (J1 edge at left)')
# Plan view of the vent slots over the board's exposed pads (KiCad orientation, y down).
fig, ax = plt.subplots(figsize=(8, 7), dpi=110)
ax.add_patch(plt.Rectangle((0, 0), BW, BD, fc='#2e8b57', ec='k', alpha=0.25))
for ref, num, net, px0, py0, px1, py1 in PADS:
    ax.add_patch(plt.Rectangle((px0, py0), px1 - px0, py1 - py0, fc='#c9a227', ec='none'))
for ref, cx, cy in (('U1', 51.0, 37.0), ('R1', 50.8, 31.0), ('J1', 42.0, 6.0), ('A1', 14.1, 20.0)):
    ax.text(cx, cy, ref, ha='center', va='center', fontsize=9, color='k', weight='bold')
ax.add_patch(plt.Rectangle((40.63, 28.7), 20.42, 4.6, fc='none', ec='k', ls='--'))     # R1 F.Fab
ax.add_patch(plt.Rectangle((49.45, 34.95), 3.1, 4.1, fc='none', ec='k', ls='--'))      # U1 F.Fab
for x0, x1, yc in top_slots:
    ax.add_patch(matplotlib.patches.FancyBboxPatch((x0 + VENT_W / 2, yc - 0.001), x1 - x0 - VENT_W, 0.002,
                 boxstyle=f'round,pad={VENT_W / 2}', fc='none', ec='#1f4fd1', lw=1.5))
for yc in side_slots:
    ax.plot([BW + GAP + 0.3, BW + GAP + WALL - 0.3], [yc, yc], color='#1f4fd1', lw=4)
ax.set_xlim(-3, BW + 4); ax.set_ylim(BD + 3, -3); ax.set_aspect('equal')
ax.set_title('Vent slots (blue) over the board pads (gold, informational); side slots drawn at the +X wall', fontsize=10)
fig.savefig(os.path.join(HERE, 'preview_vent_pad_map.png'), bbox_inches='tight'); plt.close(fig)

open(os.path.join(HERE, 'build_report.txt'), 'w').write('\n'.join(_report) + '\n')
sys.exit(0 if not fails else 1)
