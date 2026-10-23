"""Hand fixes to the tscircuit -> KiCad export of bobcat-rak-interposer.

pcb-factory's KiCad export (tsci export kicad_pcb, via tools/lib/export_kicad.py)
loses four things on this board; each is restored here, scripted so the fix is
reproducible and reviewable rather than done by mouse:

  1. board thickness: exported 1.6 mm; the Mini Card spec requires 1.0 mm.
  2. bottom-side fingers: every even contact (CE1/CE2 pads 2..52) was exported
     on F.Cu; moved back to B.Cu + B.Mask (odd contacts stay on F.Cu - top face
     = odd contacts, verified on a real card 2026-10-22).
  3. pours: the inner1/bottom GND pours and the 39 keepouts all came out as
     F.Cu zones. They are removed and replaced with GND zones on F.Cu, In1.Cu
     and B.Cu, plus a no-copper rule area over the 1.0 mm finger-bevel strip
     (JLCPCB: the bevel must carry no copper but the fingers).
  4. bridged solder jumpers: each "closed" JP was exported as a board track
     joining two nets (27 shorting_items + 54 solder_mask_bridge in KiCad
     DRC). Each becomes what it physically is: a net-tie footprint (pads 1,2)
     with the bridge as F.Cu copper inside the footprint.
  5. silkscreen: reference designators to the fab profile's 0.8 mm minimum and
     the bevel note shortened so the card edge does not clip it.
  6. part data the export dropped: J1 gets MPN PCIE-52P52H / LCSC C444927
     (SOFNG). The solder jumpers and CE1/CE2 are copper features of the board,
     and H1/H2 are unpopulated breakout headers (fit as needed), so they are DNP
     and out of the BOM/CPL. The four dia 2.6 mm holes, exported without a
     designator, become MH1..MH4.
  7. silk legibility: each jumper's outline box overlapped its own reference
     (31 silk_overlap), so the box goes and the reference stands vertical beside
     the jumper; MH1..MH4 references are hidden (they sat on the holes).

Usage (KiCad's bundled python):  python3 fix_export.py in.kicad_pcb out.kicad_pcb
"""
import sys

import pcbnew

src, dst = sys.argv[1], sys.argv[2]
board = pcbnew.LoadBoard(src)
mm = pcbnew.FromMM

# Board extents from the Edge.Cuts drawings (GetBoardEdgesBoundingBox and other
# wrappers come back unproxied in this KiCad build once anything has been removed,
# so everything is read before the board is touched).
xs, ys = [], []
for d in board.GetDrawings():
    if d.GetLayer() != pcbnew.Edge_Cuts:
        continue
    for pt in (d.GetStart(), d.GetEnd()):
        xs.append(pt.x)
        ys.append(pt.y)
x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
gnd = board.GetNetsByName()["GND"]

# 5. silkscreen: reference designators up to the profile's 0.8 mm / 0.15 mm
#    minimum (39 text_height warnings), and the bevel note shortened so it is
#    not clipped by the 30 mm card edge.
for fp in board.GetFootprints():
    ref = fp.Reference()
    ref.SetTextSize(pcbnew.VECTOR2I(mm(0.8), mm(0.8)))
    ref.SetTextThickness(mm(0.15))
for d in board.GetDrawings():
    if d.GetClass() == "PCB_TEXT" and "GOLD FINGERS" in d.GetText():
        d.SetText("1.0mm ENIG 30deg BEVEL")

# 6. part data
holes = 0
for fp in board.GetFootprints():
    ref = fp.GetReference()
    if ref == "J1":
        fp.SetValue("PCIE-52P52H")
        fp.SetField("MPN", "PCIE-52P52H")
        fp.SetField("Manufacturer", "SOFNG")
        fp.SetField("LCSC", "C444927")
        # part data, not silkscreen
        fp.Value().SetVisible(False)
        for name in ("MPN", "Manufacturer", "LCSC"):
            field = fp.GetField(name)
            if field is not None:
                field.SetVisible(False)
    elif ref.startswith("JP") or ref in ("CE1", "CE2", "H1", "H2"):
        fp.SetDNP(True)
        fp.SetExcludedFromBOM(True)
        fp.SetExcludedFromPosFiles(True)
        if ref in ("H1", "H2"):
            fp.SetValue("2x18 2.54mm header (unpopulated)")
        elif ref.startswith("JP"):
            fp.SetValue("solder jumper")
        else:
            fp.SetValue("card edge")
    elif ref == "" and "hole" in fp.GetFPIDAsString():
        holes += 1
        fp.SetReference(f"MH{holes}")
        fp.SetValue("MountingHole 2.6mm")
        fp.SetExcludedFromBOM(True)
        fp.SetExcludedFromPosFiles(True)

