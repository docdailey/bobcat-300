# Bobcat 300 (G285-V1.0, RK3566): OS, boot and hardware/GPIO map under Linux

Fact sheet, compiled 2026-10-22. Each bullet ends with a status tag:
**[VERIFIED: source]** = primary source (board output, code, device tree, image contents);
**[UNVERIFIED: origin]** = notes/community/inference only; **[CONTRADICTED: what disagrees]**.

"Saved live log" means output captured on unit 1 under Armbian on 2026-10-07 (`bm-facts.log`, `bringup.log`) or
2026-10-08/10 (recon notes). "Live session 2026-10-22" = read-only checks on unit 1 earlier that day ;
the units were unreachable later the same day.
"Armbian DTS" = `rk3566-bobcat.dts` decompiled from the release image; "stock DTS" = the factory kernel DTB decompiled
from a read-only eMMC backup of unit 1.

## 1. OS image

- Image: sicXnull/Bobcat-Armbian release 1.0, file `BobcatArmbian285.img.xz`, sha256
  `a75f1ca460f982ad435aa7fd8d94cb24192a64bdf855fc5610a0eb9f82195270`. **[VERIFIED: image hash in RUNBOOK.md, image read in research/boot-chain.md]**
- Userland: `Armbian-unofficial 26.02.0-trunk bookworm` (Debian 12). **[VERIFIED: /etc/os-release, saved live log]**
- Kernel: `6.18.4-current-rockchip64 #1 SMP PREEMPT Thu Jan 8 2026 aarch64`. **[VERIFIED: uname -a, saved live log]**
- `/proc/device-tree/model` = `Bobcat 285`; compatible `"bobcat,285", "rockchip,rk3566"`. **[VERIFIED: saved live log; Armbian DTS]**
- Kernel headers `linux-headers-current-rockchip64` are installed; gcc 12.2, make, mkimage and dtc are on the image, so
  out-of-tree modules and `boot.scr` can be built on the board. **[VERIFIED: read-only recon 2026-10-10, core3-bm/RECON.md]**
- `CONFIG_STRICT_DEVMEM=y`, `IO_STRICT_DEVMEM` unset, no module signing. **[VERIFIED: /proc/config.gz, RECON.md]**
- Held packages: `linux-image-current-rockchip64`, `linux-dtb-current-rockchip64`, `linux-u-boot-bobcat-29x-current`
  (they were already on hold when `bringup.sh` ran; note the U-Boot package is named for the 29x board). **[VERIFIED: bringup.log]**
- Reason to hold: the Bobcat is not a mainline board; an upgrade may replace the kernel/DTB/boot script. **[UNVERIFIED: README rationale, not tested]**
- First login `root` / `1234`, forced password change + user creation (standard Armbian). **[UNVERIFIED: README; standard Armbian behaviour]**

## 2. Boot chain (SD card)

- SD layout: Rockchip idbloader at sector 64 (DDR blob V1.05 + U-Boot SPL 2017.09, SPL boot order SD first, then
  eMMC); GPT p1 `uboot` (FIT: U-Boot + TF-A BL31, no OP-TEE); p2 FAT16 `/boot` (Image, boot.scr, dtbs); p3 ext4 root. **[VERIFIED: image read with dd/mtools/dtc, research/boot-chain.md]**
- U-Boot proper: Rockchip vendor `U-Boot 2017.09` built as `evb_rk3568` with a **Radxa ROCK 3C** device tree. **[VERIFIED: FIT contents, boot-chain.md]**
- TF-A: rkbin BL31 v1.44 (`androidboot.fwver=bl31-v1.44` on the cmdline). **[VERIFIED: /proc/cmdline, saved live log]**
- CPUs enter Linux at EL2; PSCI 1.1 over SMC. **[VERIFIED: dmesg, saved live log]**
- `boot.scr` is a custom 4-command script that **hard-codes bootargs and loads `dtb/rockchip/rk3566-bobcat.dtb`**; it
  never reads `armbianEnv.txt`. So `fdtfile=rk3566-bobcat-29x.dtb`, `extraargs=cma=256M` and Armbian overlays in
  `armbianEnv.txt` are inert. Cmdline changes = edit `boot.cmd`, regenerate with `mkimage`. **[VERIFIED: boot.cmd in image + /proc/cmdline lacks cma=, RECON.md]**
