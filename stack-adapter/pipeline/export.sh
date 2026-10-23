#!/bin/sh
# bobcat-rak-stack-adapter: final.kicad_pcb -> review package (kicad/, fab/, renders/).
# kicad-cli only (no pcbnew Python here).
set -e
KC=${KC:-/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli}
B=bobcat-rak-stack-adapter
W=$(cd "$(dirname "$0")" && pwd); P=$(dirname "$W")
mkdir -p "$P/kicad" "$P/fab/gerbers" "$P/renders"
cp "$W/final.kicad_pcb" "$P/kicad/$B.kicad_pcb"
cp "$W/final.kicad_pro" "$P/kicad/$B.kicad_pro"
cp "$W/$B.kicad_sch" "$P/kicad/$B.kicad_sch"
cd "$P/kicad"
$KC pcb drc --format json --severity-error --severity-warning -o "$P/fab/$B-kicad-drc.json" $B.kicad_pcb | tail -1
rm -f "$P"/fab/gerbers/*
$KC pcb export gerbers --layers F.Cu,B.Cu,F.Mask,B.Mask,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,Edge.Cuts \
  --no-x2 --subtract-soldermask -o "$P/fab/gerbers/" $B.kicad_pcb >/dev/null
$KC pcb export drill --format excellon --excellon-separate-th --excellon-units mm --generate-map --map-format gerberx2 \
  -o "$P/fab/gerbers/" $B.kicad_pcb >/dev/null
(cd "$P/fab/gerbers" && rm -f "../$B-REVIEW-gerbers.zip" && zip -q "../$B-REVIEW-gerbers.zip" *)
$KC pcb export pos --format csv --units mm --side both --exclude-dnp -o "/tmp/$B-pos.csv" $B.kicad_pcb >/dev/null
# JLCPCB CPL + BOM (J1 and R47P populated; the seven 0R options are listed as DNP)
python3 - "/tmp/$B-pos.csv" "$P/fab/$B" <<'PY'
import csv, sys
rows = list(csv.DictReader(open(sys.argv[1])))
with open(sys.argv[2] + "-cpl.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
    for r in rows:
        w.writerow([r["Ref"], f'{float(r["PosX"]):.3f}mm', f'{float(r["PosY"]):.3f}mm',
                    "Top" if r["Side"] == "top" else "Bottom", f'{float(r["Rot"]) % 360:.0f}'])
with open(sys.argv[2] + "-bom.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["Comment", "Designator", "Footprint", "LCSC", "Manufacturer", "MPN", "Qty", "Populate"])
    w.writerow(["PCIE-52P52H Mini PCIe socket", "J1", "PCIE-52P52H", "C444927", "SOFNG", "PCIE-52P52H", 1, "yes"])
    w.writerow(["0R 0402 (GPS PPS: RAK 19 -> finger 47)", "R47P", "0402", "C17168", "UNI-ROYAL", "0402WGF0000TCE", 1, "yes"])
    w.writerow(["0R 0402 (option links, DNP)", "R19,R23,R30,R31,R32,R33,R45P", "0402", "C17168", "UNI-ROYAL", "0402WGF0000TCE", 7, "no (DNP)"])
PY
# renders: flat
$KC pcb export svg --layers F.Cu,F.Mask,F.Silkscreen,Edge.Cuts,User.Drawings --mode-single --fit-page-to-board --exclude-drawing-sheet -o "$P/renders/$B-pcb-top.svg" $B.kicad_pcb >/dev/null
$KC pcb export svg --layers B.Cu,B.Mask,B.Silkscreen,Edge.Cuts --mirror --mode-single --fit-page-to-board --exclude-drawing-sheet -o "$P/renders/$B-pcb-bottom.svg" $B.kicad_pcb >/dev/null
$KC sch export svg --exclude-drawing-sheet -o "$P/renders/" $B.kicad_sch >/dev/null 2>&1 || true
[ -f "$P/renders/$B.svg" ] && mv "$P/renders/$B.svg" "$P/renders/$B-schematic.svg"
rm -f "$P/renders/$B-Sheet 1.svg"
for f in "$P"/renders/*.svg; do rsvg-convert -z 4 -b white "$f" -o "${f%.svg}.png"; done
# renders: 3D (J1 carries the SOFNG PCIE-52P52H STEP from kicad/3dmodels/)
for side in top bottom; do
  $KC pcb render --side $side --quality high --width 1600 --height 2400 --background opaque -o "$P/renders/$B-3d-$side.png" $B.kicad_pcb >/dev/null
done
$KC pcb render --side top --rotate "-55,0,35" --perspective --quality high --width 2000 --height 1600 --zoom 0.9 --background opaque -o "$P/renders/$B-3d-iso.png" $B.kicad_pcb >/dev/null
$KC pcb render --side top --rotate "-60,0,150" --perspective --quality high --width 2000 --height 1400 --zoom 2.2 --background opaque -o "$P/renders/$B-3d-socket.png" $B.kicad_pcb >/dev/null
# 1:1 paper fit-check PDF: outline, holes, socket footprint, scale bar
$KC pcb export pdf --layers Edge.Cuts,F.Fab,F.Courtyard,User.Drawings --sp --mode-single --black-and-white --scale 1 \
  --include-border-title -o "$P/renders/$B-1to1-fitcheck.pdf" $B.kicad_pcb >/dev/null
ls -la "$P/fab" "$P/renders"
