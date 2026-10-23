"""Hand fixes to the tscircuit -> KiCad export of bobcat-rak-stack-adapter (rev B).

pcb-factory's KiCad export (tsci export kicad_pcb, via tools/lib/export_kicad.py)
loses or omits the following on this board; each is restored here, scripted so
the fix is reproducible and reviewable rather than done by mouse:

  1. board thickness: exported 1.6 mm; the Mini Card spec requires 1.0 mm.
  2. bottom-side fingers: every even contact (CE1/CE2 pads 2..52) is exported
     on F.Cu; moved to B.Cu + B.Mask (top face = odd contacts, verified on a
     real card 2026-10-22).
  3. zones: the export carries no usable pours; GND zones go on F.Cu and B.Cu,
     plus rule areas: a 1.0 mm no-copper strip over the finger bevel (JLCPCB)
     and the spec's 5.8 x 5.8 mm component+routing keep-out square at each
     hold-down hole (Mini CEM 1.2 fig 2-7), all layers.
  4. part data: J1 = SOFNG PCIE-52P52H, LCSC C444927. R19/R23/R30-R33 are DNP
     0R 0402 options (UNI-ROYAL 0402WGF0000TCE, LCSC C17168). CE1/CE2 are the
     card edge (a board feature). The holes, exported without designators,
     become MH1/MH2 (Bobcat hold-down, dia 2.6) and MH3/MH4 (RAK standoffs,
     dia 2.4).
  5. silkscreen: references to the profile's 0.8 mm minimum; hole references
     hidden.
  6. drawings: a 50.00 mm scale bar on User.Drawings for the 1:1 paper check
     (not in the Gerbers).
  7. 3D: J1 gets the SOFNG PCIE-52P52H model itself (EasyEDA/LCSC C444927 STEP,
     kept next to the project in 3dmodels/). It is drawn in the same frame as
     the imported EasyEDA footprint, so it needs no offset or rotation.

Usage (KiCad's bundled python):  python3 fix_export.py in.kicad_pcb out.kicad_pcb
"""
import os
import sys

import pcbnew

src, dst = sys.argv[1], sys.argv[2]
board = pcbnew.LoadBoard(src)
mm = pcbnew.FromMM

# Read everything first: in this KiCad build, wrappers come back unproxied once
# anything has been removed from the board.
xs, ys = [], []
for d in board.GetDrawings():
    if d.GetLayer() != pcbnew.Edge_Cuts:
        continue
    for pt in (d.GetStart(), d.GetEnd()):
        xs.append(pt.x)
        ys.append(pt.y)
x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
gnd = board.GetNetsByName()["GND"]
copper = [pcbnew.F_Cu, pcbnew.B_Cu] if board.GetCopperLayerCount() == 2 else \
    [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.B_Cu]

# 5. silkscreen
for fp in board.GetFootprints():
    ref = fp.Reference()
    ref.SetTextSize(pcbnew.VECTOR2I(mm(0.8), mm(0.8)))
    ref.SetTextThickness(mm(0.15))
# (the title's arrow survives the export; no text edit needed)

# 4. part data
holes = []
for fp in board.GetFootprints():
    ref = fp.GetReference()
    if ref == "J1":
        fp.SetValue("PCIE-52P52H")
        fp.SetField("MPN", "PCIE-52P52H")
        fp.SetField("Manufacturer", "SOFNG")
        fp.SetField("LCSC", "C444927")
        fp.Value().SetVisible(False)
        for name in ("MPN", "Manufacturer", "LCSC"):
            f = fp.GetField(name)
            if f is not None:
                f.SetVisible(False)
        # the socket outline silk runs at x = +-14.95, on the 30 mm card edge;
        # pull it in to +-14.6 so it is not clipped (silk_edge_clearance)
        cx, lim = (x0 + x1) // 2, mm(14.6)
        for g in fp.GraphicalItems():
            if g.GetLayer() == pcbnew.F_SilkS and g.GetClass() == "PCB_SHAPE":
                for get, put in ((g.GetStart, g.SetStart), (g.GetEnd, g.SetEnd)):
                    p = get()
                    if abs(p.x - cx) > lim:
                        put(pcbnew.VECTOR2I(int(cx + (lim if p.x > cx else -lim)), p.y))
    elif ref.startswith("R") and ref[1:].isdigit():
        fp.SetValue("0R DNP")
        fp.SetField("MPN", "0402WGF0000TCE")
        fp.SetField("Manufacturer", "UNI-ROYAL")
        fp.SetField("LCSC", "C17168")
        for name in ("MPN", "Manufacturer", "LCSC"):
            f = fp.GetField(name)
            if f is not None:
                f.SetVisible(False)
        fp.Value().SetVisible(False)
        fp.SetDNP(True)
        fp.SetExcludedFromPosFiles(True)
    elif ref in ("CE1", "CE2"):
        fp.SetValue("card edge")
        fp.SetDNP(True)
        fp.SetExcludedFromBOM(True)
        fp.SetExcludedFromPosFiles(True)
    elif ref == "" and "hole" in fp.GetFPIDAsString():
        pad = next(iter(fp.Pads()))
        holes.append((fp, pad.GetPosition().x, pad.GetPosition().y, pad.GetDrillSize().x))

