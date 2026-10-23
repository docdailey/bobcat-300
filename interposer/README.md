# G285 → RAK5146 interposer

**Status: design in progress, not yet fabricated or tested.**

A full-size mini-PCIe card-edge board (0.8 mm, gold fingers) that plugs into the Bobcat G285 concentrator socket, with a
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