- Bootargs: `console=tty1 console=ttyS2,1500000 console=ttyFIQ0,1500000 earlycon=uart8250,mmio32,0xfe660000
  root=/dev/mmcblk0p3 rootwait rw ... keep_bootcon no_console_suspend`. No initrd. **[VERIFIED: /proc/cmdline, saved live log]**
- Root is by device name (`/dev/mmcblk0p3`), not UUID: SD = mmc0 (fe2b0000), eMMC = mmc1 (fe310000), Wi-Fi SDIO = mmc2
  (fe2c0000). **[VERIFIED: /sys/class/mmc_host, saved live log]**
- SD boots ahead of the factory eMMC with the eMMC untouched; pulling the SD restores the stock firmware. **[VERIFIED: units booted Armbian from SD with the eMMC never written (README/run notes)]**
  Which loader (eMMC's or SD's idbloader) actually runs first is not established. **[UNVERIFIED: inference in boot-chain.md]**

## 3. Debug console

- UART2 (0xFE660000, DW 8250, 24 MHz sclk), pins uart2m0 GPIO0_D1 TX / GPIO0_D0 RX, **1 500 000 8N1**: DTS
  `stdout-path = "serial2:1500000n8"`, U-Boot `baudrate=1500000`, ttyS2 at 1500000. **[VERIFIED: Armbian DTS, U-Boot env, pinmux-pins + stty, saved live log]**
- The factory firmware also uses UART2 at 1.5 Mbaud (stock U-Boot env `baudrate=1500000`, console ttyFIQ0). **[VERIFIED: stock U-Boot env from eMMC backup]**
- Older notes said 115200 8N1. **[CONTRADICTED: both stock and Armbian U-Boot envs say 1500000]**
- Adapter must do 1.5 Mbaud at 3.3 V (CP2102N/CH343/FT232R class, not PL2303). **[UNVERIFIED: no adapter session recorded]**
- Physical connector: an internal debug header ("internal micro-USB + pads" in early notes); pin order not documented. **[UNVERIFIED: community notes; FCC photo label "DEBUG"]**
- Rear micro-USB = Rockchip OTG / Maskrom. **[UNVERIFIED: community notes]**

## 4. eMMC (factory OS)

- 64 GB-class eMMC (`SLD64G`, 57.6 GiB), HS200 8-bit, appears as `mmcblk1` with `boot0`/`boot1` hw partitions. **[VERIFIED: saved live log/run notes]**
- Stock GPT: `uboot` (8 MiB offset, 4 MiB), `skyboot` (512 MiB, ext4, kernel+DTB), `update` (4 GiB ext4), `rootfs` (~53 GiB ext4). **[VERIFIED: partition table read from backup, stock/unit1/summary.txt]**
- Stock firmware: Rockchip 4.19-era kernel, DT model "Rockchip RK3566 Tiansizhihui Board", console ttyFIQ0, U-Boot
  `bootcmd=repart mmc;run ramboot;reset`. **[VERIFIED: stock DTS + U-Boot env]**
- Backup method: from Armbian, `dd if=` of boot0, boot1 and the whole disk (never mounted, never written), gzip-streamed
  off-board, sha256 compared on both ends; vendor files then read from the copy only. Dumps are not published. **[VERIFIED: emmc-pull.sh; run notes record matching hashes]**

## 5. Ethernet (GMAC1 + Motorcomm YT8512B)

