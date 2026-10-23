"""Fold a Freerouting .ses session into a KiCad board (no GUI).

pcbnew.ImportSpecctraSES() needs the PCB editor frame, like the DSN export.
Wires become PCB_TRACK segments on their layer, vias become through PCB_VIAs
sized from the padstack name ("Via[0-3]_<pad>:<drill>_um"), each on its net.
Session coordinates are in 0.1 um (resolution um 10), y up.

Usage (KiCad python): python3 ses_to_kicad.py board.kicad_pcb in.ses out.kicad_pcb
"""
import re
import sys

import pcbnew

MIN_WIDTH = pcbnew.FromMM(0.13)

src, ses_path, dst = sys.argv[1:4]
board = pcbnew.LoadBoard(src)
text = open(ses_path).read()

res = re.search(r"\(resolution um (\d+)\)", text)
per_um = int(res.group(1)) if res else 10


def nm(v: str) -> int:
    return round(float(v) / per_um * 1000)


LAYER = {"F.Cu": pcbnew.F_Cu, "In1.Cu": pcbnew.In1_Cu, "In2.Cu": pcbnew.In2_Cu, "B.Cu": pcbnew.B_Cu}
nets = {str(k): v for k, v in board.GetNetsByName().items()}


def tokens(s):
    return re.findall(r'\(|\)|"[^"]*"|[^\s()]+', s)


def parse(tok, i=0):
    out = []
    while i < len(tok):
        t = tok[i]
        if t == "(":
            sub, i = parse(tok, i + 1)
            out.append(sub)
        elif t == ")":
            return out, i + 1
        else:
            out.append(t.strip('"'))
            i += 1
    return out, i


tree, _ = parse(tokens(text))


def find(node, name):
    if isinstance(node, list):
        if node and node[0] == name:
            yield node
        for child in node:
            yield from find(child, name)


# copper already on the board (handed to Freerouting as protected wiring) comes
# back in the session too: don't add it twice
have_seg = {(t.GetLayer(), *sorted([(t.GetStart().x, t.GetStart().y), (t.GetEnd().x, t.GetEnd().y)]))
            for t in board.GetTracks() if t.GetClass() != "PCB_VIA"}
have_via = {(t.GetPosition().x, t.GetPosition().y) for t in board.GetTracks() if t.GetClass() == "PCB_VIA"}


def near(a, b):
    return abs(a[0] - b[0]) <= 200 and abs(a[1] - b[1]) <= 200   # 0.2 um: DSN rounding


tracks = vias = 0
for net in find(tree, "net"):
    if len(net) < 2 or not isinstance(net[1], str):
        continue
    netinfo = nets.get(net[1])
    if netinfo is None:
        continue
    for wire in (c for c in net if isinstance(c, list) and c and c[0] == "wire"):
        path = next(c for c in wire if isinstance(c, list) and c and c[0] == "path")
        layer, width, coords = path[1], nm(path[2]), path[3:]
        # Freerouting necks a wire down to enter a crowded pad (one came back at
        # 0.097 mm); the fab floor is 0.127, so no wire goes below 0.13 mm.
        width = max(width, MIN_WIDTH)
        pts = [(nm(coords[k]), -nm(coords[k + 1])) for k in range(0, len(coords) - 1, 2)]
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            key = sorted([(ax, ay), (bx, by)])
            if any(l == LAYER[layer] and near(key[0], a) and near(key[1], b) for l, a, b in have_seg):
                continue
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(pcbnew.VECTOR2I(ax, ay))
            t.SetEnd(pcbnew.VECTOR2I(bx, by))
            t.SetWidth(width)
            t.SetLayer(LAYER[layer])
            t.SetNet(netinfo)
            board.Add(t)
            t.thisown = False  # the board owns it; else Python frees it -> SaveBoard segfault
            tracks += 1
    for via in (c for c in net if isinstance(c, list) and c and c[0] == "via"):
        m = re.search(r"_(\d+):(\d+)_um", via[1])
        if any(near((nm(via[2]), -nm(via[3])), h) for h in have_via):
            continue
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(pcbnew.VECTOR2I(nm(via[2]), -nm(via[3])))
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetWidth(int(m.group(1)) * 1000 if m else pcbnew.FromMM(0.6))
        v.SetDrill(int(m.group(2)) * 1000 if m else pcbnew.FromMM(0.3))
        v.SetNet(netinfo)
        board.Add(v)
        v.thisown = False  # the board owns it; else Python frees it -> SaveBoard segfault
        vias += 1

# zones are refilled by kicad-cli (pcb drc --refill-zones --save-board), not here
pcbnew.SaveBoard(dst, board)
print(f"{tracks} track segments, {vias} vias (zones not refilled: run kicad-cli)")

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
