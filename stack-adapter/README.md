# G285 → RAK5146 stack adapter (rev B)

**Status: routed and KiCad-DRC-clean (review release, 2026-10-22). Not yet fabricated or tested; check everything before ordering.**

A Mini Card-sized stack adapter. Its gold fingers plug into the Bobcat G285 concentrator socket. A mini-PCIe socket sits on top,
right behind the fingers, so the RAK5146 card lies directly above the adapter, over the Bobcat's own card area. There is no
breakout and no jumper field. Rev A, the large breakout interposer, is in [../interposer-rev-a/](../interposer-rev-a/).

![3D](renders/bobcat-rak-stack-adapter-3d-iso.png)

## Why

The G285 socket carries SPI on pins 3/5/6/7. RAK's cards expect it on 45/47/49/51. The pinout was proven with a logic
analyzer; see [../docs/socket-pinout-rak5146.md](../docs/socket-pinout-rak5146.md).

## Electrical

| Bobcat (fingers) | RAK5146 (socket J1) | Treatment |
|---|---|---|
| 3 SCK | 45 | rerouted |
| 5 MISO | 47 | rerouted |
| 6 MOSI | 49 | rerouted |
| 7 CS | 51 | rerouted |
| 2, 24, 39, 41, 52 | same | 3.3 V, all tied, 0.25 mm traces |
| 4, 9, 15, 18, 21, 26, 27, 29, 34, 35, 37, 40, 43, 50 | same + socket tabs | GND, routed plus F/B pours, 131 stitching vias |
| 22 | 22 (RAK reset, active high) | straight through (sits low = RAK running) |
| **47** (SoC GPIO4_D0) | **19** (RAK GPS PPS out, 3.3 V) | **GPS PPS via R47P, 0R, FITTED** |
| 45 (SoC GPIO4_C7) | 19 (RAK GPS PPS out) | alternate PPS via R45P, 0R, DNP |
| 19 | 19 | **not connected.** DNP 0R option R19 (straight through) |
| 23 | 23 (RAK GPS reset in) | **not connected.** DNP 0R option R23 |
| 30, 31, 32, 33 | same (RAK GPS I2C / UART) | not connected. DNP 0R options R30–R33 |
| everything else | — | not connected on either side |

**GPS PPS: RAK19 → R47P → finger 47 → GPIO4_D0.**
- The GMAC1 PHC has no programmable pins (`pps_available=0`), so PPS has to land on a SoC GPIO.
- Bobcat socket pins 45 and 47 are spare SoC inputs (GPIO4_C7 / GPIO4_D0). That was verified by a read-only EXT_PORT scan with a
  1 kΩ pull on 2026-10-22.
- On the adapter, fingers 45 and 47 are their own nets (F45, F47). They are **not** the RAK's 45/47: those come from the SPI
  reroute of fingers 3 and 5.
- With R19 and R45P open, the RAK-19 net is exactly J1.19, R47P, R45P and R19. Only R47P is fitted, so it reaches finger 47 and
  nothing else (checked on the final netlist). Fit R45P instead of R47P to use GPIO4_C7.

All links are 0402 0R, UNI-ROYAL 0402WGF0000TCE (LCSC C17168, a JLCPCB basic part). On every link, pad 1 is the Bobcat finger and
pad 2 the RAK socket pin.

## Mechanical (all distances from the finger edge)

