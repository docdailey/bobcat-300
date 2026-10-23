#!/bin/sh
# 2-up JLCPCB panel: KiKit (inside pcbnew, no fills) -> source design rules into
# the panel project -> kicad-cli refill + DRC -> Gerbers/drill/zip -> renders.
set -e
cd "$(dirname "$0")"
KP=${KP:-/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3}
KC=${KC:-/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli}
B=bobcat-rak-stack-adapter-panel
SRC=../../kicad/bobcat-rak-stack-adapter
$KP make_panel.py $SRC.kicad_pcb panel.json $B.kicad_pcb 2>&1 | grep -vE "Debug: Adding|memory leak|stdpbase" || true
rm -f "~$B.kicad_pro.lck"
# KiKit writes KiCad's default 0.2 mm netclass; the board was routed to the source's rules
python3 - "$B.kicad_pro" "$SRC.kicad_pro" <<'PY'
import json, sys
d, s = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
d["net_settings"]["classes"] = s["net_settings"]["classes"]
d["board"]["design_settings"]["rules"].update(s["board"]["design_settings"]["rules"])
json.dump(d, open(sys.argv[1], "w"), indent=2)
PY
$KC pcb drc --refill-zones --save-board --format json --severity-error --severity-warning -o $B-kicad-drc.json $B.kicad_pcb | tail -1
mkdir -p gerbers && rm -f gerbers/*
$KC pcb export gerbers --layers F.Cu,B.Cu,F.Mask,B.Mask,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,Edge.Cuts \
  --no-x2 --subtract-soldermask -o gerbers/ $B.kicad_pcb >/dev/null
$KC pcb export drill --format excellon --excellon-separate-th --excellon-units mm --generate-map --map-format gerberx2 \
  -o gerbers/ $B.kicad_pcb >/dev/null
rm -f $B-gerbers.zip && (cd gerbers && zip -q ../$B-gerbers.zip *)
$KC pcb export pos --format csv --units mm --side both --exclude-dnp -o $B-pos-kicad.csv $B.kicad_pcb >/dev/null
$KC pcb render --side top --quality high --width 2400 --height 2000 --background opaque -o $B-3d-top.png $B.kicad_pcb >/dev/null
$KC pcb export svg --layers F.Cu,F.Mask,F.Silkscreen,Edge.Cuts --mode-single --fit-page-to-board --exclude-drawing-sheet -o $B-top.svg $B.kicad_pcb >/dev/null
rsvg-convert -z 4 -b white $B-top.svg -o $B-top.png