- GMAC1 `ethernet@fe010000` (stmmac/dwmac-4.20a), `phy-mode = "rmii"`, `clock_in_out = "output"` (SoC drives the
  50 MHz RMII ref; no PHY crystal), PHY at MDIO 0, PHY reset GPIO4_C2 (gpio4-18) active low, delays 0/20/100 ms.
  Interface name `end0`. **[VERIFIED: Armbian DTS; gpio debugfs shows gpio4-18 "snps,reset" ACTIVE LOW]**
- Runtime: `end0` bound to `rk_gmac-dwmac`, RMII, 100 Mb/s, PTP clock registered. **[VERIFIED: live session 2026-10-22]**
- Stock DTB GMAC node is the same (rmii, output clock). **[VERIFIED: stock DTS]**
- PHY = YT8512B, phy_id 0x00000128, bound to in-tree `motorcomm` driver entry "YT8512B Fast Ethernet"; ext regs
  already correct (AFE_PLL, RMII_EN, sleep off). **[VERIFIED: live MDIO reads recorded in yt8512b-fix/README.md]**
- Symptom: autoneg freezes (partner page received, `BMSR` autoneg-complete never sets, carrier 0). Forced 10/100 gives
  carrier and clean RX frames. **[VERIFIED: live register dumps in yt8512b-fix/README.md]**
- Fix shipped: `yt8512b-phy-init.py` + oneshot service: wait for MDIO, settle, ensure ext regs, PHY soft reset
  (BMCR 0x8000) + AN restart (0x1200), escalating to a bounded deadline. `ethtool -r` alone does not work. **[VERIFIED: code in yt8512b-fix/]**
- Root-cause wording disagrees between documents: the README says the PHY is reset before the refclk is stable and a
  soft reset fixes it; later notes say a cold power-on links on its own, a warm reboot wedges it, and only a power
  cycle clears it. **[CONTRADICTED: yt8512b-fix/README.md vs later session notes 2026-10-08]**
- The proper upstream fix (`PHY_RST_AFTER_CLK_EN` on the YT8512 entries) was not built. **[VERIFIED: README; no build artifact]**

## 6. Wi-Fi / Bluetooth

- Wi-Fi: Broadcom BCM43430/1 on SDIO (mmc2, fe2c0000), `brcmfmac`. **[VERIFIED: live session 2026-10-22, wlan0 on unit 1]**
- Firmware 7.45.98.118; a board-specific NVRAM file name is missing and the driver falls back to the generic one, which
  works. **[VERIFIED: live dmesg, unit 1, 2026-10-21: "brcmfmac43430-sdio for chip BCM43430/1"]**