# 7. silk legibility: edit and collect now, remove the boxes at the very end
jp_boxes = []
for fp in board.GetFootprints():
    ref = fp.GetReference()
    if ref.startswith("MH"):
        fp.Reference().SetVisible(False)
    if not ref.startswith("JP"):
        continue
    pads = list(fp.Pads())
    cx = sum(p.GetPosition().x for p in pads) // len(pads)
    cy = sum(p.GetPosition().y for p in pads) // len(pads)
    r = fp.Reference()
    r.SetTextAngleDegrees(90)
    r.SetPosition(pcbnew.VECTOR2I(cx - mm(1.25), cy))
    for item in fp.GraphicalItems():
        if item.GetLayer() == pcbnew.F_SilkS and item.GetClass() == "PCB_SHAPE":
            jp_boxes.append((fp, item))
# 1. thickness
ds = board.GetDesignSettings()
ds.SetBoardThickness(mm(1.0))

# 2. even fingers to the bottom
moved = 0
for fp in board.GetFootprints():
    if fp.GetReference() not in ("CE1", "CE2"):
        continue
    for pad in fp.Pads():
        n = int(pad.GetNumber())
        layers = pcbnew.LSET()
        if n % 2 == 0:
            layers.AddLayer(pcbnew.B_Cu)
            layers.AddLayer(pcbnew.B_Mask)
            moved += 1
        else:
            layers.AddLayer(pcbnew.F_Cu)
            layers.AddLayer(pcbnew.F_Mask)
        pad.SetLayerSet(layers)

# 4. bridged jumpers -> net ties (read everything first; removal comes last)
jp_pads = []
for fp in board.GetFootprints():
    if fp.GetReference().startswith("JP"):
        for pad in fp.Pads():
            jp_pads.append((pad.GetPosition().x, pad.GetPosition().y, fp.GetReference(), fp))


def near_jp(pt, tol=pcbnew.FromMM(1.0)):
    for x, y, ref, fp in jp_pads:
        if abs(pt.x - x) <= tol and abs(pt.y - y) <= tol:
            return ref, fp
    return None


bridges = []
for t in board.GetTracks():
    if t.GetClass() != "PCB_TRACK":
        continue
    a, b = near_jp(t.GetStart()), near_jp(t.GetEnd())
    if a and b and a[0] == b[0]:
        bridges.append((t, a[1], t.GetStart(), t.GetEnd(), t.GetWidth()))
for t, fp, start, end, width in bridges:
    copper = pcbnew.PCB_SHAPE(fp)
    copper.SetShape(pcbnew.SHAPE_T_SEGMENT)
    copper.SetStart(start)
    copper.SetEnd(end)
    copper.SetWidth(width)
    copper.SetLayer(pcbnew.F_Cu)
    fp.Add(copper)
    fp.AddNetTiePadGroup("1,2")

# 3. zones (and the bridge tracks) out
for t, *_ in bridges:
    board.Remove(t)
for z in list(board.Zones()):
    board.Remove(z)



def rect_outline(zone, ax, ay, bx, by):
    # zone.Outline() comes back unproxied in this build; build the polygon
    # ourselves and hand it over.
    poly = pcbnew.SHAPE_POLY_SET()
    poly.NewOutline()
    for x, y in ((ax, ay), (bx, ay), (bx, by), (ax, by)):
        poly.Append(int(x), int(y))
    zone.SetOutline(poly)


for layer in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.B_Cu):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(gnd)
    z.SetLocalClearance(mm(0.2))
    z.SetMinThickness(mm(0.2))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)  # solid: thermals starved on 0.6 mm fingers
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    rect_outline(z, x0, y0, x1, y1)
    board.Add(z)

# The fingers sit on the board's bottom edge in KiCad's frame (largest y).
finger_edge = y1
bevel = pcbnew.ZONE(board)
bevel.SetIsRuleArea(True)
bevel.SetDoNotAllowZoneFills(True)
bevel.SetDoNotAllowTracks(True)
bevel.SetDoNotAllowVias(True)
bevel.SetDoNotAllowPads(False)
bevel.SetDoNotAllowFootprints(False)
bevel.SetLayerSet(pcbnew.LSET.AllCuMask())
rect_outline(bevel, x0, finger_edge - mm(1.0), x1, finger_edge)
board.Add(bevel)

for fp, item in jp_boxes:
    fp.Remove(item)

pcbnew.SaveBoard(dst, board)
print(f"thickness 1.0 mm; moved {moved} even fingers to B.Cu; {len(bridges)} jumper bridges -> net ties; zones: GND on F/In1/B + bevel rule area")

# KiCad 10 bundled Python segfaults tearing down pcbnew SWIG objects at
# interpreter exit (exit 139, macOS crash dialog). Leave without finalisation.
import os  # noqa: E402
sys.stdout.flush()
os._exit(0)
