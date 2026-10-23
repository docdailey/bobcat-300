# Fact sheet: populating the onboard GNSS footprint (Bobcat Miner 300, G285-V1.0)

Compiled 2026-10-22. Scope: the unpopulated GNSS site on the G285-V1.0 carrier (RK3566), what to fit there, where,
and how its PPS reaches the LoRa concentrator. Status: **parts in hand, beep checks partly done, nothing soldered
yet.**

Tags: **[VERIFIED: source]** = checked against a board photo, a bench continuity (beep) test, a datasheet, or a
parts order record. **[UNVERIFIED: source]** = plausible and sourced, but not checked against hardware or a
primary document. **[CONTRADICTED: ...]** = sources disagree. Notes alone never count as
verification.

Images (original photos of the board, with annotations): `img/bobcat-neo-pinmap.png` (pad numbers and functions
drawn over the footprint), `img/bobcat-placement-map.png` (every component position from U1 to J1, with fit, beep
or leave marked). The FCC exhibit crop is **not** copied (it is an FCC exhibit image). The annotated whole-board beep
photo is not copied either, because it shows unit serial labels.

## 1. The footprint

- The site is an empty 24-pad LCC footprint next to the Wi-Fi/BT module, on the SoC side of the board. It has
  12 pads on each long side, in groups of 7 and 5 separated by a wider gap, and a pin-1 triangle at one corner of a
  7-pad group. **[VERIFIED: board photo, `img/bobcat-neo-pinmap.png`]**
- Measured from the photo: pitch ≈ 1.1 mm (22.4 px against a 20.4 px/mm scale, cross-checked with the 50.95 mm
  mPCIe card in the same frame), gap ≈ 3.0 mm, pad-row span 14.1 mm, body ≈ 12.2 × 16.3 mm. **[UNVERIFIED: these are
  photo pixel measurements; nobody has taken calipers to the board yet]**