- DTS: `wifi_chip_type = "NM372"`, `mmc-pwrseq-simple` reset GPIO2_B1 (gpio2-9, active low), host-wake gpio2-10. **[VERIFIED: Armbian DTS; gpio debugfs "reset" gpio2-9]**
- BT: UART1 (fe650000) `brcm,bcm43438-bt`, shutdown gpio2-15, host-wake gpio2-16, device-wake gpio2-17. **[VERIFIED: Armbian DTS + gpio debugfs]**
- Unit 2's Wi-Fi module was physically damaged (drill hit the shield, cracked crystal) and fails with `mmc2: error -110
  whilst initialising SDIO card`; not a software fault. **[VERIFIED: live session 2026-10-22 error; cause per bench inspection]**

## 7. Concentrator radio: power, reset, SPI

- mPCIe-style socket card ("N504S"/"N3504S"), SX1302 + 2x SX1250. Unit 2's card reads model 0x00/0x02 = SX1302 (not SX1303). **[VERIFIED: live chip_id 2026-10-22 on unit 1 with the same card: "chip version is 0x10", "chip model ID: 0x00 -> SX1302"]**
- Stock sequence (factory eMMC): `/etc/init.d/udev` exports sysfs 125 and sets it high once at boot ("rf pwr en");
  `reset_lgw_1302.sh start` drives 122 low 1 s then high, then pulses 149 high→low and returns it to input; `stop`
  unexports 149 and drives 122 low. **[VERIFIED: stock scripts from eMMC backup]**
- Mapping (bank×32+line): 125 = **gpio3-29 (GPIO3_D5) RF power enable**, 122 = **gpio3-26 (GPIO3_D2) radio power**,
  149 = **gpio4-21 (GPIO4_C5) SX1302 reset**. **[VERIFIED: arithmetic + gpiochip bases below]**
- On this 6.18 image the gpiochip bases are still 0/32/64/96/128 (gpio0..gpio4), so the stock sysfs numbers 125/122/149
  are valid unchanged. **[VERIFIED: bringup.log gpiochip label/base listing]**
- "6.x kernels move the bases" (comment in reset_lgw.sh / README). **[CONTRADICTED: bases are static on this image; the label lookup is harmless but not needed here]**
- `reset_lgw.sh` (repo) reproduces the stock sequence with bases resolved from bank labels. **[VERIFIED: code]**
- README.md labels the lines "power gpio3-29, enable gpio3-26"; RUNBOOK/reset_lgw.sh/stock call 3-29 the RF enable
  and 3-26 the power line. **[CONTRADICTED: README naming vs stock udev comment "#rf pwr en" on 125]**
- Armbian DTS `lora-3v3-regulator` uses GPIO line 25 of phandle 0xd0 (`regulator-always-on`). In the 285 DTB phandle
  0xd0 is `usb@fd840000`, so the reference is broken; in the 29x DTB 0xd0 is gpio3 (gpio3-25). Stock never drives
  gpio3-25. **[VERIFIED: Armbian 285 + 29x DTS phandle resolution; stock scripts]**
- Socket power pins switched by gpio3-29 + gpio3-26 measure ~3.4 V. **[VERIFIED: meter on socket tails, unit 1, 2026-10-22, toggling the GPIOs]**
- Radio SPI: **SPI1** `spi@fe620000`, group spi1m1: CS0 gpio3-1 (GPIO3_A1), gpio3-17/18/19 (GPIO3_C1/C2/C3), mux
  function spi1; device `/dev/spidev1.0` → `fe620000.spi/spi1/spi1.0`. **[VERIFIED: pinmux-pins + /sys/class/spidev, saved live log; live session 2026-10-22]**
- At runtime gpio3-26 (122) and gpio3-29 (125) are exported by `reset_lgw.sh`; gpio3-25 is unclaimed; gpio4-21 (149) is unclaimed until exported. **[VERIFIED: live session 2026-10-22]**
- `spi_dev@0` node: `armbian,spi-dev`, `spi-max-frequency` 12 MHz, `spi-lsb-first` (same flags as stock's
  `rockchip,spidev`). sx1302_hal works through it regardless. **[VERIFIED: Armbian + stock DTS; 12 MHz also live session 2026-10-22]**
- Stock packet-forwarder configs name `/dev/spidev1.0`. **[VERIFIED: stock global_conf from backup]**
- On the G285 socket, SPI is on card pins 3/5/6/7 (SCK/MISO/MOSI/CS), not the RAK2287/5146 positions 45/47/49/51, so a
  RAK5146 reads 0xFF without an adapter. **[VERIFIED: logic-analyzer removal tests 2026-10-22; see socket-pinout doc]**

## 8. Broken `spi-gpio` node

- Armbian 285 DTS has a top-level `spi-gpio` (sck/miso/mosi lines 19/18/17, CS 1 and 2, two `spidev` children)
  whose GPIO phandle 0xd0 points at `usb@fd840000`; dmesg: `OF: /spi-gpio: could not get #gpio-cells for /usb@fd840000`,
  `platform spi-gpio: deferred probe pending`. It never probes and is harmless (live DT still shows it `status = okay`). **[VERIFIED: Armbian DTS + dmesg, saved live log; live session 2026-10-22]**