# Bobcat hold-down (2.6) first, then the RAK standoffs (2.4), left to right.
holes.sort(key=lambda h: (-round(pcbnew.ToMM(h[3]), 1), h[1]))
for i, (fp, hx, hy, drill) in enumerate(holes, start=1):
    fp.SetReference(f"MH{i}")
    fp.SetValue("Bobcat hold-down 2.6mm" if pcbnew.ToMM(drill) > 2.5 else "RAK standoff M2 2.4mm")
    fp.Reference().SetVisible(False)
    fp.Value().SetVisible(False)  # its Fab text sat on the hole in the fit-check PDF
    fp.SetExcludedFromBOM(True)
    fp.SetExcludedFromPosFiles(True)

# 1. thickness
board.GetDesignSettings().SetBoardThickness(mm(1.0))

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

# 6. scale bar on User.Drawings, below the board
bar_y = y1 + mm(6)
for sx, sy, ex, ey in ((x0, bar_y, x0 + mm(50), bar_y),
                       (x0, bar_y - mm(1.5), x0, bar_y + mm(1.5)),
                       (x0 + mm(50), bar_y - mm(1.5), x0 + mm(50), bar_y + mm(1.5))):
    seg = pcbnew.PCB_SHAPE(board)
    seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
    seg.SetStart(pcbnew.VECTOR2I(int(sx), int(sy)))
    seg.SetEnd(pcbnew.VECTOR2I(int(ex), int(ey)))
    seg.SetWidth(mm(0.2))
    seg.SetLayer(pcbnew.Dwgs_User)
    board.Add(seg)
    seg.thisown = False  # the board owns it; else Python frees it -> SaveBoard segfault
label = pcbnew.PCB_TEXT(board)
label.SetText("50.00 mm - print at 100% (actual size) and measure this bar")
label.SetLayer(pcbnew.Dwgs_User)
label.SetTextSize(pcbnew.VECTOR2I(mm(1.2), mm(1.2)))
label.SetTextThickness(mm(0.15))
label.SetPosition(pcbnew.VECTOR2I(int(x0 + mm(25)), int(bar_y + mm(3))))
board.Add(label)
label.thisown = False  # the board owns it

# dimension notes beside the outline (User.Drawings), measured from the finger edge
j1 = next(fp for fp in board.GetFootprints() if fp.GetReference() == "J1")
j1_front = min(y1 - p.GetPosition().y - p.GetSize().y / 2 for p in j1.Pads() if p.GetNumber() in ("1", "53"))
j1_line = y1 - next(p for p in j1.Pads() if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH).GetPosition().y
by_drill = {}
for _fp, hx, hy, d in holes:
    by_drill.setdefault(round(pcbnew.ToMM(d), 1), []).append((hx, hy))
notes = [f"outline {pcbnew.ToMM(y1 - y0):.2f} x 30.00 mm (31.30 at the socket tabs)",
         "all distances from the finger edge (bottom):"]
for d, pts in sorted(by_drill.items(), reverse=True):
    what = "Bobcat hold-down" if d > 2.5 else "RAK standoff (M2)"
    notes.append(f"{what} dia {d:.1f}: {pcbnew.ToMM(y1 - pts[0][1]):.2f} mm, "
                 f"x +-{pcbnew.ToMM(abs(pts[0][0] - (x0 + x1) / 2)):.2f}")
notes += [f"RAK socket card-edge line: {pcbnew.ToMM(j1_line):.2f} mm",
          f"RAK socket front (pads/tabs): {pcbnew.ToMM(j1_front):.2f} mm",
          f"RAK card end (line + 50.95): {pcbnew.ToMM(j1_line) + 50.95:.2f} mm "
          f"= stock card + {pcbnew.ToMM(j1_line):.2f}",
          "Mini Card top keep-out: 3.20 (4.20 at key)"]
