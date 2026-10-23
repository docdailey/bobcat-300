# G285 → RAK5146 interposer

**Status: routed and KiCad-DRC-clean (review release). Not yet fabricated or tested; check everything before ordering.**

A full-size mini-PCIe card-edge board (1.0 mm, gold fingers) that plugs into the Bobcat G285 concentrator socket, with a
mini-PCIe socket on top for a RAK5146 (SX1303 + ZOE-M8Q GPS, SPI variant).

## Why

The G285 socket carries SPI on pins 3/5/6/7. RAK's cards expect 45/47/49/51. See
[../docs/socket-pinout-rak5146.md](../docs/socket-pinout-rak5146.md).

## Specification

| Bobcat (fingers) | RAK5146 (socket) | Treatment |
|---|---|---|
| 3 SCK | 45 | reroute |
| 5 MISO | 47 | reroute |
| 6 MOSI | 49 | reroute |
| 7 CS | 51 | reroute |
| 19 | 19 (RAK GPS PPS out) | **isolated** |
| 23 | 23 (RAK GPS reset in) | **isolated** |
| 2, 24, 39, 41, 52 | same | 3.3 V straight through |
| all GND | same | straight through |
| 22 | 22 (RAK reset, active high) | straight through (sits low = RAK running) |
| everything else | same | straight through |

- Every pin on 0.1 in. headers behind default-closed solder jumpers, so the board doubles as a breakout/probe board.
- Original pin positions for 3/5/6/7 and 45/47/49/51 are on jumpers, default open, so the reroute can be undone.

Design files, renders and a REVIEW fab package are in this directory (see Files below).

## Design status (2026-10-22)

Drafted in a tscircuit-based board pipeline; **not fab-ready**.

- 4-layer, **1.0 mm** (PCI-SIG Mini Card thickness), ENIG with hard-gold fingers and a 30° bevel. The outline is 50 × 109.5 mm
  because JLCPCB won't bevel fingers on boards under 50 mm, so the board overhangs the G285 by about 58 mm (a bench
  fixture; the lid won't close).
- Card edge per the PCI-SIG Mini Card Electromechanical Spec Rev 1.2: 52 contacts, key, Ø2.6 mm hold-down holes.
- RAK socket: SOFNG PCIE-52P52H (LCSC C444927). The RAK card needs ~3.2 mm M2 standoffs.
- 37 solder jumpers: reroute closed, original 3/5/6/7 ↔ 45/47/49/51 and 19/23 open; two 2×18 breakout headers.
- **Routing complete.** Freerouting (300 passes) on a DSN written from the KiCad board: every signal routed, GND
  through a solid In1.Cu plane plus F/B pours stitched with 193 vias. 1228 track segments, 143 routed vias.
- **KiCad DRC (kicad-cli 10.0.4): 0 errors, 0 unconnected.** The 52 `copper_edge_clearance` findings on the finger
  pads are exempted and itemised by the fab profile's named `card_edge` override. 46 `lib_footprint_issues`
  warnings remain (the exported footprints are not from a KiCad library).
- **gerber_check (jlcpcb-4layer-cardedge): all pass.** 4 copper layers, outline 50.1 × 109.6 mm, min drill 0.2 mm
  (414 holes), closest drill pair 0.402 mm, drill to edge 0.45 mm, no orphan paste, min aperture 0.127 mm.
- **Not factory export_ready.** Every hard gate passes; the factory loop stops at `human` on the soft gate
  `completeness ≥ 3.0` (Jev judged 2.81–2.92 and named no defect). The fab zip here was made with kicad-cli
  directly and is marked REVIEW. Nothing has been ordered or uploaded.
- **Hand fixes, all scripted** (`pipeline/`): the tscircuit→KiCad export put the 26 even fingers on F.Cu, set 1.6 mm,
  mis-layered the pours and keepouts, and modelled the 27 bridged jumpers as cross-net tracks. `fix_export.py`
  corrects each (even fingers back on B.Cu, 1.0 mm, GND zones on F/In1/B with a 1 mm no-copper bevel strip,
  net-tie jumpers, 0.8 mm refdes, J1 MPN/LCSC, DNP flags, MH1–MH4). Then `kicad_to_dsn.py` → Freerouting →
  `ses_to_kicad.py` → `stitch_gnd.py`.
- Finger face orientation checked on a real card (2026-10-22): the top (component) face carries the **odd** contacts. The 5th
  and 8th contacts from the short end on the top face beep to ground = pins 9 and 15, matching the spec and this design. **[VERIFIED: continuity]**

## Files

- `kicad/` KiCad 10 project: `bobcat-rak-interposer.kicad_pcb` / `.kicad_pro` / `.kicad_sch` (the factory's source for this board).
- `fab/` `bobcat-rak-interposer-REVIEW-gerbers.zip` (Gerbers, PTH/NPTH Excellon, drill maps), BOM and CPL (J1 only; everything else is DNP or a board feature).
- `renders/` PCB top, bottom, In1 GND plane and schematic (SVG + PNG).
- `pipeline/`: the conversion and routing scripts (export fixes, KiCad↔Specctra DSN/SES, ground stitching).
- JLCPCB options when approved: 4 layers, 1.0 mm, ENIG, gold fingers, 30° bevel, no V-cut panel, no impedance control.
