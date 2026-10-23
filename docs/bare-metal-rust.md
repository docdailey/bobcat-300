# Fact sheet: bare-metal Rust on the Bobcat Miner 300 (G285-V1.0, RK3566)

Compiled 2026-10-22. Scope: the full bare-metal Rust firmware (branch `bm/skeleton`, directory `bare_metal/`), the
"carved core" bare-metal Rust blob that actually runs on core 3 under Linux (`core3-bm/`), the Linux-side time-transfer
logger that is deployed (`chirp-logger/phc_logd.c`), and how they relate to the truck node's bare-metal Rust firmware.

Tags: **[VERIFIED: ...]** = checked in code, docs, git history or a command run for this sheet. **[UNVERIFIED: ...]** =
only in project notes / project notes. **[CONTRADICTED: ...]** = sources disagree.

Two things are easy to conflate, so up front:
- **`bare_metal/` (full bare metal)**: replaces Linux entirely, booted by U-Boot `booti`. **Has run under QEMU only.**
- **`core3-bm/` (carved core)**: Linux keeps cores 0-2; core 3 is offlined and runs a small Rust blob started via PSCI
  CPU_ON. **This one has run on real hardware** and is part of the deployed time-transfer path.

## 1. Goals and rules

- Target: LoRa time transfer between three G285 nodes at **5-10 ns**, each validated against its own ZED-F9T (PPS +
  qErr), with three-cornered-hat analysis. [VERIFIED: bare_metal/PLAN.md, README.md]
- Modelled on the truck node's bare-metal Rust firmware (Raspberry Pi Zero 2 W), whose PPS engine measured 40-80 ns.
  [VERIFIED: PLAN.md; pps.rs header]
- Order of work: Linux (Armbian on SD) bring-up first to answer a 12-item "Linux must confirm" list, then bare metal.
  [VERIFIED: HARDWARE.md, PLAN.md]
- The factory eMMC is never written; everything runs from the Armbian microSD through its own U-Boot.
  [VERIFIED: README.md, docs/first-boot.md]
- **No-TX rule**: the concentrator never transmits from the bare-metal firmware. No TX code exists; the SX1302 driver
  can write only the OTP byte-pointer register (`WRITE_ALLOWLIST = [OTP_BYTE_ADDR]`), and writes to TX_TOP addresses
  are refused before reaching the bus. [VERIFIED: firmware/logic/src/sx1302.rs:16-38,100-125]
- `test/no-tx.sh` greps all firmware/logic sources for TX API names, TX register blocks, SX1250 TX opcodes and mux
  targets, checks the allowlist is unchanged, and self-tests by catching a planted call. Ran today: `PASS (35 source
  files clean, allowlist = OTP pointer only, guard self-test ok)`. [VERIFIED: test/README.md; ran test/run-all.sh]
- Note: the no-TX rule applies to `bare_metal/` only. The deployed Linux logger `phc_logd` **does** transmit
  (licensed amateur two-way time transfer, see §6). [VERIFIED: chirp-logger/phc_logd.c header, PONG_* defines]

## 2. Architecture of `bare_metal/` (phase 1 skeleton, built 2026-10-06)

- Crate `bobcat-bm` 0.1.0, `aarch64-unknown-none`, `panic = "abort"`; workspace member `logic` (`bobcat-logic`) holds
  host-testable pure logic (FDT, GPT, Rockchip arithmetic, SX1302 framing, PPS tracker, seqlock, NDJSON/SD log).
  Only external dep: `embedded-sdmmc` 0.10 (no_std FAT). [VERIFIED: firmware/Cargo.toml, logic/src/]
- ~7,150 lines across firmware/src, board/ and logic/src. [VERIFIED: `wc -l`]
- **Boot**: vendor U-Boot (2017.09, ROCK 3C build) `booti` -> arm64 Image header (`_head`) -> `_start` copies the
  image to its link address **0x0200_0000** if loaded elsewhere (U-Boot loads at `kernel_addr_r` 0x00a80000) ->
  EL2->EL1 drop (EL3/EL2/EL1 entry all handled) -> VBAR, stacks, .bss -> `kmain`. QEMU build links at 0x4100_0000,
  14 MiB above where QEMU loads it, so every QEMU boot exercises self-relocation.
  [VERIFIED: src/boot.s header; build.rs:8; HARDWARE.md; test/README.md]
