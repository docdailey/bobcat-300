#!/bin/sh
# bobcat-rak-stack-adapter: exported board -> routed, stitched, DRC'd board.
# One batched run; pcbnew scripts never fill zones (kicad-cli does), and each
# sleeps 3 s before os._exit so KiCad's thread pool is idle at exit.
#   run_pipeline.sh            (expects bobcat-rak-stack-adapter.kicad_pcb/.kicad_pro and fixed.ses)
# Freerouting runs separately on beast:  java -jar freerouting.jar -de fixed.dsn -do fixed.ses -mp 150
set -e
KP=${KP:-/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3}
KC=${KC:-/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli}
Q="Debug: Adding|memory leak|stdpbase"
py() { $KP "$@" 2>&1 | grep -vE "$Q" || true; }
refill() { cp fixed.kicad_pro "${1%.kicad_pcb}.kicad_pro"; $KC pcb drc --refill-zones --save-board -o /tmp/sa_refill.json "$1" >/dev/null; }
step=${1:-route}
if [ "$step" = dsn ]; then
  py fix_export.py bobcat-rak-stack-adapter.kicad_pcb fixed.kicad_pcb
  cp bobcat-rak-stack-adapter.kicad_pro fixed.kicad_pro
  # the export carries 0.25 mm hole-to-hole; the fab profile (and gerber_check) wants 0.5
  python3 -c 'import json,sys; p=sys.argv[1]; d=json.load(open(p)); d["board"]["design_settings"]["rules"]["min_hole_to_hole"]=0.5; json.dump(d,open(p,"w"),indent=2)' fixed.kicad_pro
  py kicad_to_dsn.py fixed.kicad_pcb fixed.dsn
  exit 0
fi
py ses_to_kicad.py fixed.kicad_pcb fixed.ses imported.kicad_pcb
py space_vias.py imported.kicad_pcb routed.kicad_pcb
refill routed.kicad_pcb
py stitch_gnd.py routed.kicad_pcb s0.kicad_pcb grid
refill s0.kicad_pcb
for i in 1 2 3; do
  py stitch_gnd.py s$((i-1)).kicad_pcb s$i.kicad_pcb targeted
  refill s$i.kicad_pcb
  last=s$i.kicad_pcb
done
# islands kept while stitching; any fragment still without a via is floating copper: remove it
sed 's/(island_removal_mode 1)/(island_removal_mode 0)/' $last > islands.kicad_pcb
refill islands.kicad_pcb
py stitch_gnd.py islands.kicad_pcb final.kicad_pcb prune
cp fixed.kicad_pro final.kicad_pro
$KC pcb drc --refill-zones --save-board --format json --severity-error --severity-warning -o drc_final.json final.kicad_pcb | tail -1