- Same node in the 29x DTB resolves to gpio3 (the same pins as SPI1 m1). The 285 DTB carries a stale phandle copied from
  the 29x tree. **[VERIFIED: phandle 0xd0 = gpio@fe760000 in 29x DTS]**

## 9. SARADC card-presence check

- Stock rule: card present if SARADC channel 2 ≥ 920 with gpio3-29 high; `bobcat-selftest.sh` copies it. **[VERIFIED: stock behaviour per run notes; selftest code]**
- Unit 2 read 991 with RF enable on; unit 1 read 147 with RF enable off. **[UNVERIFIED: run notes]**
- Unit 1 reads `in_voltage2_raw` ~850 with the socket **empty** and 206/309 (RF enable off/on) with a working card
  that answers on SPI: the reading goes the opposite way to the stock rule. The check is unreliable; use `chip_id`. **[VERIFIED: live session 2026-10-22]**
  **[CONTRADICTED: stock ≥ 920 rule]**
- Saradc node is `okay` in the Armbian DTS (IIO `iio:device0`). Stock adds `adc-keys` (one "menu" key) on SARADC ch0;
  the Armbian DTS has no adc-keys. **[VERIFIED: both DTS files]**

## 10. Buses, RTC, other UARTs

- I2C enabled: i2c0 (fdd40000: TCS4525 vdd_cpu @0x1c, RK809 PMIC @0x20), i2c2 (fe5b0000) and i2c4 (fe5d0000);
  `/dev/i2c-0`, `-2`, `-4` exist. **[VERIFIED: Armbian DTS + bringup.log]**
- RTC: Armbian and stock DTS both declare `haoyu,hym8563` @0x51 on **both** i2c2 and i2c4; which bus has the chip is
  unconfirmed. A CR1220 holder (FCC photo label "RTC") backs it. **[VERIFIED: DTS; chip location UNVERIFIED]**
- GNSS research notes say `pcf8563@51` on I2C4 only. **[CONTRADICTED: that is a third-party (Nebra) factory DTB; our two DTBs say hym8563 on i2c2 and i2c4]**
- UART1 = Bluetooth; UART2 = console; UART5 (fe690000, GPIO2_A1 RX / GPIO2_A2 TX) is `disabled` in both DTBs;
  `/dev/ttyS5` exists only as a placeholder. **[VERIFIED: both DTS; bringup.log ttyS listing]**
- No STTS751 temperature sensor on the G285; stock sx1302_hal fails `lgw_start` without it.
  `hal-bobcat.patch` makes the sensor optional and returns a fixed 25.0 °C (RSSI compensation), and adds a
  chip-model print to `chip_id`. Consequence: any "concentrator temperature" logged by HAL users is that constant. **[VERIFIED: patch code; sensor absence UNVERIFIED by i2cdetect]**
- No 1-Wire bus or extra temperature sensors found in either DTS. **[VERIFIED: DTS grep]**

## 11. GNSS / PPS

- No GNSS fitted. Stock forwarder configs set `gps_tty_path=/dev/ttyS5` but stock init scripts disable GPS. **[VERIFIED: stock configs/scripts]**
- No `pps-gpio` node, no `/dev/pps*`. **[VERIFIED: DTS grep + bringup.log]**
- Card pin 19 = SX1302 PPS input (RAK2287-family pinout); the carrier has no PPS source wired to it. **[UNVERIFIED: pinout inference + PPS counter stays constant]**
- PPS options used so far: a bare-metal core drives a PHC-locked pulse from a free GPIO. **[VERIFIED: core3-bm code; the production pin choice is not recorded in the repo]**

## 12. LEDs and buttons

