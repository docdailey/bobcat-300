# G285 → RAK5146 interposer

**Status: design in progress, not yet fabricated or tested.**

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

Design files and fab outputs will land here after review.

## Design status (2026-10-22)

Drafted in a tscircuit-based board pipeline; **not fab-ready**.

- 4-layer, **1.0 mm** (PCI-SIG Mini Card thickness), ENIG with hard-gold fingers and a 30° bevel. The outline is 50 × 109.5 mm
  because JLCPCB won't bevel fingers on boards under 50 mm, so the board overhangs the G285 by about 58 mm (a bench
  fixture; the lid won't close).
- Card edge per the PCI-SIG Mini Card Electromechanical Spec Rev 1.2: 52 contacts, key, Ø2.6 mm hold-down holes.
- RAK socket: SOFNG PCIE-52P52H (LCSC C444927). The RAK card needs ~3.2 mm M2 standoffs.
- 37 solder jumpers: reroute closed, original 3/5/6/7 ↔ 45/47/49/51 and 19/23 open; two 2×18 breakout headers.
- Routing: 99.5% routed, 1 open net (a ground link) and 7 DRC errors from the auto-router. To finish, either rerun with
  Freerouting or complete it by hand in KiCad, then run a full KiCad DRC.
- Finger face orientation checked on a real card (2026-10-22): the top (component) face carries the **odd** contacts. The 5th
  and 8th contacts from the short end on the top face beep to ground = pins 9 and 15, matching the spec and this design. **[VERIFIED: continuity]**
