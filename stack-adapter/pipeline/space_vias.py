"""Push routed vias apart to the fab profile's 0.5 mm drill-to-drill spacing.

Freerouting honours the DSN via_via clearance on most but not all via pairs (one
came back 0.479 mm drill to drill on the 60.3 mm board). For every pair of
different-net vias closer than HOLE_GAP, the via of the non-power net is moved
straight away from the other by the shortfall + 0.02 mm, dragging the track ends
that sit on it. The moves are a few hundredths of a mm; kicad-cli DRC after this
step is what proves nothing else got too close.

Usage (KiCad python): python3 space_vias.py in.kicad_pcb out.kicad_pcb
No zone fills here (kicad-cli refills afterwards).
"""
import math
import os
import sys
import time

import pcbnew

src, dst = sys.argv[1], sys.argv[2]
board = pcbnew.LoadBoard(src)
mm = pcbnew.FromMM
HOLE_GAP = mm(0.5)   # jlcpcb-2layer-cardedge min_hole_to_hole_mm
MARGIN = mm(0.02)
POWER = ("GND", "V3V3")

vias = [t for t in board.GetTracks() if t.GetClass() == "PCB_VIA"]
segs = [t for t in board.GetTracks() if t.GetClass() != "PCB_VIA"]
moved = 0
for i, a in enumerate(vias):
    for b in vias[i + 1:]:
        if a.GetNetCode() == b.GetNetCode():
            continue
        pa, pb = a.GetPosition(), b.GetPosition()
        d = math.hypot(pa.x - pb.x, pa.y - pb.y)
        gap = d - a.GetDrill() / 2 - b.GetDrill() / 2
        if gap >= HOLE_GAP:
            continue
        mover, other = (b, a) if a.GetNetname() in POWER else (a, b)
        pm, po = mover.GetPosition(), other.GetPosition()
        push = HOLE_GAP - gap + MARGIN
        ux, uy = (pm.x - po.x) / d, (pm.y - po.y) / d
        new = pcbnew.VECTOR2I(int(pm.x + ux * push), int(pm.y + uy * push))
        for s in segs:
            if s.GetNetCode() != mover.GetNetCode():
                continue
            if (s.GetStart() - pm).EuclideanNorm() < mm(0.01):
                s.SetStart(new)
            if (s.GetEnd() - pm).EuclideanNorm() < mm(0.01):
                s.SetEnd(new)
        mover.SetPosition(new)
        moved += 1
        print(f"moved {mover.GetNetname()} via {pcbnew.ToMM(push):.3f} mm away from "
              f"{other.GetNetname()} (drill gap was {pcbnew.ToMM(gap):.3f})")

pcbnew.SaveBoard(dst, board)
print(f"space_vias: {moved} via(s) moved")

# KiCad 10 bundled Python: let the thread pool go idle, then leave without the
# SWIG finaliser (both crash at exit otherwise).
time.sleep(3)
sys.stdout.flush()
os._exit(0)