- MMU identity map + caches; DRAM below 2 MiB (TF-A, SCMI) left unmapped; firmware maps 2 MiB..1 GiB.
  [VERIFIED: HARDWARE.md "Memory"; first-boot.md §5]
- **SMP**: PSCI CPU_ON over SMC (TF-A BL31) with targets from the FDT `/cpus` (MPIDR Aff1 = core on the A55
  cluster); each core keeps its logical id in TPIDR_EL1. [VERIFIED: src/smp.rs:1-110; src/boot.s]
- **Core roles**: core 0 = main loop (console, SD, radio); core 1 = idle, reserved for concentrator RX polling in
  phase 2; core 2 = idle; **core 3 = PPS busy-poll engine** with DAIF masked. [VERIFIED: src/app.rs:3-4; src/pps.rs:32]
- **GIC**: GICv3 (GIC-600), GICD 0xFD40_0000, GICR 0xFD46_0000 stride 0x20000; one PPI (EL1 physical timer, INTID 30)
  exercised end to end. [VERIFIED: board/rk3566.rs:21-23; src/timer.rs:57-71]
- **Timer**: ARM generic counter at 24 MHz (41.7 ns tick). [VERIFIED: HARDWARE.md; pps.rs header]
- **PPS engine (core 3)**: ported from the truck firmware. Sleeps with WFE on the timer event stream (~10.7 us) until
  the predicted edge minus uncertainty, then spins on the GPIO EXT_PORT register; edge stamped at the midpoint of the
  last-low/first-high window; sub-tick interpolation with the PMU cycle counter, recalibrated before and after each
  edge so DVFS cannot bias it. Under QEMU the PMU is off (host preemption makes counter/cycle pairs non-atomic).
  [VERIFIED: src/pps.rs:1-50]

## 3. Drivers: implemented vs stubbed

| Driver | State | Tag |
|---|---|---|
| UART2 (DW 8250, 0xFE66_0000) | Written; inherits U-Boot's rate (1,500,000 8N1, 24 MHz, divisor 1); console mirrored to SD log. Not run on hardware (QEMU uses PL011). | [VERIFIED: board/rk3566.rs:34-38; README.md; test/README.md] |
| GPIO / pinmux / CRU | Written (v2 write-masked GPIO, GRF/PMU_GRF iomux). Hardware-only, untested. | [VERIFIED: PLAN.md phase 1; HARDWARE.md] |
| SPI1 (0xFE62_0000) | Written; clk_spi1 switched to xin24m, /12 = **2 MHz**. Header says "HARDWARE ONLY, NOT YET RUN". | [VERIFIED: src/spi.rs:6-7,59-73] |
| SX1302 identify | Power/reset sequence, version register 0x5606 (=0x10), OTP model byte (SX1302 vs SX1303), EUI -> `chip_id` record. Tested in QEMU against `FakeSx1302` behind the same SPI trait. | [VERIFIED: src/radio.rs:1-12; logic/src/sx1302.rs:157-275] |
| SD/FAT logging | DW MSHC (SDMMC0) driver + `embedded-sdmmc`; NDJSON under `/BOBCAT/` on GPT partition 2 only; opt-in (never creates the folder); append-only; block-level fence to the FAT partition. QEMU uses virtio-blk. | [VERIFIED: src/sdlog.rs:1-12,39,91-93; test/README.md] |
| PPS input pin | **Not decided**: `PPS_PIN: Option<Pin> = None`; engine not started on hardware. | [VERIFIED: board/rk3566.rs:76; app.rs:214-223] |
| Ethernet, Wi-Fi, SX1302 RX, I/Q capture | Not implemented (phases 2-3). | [VERIFIED: PLAN.md] |

## 4. Test strategy and results (run for this sheet, 2026-10-22, local only)

- `cargo test -p bobcat-logic --target aarch64-apple-darwin`: **41 passed, 0 failed**. [VERIFIED: command run]
- `test/run-all.sh` (exit 0): host 41/41; `no-tx.sh` PASS; `qemu-boot.sh` **PASS (27 checks)**; `qemu-sd.sh` **PASS
  (21 checks)**; `qemu-panic.sh` **PASS (6 checks)**. [VERIFIED: command run]
- QEMU stand-in: `-M virt,gic-version=3,virtualization=on -cpu cortex-a55 -smp 4 -m 1G`: EL2 entry with FDT in x0,
  PSCI over SMC, GICv3. [VERIFIED: firmware/Makefile; test/README.md]