for i, t in enumerate(notes):
    n = pcbnew.PCB_TEXT(board)
    n.SetText(t)
    n.SetLayer(pcbnew.Dwgs_User)
    n.SetTextSize(pcbnew.VECTOR2I(mm(1.0), mm(1.0)))
    n.SetTextThickness(mm(0.12))
    n.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
    n.SetPosition(pcbnew.VECTOR2I(int(x1 + mm(4)), int(y0 + mm(4) + i * mm(2.2))))
    board.Add(n)
    n.thisown = False  # the board owns it
print("; ".join(notes))

# 3. zones and rule areas (zones from the export, if any, out first)
for z in list(board.Zones()):
    board.Remove(z)


def rect(zone, ax, ay, bx, by):
    poly = pcbnew.SHAPE_POLY_SET()
    poly.NewOutline()
    for x, y in ((ax, ay), (bx, ay), (bx, by), (ax, by)):
        poly.Append(int(x), int(y))
    zone.SetOutline(poly)
    poly.thisown = False  # SetOutline keeps the pointer; Python must not free it


for layer in copper:
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(gnd)
    z.SetLocalClearance(mm(0.2))
    z.SetMinThickness(mm(0.2))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    # NEVER while stitching (stitch_gnd.py needs the unanchored fragments to
    # find them); the pipeline switches it to ALWAYS before the final refill.
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_NEVER)
    rect(z, x0, y0, x1, y1)
    board.Add(z)
    z.thisown = False  # the board owns it; else Python frees it -> SaveBoard segfault
def keepout(ax, ay, bx, by, pads_ok=True):
    k = pcbnew.ZONE(board)
    k.SetIsRuleArea(True)
    k.SetDoNotAllowZoneFills(True)
    k.SetDoNotAllowTracks(True)
    k.SetDoNotAllowVias(True)
    k.SetDoNotAllowPads(not pads_ok)
    k.SetDoNotAllowFootprints(False)
    k.SetLayerSet(pcbnew.LSET.AllCuMask())
    rect(k, ax, ay, bx, by)
    board.Add(k)
    k.thisown = False  # the board owns it; else Python frees it -> SaveBoard segfault
keepout(x0, y1 - mm(1.0), x1, y1)                       # finger bevel strip
for _fp, hx, hy, _d in holes:                           # Mini CEM fig 2-7
    keepout(hx - mm(2.9), hy - mm(2.9), hx + mm(2.9), hy + mm(2.9))

pcbnew.SaveBoard(dst, board)

# 7. 3D model for J1, written into the saved file: pushing an FP_3DMODEL through
#    SWIG made SaveBoard segfault in this build.
import re  # noqa: E402
text = open(dst).read()
start = text.index('(property "Reference" "J1"')
fp_start = text.rfind("\n\t(footprint ", 0, start)
depth, i = 0, fp_start + 2
while True:
    c = text[i]
    depth += c == "("
    depth -= c == ")"
    if depth == 0:
        break
    i += 1
block = re.sub(r"\n\t\t\(model .*?\n\t\t\)", "", text[fp_start:i], flags=re.S)
model = ('\n\t\t(model "${KIPRJMOD}/3dmodels/PCIE-52P52H_C444927.step"'
         '\n\t\t\t(offset (xyz 0 0 0))\n\t\t\t(scale (xyz 1 1 1))\n\t\t\t(rotate (xyz 0 0 0))\n\t\t)')
open(dst, "w").write(text[:fp_start] + block + model + "\n\t" + text[i:])
print(f"thickness 1.0 mm; {moved} even fingers -> B.Cu; GND zones on {len(copper)} layers; "
      f"bevel strip + {len(holes)} hold-down keep-outs; scale bar; J1 3D model")

# KiCad 10 bundled Python segfaults tearing down pcbnew SWIG objects at
# interpreter exit (exit 139, macOS crash dialog). Leave without finalisation.
# KiCad's background thread pool (zone triangulation after load) must finish
# before the process goes: os._exit() during it crashed in CacheTriangulation,
# and normal interpreter exit crashes in the SWIG finaliser. So: wait, then go.
import time  # noqa: E402
time.sleep(3)
sys.stdout.flush()
os._exit(0)
