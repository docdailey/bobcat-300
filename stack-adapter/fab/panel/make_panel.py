"""2-up JLCPCB panel of bobcat-rak-stack-adapter with KiKit (1.8.1, user site).

Two boards side by side, finger edges flush on the panel's bottom edge, joined
by mouse-bite tabs on the long sides only; 5 mm rails left and right carry 3
fiducials and 4 tooling holes. No V-cut; nothing on the finger edge.
Zones are NOT filled here (kicad-cli refills afterwards); KiKit runs inside
pcbnew, so the process waits for KiCad's thread pool and leaves via os._exit.

Usage (KiCad python): python3 make_panel.py board.kicad_pcb panel.json out.kicad_pcb
"""
import os
import sys
import time

from kikit.ui import cli

src, cfg, dst = sys.argv[1:4]
rc = 0
try:
    cli.main(["panelize", "--preset", cfg, src, dst], standalone_mode=False)
except SystemExit as e:
    rc = e.code or 0
except Exception as e:  # report, still exit cleanly
    print("kikit failed:", repr(e))
    rc = 1
print("panel written" if os.path.exists(dst) and rc == 0 else f"rc={rc}")
time.sleep(3)
sys.stdout.flush()
os._exit(rc)
