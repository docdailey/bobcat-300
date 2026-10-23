#!/bin/sh
# Power up / reset the SX1302 card on a Bobcat 300 G285 (sx1302_hal calls this as ./reset_lgw.sh start|stop).
#
# Matches the stock G285 firmware exactly (read from unit 1's eMMC backup, 2026-10-07). On its 4.19 kernel (sysfs base
# 0, bank*32+line) the stock boot script /etc/init.d/udev sets gpio 125 high ("#rf pwr en") once at boot, and
# /usr/bin/reset_lgw_1302.sh then cycles 122 and pulses 149. Newer kernels give gpiochips dynamic bases, so the
# numbers are rebuilt from each Rockchip bank's label.
#   125 = gpio3 line 29   RF power enable: high (stock: at boot, left high)
#   122 = gpio3 line 26   radio power: low, 1 s, high
#   149 = gpio4 line 21   SX1302 reset: pulse high then low, then released to input
# (gpio3-25, the Armbian DTB's lora_3v3 regulator, is not used: that reference is broken and stock never drives it.)

RFEN_BANK=gpio3 RFEN_LINE=29
POWER_BANK=gpio3 POWER_LINE=26
RESET_BANK=gpio4 RESET_LINE=21

die() { echo "reset_lgw: $*" >&2; exit 1; }

# sysfs number of <bank> <line>: find the gpiochip whose label is the bank (e.g. "gpio3"), add the line to its base
num() {
    for c in /sys/class/gpio/gpiochip*; do
        [ "$(cat "$c/label" 2>/dev/null)" = "$1" ] && { echo $(( $(cat "$c/base") + $2 )); return 0; }
    done
    die "no gpiochip labelled $1 (labels: $(cat /sys/class/gpio/gpiochip*/label 2>/dev/null | tr '\n' ' '))"
}

[ -d /sys/class/gpio ] || die "/sys/class/gpio missing (kernel without GPIO_SYSFS)"
RFEN=$(num $RFEN_BANK $RFEN_LINE) || exit 1
POWER=$(num $POWER_BANK $POWER_LINE) || exit 1
RESET=$(num $RESET_BANK $RESET_LINE) || exit 1

exp()   { [ -d /sys/class/gpio/gpio$1 ] || { echo "$1" > /sys/class/gpio/export; sleep 0.1; }; }
unexp() { [ -d /sys/class/gpio/gpio$1 ] && { echo "$1" > /sys/class/gpio/unexport; sleep 0.1; }; }
out()   { exp $1; echo out > /sys/class/gpio/gpio$1/direction; echo $2 > /sys/class/gpio/gpio$1/value; }

case "$1" in
    start)
        echo "SX1302 rf-enable gpio$RFEN, power gpio$POWER, reset gpio$RESET"
        out $RFEN 1; sleep 0.2
        out $POWER 0; sleep 1
        out $POWER 1; sleep 0.2
        unexp $RESET
        out $RESET 1; sleep 0.1; echo 0 > /sys/class/gpio/gpio$RESET/value; sleep 0.1
        echo in > /sys/class/gpio/gpio$RESET/direction; sleep 0.1
        ;;
    stop)
        unexp $RESET
        out $POWER 0; out $RFEN 0
        ;;
    *)
        echo "Usage: $0 {start|stop}"; exit 1 ;;
esac
exit 0
