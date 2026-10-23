"""Specctra DSN from a KiCad board, for Freerouting, without the KiCad GUI.

pcbnew.ExportSpecctraDSN() needs the PCB editor frame and returns False from a
script; kicad-cli has no Specctra exporter. pcb-factory's own DSN (dsn-converter,
from circuit JSON) misplaces pads on this board (CE1 +2.8 mm, JP/H -0.98 mm), so
it cannot be used either. This writes the DSN from the board KiCad itself holds:

  * every pad at its absolute position (each footprint placed at 0,0 / rot 0, so
    no rotation convention can go wrong), rect pads as rect, round as circle,
    SMD pads on their own copper layer, plated holes on all four;
  * In1.Cu as a GND power plane, so ground is stitched with vias, not routed;
  * net-tie copper inside the bridged solder jumpers and every NPTH hole as
    keepouts; the board outline as the boundary.

Coordinates: KiCad nm, y down -> DSN um (unit um, resolution um 10), y up.
Usage (KiCad python): python3 kicad_to_dsn.py board.kicad_pcb out.dsn
"""
import sys

import pcbnew

src, dst = sys.argv[1], sys.argv[2]
board = pcbnew.LoadBoard(src)

RES = 10  # DSN units per um
LAYERS = ["F.Cu", "B.Cu"] if board.GetCopperLayerCount() == 2 else ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"]
# Four layers: In1.Cu is a GND plane and ground is stitched to it. Two layers:
# no plane; ground is routed like any other net and the pours are added after.
PLANE_NET, PLANE_LAYER = ("GND", "In1.Cu") if len(LAYERS) == 4 else (None, None)
# Two layers: GND is not routed at all. Its pads stay obstacles; the F/B pours
# plus stitch_gnd.py connect them, and the tracks it would take go to signals.
POUR_ONLY = None  # GND IS routed as well: pour-only left finger 9 and socket 27/29 islands no via could reach
SIGNAL_LAYERS = [l for l in LAYERS if l != PLANE_LAYER]
VIA_PAD_UM, VIA_HOLE_UM = 600, 300     # 0.15 mm annular ring, 0.30 drill (jlcpcb-2layer-cardedge)
WIDTH_UM, CLEAR_UM = 140, 130      # over the 0.127/0.127 floor of jlcpcb-2layer-cardedge; wider clearance left nets unroutable
POWER_WIDTH_UM = 250
HOLE_GAP_UM = 500  # min drill-to-drill (jlcpcb-2layer-cardedge min_hole_to_hole_mm)
VIA_VIA_UM = HOLE_GAP_UM - (VIA_PAD_UM - VIA_HOLE_UM) + 10  # pad-to-pad that keeps two via drills >= 0.5 apart


def X(v):  # nm -> um (DSN unit), 0.1 um precision
    return round(v / 1000, 1)


def Y(v):
    return -round(v / 1000, 1)


def q(s):
    return '"' + str(s).replace('"', "") + '"'


out = []
w = out.append

# --- outline ----------------------------------------------------------------
# Edge.Cuts is a set of segments; chain them into one polygon.
segs = []
for d in board.GetDrawings():
    if d.GetLayer() == pcbnew.Edge_Cuts:
        segs.append(((d.GetStart().x, d.GetStart().y), (d.GetEnd().x, d.GetEnd().y)))
poly = [segs[0][0], segs[0][1]]
rest = segs[1:]
while rest:
    tail = poly[-1]
    for i, (a, b) in enumerate(rest):
        if abs(a[0] - tail[0]) + abs(a[1] - tail[1]) < 2000:
            poly.append(b)
            rest.pop(i)
            break
        if abs(b[0] - tail[0]) + abs(b[1] - tail[1]) < 2000:
            poly.append(a)
            rest.pop(i)
            break
    else:
        raise SystemExit(f"outline does not close: {len(rest)} segment(s) left")

# --- pads -> images / padstacks / nets ------------------------------------------
padstacks = {}
images = []
nets = {}
keepouts = []


def padstack_for(pad):
    sx, sy = X(pad.GetSize().x), -Y(pad.GetSize().y)
    # absolute orientation (footprint + pad); this board only uses multiples of 90
    if round(pad.GetOrientationDegrees()) % 180 == 90:
        sx, sy = sy, sx
    th = pad.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH,)
    # GetLayerName() reports F.Cu for a bottom-only pad in this build; ask directly
    names = LAYERS if th else (["B.Cu"] if pad.IsOnLayer(pcbnew.B_Cu) and not pad.IsOnLayer(pcbnew.F_Cu) else ["F.Cu"])
    shape = pad.GetShape()
    rnd = shape == pcbnew.PAD_SHAPE_CIRCLE
    key = ("C" if rnd else "R") + f"{sx:g}x{sy:g}_" + ("TH" if th else names[0])
    if key not in padstacks:
        if rnd:
            shapes = [f"(shape (circle {l} {sx}))" for l in names]
        else:
            shapes = [f"(shape (rect {l} {-sx / 2:g} {-sy / 2:g} {sx / 2:g} {sy / 2:g}))" for l in names]
        padstacks[key] = f"(padstack {q(key)} {' '.join(shapes)} (attach off))"
    return key