- gpio-leds on gpio0: D3 (gpio0-27) `led-status` (trigger heartbeat), D4 (gpio0-28) `led-pwr` (on), D5 (gpio0-29) `led-eth`, D6 (gpio0-30) `led-wifi`, all active high. **[VERIFIED: Armbian DTS + gpio debugfs]**
- Stock front RGB LED on sysfs 128/129/130 = gpio4-0/1/2 (stock boot sets 0/0/1); not in the Armbian DTS. **[VERIFIED: stock /etc/init.d/udev]**
- Buttons: stock `adc-keys` "menu" on SARADC ch0; no gpio-keys in either DTS. FCC photo labels RECOVERY and RESET. **[VERIFIED: DTS; button labels UNVERIFIED]**

## 13. PTP / time

- The PHC is the **GMAC1 (stmmac) clock**, `/dev/ptp0` "stmmac ptp", not a PHY clock: HW TX/RX timestamps, 1 external
  timestamp channel, 0 periodic outputs, 0 programmable pins, `pps_available=0`, max_adj 62.5 ms/s. **[VERIFIED: PHC capability dump, saved live session 2026-10-08]**
- "YT8512B PHC" (task brief wording). **[CONTRADICTED: YT8512B has no PHC; ptp0 is the stmmac MAC clock]**
- PHC registers at GMAC1 +0xb00 (TCR 0x303, sub-second increment 32 ns from a 62.5 MHz ptp_ref). **[VERIFIED: RECON.md register reads]**
- ptp4l 3.1.1 slave (`slaveOnly`, domain 44, hybrid E2E, linreg servo) disciplines ptp0; chrony 4.3 uses
  `refclock PHC /dev/ptp0 tai` + `hwtimestamp end0`. chrony 4.3 rejects `leapseclist` (4.4+); `leapsectz right/UTC`
  suffices. **[UNVERIFIED: session notes; configs not in the repo]**
- Reported system-clock RMS ~7 ns vs the PHC. **[UNVERIFIED: chronyc output in a session log]**

## 14. Other quirks

- Reserved RAM 0x020f0000–0x0262ffff: a bare-metal image linked at 0x02000000 must stay small. **[VERIFIED: /proc/iomem]**
- `mem=2044M` frees the top 2 MiB for a carved core (requires editing `boot.cmd`). **[VERIFIED: core3-bm code + BRINGUP.md]**
- Clocks: clk_spi1 200 MHz parent; sclk_uart2 24 MHz; SD 50 MHz HS. **[VERIFIED: clk_summary, saved live log]**
- A read-only /dev/mem scan of the GPIO EXT_PORT (input level) registers shows lines that toggle on their own: gpio0-D3
  (the status LED output), gpio2-B0, gpio3-B0, gpio4-A0. Avoid those for edge capture without checking. **[VERIFIED: live session 2026-10-22]**

## Contradictions & open questions

1. **Ethernet root cause**: soft-reset-after-refclk (README) vs cold-links/warm-wedges/POR-only (later notes). Validate cold boot and a warm reboot with the service enabled.
2. **Radio line naming**: README swaps "power"/"enable" for gpio3-29/26 vs stock and RUNBOOK. Stock: 3-29 = RF power enable, 3-26 = power-cycled line.
3. **Dynamic gpiochip bases**: claimed for 6.x, but bases are bank×32 on this image; 125/122/149 work raw.
4. **SARADC ch2 ≥ 920** presence rule is inverted on unit 1 (~850 empty, 206/309 with a working card). Treat as unreliable.
5. **RTC**: hym8563 declared on both i2c2 and i2c4; which one is real? Check `i2cdetect -y 2/4` and `/dev/rtc*`.
6. **Console**: 1.5 Mbaud confirmed in configs; physical header pinout and a scope/adapter capture not recorded.
7. **Which idbloader boots first** (eMMC vs SD) is inferred, not observed.
8. **Wi-Fi firmware version and chip_id outputs** were seen in sessions but no saved log is in the repo.
9. **PTP configs** (ptp4l/chrony files) live only on the card; not in the repo.
10. **Unit identity**: notes disagree about which unit had the Ethernet fix proven (units were relabelled); describe by behaviour, not unit.