- PPS test is load-independent: the fake GPS pin is a pure function of the guest counter (1 s + 37 ppm, a spike
  after edge 20, no pulses at seconds 30-32); `pps-truth.py` checks every reported edge against that schedule.
  [VERIFIED: test/README.md; src/pps.rs:743-750; commit 2f98e2e]
- SD suite: GPT card image laid out like the Armbian card, `fsck.fat -n` clean after a kill, partitions 1/3 and the
  FAT boot sector untouched, no `/BOBCAT` = card byte-identical. [VERIFIED: test/README.md]
- Not emulatable: DW UART, Rockchip GPIO/IOMUX/CRU, SPI1, DW MSHC, real SX1302, PPS pin. [VERIFIED: README.md]

## 5. Status: what has run where

- `bare_metal/` firmware: **QEMU only**. README: "Skeleton, built 2026-10-06; runs under QEMU only so far."
  first-boot.md: "Everything here has run under QEMU `virt` only." No run log of a hardware boot exists in
  `docs/runs/` (only a Linux session). [VERIFIED: README.md; docs/first-boot.md; ls docs/runs]
- Last commit on the branch: `1dd750e` (unit 1 notes). 13 commits total, all 2026-10-06/07.
  [VERIFIED: `git log --oneline`]
- Board facts confirmed under Linux on unit 1 (2026-10-06/07): entry at **EL2**; PSCI 1.1; GICv3 addresses as above;
  24 MHz timer; RAM 0x0020_0000-0x7fff_ffff; console UART2 at 1.5 Mbaud; radio SPI = SPI1 CS0; no onboard GNSS.
  [VERIFIED: docs/runs/2026-10-07-unit1/README.md]
- Radio power, stock sequence (read from the eMMC backup): GPIO3_D5 (gpio3-29, "rf pwr en") high at boot; then
  gpio3-26 cycled (low 1 s, high) and gpio4-21 pulsed (reset). The DTB's gpio3-25 `lora_3v3` reference is unused.
  [VERIFIED: docs/runs/2026-10-07-unit1/README.md; board/rk3566.rs:55-58]
- Unit 1 radio read "not detected" (version 0x00) **with the RF enable off**, so inconclusive. [VERIFIED: same README]
- Unit 2: version 0x10, model **SX1302** (not SX1303); OTP model/EUI readable only after `lgw_start` (radio clock up);
  HAL needs a patch because the G285 has no STTS751. [UNVERIFIED: project notes 2026-10-07]
- Ethernet (GMAC1, RMII, Motorcomm YT8512B PHY) would not link on unit 1. [VERIFIED: unit1 README]
  [CONTRADICTED: later project notes say a unit runs wired-only on Ethernet as of 2026-10-21, so this was resolved
  later; resolution not documented in the sources read]
- Image footprint: QEMU build `__image_end - start` = 0xCA000 (808 KiB incl. stacks), under the ~960 KiB gap before
  the reserved region at 0x020F_0000 found on unit 1. Hardware build flat binary 178,128 B. No link-time assert
  enforces the limit. [VERIFIED: llvm-nm; ls -l; unit1 README]

## 6. The path actually deployed: Linux + carved core 3 + `phc_logd`

### 6a. `core3-bm`: carved-core Rust blob (runs on hardware)
- Linux boots with `mem=2044M`; cpu3 is offlined; `core3ctl load` writes the blob to 0x7FE0_0000; a small kernel
  module issues PSCI CPU_ON. Shared region at 0x7FF0_0000 (seqlocked heartbeat, 1024-slot edge ring). `memmap=` is
  x86-only, and this image's boot.scr hardcodes bootargs (armbianEnv.txt is inert). [VERIFIED: core3-bm/README.md;
  commit 6599e0a]
- Phase A (2026-10-10/11): EL2->EL1 drop, identity MMU mapping only the carve + GPIO banks, CNTVCT-stamped GPIO
  edges, park -> CPU_OFF for rebootless reload. Bring-up session 2026-10-11: "all gates passed, blob resident";
  systemd autostart unit gates on the `/proc/iomem` carve check and fails closed to 4-core Linux.
  [VERIFIED: commits 6599e0a, 81c1733]