for fp in board.GetFootprints():
    ref = fp.GetReference()
    pins = []
    for pad in fp.Pads():
        if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
            if ref.startswith("MH"):
                # Mini CEM fig 2-7: 5.8 x 5.8 mm component+routing keep-out
                cx, cy = X(pad.GetPosition().x), Y(pad.GetPosition().y)
                keepouts.append(f'(keepout "" (rect signal {cx - 2900} {cy - 2900} {cx + 2900} {cy + 2900}))')
            else:
                # radius: drill/2 + the 0.5 mm drill-to-drill gap, less what the via
                # pad (ring 0.15) and clearance already add, + 0.05 margin
                keepouts.append(f'(keepout "" (circle signal {X(pad.GetDrillSize().x) + 2 * (HOLE_GAP_UM - (VIA_PAD_UM - VIA_HOLE_UM) // 2 - CLEAR_UM + 50)} '
                                f'{X(pad.GetPosition().x)} {Y(pad.GetPosition().y)}))')
            continue
        if not pad.GetNumber():
            continue
        ps = padstack_for(pad)
        name = pad.GetNumber()
        pins.append(f"(pin {q(ps)} {q(name)} {X(pad.GetPosition().x)} {Y(pad.GetPosition().y)})")
        net = pad.GetNetname()
        if net:
            nets.setdefault(net, []).append(f"{ref}-{name}")
    # net-tie copper (bridged jumpers) is an obstacle for every other net
    for item in fp.GraphicalItems():
        if item.GetLayer() == pcbnew.F_Cu and item.GetClass() == "PCB_SHAPE":
            s, e = item.GetStart(), item.GetEnd()
            half = X(item.GetWidth()) / 2
            x0, x1 = sorted((X(s.x), X(e.x)))
            y0, y1 = sorted((Y(s.y), Y(e.y)))
            pins.append(f'(keepout "" (rect F.Cu {x0 - half} {y0 - half} {x1 + half} {y1 + half}))')
    if pins:
        images.append((ref, pins))

# board-level NPTH holes (mounting holes) are footprints too in this export;
# any loose pcb holes are not represented by pcbnew as items, so nothing else.

# --- emit ------------------------------------------------------------------------
w(f"(pcb {q(src)}")
w('  (parser (string_quote ") (space_in_quoted_tokens on) (host_cad "kicad_to_dsn.py") (host_version "1"))')
w(f"  (resolution um {RES})")
w("  (unit um)")
w("  (structure")
for i, l in enumerate(LAYERS):
    kind = "power" if PLANE_LAYER and l == PLANE_LAYER else "signal"
    w(f"    (layer {l} (type {kind}) (property (index {i})))")
w("    (boundary (path pcb 0 " + " ".join(f"{X(x)} {Y(y)}" for x, y in poly) + "))")
if PLANE_NET:
    w(f"    (plane {q(PLANE_NET)} (polygon {PLANE_LAYER} 0 " + " ".join(f"{X(x)} {Y(y)}" for x, y in poly) + "))")
# JLCPCB finger bevel: no copper but the fingers within 1.0 mm of the edge
_fx0, _fx1 = min(X(x) for x, _ in poly), max(X(x) for x, _ in poly)
_fy = min(Y(y) for _, y in poly)
keepouts.append(f'(keepout "" (rect signal {_fx0} {_fy} {_fx1} {_fy + 1000}))')
for k in keepouts:
    w("    " + k)
w(f'    (via "Via[0-3]_{VIA_PAD_UM}:{VIA_HOLE_UM}_um")')
w(f"    (rule (width {WIDTH_UM * RES // RES}) (clearance {CLEAR_UM}) (clearance {CLEAR_UM} (type default_smd)) (clearance 50 (type smd_smd)) "
  f"(clearance {VIA_VIA_UM} (type via_via)))")
w("  )")
w("  (placement")
for ref, _ in images:
    w(f"    (component {q('IMG_' + ref)} (place {q(ref)} 0 0 front 0))")
w("  )")
w("  (library")
for ref, pins in images:
    w(f"    (image {q('IMG_' + ref)}")
    for p in pins:
        w("      " + p)
    w("    )")
for ps in padstacks.values():
    w("    " + ps)
via_shapes = " ".join(f"(shape (circle {l} {VIA_PAD_UM}))" for l in LAYERS)
w(f'    (padstack "Via[0-3]_{VIA_PAD_UM}:{VIA_HOLE_UM}_um" {via_shapes} (attach off))')
w("  )")
w("  (network")
nets.pop(POUR_ONLY, None)
for net, pins in sorted(nets.items()):
    w(f"    (net {q(net)} (pins {' '.join(pins)}))")
power = [n for n in nets if n in ("GND", "V3V3")]
signal = [n for n in nets if n not in power]
w(f"    (class signal {' '.join(q(n) for n in signal)} (circuit (use_via \"Via[0-3]_{VIA_PAD_UM}:{VIA_HOLE_UM}_um\")) (rule (width {WIDTH_UM}) (clearance {CLEAR_UM}) (clearance {VIA_VIA_UM} (type via_via))))")
w(f"    (class power {' '.join(q(n) for n in power)} (circuit (use_via \"Via[0-3]_{VIA_PAD_UM}:{VIA_HOLE_UM}_um\")) (rule (width {POWER_WIDTH_UM}) (clearance {CLEAR_UM}) (clearance {VIA_VIA_UM} (type via_via))))")
w("  )")
w("  (wiring)")
w(")")

with open(dst, "w") as fh:
    fh.write("\n".join(out) + "\n")
print(f"{len(images)} components, {sum(len(p) for _, p in images)} pins+keepouts, {len(nets)} nets, "
      f"{len(padstacks)} padstacks, {len(keepouts)} hole keepouts, outline {len(poly)} pts")

# KiCad 10 bundled Python segfaults tearing down pcbnew SWIG objects at
# interpreter exit (exit 139, macOS crash dialog). Leave without finalisation.
import os  # noqa: E402
# KiCad's background thread pool (zone triangulation after load) must finish
# before the process goes: os._exit() during it crashed in CacheTriangulation,
# and normal interpreter exit crashes in the SWIG finaliser. So: wait, then go.
import time  # noqa: E402
time.sleep(3)
sys.stdout.flush()
os._exit(0)