- The geometry matches the u-blox NEO form factor: 16.0 × 12.2 mm, 1.1 mm pitch, 3.0 mm gap, 24 pads.
  **[VERIFIED: u-blox NEO-M8 data sheet UBX-15031086, mechanical table (A = 16.0, B = 12.2, E = 1.1, F = 3.0),
  https://content.u-blox.com/sites/default/files/NEO-M8-FW3_DataSheet_UBX-15031086.pdf]**
- Pad numbering on the board: the four pads that beep to GND are 10, 12, 13 and 24. Those are exactly the NEO GND
  pins, so the numbering is confirmed: pin 1 is at the triangle and 1-12 run along the triangle's side. In the
  orientation of `bobcat-placement-map.png` (Wi-Fi module on the left), the bottom row is 1→12 left to right and
  the top row is 24→13 left to right. **[VERIFIED: beep test on the spare unit, 2026-10-11, plus the GND pin list
  in HIM UBX-15029985 Table 2]**
- In the KiCad stock library, only one footprint has 24 pads in two 7+5 rows at 1.1 mm pitch:
  `RF_GPS.pretty/ublox_NEO`. **[UNVERIFIED: library scan from the research notes, not re-run]**
- No public schematic or BOM exists. Every FCC filing under grantee 2AZCK holds the schematic and BOM as
  confidential. **[UNVERIFIED: FCC exhibit index as seen in the 2026-10-11 research; fccid.io now returns 403]**

## 2. What the factory designed for

- The board was designed with GNSS but shipped without it. The stock packet-forwarder config sets
  `"gps_tty_path": "/dev/ttyS5"`, the init scripts carry `#disabled gps`, and the DTB defines UART5
  (`serial@fe690000`, `uart5m0-xfer` = GPIO2_A1 RX / GPIO2_A2 TX) with `status = "disabled"`. There is no pps-gpio
  node. **[UNVERIFIED: stock eMMC extraction, plus the public decompiled DTB in
  https://github.com/NebraLtd/balena-bobcat-rk3566 (`add-rk3566-bobcat-dts.patch`); not re-read for this sheet]**
- The only populated example found anywhere is on the earlier PX30-generation board, **G280-V1.1**, in FCC ID
  2AZCK-MINER300 internal photo exhibit 5189067, photo 6
  (https://fccid.io/2AZCK-MINER300/Internal-Photos/Internal-photo-5189067). The module fitted there is a green
  NEO-format board whose main chip is marked **UC6226NIS**, with pad groups visibly 7+5. **[VERIFIED: the exhibit
  crop image; the chip marking is legible]**
- The UC6226 is a Unicore multi-GNSS SoC (GPS/BDS/GLONASS/Galileo, QFN40/WLCSP), which fits the product manual's
  "GPS1&BDS1". **[UNVERIFIED: trade-press listings only, e.g.
  https://everythingrf.com/products/gnss-soc/unicore-communications/817-763-uc6226; no official Unicore datasheet
  was found]**
- On the G280, about six 0402 parts are fitted between the u.FL and the module, along with one SOT-23-class part in
  or beside the antenna path (ESD, bias or LNA; not identified). **[VERIFIED: the exhibit crop image]** The G280 and
  G285 layouts differ, so these positions do not map pad for pad. **[VERIFIED: board photo vs. exhibit]**
- No populated G285 or TU-GM1002Z has been found. The RK3566 test sample in FCC ID 2AZCK-MINER3001 silkscreens the
  empty footprint `GPS`, the empty u.FL `GPS_ANT`, and the coin-cell holder `RTC`. **[UNVERIFIED: research notes
  from 2026-10-11 (exhibit 5581023); not re-fetched, 403]**

## 3. Module choice and pin mapping

- **Chosen module: u-blox NEO-M8T-0**, the timing variant in the NEO form factor. It is a 24-pin LCC,
  12.2 × 16.0 × 2.4 mm, VCC 2.7-3.6 V, with survey-in and fixed-position modes, timing accuracy ≤ 20 ns (clear sky)
  and time-pulse jitter ±11 ns. **[VERIFIED: NEO/LEA-M8T product summary UBX-16000801,
  https://content.u-blox.com/sites/default/files/products/documents/NEO-LEA-M8T_ProductSummary_%28UBX-16000801%29.pdf;
  part ordered, order record]**
- The NEO-M8T's antenna management is "external with logic-level antenna switching". The antenna supervisor is a
  LEA-M8T feature, so a DC-blocked feed has nothing to trip. **[VERIFIED: UBX-16000801]**
- Moisture handling: the NEO-M8 family is MSL 4, so bake the module before reflow if it has been exposed.
  **[VERIFIED for NEO-M8N/Q/M/J: UBX-15031086 §7.2.1; UNVERIFIED for M8T, whose own data sheet UBX-15025193 was not
  fetched]**

| Pad | NEO-M8T function | Board destination | Status |
|---|---|---|---|
| 1 | TP2 / SAFEBOOT_N (2nd time pulse) | 0201-class pair nearby; must not be pulled low at reset | GND short not yet checked |
| 2 | D_SEL (open = UART/I2C) | pair nearby | must not be grounded; not yet checked |
| 3 | TIMEPULSE (1PPS) | empty series position **R8** → mPCIe socket **pin 19** | **beeped** |
| 4 | EXTINT0 | pair in R9-R12 area | leave open |
| 5/6 | USB_DM/DP | pairs in R9-R12 area | leave open |
| 7 | VDD_USB | a component position (likely R12), **not** directly to GND | beeped |
| 8 | RESET_N | C6 position below | leave open |
| 9 | VCC_RF | C7 (10 nF slot) | leave empty |
| 10, 12, 13, 24 | GND | GND | **beeped** |
| 11 | RF_IN | RF chain RF1-RF6 → **J1** u.FL footprint at board edge | traced in photo, not beeped |
| 14 | LNA_EN | — | leave open |
| 15 | EXTINT1 (M8T only) | — | leave open |
| 18/19 | SDA/SCL | — | leave open |
| 20/21 | TXD/RXD | toward test-point row / UART5 (GPIO2_A1/A2) | **not yet confirmed** |
| 22 | V_BCKP | a component; far end not yet beeped | open item |
| 23 | VCC | C1/C2 nearby; source rail unknown | open item |

- Pin functions in the table come from **[VERIFIED: UBX-15031086 pin table; HIM UBX-15029985 Table 2, including
  the M8T-specific TP2 on pin 1, EXTINT0 on pin 4 and EXTINT1 on pin 15,
  https://content.u-blox.com/sites/default/files/NEO-8Q-NEO-M8-FW3_HIM_UBX-15029985.pdf]**.
- Pad 3 reaches an unpopulated series position (R8), and the other side of R8 reaches mPCIe socket pin 19. The PPS
  is therefore routed by design, and a 0 Ω or 1 kΩ part at R8 completes it without a wire. **[VERIFIED: beep test,
  spare unit, 2026-10-11]**
- Pad 7 goes to a component footprint, not straight to GND. **[VERIFIED: beep test]** u-blox requires VDD_USB to be
  connected to GND when USB is unused. **[VERIFIED: HIM §1.3.3 and Table 2]** Plan: fit 0 Ω at that position after
  checking that its far pad is GND.
- Pad 11 → matching chain → 3-pad u.FL footprint at the board edge (via-fenced coplanar trace). **[VERIFIED: board
  photo]** Continuity has not been checked; the chain is unpopulated, so it would read open anyway.
- Pads 20/21 → UART5 is supported by software evidence only; the copper path has not been beeped. **[UNVERIFIED]**
- The CR1220 cell backs a PCF8563/HYM8563-class RTC at I2C4 0x51 (DTB). It is not known to feed V_BCKP.
  **[UNVERIFIED: DTB extraction]**

## 4. Components to populate

Position names come from `img/bobcat-placement-map.png`. Sizes for the series positions have not been measured,
so 0402 and 0603 versions of several parts were ordered.

| Position | Function | Value | Package | MPN ordered | Status |
|---|---|---|---|---|---|
| U1 | GNSS module | NEO-M8T-0 | 24-LCC 12.2×16 | NEO-M8T-0 (u-blox) | in hand, not fitted |
| J1 | antenna connector (GPS_ANT) | U.FL receptacle, 50 Ω | SMD 3-pad | U.FL-R-SMT-1(10) (Hirose) ×2 | in hand |
| RF1, RF3-RF5, RF6 | RF_IN series (in line) | 0 Ω | 0402 / 0603 | ERJ-2GE0R00X / RC0603JR-070RL | fit only positions the beep shows **in line** |
| RF2 | 3-pad part, square centre | unknown (SOT-23-class on G280) | 3-pad | — | bridge only if the beep proves it is the signal path |
| S1, S2, C7 | shunt / bias / VCC_RF bypass | — | 0402 | — | **leave empty** |
| R8 | TIMEPULSE → mPCIe pin 19 | 0 Ω (or 1 kΩ) | 0402 / 0603 | ERJ-2GE0R00X, ERJ-2RKF1001X / RC0603JR-070RL, ERJ-3EKF1001V | fit; pad sized on the day |
| C1 | VCC decoupling, pad 23 | 100 nF X7R | 0402 / 0603 | GRM155R71C104KA88J / CC0603KRX7R9BB104 | fit if beep confirms pad 23 to GND |
| C2 | VCC bulk, pad 23 | 10 µF 6.3 V X5R | 0603 only | GRM188R60J106ME47D | fit if beep confirms; **no 0402 10 µF ordered** |
| R12 (probable) | VDD_USB (pad 7) to GND | 0 Ω | 0402 / 0603 | ERJ-2GE0R00X / RC0603JR-070RL | fit if far pad is GND |
| V_BCKP position | pad 22 to cell or VCC | 0 Ω, or strap 22→23 | 0402 / 0603 | as above | depends on beep check 3 |
| R1-R4 grid | UART/LED series | 0 Ω | — | as above | bridge only what breaks pad 20/21 continuity |
| D1, D2 (+ series R) | status LED footprints | — | — | — | skip |
| U2?, C4 | 5-pad SOT-23-5 + 0603, possibly an LDO | — | — | — | fit nothing unless pad 23 lacks 3.3 V |
| C3, C5, R5-R7 | unknown | — | — | — | leave |
| off-board | pigtail | U.FL (MHF I) → SMA(F) bulkhead, 1.37 mm, 150 mm | — | CAB.01084 (Taoglas) | in hand |

- Ordered part values and packages **[VERIFIED: parts order record descriptions, e.g. "RES SMD 0 OHM JUMPER 1/10W
  0402", "CAP CER 10UF 6.3V X5R 0603", "CONN U.FL RCPT STR 50 OHM SMD", "I-PEX MHFI(U.FL) TO 150MM 1.37MM"]**. The
  SMA(F) bulkhead end of CAB.01084 **[VERIFIED: RS listing, https://uk.rs-online.com/web/p/coaxial-cable/0690927]**.
- The positions and roles of every part (which pad goes in line, which is a shunt) are read from a photo.
  **[UNVERIFIED until beep check 6]**
- The C1/C2 values (100 nF + 10 µF) are generic decoupling practice. No explicit decoupling values were found in
  the HIM text. **[UNVERIFIED]**
- Not ordered, optional: a 47-100 pF C0G DC block for an RF series position, and BAT54 + 1 µF to diode-OR the
  coin cell into V_BCKP.

## 5. Antenna path

- Feed in this build: the output of a DC-blocked, amplified GNSS splitter. No bias inductor, no bias-tee cap and
  no supervisor are needed. RF series positions get 0 Ω; bias and shunt positions stay empty. **[UNVERIFIED:
  design intent; the splitter's DC blocking is from its product listing, not measured]**
- Limits: RF_IN absolute maximum is +15 dBm (50 Ω source). For an active antenna, u-blox recommends 15 dB minimum
  and 50 dB maximum gain. **[VERIFIED: UBX-15031086 absolute-maximum table and active-antenna recommendations]**
- If you use a single active antenna without a powered splitter, you must bias it yourself. The u-blox reference
  feeds VCC_RF through a 27 nH inductor (LQG15HS27NJ02) onto RF_IN, and uses a 47 pF DC block (GRM1555C1E470JZ01)
  when the bias comes from an external supply. **[VERIFIED: HIM UBX-15029985 §2.4.2 and reference BOM]** The
  G285's bias positions (S1/S2/C7) have not been identified. **[UNVERIFIED]**
- On the NEO-M8T, the SAW filter and extra LNA are on the module, so a passive antenna can connect directly.
  **[VERIFIED: UBX-16000801]**

## 6. PPS routing

- **To the concentrator:** pad 3 → R8 → mPCIe pin 19. **[VERIFIED: beep test]**
- On the stock N504S/N3504S card, pin 19 is assumed to be the SX1302 PPS input, following the RAK2287-family
  pinout, and the HAL enables the PPS latch counter. **[UNVERIFIED: no pulse has ever been delivered to pin 19 and
  seen in `pps_cnt`. The G285 socket is non-standard elsewhere (SPI on pins 3/5/6/7 rather than RAK's 45-51,
  proven with a logic analyzer), so the RAK-family assumption for pin 19 is not safe to take on trust]**
- **To the SoC:** there is no pps-gpio node in either DTB, and no copper path from pad 3 to an SoC GPIO has been
  found. The SoC would only see the PPS by tapping the pad-3 net or a status-LED pad with a wire and adding a
  pps-gpio overlay. **[UNVERIFIED: no beep test was done for an SoC path]**
- The serial port for NMEA/UBX is UART5 (`/dev/ttyS5`) once a DT overlay enables it:
  `&uart5 { status = "okay"; pinctrl-names = "default"; pinctrl-0 = <&uart5m0_xfer>; };`
  **[UNVERIFIED: overlay not tested; copper path not beeped]**

## 7. Bench beep results (spare unit, 2026-10-11, power off, card out)

- GND at pads 10, 12, 13 and 24, which confirms the numbering. **[VERIFIED: beep test]**
- Pad 3 → empty series footprint (R8) → mPCIe pin 19. **[VERIFIED: beep test]**
- Pad 7 → a component footprint, not directly to GND. **[VERIFIED: beep test]**
- Pad 22 → a component; its far end has not been beeped. **[VERIFIED: beep test (partial)]**
- Pads 20/21 → UART5 test points: **not done.** Pad 23 source rail: **not done.** Pads 1, 2, 8, 3 and 23 and the
  J1 centre pad must not short to GND: **not done.**

## 8. Install-day plan (not yet executed)

1. Setup: board unpowered, mPCIe card out, coin cell out, module freshly baked.
2. Measure the pad sizes of R8, the pad-7 position, RF1-RF6, C1 and C2, to choose 0402 or 0603.
3. Power-off checks: pad 23 to 3.3 V (directly, or only via U2?); C1/C2 between pad 23 and GND; pad 22's far end to
   the cell + or to pad 23; pad 7's position, far pad to GND; R8 identity; walk pad 11 → J1 marking each position in
   line or shunt; pads 20/21 → test points. Check that pads 1, 2, 8, 3 and 23 and the J1 centre do **not** short to
   GND.
4. Power-on (12 V, no module, card out): pad 23 must read 2.7-3.6 V, and no pad may exceed 3.6 V (the VCC
   absolute maximum). **[VERIFIED limits: UBX-15031086]** Power off and wait 30 s.
5. Fit passives in this order: J1 + in-line RF 0 Ω → R8 → C1/C2 → pad-7 0 Ω → V_BCKP 0 Ω or strap 22→23 (u-blox:
  "If no backup supply voltage is available, connect the V_BCKP pin to VCC" **[VERIFIED: HIM §1.3.2]**). Re-check
  continuity and voltage after each step.
6. Module: flux, match pin 1 to the triangle, tack opposite corners, solder the rest. Mask the Wi-Fi module with
   Kapton and preheat the board for hot air. Inspect for bridges at 22-23-24, 10-11-12 and 20-21.
7. First light: antenna on J1, card in, power up; watch `pps_cnt` on the logger's status lines go from 0 to
   counting after the first fix.

Install-day status as of 2026-10-22: the module is not fitted on any unit. **[UNVERIFIED: project log]**

## 9. Risks

- **mPCIe pin 19 conflict with a RAK5146.** On the RAK5146, pin 19 is the PPS **output** of its on-card ZOE-M8Q
  ("Time pulse output"), and pin 23 is RESET_GPS (an active-low input). **[VERIFIED: RAK5146 datasheet pin table,
  https://docs.rakwireless.com/product-categories/wislink/rak5146/datasheet/]** On a carrier with a populated
  NEO-M8T and a fitted R8, TIMEPULSE and the RAK PPS output would drive the same net. **Never combine them**:
  leave R8 empty, or isolate pin 19 in the interposer the RAK5146 already needs for its SPI remap.
- **Pin 1 / pin 2 / pin 8 grounded by the board:** a grounded pin 1 boots the module into safeboot (HIM: "Do not
  pull low during reset"), a grounded pin 2 selects SPI, and a grounded pin 8 holds the module in reset.
  **[VERIFIED: HIM Table 2]** The board's handling of these pins is not yet checked.
- **Supply may be switched.** A commented-out `#set_gpio 112 1  # GPS power` in Nebra's board-init.sh hints at a
  switched GPS rail, and U2? may be a load switch or LDO. **[UNVERIFIED]**
- **Pin-7 trap for non-u-blox modules:** on the Quectel LC29H/LC29T, pin 7 is a 2.8 V output, so a NEO-style ground
  strap there would short it. **[UNVERIFIED: Quectel LC29H HD V1.3, as cited in the research notes]**
- Hot-air rework next to the Wi-Fi module and the RK3566 shield; MSL 4 moisture handling (see §3).

## Contradictions & open questions

- **[CONTRADICTED: the install plan, check 4, says "u-blox allows VDD_USB open"; HIM §1.3.3 says that if USB is
  unused, VDD_USB "must be connected to GND".]** Follow the HIM: fit the pad-7 0 Ω to GND.
- **[CONTRADICTED: the 2026-10-11 research table says the G280-V1.1 photos show "no NEO-shaped footprint visible"
  and a second, unidentified green module; the 2026-10-16 review of the same exhibit's photo 6 shows that the second
  module is the populated UC6226 NEO-format GNSS.]** The later reading is supported by the legible chip marking.
- **[CONTRADICTED: the plan says "0R/1k/100nF/10uF in 0402 and 0603"; the order record has 10 µF in 0603 only.]**
  If C2 turns out to be an 0402 pad, a 0603 part will overhang it.
- **[CONTRADICTED: the research notes say the u-blox reference puts "10 µF + 100 nF at the pin"; this value pair
  was not found in the HIM text.]**
- Open: does pin 19 actually reach the SX1302 PPS latch on the stock card? This is the critical unknown; a bench
  pulse on pin 19 with `pps_cnt` watched would settle it before any soldering.
- Open: the pad-23 supply source (direct 3.3 V, or through U2?/a GPIO-switched rail).
- Open: the far end of pad 22; the RF in-line vs. shunt positions; the identity of RF2; the copper path from pads
  20/21; whether pads 1, 2 and 8 are free of pull-downs.
- Open: the pad sizes (0402 vs. 0603) at every position.
- Open: whether any SoC GPIO receives the PPS (none found).
- Open: the NEO-M8T data sheet (UBX-15025193) itself was not fetched; the M8T-specific facts here come from the
  HIM and the product summary.
