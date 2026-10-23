#!/bin/sh
# chip_id every 2 s for 10 min: each run powers up, resets, and reads the version/EUI over SPI1 (card answers on MISO)
cd /opt/sx1302_hal/util_chip_id
end=$(( $(date +%s) + 600 ))
while [ $(date +%s) -lt $end ]; do timeout 15 ./chip_id -d /dev/spidev1.0 2>&1 | grep -E "version" ; sleep 2; done
