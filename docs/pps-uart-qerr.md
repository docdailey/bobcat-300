# Notes: GPS PPS, the GPS UART and qErr on the Bobcat Miner 300 (G285) with a RAK5146

Compiled 2026-10-22. Scope: getting the RAK5146's GPS time pulse (PPS) and its serial port to the Bobcat's RK3566,
and correcting the u-blox quantization sawtooth (qErr). Covers the hardware path, how the carved core 3 captures
the edge, the UART mapping that is still open, and the qErr hook.

Tags: **[VERIFIED: source]** = checked in code, host tests, a datasheet or a bench measurement. **[UNVERIFIED:
source]** = design intent, project notes or community reports not yet confirmed here. Nothing in the PPS
capture or qErr path has run on hardware yet: "verified" for the software means verified by host tests on a
development machine, not on the board.

## 1. The PPS path and how core 3 captures it

### Wiring

```
RAK5146 pin 19 (GPS PPS out, 3.3 V, rising edge, 1 Hz)
  -> adapter link R47P
  -> Bobcat mini-PCIe socket pin 47
  -> RK3566 GPIO4_D0 (GPIO bank 4, line 24; Linux gpio-152)

alternate: adapter link R45P -> socket pin 45 -> GPIO4_C7 (bank 4, line 23; gpio-151)
```