| Item | Value | Source |
|---|---|---|
| Outline | **60.30 × 30.00 mm**, 31.30 mm across the socket-tab ears (3.20–7.90 mm) | this design |
| Thickness / fingers | 1.0 mm, contacts 0.60 × 2.55 on 0.80, odd contacts on top (verified on a real card) | PCI-SIG Mini CEM 1.2 |
| Bobcat hold-down holes | Ø2.6 at **48.05**, x ±12.10 | Mini CEM fig 2-3 |
| RAK socket J1 | SOFNG PCIE-52P52H (LCSC C444927), top side; pin N at the same x as finger N | |
| J1 card-edge line (where the RAK card's edge seats; the peg line) | **9.30** | footprint + Mini CEM host-socket datum |
| J1 front (odd-row pads, solder tabs) | **4.20**, i.e. **1.65 mm past the 2.55 mm fingers**; J1 body from 5.50 | see "How close" |
| RAK standoff holes | Ø2.4 NPTH at **57.35** (9.30 + 48.05), x ±12.10 | Mini CEM fig 2-3 |
| RAK card far end | 9.30 + 50.95 = **60.25** | |
| Hold-down keep-outs | 5.8 × 5.8 mm, all layers, at every hole | Mini CEM fig 2-7 |
| Bottom side | flat: no components, fingers + routing + GND only | |

**How close the socket can sit to the fingers.** Three limits apply. The third one binds:

1. **Spec.** Mini CEM 1.2 fig 2-7 has a top-side "component keep out area for connector" of **3.20 mm MIN** from the edge, and
   4.20 mm only behind the key slot. Fig 2-9 shows the host connector housing reaching 3.20 mm MAX onto the card.
2. **Fab.** JLCPCB's gold-finger rules set no finger-to-pad spacing. They require only:
   - a full solder-mask opening on the fingers
   - no copper in the bevel
   - the 50 mm minimum size

   The fab profile's general rules still apply: 0.127 mm pad to pad, 0.30 mm copper to edge. J1's solder tabs sit over the
   card's corner notches (edge at 3.20 mm), so the tab front must be at ≥ 3.50 mm. That gives S ≥ 8.6 mm.
3. **Routing escape (binding).** These top fingers have to leave sideways:
   - SPI 3/5/7
   - the PPS fingers 45/47
   - the option fingers 19/23/31/33

   Each needs a via between its end (2.55 mm) and J1's pads, and the bottom fingers' traces (MOSI 6) must pass between those
   vias. Freerouting completes at **S = 9.30** (pads at 4.20). At S = 9.1 / 9.0 / 8.8 / 8.6 it leaves 1 / 1 / 4 / 4 nets
   unrouted after pours.

   Pre-placing the escape vias in a 0.95 mm gap was also tried. Those through vias land among the bottom fingers and wall in
   MOSI 6, so it doesn't work.

**Fit inside the G285.** The space measured past a stock card is 17 mm, so the stack must end within 50.95 + 17 = 67.95 mm of the
finger edge. Seating depth is already inside the numbers above:

- The adapter's fingers seat in the Bobcat socket exactly like the stock card. The 48.05 mm hold-down distance is measured from
  that same seated edge, so there is no offset.
- The RAK card's edge seats in J1 at the card-edge line, 9.30 mm. Its first few mm are inside the J1 body, and it ends at
  9.30 + 50.95 = 60.25 mm.

The stack therefore ends at **60.30 mm** (the outline; the RAK card at 60.25). That is 9.35 mm past a stock card and 7.65 mm inside
the 67.95 mm limit.

**Heights.**

- J1 holds the RAK card plane at 3.25 mm, so the card's underside is 2.75 mm above the adapter.
- RAK standoffs: **M2, 2.75 mm** (or a 2.5 mm M2 SMT/press standoff plus a 0.25 mm washer).
- The Bobcat hold-down screws at 48.05 sit under the RAK card. An M2 pan or wafer head of ≤ 1.6 mm clears the 2.75 mm gap.
- J1's two plastic pegs (Ø1.8 / Ø1.3 NPTH at 9.30) poke ~0.6 mm out of the bottom. Check them against the G285 board under the
  card; trim them flush if they touch.
- No Z conflict with the Bobcat socket. Its housing covers the card only inside the 3.20 mm keep-out (4.20 at the key), and every
  part of J1 starts at 4.20 mm or more.

**Paper fit check.** Print [renders/bobcat-rak-stack-adapter-1to1-fitcheck.pdf](renders/bobcat-rak-stack-adapter-1to1-fitcheck.pdf)
at 100% (A4 page) and confirm that the bar reads 50.00 mm. The page has the outline, holes, J1 footprint and courtyard, and the
dimensions above as text. Also check the ears against the Bobcat socket's side latches.

## Fabrication: JLCPCB gold fingers on a 30 mm card

JLCPCB does not accept a board this size with gold fingers as a single board:

- The length and width of a single board **or panel** with gold fingers must each be ≥ 50 mm, and chamfers are not offered under
  5 × 5 cm.
- Fingers on a V-cut panel cannot be bevelled.
- Only ENIG gives gold fingers.
- The finger area gets a full solder-mask opening, and the bevel zone must hold no copper. This board keeps a 1.0 mm no-copper
  strip, except the fingers.
- With a 30° bevel on 1.0 mm, the bevel reaches ≈ 0.43 mm in: L = (1.0/2 − 0.5/2)/tan 30°.

Sources: [JLCPCB: gold fingers](https://jlcpcb.com/help/article/jlcpcb-gold-fingers),
[JLCPCB order FAQ: gold fingers](https://jlcpcb.com/quote/pcbOrderFaq/Gold%20Fingers).

**The order uses the 2-up panel in [fab/panel/](fab/panel/)** (built with KiKit 1.8.1; `make_panel.sh` rebuilds it):

- **Layout:** two boards side by side, finger edges flush on the panel's bottom edge. That edge carries nothing else: no rail,
  no tab, no V-cut.
- **Tabs:** mouse-bite tabs, two per long side, about 20 and 40 mm from the finger edge. Each is 3 mm wide with 0.5 mm NPTH
  holes at 1.0 mm pitch, which keeps drills 0.5 mm apart.
- **Rails:** 5 mm rails left and right only, with 3 fiducials (1 mm copper, 2 mm opening) and 4 tooling holes (Ø2.0).
- **Size:** 78.7 × 60.4 mm, which clears 50 × 50.
- **Checks:** KiCad DRC 0 errors and 0 unconnected; the 104 finger-pad edge findings are the card-edge override, 52 per board.
  gerber_check (jlcpcb-2layer-cardedge): **all pass, including outline**.

GND stitching vias keep 1.0 mm from the board outline, so they stay clear of the mouse-bites.

**JLCPCB / JLCONE order options**

PCB:

| Option | Setting |
|---|---|
| Base material | FR-4 |
| Layers | 2 |
| Dimensions | 78.7 × 60.4 mm |
| PCB qty | 5 panels (= 10 boards; 5 is JLC's minimum) |
| Product type | industrial/consumer |
| Different design | 1 |
| Delivery format | **Panel by Customer**, 2 × 1 = 2 pcs/panel, break-away = **mouse-bites / tab-route** (no V-cut) |
| Thickness | **1.0 mm** |
| Color | any (green is the cheapest) |
| Surface finish | **ENIG** |
| Gold fingers | **Yes** |
| Bevel | **30°**, on the finger edge (the bottom edge of the panel) |
| Copper weight | 1 oz |
| Via covering | tented |
| Remove order number | as preferred |
| Castellated / impedance | no |

PCBA:

| Option | Setting |
|---|---|
| Type | **Economic** |
| Side | **Top** |
| Qty | **3 panels = 6 boards** (≥ 5) |
| Tooling holes | added by customer |
| Edge rails / fiducials | already on the panel; don't add more |
| Files | `fab/panel/bobcat-rak-stack-adapter-panel-bom.csv` and `-cpl.csv` |

- **BOM:** J1_0, J1_1 = C444927 (SOFNG PCIE-52P52H, Extended, offered for Economic and Standard); R47P_0, R47P_1 = C17168 (0R 0402, Basic). Every other footprint is DNP and left out.
- **Economic vs Standard:** J1 is a plain single-sided SMT part that JLCPCB lists for Economic assembly. Standard adds cost and lead
  time for nothing on this board.

**J1 rotation in JLCPCB's preview.** The KiCad footprint *is* the EasyEDA/JLC footprint for C444927 (imported unchanged), placed at
180°. The CPL's 180° therefore puts JLC's model in the same frame. In the preview, check three things:
- The socket body sits over both pad rows, with its card slot opening toward the board's hold-down holes, away from the gold fingers.
- The **larger Ø1.8 peg is on the left** (fingers at the bottom) and the Ø1.3 peg on the right. The pegs are asymmetric, so a wrong
  rotation shows up as pegs off their holes.
- R47P sits at 270° on its two pads, left of the option row.

If the preview shows the pegs swapped or the body off the pads, set J1 to 0° there; don't edit the files.

Sources: [JLCPCB: edge rails and fiducials for assembly](https://jlcpcb.com/help/article/how-to-add-edge-rails-fiducials-for-pcb-assembly-order),
[JLCPCB: process edges and positioning holes](https://jlcpcb.com/help/article/specifications-for-adding-process-edges-and-positioning-holes),
[JLCPCB assembly capabilities](https://jlcpcb.com/capabilities/pcb-assembly-capabilities),
[C444927](https://jlcpcb.com/partdetail/C444927).

The single board's REVIEW zip in `fab/` fails `outline` (31.4 × 60.4 mm < 50 × 50) by design and is for review only. Order the panel.

## Design status (2026-10-22)

The design starts in a tscircuit-based board pipeline (pcb-factory, board `bobcat-rak-stack-adapter`, branch
`bobcat-rak-interposer`). It is finished in KiCad by scripts, never by mouse; the scripts are in `pipeline/`:

1. `fix_export.py` repairs the tscircuit → KiCad export:
   - the even fingers go back to B.Cu, and the thickness is set to 1.0 mm
   - GND pours, the bevel strip and the hold-down keep-outs are added
   - part data is set: R47P is fitted, the other links are DNP
   - the holes become MH1–MH4, and the J1 silk is kept off the edge
   - the J1 3D model goes on, and the scale bar and dimension notes go on the fit-check page
2. `kicad_to_dsn.py` writes the Specctra DSN. Settings:
   - 0.6/0.3 vias
   - signal 0.14 mm, clearance 0.13 mm, 3V3 0.25 mm
   - via-to-via and peg keep-outs sized so drills stay ≥ 0.5 mm apart
3. Freerouting 2.4.1 (150 passes) gave 0 unrouted after pours (`pipeline/freerouting.log`).
4. `ses_to_kicad.py` imports the routes.
5. `space_vias.py` restores 0.5 mm drill spacing if any via pair is closer; nothing needed moving on this route.
6. `stitch_gnd.py` places 131 stitching vias, each ≥ 1.0 mm from the outline, (grid, then targeted fragments, then a prune of floating ones). Zone refills are
   done by `kicad-cli` between passes.
7. `run_pipeline.sh` runs steps 4–6; `export.sh` makes the package.

Results:

- **KiCad DRC (kicad-cli 10.0.4): 0 errors, 0 unconnected.**
  - The 52 `copper_edge_clearance` findings are on the finger pads only. They are exempted and itemised by the fab profile's
    named `card_edge` override.
  - 15 `lib_footprint_issues` warnings remain: the exported footprints are not from a KiCad library.
- **gerber_check (jlcpcb-2layer-cardedge): all pass except `outline`** (see Fabrication). The values:
  - 2 copper layers
  - min drill 0.30 mm
  - closest drill pair 0.507 mm (limit 0.50)
  - drill to edge 1.4 mm
  - no orphan paste
  - min aperture 0.14 mm
- **Factory loop.** Every hard gate passes. The loop stops on the soft gate `completeness ≥ 3.0` (Jev 2.98) with `edit_source` and
  names no defect, the same as rev A. It is **not export_ready**, and the fab zip here was made with kicad-cli directly and is
  marked REVIEW. Nothing has been ordered or uploaded.
- Routing: 355 track segments, 45 routed vias, 131 GND stitching vias.

## Files

- `kicad/`: the KiCad 10 project (`bobcat-rak-stack-adapter.kicad_pcb` / `.kicad_pro` / `.kicad_sch`, the factory's source for
  this board). It also holds `3dmodels/PCIE-52P52H_C444927.step`, the SOFNG socket model from EasyEDA/LCSC.
- `fab/`:
  - `bobcat-rak-stack-adapter-REVIEW-gerbers.zip`: Gerbers, PTH/NPTH Excellon and drill maps, single board, not panelised
  - the KiCad DRC and gerber_check JSON
  - BOM and CPL: J1 and R47P are populated; R19, R23, R30–R33 and R45P are DNP. **Check J1's rotation in JLCPCB's placement
    preview**, because EasyEDA-derived parts often need a 180° correction.
- `renders/`:
  - 3D views (iso, top, bottom, a socket close-up)
  - flat top/bottom copper and the schematic (SVG + PNG)
  - the 1:1 fit-check PDF
- `pipeline/`: the scripts above, `index.tsx` (the board source as committed in pcb-factory) and the Freerouting log. To rebuild:
  1. Put the exported `bobcat-rak-stack-adapter.kicad_*` in a work dir next to the scripts.
  2. `run_pipeline.sh dsn`
  3. Run Freerouting on `fixed.dsn` to make `fixed.ses`.
  4. `run_pipeline.sh`
  5. `export.sh` (it writes to the parent of the work dir).

## Assembly order

1. Solder J1 and R47P (or have JLCPCB place them). Leave R19, R23, R30–R33 and R45P empty.
2. Fit two M2 × 2.75 mm standoffs at the RAK holes (57.35 mm).
3. Plug the adapter into the G285 socket and screw it down at 48.05 mm with low-head M2 screws.
4. Insert the RAK5146 into J1 at an angle, press it down onto the standoffs and screw it down.
5. Run `chip_id`; expect a real version byte, not `0xFF`. GPS PPS then arrives on GPIO4_D0.