- Phase B / ABI v3 (2026-10-11): blob reads the PHC directly (GMAC1 system-time registers, 32 ns steps at the
  62.5 MHz PTP ref, disciplined by ptp4l), keeps a CNTVCT->PHC map refreshed every ~50 us, stamps edges in PHC time,
  and drives a **PHC-locked pulse output** to feed the SX1302's PPS input. 11 host ABI tests.
  [VERIFIED: core3-bm/README.md; commit b40e7dd]
- This contradicts the earlier research recommendation (§7). [see Contradictions]

### 6b. `phc_logd` (Linux, C, sx1302_hal)
- Two-way time transfer (TWTT) between the truck node (bare-metal Rust, SX1276) chirping on **even** UTC seconds and
  the Bobcat replying ("pong", format 0xC3) on **odd** seconds. RX: 904.6 MHz / BW500 / **SF9**; chirp format 0xC1.
  Pong TX: 923.3 MHz, BW500, **SF9, CR 4/5**, 27 dBm. [VERIFIED: phc_logd.c:323-330,560-582; truck
  firmware/logic/src/lora.rs:143,436,636,712]
- Delay math: windowed least-squares fit of SX1302 `count_us` <-> `/dev/ptp0` (ptp4l-disciplined, TAI), int32 deltas
  for wrap safety, integer-ns so it is ready for SX1303 `ftime`. Logs RSSI, SNR, CFO, concentrator temperature.
  [VERIFIED: phc_logd.c header; chirp-logger/README.md]
- Pong keying evolution (all measured at the truck, ~300 ns RxDone brackets):
  - Stage-then-trigger fire: arrival spread sd **1259 us -> 58 us**; 58/58 received (2026-10-10). [VERIFIED: commit 19a154a]
  - Fire-lead walk #3 (SF8, immediate trigger): truck rx_fine mean **-562 ns, sd 2.97 us, n=1495** (2026-10-11).
    [VERIFIED: commit 39c60fb]
  - SX1302 **counter-match (timestamped) trigger does fire**; the earlier "stuck SCHEDULED" verdict was a misread of
    TX_STATUS. It removed the immediate path's ~200 us late tail (0/110 past +30 us vs ~16%). [VERIFIED: commit 571a2fe]
  - Two-sided result with counter match: core mean **+1.0 us, sd 3.0 us** (n=110, 87%); ~10% early skirt to -85 us
    traced to count<->PHC fit extrapolation. [VERIFIED: commit 3d5ca5e]
  - SF9 hardware-trail walk #3: core at **+4.7 us, sd 2.6 us** (n=50). [VERIFIED: phc_logd.c:77 comment; commit bffad6c]
- **GPS-keyed pong** (`pong.gps`, 2026-10-11/12): stage with the HAL's ON_GPS trigger so the SX1302 starts the packet
  in hardware ~1497 us after the core-3 PHC pulse reaches its PPS pin; no Linux on the keying path. Committed with the
  flag **off**; requires a wire from an RK3566 GPIO to the concentrator socket PPS pin. [VERIFIED: commit 2a58037;
  phc_logd.c:93-110] Dry run without the wire: 7/7 pongs fell back ("gpsmiss") and were received.
  [UNVERIFIED: project notes 2026-10-12] Whether the wire was ever fitted and GPS mode enabled: no evidence found.
- Part 97 station ID every 300 s on the pong channel. [VERIFIED: phc_logd.c:84-87; commit a0d1e33]
- Later aggregate numbers (project notes, not re-measured): Bobcat RX chirp arrival vs even second, mean -4.73 us,
  sd 1.42 us, n=1799 (2026-10-12); 798/802 chirps received, delay median -5.4 us (2026-10-17).
  [UNVERIFIED: project notes / project notes; DB not queried]

## 7. Key lessons

- **SX1302 cannot transmit CR 4/8**: the TX FSM never leaves EMITTING; CR 4/5 fixes it. It receives CR 4/8 fine.
  [VERIFIED: commit c820719; phc_logd.c:71-76]
- **Fine timestamp (`ftime`) needs an SX1303**; on the SX1302 the HAL refuses it, leaving `count_us` (1 us, ~2.5 us
  per-packet jitter in practice). An SX1303 card (RAK5146) is the planned upgrade. [VERIFIED (plan + ~2.5 us):
  chirp-logger/README.md "TODO when SX1303 lands"] [UNVERIFIED (exact HAL error text): project notes 2026-10-08]
