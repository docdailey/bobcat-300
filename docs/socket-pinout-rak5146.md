# Mini-PCIe socket pinout, RAK5146 and the interposer: fact sheet

Status tags: **[VERIFIED: source]**, **[UNVERIFIED: source]**, **[CONTRADICTED: what disagrees]**.

## The socket is not RAK/Semtech-standard

- The G285 concentrator socket is a standard mini-PCIe (52-pin, 0.8 mm pitch) connector, but its signal assignment
  follows Bobcat's own card (N3504S, PCB "N350(H)-01A"), not the RAK2287/RAK5146 convention. **[VERIFIED: logic-analyzer removal tests + continuity, unit 1, 2026-10-22]**
- Stock card N3504S carries SX1302/SX1303 and band (868/915/923 MHz) build-option pads; the units here read SX1302,
  version 0x10. **[VERIFIED: card silkscreen photo; chip_id output]**

### SPI (proven by removal: unplug one probe, that one signal dies, the rest of the bus stays live)

| Bobcat socket pin | Signal | Evidence |
|---|---|---|
| 3 | SCK  | clock died on removal; 1.000 MHz under a test stimulus, 1.998 MHz under the Semtech HAL **[VERIFIED: DSLogic capture]** |
| 5 | MISO | stock card answered version 0x10 on it; replies died on removal **[VERIFIED: DSLogic capture]** |
| 6 | MOSI | decoded the A5 0F test pattern and HAL register traffic; died on removal **[VERIFIED: DSLogic capture]** |
| 7 | CS   | ~321 µs assertions bracketing every clock burst; died on removal **[VERIFIED: DSLogic capture]** |

- Matches the community map on helium-repurposed.deobfuscated.org (Bobcat Miner 300 page: "SPI (CLK/MOSI/MISO/CE) on
  minipcie pins 3, 6, 5, 7"). **[VERIFIED: page fetched 2026-10-22]**
- SoC side: SPI1 on pinmux group spi1m1 (GPIO3_C1/C2/C3 + CS0 GPIO3_A1), `/dev/spidev1.0`. **[VERIFIED: pinmux-pins on unit 1]**

### Power, ground, other pins

- 3.3 V on pins 2, 24, 39, 41, 52 (3.4 V measured), switched by RF-enable GPIO3_D5 (gpio3-29) and power GPIO3_D2
  (gpio3-26). **[VERIFIED: meter, unit 1, toggling the GPIOs]**
- Ground: pins 4 and 18 beep to the shield can. **[VERIFIED: continuity]**
- Pin 22: the Bobcat's SX1302 reset line (GPIO4_C5 / gpio4-21) was toggled at 1 Hz and never appeared on pin 22 (or 17,
  19, 20, 23, or any short-side pin). Pin 22 sits at 0 V. The community page lists reset on 22 for its own wiring. **[CONTRADICTED: community page lists RST on 22; our toggle test did not see the stock reset there]**
- Odd pins 1, 3, 5, 7, 11, 13, 17, 19, 23 are wired from a column of series resistors beside the socket; 1/11/13/17/19/23
  functions unknown. **[VERIFIED: continuity, unit 1]**
- Pins 36/38 (USB D-/D+) reach an unpopulated 0402 pair: a USB build option, not fitted. **[VERIFIED: continuity]**
- RAK's SPI pins on the Bobcat: 45 → spare SoC GPIO4_C7, 47 → GPIO4_D0, 49 and 51 unconnected. **[VERIFIED: read-only
  /dev/mem GPIO input scan + 1 kΩ pull on each pin]** So no software-only (bit-bang) fix is possible.

## RAK5146 (from the RAK datasheet)

- RAK5146-115 / PID 516010 = 9xx MHz band, SPI interface, GPS (ZOE-M8Q), no LBT. **[VERIFIED: RAK datasheet ordering table + package label]**
- SPI 45 SCK / 47 MISO / 49 MOSI / 51 CSN; reset 22 (active high, ≥100 ns); 3.3 V on 2/24/39/41/52; ~82 mA RX, ~0.5 A TX
  at 27 dBm. **[VERIFIED: RAK5146 datasheet]**
- Pins that collide with Bobcat-driven lines: 19 = GPS PPS **output**, 23 = GPS reset **input** (active low).
  1/3/5/7/11 are "unconnected by default" (reserved SX1261), 13 = USB-variant MCU reset, 17 NC. **[VERIFIED: RAK5146 datasheet pin table]**
- In an unmodified G285 the RAK5146 reads chip version 0xFF (MISO idle-high, CS never reaches pin 51), in both units.
  **[VERIFIED: chip_id on unit 1 and unit 2]**

## Interposer specification (rev A; rev B keeps the electrical core)

- Card-edge (gold-finger) mini-PCIe board, full-size outline, 1.0 mm, plugs into the Bobcat; mini-PCIe socket on top for the RAK5146.
- Reroute: Bobcat 3 → RAK 45 (SCK), 5 → 47 (MISO), 6 → 49 (MOSI), 7 → 51 (CS).
- Isolate: 19 and 23 (do not pass through).
- Straight through: 3.3 V (2, 24, 39, 41, 52), all grounds, 22 (held low = RAK running).
- Every pin to a 0.1 in. header behind a default-closed solder jumper (doubles as a breakout/probe board).
- No off-the-shelf pass-through interposer with per-pin jumpers was found (only socket-only breakouts). **[VERIFIED: searches 2026-10-22]**
- Rev A (breakout interposer, every pin on jumpers + headers, 50 × 109.5 mm) was routed and DRC-clean but rejected as too
  big: [../interposer-rev-a/](../interposer-rev-a/).
- **Rev B, the stack adapter** ([../stack-adapter/](../stack-adapter/)): Mini Card width, 60.3 mm long, RAK socket right behind
  the fingers so the RAK card stacks over the Bobcat's card area. Only the four SPI reroutes, 3.3 V, GND and 22; 19/23 not
  connected (DNP 0R options for 19, 23, 30–33). No breakout. Routed and KiCad-DRC-clean; not fabricated.
  **[UNVERIFIED: not built or tested]**

## Lessons (methods)

- SARADC channel 2 ("card present" in stock firmware) is not a rail monitor: ~850 with the socket empty or a RAK fitted,
  157/991 (off/on) with the stock card on unit 2, but 206/309 on unit 1 with the same card working. Don't judge a card by it.
- Meter-probing 0.8 mm staggered socket tails led to a false "CS = 17"; solder short test leads and use removal tests.
- A logic analyzer's channel order may not match the planned lead map; only removal tests tie a channel to a pin. Before
  calling a removal negative, confirm a known-good channel is still live (idle gaps look like a killed signal).

## Contradictions & open questions

- Reset on pin 22: the community map says yes, our toggle of GPIO4_C5 says the stock reset does not reach 22. Harmless for the
  RAK (reset is active high, pin 22 sits low), but unresolved.
- Functions of Bobcat odd pins 1, 11, 13, 17, 19, 23 (the community page used 19 = BUSY and 1 = IRQ for an SX1262 hack).