- RAK5146 pin 19 is the GPS PPS output. **[VERIFIED: RAK5146 datasheet pin table, as recorded in the socket fact sheet]**
- Bobcat socket pins 45 and 47 reach the SoC GPIOs GPIO4_C7 and GPIO4_D0. **[VERIFIED: read-only scan of every GPIO
  bank's input register while each socket pin was pulled through 1 kΩ]**
- On the stack adapter, R47P (0 Ω, **fitted**) takes the RAK's PPS (pin 19) to socket finger 47; R45P (unfitted) is the
  alternate onto finger 45. Fingers 45 and 47 are their own nets: the RAK's 45/47 are fed only by the SPI reroute from
  Bobcat 3/5. **[VERIFIED: adapter netlist and BOM (stack-adapter/); not yet built or continuity-checked on a board]**
- On the RAK side, pins 45 and 47 are SPI SCK and MISO. The interposer reroutes the RAK's SPI onto the Bobcat's
  SPI pins (3/5/6/7), so on the adapter the Bobcat-47 → RAK-47 path must be **open**. Otherwise PPS and MISO
  share a net. **[VERIFIED: socket pinout by logic-analyzer removal tests; adapter continuity UNVERIFIED]**
- RAK pin 19 must not also reach Bobcat socket pin 19, which belongs to the stock card's PPS net. The interposer
  isolates 19. **[VERIFIED: interposer spec; build UNVERIFIED]**
- **IO voltage of GPIO4_C7/D0: 3.3 V, by strong evidence.** The RAK's PPS is 3.3 V, so a 1.8 V pad group would
  need a level shifter.
  - The G285 device tree's io-domains node gives vccio1/5/6/7 = vcc_3v3 (SWITCH_REG1), vccio2/4 = vcc_1v8
    (DCDC_REG5), vccio3 = vccio_sd and pmuio1/2 = vcc3v3_pmu. **[VERIFIED: G285 DTB]**
  - With socket power on and no card fitted, socket pins 45 and 47 idled at 3.3 V on a meter. A 1 kΩ to ground
    pulled them to 0, and the input-register scan saw GPIO4_C7/D0 follow.
    **[VERIFIED: meter + EXT_PORT scan on a test unit, 2026-10-22]**
  - Which vccio domain owns GPIO4_C7/D0 in the RK3566 datasheet's IO table. **[UNVERIFIED]**

  Keep it as a gate before fitting the RAK on any unit: confirm the domain, or repeat the meter check.

### Capture on core 3

The Bobcat runs Linux on cores 0-2. Core 3 is taken offline and runs a small bare-metal Rust program started
through PSCI. It shares one megabyte of memory with Linux. The PPS engine is a port of an earlier Raspberry Pi
Zero 2 W bare-metal timing node's engine, which measured 38-44 ns per-edge jitter there.
**[VERIFIED: code; the Pi figure from that project's field logs, UNVERIFIED here]**

- **Prediction.** A tracker learns the 24 MHz counter's frequency against the GPS seconds, rejects glitches,
  bridges missed pulses and predicts the next edge. Once locked, the prediction window is about ±21 µs.
  **[VERIFIED: host tests]**
- **Capture spin.** Only inside the predicted window does the core run a tight assembly loop. Each pass loads
  the GPIO input register (EXT_PORT), tests the bit, and reads the CPU cycle counter. The edge lies between the
  last low read and the first high read. **[VERIFIED: code + disassembly; UNVERIFIED on hardware]**
- **Sub-tick dating.** The cycle counts are converted to 24 MHz counter time using two calibration points, one
  before and one after the spin. If Linux changed the CPU clock mid-spin, the edge is dropped rather than
  mis-dated. **[VERIFIED: host tests]**
- **PHC stamp.** The edge is stamped with the PTP hardware clock (the Ethernet MAC's PTP clock, disciplined by
  ptp4l). The stamp is the mean of 16 bracketed PHC reads taken right after the edge, each projected back to it.
  The output per edge is the signed offset of the GPS PPS from the nearest PHC second. **[VERIFIED: host tests]**
- **Read-only.** The pin is only read. Core 3 never writes its direction, pull or pin mux, and refuses the pin
  if it is configured as an output. **[VERIFIED: code]**
- **Phase trim.** A slow, quality-gated integrator is ported from the Pi engine and its value is reported. It
  is self-referenced, so it cannot see a latency that is common to every edge. The PPS-vs-PHC offset is
  therefore published raw. Calibrating the absolute capture latency needs an outside reference.
  **[VERIFIED: host test showing a constant 150 ns latency leaves the trim unchanged]**

## 2. The GPS UART (not mapped yet)

- RAK5146 pin 31 is the host's TX into the GPS (GPS RX), and pin 33 is the GPS's TX to the host. The links R31
  and R33 on the adapter are unfitted (R30/R32 likewise for the GPS I2C pins). **[VERIFIED: adapter netlist and BOM;
  RAK pin functions per the RAK5146 pin table, re-check against the RAK datasheet before fitting]**
- **The Bobcat side of socket pins 31 and 33 is NOT mapped.** The socket survey covered the odd pins 1-23 and
  pins 45-51, not 31/33. **[VERIFIED: the socket fact sheet has no entry for 31/33]**

### Method to map it (read-only first)

1. **Find the GPIO.** Run the read-only scanner, which samples every GPIO bank's EXT_PORT register (offset 0x70)
   through /dev/mem and prints any bit that changes. Pull socket pin 31 to 3.3 V through **1 kΩ**, then to GND
   through 1 kΩ, and watch for the bit that follows. Repeat for 33. The resistor is not optional: if the pin
   turns out to be a SoC output, 1 kΩ limits the fight to about 3 mA. Never touch the pin with a bare 3.3 V or
   GND lead. **[VERIFIED: the same method found 45/47 → GPIO4_C7/D0]**
2. **Find the UART.** Look up the found GPIO in the RK3566 IOMUX table and see whether one of its functions is
   a UART TX/RX (UARTn, mux variant m0/m1/m2). Its partner pin must be the one socket 33 or 31 reached, with the
   directions crossed (GPS TX → SoC RX). On a live system the pinctrl debugfs lists the pin's groups and
   functions, and the device tree tells you whether that UART is enabled.
3. **Check the voltage.** The GPIO's IO-domain voltage must be 3.3 V. Use the same evidence as for the PPS: the
   device tree's vccioN supplies, and a meter on the idle socket pin. On this board vccio2/4 are 1.8 V, so this
   is a real check.
4. **If both pins land on one UART's TX/RX:** enable that UART with a device-tree overlay and read the GPS at its
   default rate. If they land on plain GPIOs with no UART function, use the fallback.

### Jumper fallback

- The board has an unpopulated GNSS footprint whose serial pads point at UART5 (GPIO2_A1 = RX, GPIO2_A2 = TX).
  UART5 is defined in the device tree (`uart5m0-xfer`) but `disabled`. The fallback is to jumper RAK 33 (GPS TX)
  to the UART5 RX point and RAK 31 (GPS RX) to UART5 TX, then enable UART5 with an overlay.
  **[VERIFIED: UART5 node and pin group in the device tree. UNVERIFIED: copper from the footprint pads to those
  SoC pins (not yet beeped), and the domain of GPIO2_A1/A2 (the DTB alone does not say which vccio it is)]**

## 3. qErr: the u-blox sawtooth

### What it is

- A u-blox receiver can only place its PPS edge on a tick of its own internal clock. Each pulse is therefore off
  from the ideal second by a quantization error. That error walks as a sawtooth of roughly ±10-20 ns on M8-class
  receivers. **[UNVERIFIED for the RAK5146's ZOE-M8Q: general u-blox M8 behavior; measure it]**
- The receiver reports the error in **UBX-TIM-TP** (class 0x0D, id 0x01, 16-byte payload). The fields are towMS
  (U4), towSubMS (U4, ms·2^-32), qErr (I4, **picoseconds**), week (U2), flags (X1: bit 0 timeBase GNSS/UTC,
  bit 1 UTC available, bit 4 qErrInvalid) and refInfo (X1). The message describes the **next** time pulse: it
  is sent after pulse N-1, and its time of week and qErr belong to pulse N. Reference: *u-blox 8 / u-blox M8
  Receiver Description Including Protocol Specification*, UBX-13003221, section on UBX-TIM-TP.
  **[UNVERIFIED: field layout and flag bits as implemented in the decoder; not yet checked against a live
  ZOE-M8Q]**
- One report says qErr is not supported on the M8 "FTS" product variant. Check that the ZOE-M8Q actually outputs
  TIM-TP with a valid qErr before relying on it ([time-nuts, 2018](https://www.febo.com/pipermail/time-nuts/2018-May/110500.html)).
  **[UNVERIFIED]**
- **Sign convention.** The convention assumed here is qErr = actual pulse − ideal pulse, so the ideal edge is
  the measured edge minus qErr. A negative qErr means the next pulse will be early. This matches community
  readings of the field ([time-nuts, 2018](https://www.febo.com/pipermail/time-nuts/2018-May/110479.html)), but
  the wording of the u-blox document itself has not been checked for this note. **[UNVERIFIED]** It is cheap to
  settle on the bench: with the right sign, the per-edge jitter drops by about the sawtooth's spread; with the
  wrong sign, the sawtooth doubles. The core-3 engine has a flag to flip the sign without a rebuild.

### How it is matched and subtracted

1. **Reader (not built yet).** A Linux reader gets TIM-TP from the GPS UART. It verifies the checksum and
   computes the TAI second of the pulse the message describes: GPS week and time of week, plus 19 s from GPS to
   TAI. If the pulse's time base is UTC, it adds TAI−UTC instead. A message whose pulse is not on a whole second
   gets no key.
2. **Table.** The reader writes `{TAI second, qErr ps, valid}` into a small table in the shared memory. The
   table has eight slots, slot = second mod 8, each guarded by its own sequence lock. The write must happen
   **before** that pulse arrives.
3. **Lookup.** When core 3 captures an edge, it takes the edge's nearest PHC second as the key. It applies the
   qErr only if an entry exists for exactly that second, is marked valid, and has |qErr| ≤ 100 ns.
4. **Subtraction.** The qErr is subtracted from the edge time and from its PHC time **before** anything else
   uses the edge: before the tracker, so before the trim, and before the PPS-vs-PHC averages.
5. **Logging.** Every edge records what happened: applied, missing (no entry for that second), invalid, out of
   range, or no PHC stamp. It also records the qErr subtracted, so the raw value is always recoverable.

**[VERIFIED: host tests for slot keying, ahead-of-time writes, slot reuse, torn reads, matching only the exact
second, invalid/range rejection, the exact edge shift, and the sawtooth removed before the tracker. UNVERIFIED on
hardware]**

### Why averaging without it is biased

- The sawtooth is not white noise. It is a beat between the receiver's clock period and the one-second grid. When
  the receiver's oscillator sits near a multiple of that grid, the beat slows down, and qErr can stay on one side
  of zero for minutes ("hanging bridges"). An average over minutes then inherits a bias of up to the sawtooth
  amplitude instead of averaging it away. **[UNVERIFIED for this receiver: general behavior of quantized-PPS
  receivers]**
- Per-edge correction removes the sawtooth before the averaging. **[VERIFIED: host test, a ±10 ns, 37 s beat
  sawtooth on 5 ns jitter: the residual spread returns to the jitter alone once corrected]**

### The SX1303 latch needs the same correction

- The concentrator (SX1302/SX1303) latches its internal 32 MHz counter on a PPS edge. With a u-blox PPS on that
  input, the latched count belongs to the **actual** pulse, which is qErr away from the ideal second. Any
  software that maps the concentrator counter (and the SX1303 fine timestamps built on it) to GPS time must
  subtract the same per-pulse qErr, matched by the same second. The latch's 31.25 ns resolution is coarser than
  qErr, but the bias it leaves in an average is not. **[UNVERIFIED: follows from the latch semantics; not yet
  measured on this board]**

### Mandatory: verify the UBX checksum

- Every UBX frame ends with an 8-bit Fletcher checksum over class, id, length and payload. A reader **must**
  verify it and drop any frame that fails, before trusting any field.
- A UBX logger on an earlier project had no checksum check. Resynchronising on the two-byte sync `b5 62`, it
  landed on false headers inside other messages' payloads and wrote garbage qErr values into its logs. **[VERIFIED:
  that project's history]**
- The decoder provided for the future reader is gated on the checksum. Its tests include a planted false
  `b5 62` sync and single-bit flips. **[VERIFIED: host tests]**
- The core's ±100 ns range check is only a backstop. It cannot catch a plausible-looking garbage value.