- **Legacy timestamp correction**: without ftime, the SX1302 latches the counter when decoding finishes and the HAL's
  `legacy_timestamp_correction()` subtracts a modelled pipeline delay so `count_us` means end-of-packet; a few-us
  error in that model explains a constant ~-4.5 us offset vs the truck's directly measured TxDone.
  [UNVERIFIED: project notes 2026-10-10; HAL source not available locally to confirm]
- The board's factory TX gain LUT must be loaded in full (16 rows, 12-27 dBm); with one row every power request gave
  22 dBm. [VERIFIED: commit bdc5fa6]
- Counter-match keying vs software trigger: the jitter was the ~30 syscall-spaced staging writes, not wake timing;
  the state-machine reset must immediately precede the trigger (single-write fire: 0/86 received).
  [VERIFIED: commit 19a154a]
- The SX1302 has no RxDone edge; time comes from RX-buffer metadata the host polls over SPI. [VERIFIED: consistent
  with phc_logd.c fit design] 
- Radio "not detected" reads are meaningless with the RF enable (gpio3-29) off. [VERIFIED: unit1 README]
- Full Rockchip AMP is not available on this stack (needs closed rkbin BL31 SIP + vendor U-Boot/kernel).
  [VERIFIED: research/amp-vs-baremetal.md]

## 8. Relation to the truck node's bare-metal Rust firmware

- Shared lineage: `bare_metal/` boot.s, PPS engine and logic (FDT/seqlock/SD log) and `core3-bm` boot/MMU/seqlock
  are ported from it. [VERIFIED: pps.rs header; core3-bm/README.md; commit e44f2e8]
- Truck side: SX1276, chirp 0xC1 on even seconds (SF9/CR4/8 since its v20), listens for 0xC3 pong on odd seconds;
  TxDone captured on a GPIO by its core 3. [VERIFIED: truck lora.rs:14,143,281,540,636,712]
- Truck TxDone vs PPS second ~ -5..+26 ns mean, ~85-100 ns sd. [UNVERIFIED: project notes 2026-10-12]

## 9. What's next (as documented)

- `bare_metal/` phase 1 on hardware: by-hand `booti` from the U-Boot prompt (docs/first-boot.md), then phase 2
  (receive-only SX1302 via libloragw behind a C shim + Rust FFI, every TX entry compiled out, STTS751 stubbed, >=32 KiB
  stack) and phase 3 (I/Q via VICAP DMA, Ethernet). [VERIFIED: PLAN.md; first-boot.md]
- Choose and wire a PPS pin (to the RK3566 and the socket PPS pin). [VERIFIED: HARDWARE.md; pps-path.md referenced]
- SX1303 (RAK5146) swap and `ftime` read in `phc_logd`. [VERIFIED: chirp-logger/README.md TODO]
- Populate the G285's unpopulated GNSS footprint on a spare unit. [VERIFIED: master commits 7246dae, 5cbd411]

## Contradictions & open questions

1. **Research said "full bare metal, not AMP"; what shipped is a carved-core hybrid.** `amp-vs-baremetal.md` rejects
   Rockchip's AMP SDK (correctly: closed BL31 SIP), but the deployed `core3-bm` is a different, home-made AMP (mem=
   carve + PSCI CPU_ON from a kernel module) under mainline Linux. The full `bare_metal/` image has not booted on a
   board since 2026-10-07. The hybrid is the working path.
2. **Stale comments**: `firmware/Cargo.toml` says the QEMU fake GPS PPS runs "on core 2"; `pps.rs`/`app.rs` put the
   engine on core 3. `phc_logd.c` header says RX is SF8; code configures SF9 (since 2026-10-11).
3. **Ethernet**: unit-1 notes say no link; later notes have units running wired. A PHY reset service was added (repo `yt8512b-fix/`, 2026-10-08); the exact root cause is still disputed (see the OS sheet, Ethernet section).
4. **GPS-keyed pong**: code exists, flag committed off; no evidence the PPS wire was fitted or the mode run live.
5. **The ~4.5 us RX offset / legacy-correction explanation** is only in project notes; confirm against the
   HAL's `loragw_sx1302_timestamp.c`.
6. **Deployed `phc_logd` may differ from the repo** (last repo commit 2026-10-11/12; device not inspected).
7. No link-time assert keeps the image below the reserved region at 0x020F_0000.
