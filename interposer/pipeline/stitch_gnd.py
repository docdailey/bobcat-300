"""GND stitching vias for the routed bobcat-rak-interposer.

After routing, KiCad DRC left the outer GND pours in fragments that reach no
other ground (unconnected Zone [GND] on F.Cu / B.Cu). A through via inside a
fragment ties it to the solid In1.Cu GND plane. Vias go on a 2 mm grid where:

  * the point is inside the filled GND pour on BOTH F.Cu and B.Cu,
  * every other net's copper (tracks on all four layers, pads, vias) is at least
    via radius + 0.15 mm away,
  * the point is >= 1.2 mm from the finger edge (JLCPCB bevel) and >= 0.6 mm
    from every NPTH hole edge, and its drill is >= 0.5 mm from every other via's.

A 3 mm grid first; then every F/B fragment still without a via (slivers left
between bus traces, each holding one ground finger) gets one via from a 0.2 mm
search inside the fragment, refilling and repeating until none is left.

Usage (KiCad python): python3 stitch_gnd.py routed.kicad_pcb out.kicad_pcb
"""
import math
import sys

import pcbnew

src, dst = sys.argv[1], sys.argv[2]
board = pcbnew.LoadBoard(src)
mm = pcbnew.FromMM
VIA_PAD, VIA_DRILL, CLEAR, PITCH = mm(0.5), mm(0.2), mm(0.15), mm(3.0)
HOLE_GAP = mm(0.5)  # drill edge to drill edge, any via (avoids hole_to_hole)
need = VIA_PAD / 2 + CLEAR

gnd = {str(k): v for k, v in board.GetNetsByName().items()}["GND"]
gnd_code = gnd.GetNetCode()

# read everything up front (wrappers misbehave after the board is modified)
xs, ys = [], []
for d in board.GetDrawings():
    if d.GetLayer() == pcbnew.Edge_Cuts:
        for p in (d.GetStart(), d.GetEnd()):
            xs.append(p.x)
            ys.append(p.y)
finger_edge = max(ys)

segs, circles, rects = [], [], []
all_vias = [(t.GetPosition().x, t.GetPosition().y) for t in board.GetTracks() if t.GetClass() == "PCB_VIA"]
for t in board.GetTracks():
    if t.GetNetCode() == gnd_code:
        continue
    if t.GetClass() == "PCB_VIA":
        circles.append((t.GetPosition().x, t.GetPosition().y, t.GetWidth(pcbnew.F_Cu) / 2))
    else:
        segs.append((t.GetStart().x, t.GetStart().y, t.GetEnd().x, t.GetEnd().y, t.GetWidth() / 2))
holes = []
for fp in board.GetFootprints():
    for pad in fp.Pads():
        pos = pad.GetPosition()
        if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
            holes.append((pos.x, pos.y, pad.GetDrillSize().x / 2))
            continue
        # every pad is an obstacle, ground ones included: a via must not land in
        # a pad (via-in-pad) or drill into a header hole
        sx, sy = pad.GetSize().x, pad.GetSize().y
        if round(pad.GetOrientationDegrees()) % 180 == 90:
            sx, sy = sy, sx
        rects.append((pos.x - sx / 2, pos.y - sy / 2, pos.x + sx / 2, pos.y + sy / 2))
    for item in fp.GraphicalItems():  # net-tie bridges
        if item.GetLayer() == pcbnew.F_Cu and item.GetClass() == "PCB_SHAPE":
            s, e = item.GetStart(), item.GetEnd()
            segs.append((s.x, s.y, e.x, e.y, item.GetWidth() / 2))

zones = {z.GetLayer(): z for z in board.Zones() if not z.GetIsRuleArea() and z.GetNetCode() == gnd_code}


def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    if dx == dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def clear(px, py):
    if finger_edge - py < mm(1.2):
        return False
    for ax, ay, bx, by, hw in segs:
        if seg_dist(px, py, ax, ay, bx, by) < need + hw:
            return False
    for cx, cy, r in circles:
        if math.hypot(px - cx, py - cy) < need + r:
            return False
    for x0, y0, x1, y1 in rects:
        dx = max(x0 - px, 0, px - x1)
        dy = max(y0 - py, 0, py - y1)
        if math.hypot(dx, dy) < need:
            return False
    for cx, cy, r in holes:
        if math.hypot(px - cx, py - cy) < r + mm(0.6) + VIA_PAD / 2:
            return False
    for vx, vy in all_vias:
        if math.hypot(px - vx, py - vy) < VIA_DRILL + HOLE_GAP:
            return False
    return True


def add_via(x, y):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pcbnew.VECTOR2I(int(x), int(y)))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetWidth(VIA_PAD)
    v.SetDrill(VIA_DRILL)
    v.SetNet(gnd)
    board.Add(v)
    all_vias.append((int(x), int(y)))


added = 0
y = min(ys) + PITCH / 2
while y < max(ys):
    x = min(xs) + PITCH / 2
    while x < max(xs):
        p = pcbnew.VECTOR2I(int(x), int(y))
        inside = all(z.HitTestFilledArea(l, p) for l, z in zones.items() if l in (pcbnew.F_Cu, pcbnew.B_Cu))
        if inside and clear(x, y):
            add_via(x, y)
            added += 1
        x += PITCH
    y += PITCH
pcbnew.ZONE_FILLER(board).Fill(board.Zones())

targeted = 0
for _round in range(4):
    placed = False
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = zones.get(layer)
        if z is None:
            continue
        polys = z.GetFilledPolysList(layer)
        for i in range(polys.OutlineCount()):
            frag = pcbnew.SHAPE_POLY_SET()
            frag.AddOutline(polys.Outline(i))
            if any(frag.Contains(pcbnew.VECTOR2I(vx, vy)) for vx, vy in all_vias):
                continue
            bb = polys.Outline(i).BBox()
            step = mm(0.2)
            found = None
            yy = bb.GetY()
            while yy <= bb.GetY() + bb.GetHeight() and not found:
                xx = bb.GetX()
                while xx <= bb.GetX() + bb.GetWidth():
                    pt = pcbnew.VECTOR2I(int(xx), int(yy))
                    if frag.Contains(pt) and clear(xx, yy):
                        found = (xx, yy)
                        break
                    xx += step
                yy += step
            if found:
                add_via(*found)
                targeted += 1
                placed = True
            else:
                print(f"no via spot in {board.GetLayerName(layer)} fragment at "
                      f"{pcbnew.ToMM(bb.Centre().x):.2f},{pcbnew.ToMM(bb.Centre().y):.2f}")
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    if not placed:
        break

pcbnew.SaveBoard(dst, board)
print(f"added {added} grid + {targeted} targeted GND stitching vias; zones refilled")

# KiCad 10 bundled Python segfaults tearing down pcbnew SWIG objects at
# interpreter exit (exit 139, macOS crash dialog). Leave without finalisation.
import os  # noqa: E402
sys.stdout.flush()
os._exit(0)
